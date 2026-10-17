# agent: claude-code  2026-10-17
"""Score a harness on a set of tasks: k samples each, run in parallel, cached on disk so re-runs are free."""
from __future__ import annotations

import hashlib
import json
import math
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean

from .config import Harness
from .suite import Task
from .team import Outcome, run_task

CODE_VERSION = "2"  # bump when prompts, token budgets or scoring change, so old cached runs are not reused
MAX_ERROR_RATE = 0.25
TASK_RETRIES = 2  # a run that ends in an error (dropped connection, bad reply) is tried again before it counts


class EvalFailed(RuntimeError):
    pass


def task_fingerprint(t: Task) -> str:
    return hashlib.sha1((t.spec + "\x00" + "\x00".join(t.tests)).encode()).hexdigest()[:10]


CACHE_PATH = Path(__file__).resolve().parents[2] / "runs" / "cache.jsonl"


def harness_fingerprint(h: Harness) -> str:
    """Identifies everything that changes behaviour (not the version number or receipts)."""
    body = json.dumps({"m": h.models, "b": h.base_instruction, "r": [r["text"] for r in h.rules], "t": h.team},
                      sort_keys=True)
    return hashlib.sha1(body.encode()).hexdigest()[:16]


class Cache:
    def __init__(self, path: Path | None = CACHE_PATH):
        self.path, self.lock, self.data = path, threading.Lock(), {}
        if path and path.exists():
            for line in path.read_text().splitlines():
                try:
                    rec = json.loads(line)
                    self.data[rec["key"]] = rec["outcome"]
                except (ValueError, KeyError):
                    pass

    def get(self, key: str) -> Outcome | None:
        d = self.data.get(key)
        if not d:
            return None
        d = dict(d)
        d["usage"] = [tuple(u) for u in d.get("usage", [])]
        return Outcome(**d)

    def put(self, key: str, o: Outcome) -> None:
        if o.error:  # never cache failures
            return
        with self.lock:
            self.data[key] = asdict(o)
            if self.path:
                self.path.parent.mkdir(exist_ok=True)
                with self.path.open("a") as f:
                    f.write(json.dumps({"key": key, "outcome": asdict(o)}) + "\n")


@dataclass
class Eval:
    harness_version: int
    tasks: dict  # id -> Task
    outcomes: list  # list[Outcome]

    def task_scores(self) -> dict[str, float]:
        by: dict[str, list[float]] = {}
        for o in self.outcomes:
            by.setdefault(o.task_id, []).append(o.score)
        return {k: mean(v) for k, v in by.items()}

    def mean(self, *splits: str, family: str | None = None) -> float:
        s = self.task_scores()
        ids = [i for i in s if (not splits or self.tasks[i].split in splits)
               and (family is None or self.tasks[i].family == family)]
        return mean(s[i] for i in ids) if ids else float("nan")

    def overconfidence(self, *splits: str) -> float:
        """Share of runs where the team said 'done' but the hidden tests disagreed."""
        os_ = [o for o in self.outcomes if not splits or self.tasks[o.task_id].split in splits]
        return sum(o.overconfident for o in os_) / len(os_) if os_ else float("nan")

    @property
    def cost(self) -> float:
        return sum(o.cost for o in self.outcomes)

    def errors(self) -> int:
        return sum(1 for o in self.outcomes if o.error)


def paired_delta(new: Eval, old: Eval, *splits: str) -> tuple[float, float]:
    """Mean per-task score change on the same tasks, and its standard error."""
    a, b = new.task_scores(), old.task_scores()
    ids = [i for i in a if i in b and (not splits or new.tasks[i].split in splits)]
    if not ids:
        return 0.0, 0.0
    d = [a[i] - b[i] for i in ids]
    se = (sum((x - mean(d)) ** 2 for x in d) / (len(d) - 1)) ** 0.5 / math.sqrt(len(d)) if len(d) > 1 else 0.0
    return mean(d), se


def run_eval(llm, h: Harness, tasks: list[Task], k: int = 3, workers: int = 8, cache: Cache | None = None,
             progress=None, sample_offset: int = 0) -> Eval:
    """`sample_offset` picks a different range of sample numbers, i.e. fresh runs instead of cached ones."""
    fp = harness_fingerprint(h)
    jobs = [(t, s) for t in tasks for s in range(sample_offset, sample_offset + k)]

    def one(job):
        t, s = job
        key = f"{CODE_VERSION}:{fp}:{task_fingerprint(t)}:{s}"
        o = cache.get(key) if cache else None
        if o is None:
            o = run_task(llm, h, t, s)
            for _ in range(TASK_RETRIES):
                if not o.error:
                    break
                o = run_task(llm, h, t, s)  # recover: try again; only a run that keeps failing counts as failed
            if cache:
                cache.put(key, o)
        if progress:
            progress(o)
        return o

    with ThreadPoolExecutor(max_workers=workers) as ex:
        outcomes = list(ex.map(one, jobs))
    bad = [o for o in outcomes if o.error]
    if len(bad) > MAX_ERROR_RATE * len(outcomes):
        raise EvalFailed(f"{len(bad)} of {len(outcomes)} runs failed with an error, e.g. {bad[0].error}. "
                         "Check the key, the model ids (rah models) and the rate limits.")
    return Eval(h.version, {t.id: t for t in tasks}, outcomes)
