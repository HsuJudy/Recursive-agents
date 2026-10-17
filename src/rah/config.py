# agent: claude-code  2026-10-17
"""The harness: everything the system is allowed to rewrite about itself. The models stay fixed; this changes.

A harness is a base instruction, a list of rules, and the team settings. Each change is one "unit":
a rule, or a team setting that differs from its default. Every kept unit carries a receipt (its measured effect).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path

import yaml

MAX_RULE_CHARS = 200

DEFAULT_MODELS = {
    "builder": "nvidia/Nemotron-3-Nano-30B-A3B",
    "verifier": "deepseek-ai/Deepseek-V4-Flash",
    "analyst": "deepseek-ai/DeepSeek-V4-Pro",
    "proposer": "deepseek-ai/DeepSeek-V4-Pro",
}

TEAM_DEFAULTS = {"self_tests": True, "verifier": False, "edge_cases": False, "max_attempts": 1}
TEAM_CHOICES = {"self_tests": (True, False), "verifier": (True, False), "edge_cases": (True, False),
                "max_attempts": (1, 2, 3, 4)}

BASE_INSTRUCTION = (
    "You are a careful Python programmer. Follow the task text exactly. Write the function, then write your own "
    "assert-based tests for it."
)


class ChangeError(ValueError):
    pass


@dataclass
class Harness:
    version: int = 0
    models: dict = field(default_factory=lambda: dict(DEFAULT_MODELS))
    base_instruction: str = BASE_INSTRUCTION
    rules: list = field(default_factory=list)  # [{"id": "R1", "text": "..."}]
    team: dict = field(default_factory=lambda: dict(TEAM_DEFAULTS))
    receipts: dict = field(default_factory=dict)  # unit key -> evidence dict
    next_rule: int = 1

    # ---- units --------------------------------------------------------------------------
    def units(self) -> list[str]:
        u = [f"rule:{r['id']}" for r in self.rules]
        u += [f"team:{k}" for k, v in self.team.items() if v != TEAM_DEFAULTS[k]]
        return u

    def describe(self, unit: str) -> str:
        kind, name = unit.split(":", 1)
        if kind == "rule":
            return next(r["text"] for r in self.rules if r["id"] == name)
        return f"team.{name} = {self.team[name]}"

    # ---- changes (always return a new Harness; never mutate) ----------------------------
    def with_change(self, change: dict) -> "Harness":
        h = copy.deepcopy(self)
        kind = change.get("kind")
        if kind == "add_rule":
            text = str(change.get("text", "")).strip()
            if not text:
                raise ChangeError("empty rule")
            if len(text) > MAX_RULE_CHARS:
                raise ChangeError(f"rule is {len(text)} characters; the limit is {MAX_RULE_CHARS}")
            if any(r["text"].lower() == text.lower() for r in h.rules):
                raise ChangeError("duplicate rule")
            h.rules.append({"id": f"R{h.next_rule}", "text": text})
            h.next_rule += 1
        elif kind == "set_team":
            key, value = change.get("key"), change.get("value")
            if key not in TEAM_CHOICES or value not in TEAM_CHOICES[key]:
                raise ChangeError(f"bad team setting {key}={value!r}")
            if h.team[key] == value:
                raise ChangeError("no change")
            h.team[key] = value
        else:
            raise ChangeError(f"unknown change kind {kind!r}")
        h.version += 1
        return h

    def without_unit(self, unit: str) -> "Harness":
        h = copy.deepcopy(self)
        kind, name = unit.split(":", 1)
        if kind == "rule":
            h.rules = [r for r in h.rules if r["id"] != name]
        else:
            h.team[name] = TEAM_DEFAULTS[name]
        h.receipts.pop(unit, None)
        h.version += 1
        return h

    def with_models(self, **models: str) -> "Harness":
        h = copy.deepcopy(self)
        h.models.update(models)
        return h

    # ---- text the builder sees ----------------------------------------------------------
    def system_prompt(self) -> str:
        out = [self.base_instruction]
        if self.rules:
            out.append("Rules learned from past mistakes (follow all of them):")
            out += [f"- {r['text']}" for r in self.rules]
        return "\n".join(out)

    # ---- files --------------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {"version": self.version, "models": self.models, "base_instruction": self.base_instruction,
                "rules": self.rules, "team": self.team, "receipts": self.receipts, "next_rule": self.next_rule}

    @classmethod
    def from_dict(cls, d: dict) -> "Harness":
        h = cls()
        h.version = d.get("version", 0)
        h.models = {**DEFAULT_MODELS, **d.get("models", {})}
        h.base_instruction = d.get("base_instruction", BASE_INSTRUCTION)
        h.rules = list(d.get("rules", []))
        h.team = {**TEAM_DEFAULTS, **d.get("team", {})}
        h.receipts = dict(d.get("receipts", {}))
        h.next_rule = d.get("next_rule", len(h.rules) + 1)
        return h

    def save(self, path: str | Path) -> None:
        Path(path).write_text("# agent: claude-code  2026-10-17\n" + yaml.safe_dump(self.to_dict(), sort_keys=False,
                                                                                    width=100))

    @classmethod
    def load(cls, path: str | Path) -> "Harness":
        return cls.from_dict(yaml.safe_load(Path(path).read_text()) or {})
