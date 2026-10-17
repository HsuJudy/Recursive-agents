# agent: claude-code  2026-10-17
"""Model access: Crusoe Managed Inference (OpenAI-compatible) with retries, a call cap and cost tracking.

`StubLLM` has the same interface and needs no key; it is used for tests and for the offline dry run.
"""
from __future__ import annotations

import os
import random
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# USD per 1M tokens (input, output), from Crusoe's hackathon guide. Unknown models count as 0.
PRICES: dict[str, tuple[float, float]] = {
    "deepseek-ai/Deepseek-V4-Flash": (0.14, 0.28),
    "deepseek-ai/DeepSeek-V4-Pro": (1.74, 3.48),
    "google/gemma-4-31b-it": (0.14, 0.40),
    "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B": (0.05, 0.20),
    "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B": (0.30, 2.40),
    "openai/gpt-oss-120b": (0.05, 0.20),
    "zai-org/GLM-5.3-Flash": (0.15, 0.50),
}

DEFAULT_BASE_URL = "https://api.inference.crusoecloud.com/v1"


class CallCapExceeded(RuntimeError):
    pass


@dataclass
class Reply:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


def load_env(path: str | Path | None = None) -> None:
    """Read KEY=VALUE lines from .env into os.environ (never overrides, never prints)."""
    p = Path(path) if path else Path(__file__).resolve().parents[2] / ".env"
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("'\""))


def clean(text: str) -> str:
    """Drop hidden-reasoning blocks some models put in the visible text."""
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    return re.sub(r"<think>.*$", "", text, flags=re.S).strip()  # an unclosed block means the answer never came


class Meter:
    """Thread-safe counters for calls, tokens and cost."""

    def __init__(self, max_calls: int | None = None):
        self._lock = threading.Lock()
        self.max_calls = max_calls
        self.calls = 0
        self.tokens: dict[str, list[int]] = {}

    def record(self, model: str, prompt: int, completion: int) -> None:
        with self._lock:
            t = self.tokens.setdefault(model, [0, 0])
            t[0] += prompt
            t[1] += completion

    def reserve_call(self) -> None:
        with self._lock:
            if self.max_calls is not None and self.calls >= self.max_calls:
                raise CallCapExceeded(f"call cap of {self.max_calls} reached")
            self.calls += 1

    def cost(self) -> float:
        with self._lock:
            return sum(
                p * PRICES.get(m, (0, 0))[0] / 1e6 + c * PRICES.get(m, (0, 0))[1] / 1e6
                for m, (p, c) in self.tokens.items()
            )

    def snapshot(self) -> tuple[int, float]:
        return self.calls, self.cost()


class CrusoeLLM(Meter):
    def __init__(self, max_calls: int | None = None):
        load_env()
        super().__init__(max_calls if max_calls is not None else int(os.environ.get("RAH_MAX_CALLS", "3000")))
        key = os.environ.get("CRUSOE_API_KEY", "")
        if not key or key.startswith("paste-"):
            raise RuntimeError("CRUSOE_API_KEY is not set. Copy .env.example to .env and add your key.")
        from openai import OpenAI

        self.client = OpenAI(
            base_url=os.environ.get("CRUSOE_BASE_URL", DEFAULT_BASE_URL), api_key=key, timeout=120, max_retries=0
        )

    def chat(self, model: str, messages: list[dict], max_tokens: int = 2048, temperature: float = 0.0,
             thinking: bool = False) -> Reply:
        extra = {"chat_template_kwargs": {"thinking": True}} if thinking else None
        delay = 1.0
        for attempt in range(7):
            self.reserve_call()  # every try counts against the cap, retries included
            try:
                r = self.client.chat.completions.create(
                    model=model, messages=messages, max_tokens=max_tokens, temperature=temperature,
                    **({"extra_body": extra} if extra else {}),
                )
                u = r.usage
                pt, ct = (u.prompt_tokens, u.completion_tokens) if u else (0, 0)
                self.record(model, pt, ct)
                return Reply(clean(r.choices[0].message.content or ""), pt, ct)
            except Exception as e:  # rate limit, overload, network: back off and retry; anything else is final
                status = getattr(e, "status_code", None)
                transient = status in (429, 500, 502, 503, 504) or type(e).__name__ in (
                    "APIConnectionError", "APITimeoutError")
                if not transient or attempt == 6:
                    raise
                time.sleep(min(delay, 30) + random.random())
                delay *= 2
        raise RuntimeError("unreachable")


class StubLLM(Meter):
    """Offline stand-in. `handler(model, messages) -> str`. Results from it are never model results."""

    def __init__(self, handler: Callable[[str, list[dict]], str], max_calls: int | None = None):
        super().__init__(max_calls)
        self.handler = handler

    def chat(self, model: str, messages: list[dict], max_tokens: int = 2048, temperature: float = 0.0,
             thinking: bool = False) -> Reply:
        self.reserve_call()
        text = self.handler(model, messages)
        n = sum(len(m["content"]) for m in messages) // 4
        self.record(model, n, len(text) // 4)
        return Reply(text, n, len(text) // 4)
