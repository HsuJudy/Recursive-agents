# agent: claude-code  2026-10-17
"""Demo-readiness scorecard: does this repo show what the hackathon judges look for?

Seven criteria, each backed by checks that actually run the code (offline, free, no key, no AI judge):
autonomy, delegation, persistence, recovery, long-running loop, required stack, clear demo.

Every run is appended to runs/judge_history.jsonl. `--gate` refuses a change that makes any previously passing
check fail or lowers the overall score. That is the keep-or-reject rule for improving the repo itself.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from .config import Harness
from .evaluate import Cache, EvalFailed, run_eval
from .llm import DEFAULT_BASE_URL, PRICES, CallCapExceeded, StubLLM
from .loop import Log, ablate, improve
from .stub import DECOY, OfflineModel
from .suite import load_suite, select

ROOT = Path(__file__).resolve().parents[2]
HISTORY = ROOT / "runs" / "judge_history.jsonl"

CRITERIA = ["autonomy", "delegation", "persistence", "recovery", "long_running", "stack", "demo"]


@dataclass
class Check:
    criterion: str
    name: str
    passed: bool
    detail: str


def _quiet(_):
    return None


def _pipeline(tmp: Path, rounds: int = 4, verifier: bool = False, models_seen: set | None = None, run_id="judge"):
    """The whole self-improvement pipeline on the offline stand-in. Returns (h0, h1, h2, log)."""
    om = OfflineModel()

    def handler(model, messages):
        if models_seen is not None:
            models_seen.add(model)
        return om(model, messages)

    llm = StubLLM(handler)
    tasks = load_suite()
    h0 = Harness().with_change({"kind": "add_rule", "text": DECOY})
    if verifier:
        h0.team["verifier"] = True
    log = Log(run_id, path=tmp / "decisions.jsonl", emit=_quiet)
    vdir = tmp / "versions" / run_id
    vdir.mkdir(parents=True, exist_ok=True)
    h0.save(vdir / "v0.yaml")
    h1, _ = improve(llm, h0, tasks, rounds, 1, Cache(None), log, save_dir=vdir)
    h2, _ = ablate(llm, h1, tasks, 1, Cache(None), log)
    return h0, h1, h2, log


# ---- the checks ---------------------------------------------------------------------------------------------
def check_autonomy(tmp: Path) -> list[Check]:
    src = "\n".join(p.read_text() for p in (ROOT / "src" / "rah").glob("*.py") if p.name != "judge.py")
    asks = re.findall(r"(?<![\w.])input\(", src)
    _, _, _, log = _pipeline(tmp / "a")
    return [
        Check("autonomy", "never asks a human for input", not asks, f"{len(asks)} input() calls in src"),
        Check("autonomy", "whole pipeline runs start to finish unattended", len(log.decisions) > 0,
              f"{len(log.decisions)} decisions made with no human input"),
    ]


def check_delegation(tmp: Path) -> list[Check]:
    h = Harness.load(ROOT / "harness.yaml")
    roles = [h.models[r] for r in ("builder", "verifier", "proposer")]
    seen: set = set()
    _pipeline(tmp / "d", verifier=True, models_seen=seen)
    return [
        Check("delegation", "builder, verifier and proposer are three different models", len(set(roles)) == 3,
              ", ".join(roles)),
        Check("delegation", "at least 3 specialist models actually get called in one run", len(seen) >= 3,
              f"{len(seen)} models called"),
    ]


def check_persistence(tmp: Path) -> list[Check]:
    out = []
    t = tmp / "p"
    _, h1, _, log = _pipeline(t)
    versions = sorted((t / "versions" / "judge").glob("v*.yaml"))
    kept = [d for d in log.decisions if d.action == "keep"]
    out.append(Check("persistence", "every kept change is saved as a versioned harness file",
                     len(versions) >= len(kept) + 1, f"{len(versions)} files for {len(kept)} kept changes"))
    lines = (t / "decisions.jsonl").read_text().splitlines()
    out.append(Check("persistence", "every decision is written to a log that survives a crash",
                     len(lines) == len(log.decisions), f"{len(lines)} lines"))
    cp = t / "cache.jsonl"
    from .team import Outcome
    c1 = Cache(cp)
    c1.put("k", Outcome("x", 0, score=1.0))
    out.append(Check("persistence", "model answers are cached on disk, so a restart does not redo work",
                     Cache(cp).get("k") is not None, "reloaded from disk"))
    out.append(_resume_check(tmp / "r"))
    return out


def _resume_check(t: Path) -> Check:
    name = "a stopped run resumes where it left off and ends in the same place as an uninterrupted run"
    try:
        from .loop import resume_state
    except ImportError:
        return Check("persistence", name, False, "no resume_state in loop.py")
    tasks = load_suite()
    cache = Cache(None)
    h0 = Harness().with_change({"kind": "add_rule", "text": DECOY})
    direct, _ = improve(StubLLM(OfflineModel()), h0, tasks, 4, 1, cache, Log("direct", path=None, emit=_quiet))
    om = OfflineModel()  # same stand-in across both halves, as the same real model would be
    llm = StubLLM(om)
    vdir = t / "versions" / "rid"
    vdir.mkdir(parents=True)
    h0.save(vdir / "v0.yaml")
    improve(llm, h0, tasks, 2, 1, cache, Log("rid", path=t / "decisions.jsonl", emit=_quiet), save_dir=vdir)
    h, done, rejected = resume_state("rid", runs_dir=t)
    resumed, _ = improve(llm, h, tasks, 4, 1, cache, Log("rid", path=t / "decisions.jsonl", emit=_quiet),
                         save_dir=vdir, start_round=done, rejected=rejected)
    same = [r["text"] for r in resumed.rules] == [r["text"] for r in direct.rules]
    return Check("persistence", name, same and done == 2, f"resumed after round {done}; same rules: {same}")


class _Flaky:
    """Stand-in whose first call for each task raises, like a dropped connection."""

    def __init__(self):
        self.om, self.failed = OfflineModel(), set()

    def __call__(self, model, messages):
        key = messages[-1]["content"]
        if key not in self.failed:
            self.failed.add(key)
            raise ConnectionError("simulated dropped connection")
        return self.om(model, messages)


def check_recovery(tmp: Path) -> list[Check]:
    out = []
    tasks = select(load_suite(), "train")
    try:
        ev = run_eval(StubLLM(_Flaky()), Harness(), tasks, 1, 1, Cache(None))
        out.append(Check("recovery", "a dropped connection on every task is retried, not counted as a failure",
                         ev.errors() == 0, f"{ev.errors()} errors left of {len(ev.outcomes)} runs"))
    except EvalFailed as e:
        out.append(Check("recovery", "a dropped connection on every task is retried, not counted as a failure",
                         False, f"eval aborted: {str(e)[:80]}"))
    from .team import run_task
    bad = StubLLM(lambda m, msgs: "```python\ndef f(): return 1\n```\n```python\nassert f() == 2\n```")
    h = Harness()
    h.team["max_attempts"] = 4
    o = run_task(bad, h, tasks[0])
    out.append(Check("recovery", "the monitor stops an agent that repeats the same mistake",
                     o.stop_reason.startswith("loop") and o.attempts == 2, f"stopped: {o.stop_reason!r}, "
                                                                          f"{o.attempts} attempts of 4"))
    try:
        run_eval(StubLLM(OfflineModel(), max_calls=5), Harness(), tasks, 1, 1, Cache(None))
        capped = False
    except CallCapExceeded:
        capped = True
    out.append(Check("recovery", "a spending cap stops the run instead of being swallowed", capped, ""))
    _, _, _, log = _pipeline(tmp / "g")
    rej = [d for d in log.decisions if d.action == "reject" and "val dropped" in d.reason]
    out.append(Check("recovery", "a change that hurts held-out tasks is rejected and rolled back", bool(rej),
                     f"{len(rej)} rejected for hurting val"))
    return out


def check_long_running(tmp: Path) -> list[Check]:
    rounds = 4
    _, h1, h2, log = _pipeline(tmp / "l", rounds=rounds)
    per_round = [d for d in log.decisions if d.round > 0]
    ablation = {d.unit for d in log.decisions if d.action in ("retain", "delete")}
    out = [
        Check("long_running", "loop runs the stated number of rounds, then stops", len(per_round) == rounds,
              f"{len(per_round)} decisions in {rounds} rounds"),
        Check("long_running", "after the rounds, every kept change gets an audit verdict",
              set(h1.units()) <= ablation, f"{len(ablation)} audited"),
    ]
    om, n = OfflineModel(), [0]

    def stuck(model, messages):
        if "improve a coding team's harness" in messages[0]["content"]:
            n[0] += 1
            return json.dumps({"kind": "add_rule", "text": f"Prefer tabs, variant {n[0]}."})
        return om(model, messages)

    log2 = Log("stuck", path=None, emit=_quiet)
    h0 = Harness()
    improve(StubLLM(stuck), h0, load_suite(), 10, 1, Cache(None), log2)
    rounds_used = len([d for d in log2.decisions if d.round > 0])
    out.append(Check("long_running", "stops early with a stated reason when it stops making progress",
                     rounds_used < 10, f"used {rounds_used} of 10 rounds with nothing to gain"))
    return out


def check_stack() -> list[Check]:
    h = Harness.load(ROOT / "harness.yaml")
    unknown = [m for m in h.models.values() if m not in PRICES]
    return [
        Check("stack", "every model in harness.yaml is a known Crusoe model", not unknown, f"unknown: {unknown}"),
        Check("stack", "the builder is Nemotron", "nemotron" in h.models["builder"].lower(), h.models["builder"]),
        Check("stack", "default endpoint is Crusoe Managed Inference", "crusoe" in DEFAULT_BASE_URL, DEFAULT_BASE_URL),
    ]


def check_demo(tmp: Path) -> list[Check]:
    from .cli import table
    script = ROOT / "demo" / "run_demo.sh"
    ok_script = script.exists() and os.access(script, os.X_OK)
    syntax = ok_script and subprocess.run(["bash", "-n", str(script)], capture_output=True).returncode == 0
    h0, _, h2, _ = _pipeline(tmp / "c")
    llm, tasks = StubLLM(OfflineModel()), load_suite()
    b, a = (run_eval(llm, h, tasks, 1, 4, Cache(None)) for h in (h0, h2))
    shown = table(b, a, h0, h2, "judge", 0.0, 0)
    doc = (ROOT / "demo" / "DEMO.md").read_text().lower() if (ROOT / "demo" / "DEMO.md").exists() else ""
    words = ["autonom", "delegat", "persist", "recover"]
    missing = [w for w in words if w not in doc]
    return [
        Check("demo", "one runnable, executable demo script exists", bool(syntax), str(script.relative_to(ROOT))),
        Check("demo", "the result table shows unseen-task score and the overconfidence number",
              "TEST tasks (never seen)" in shown and "said 'done' but was wrong" in shown, ""),
        Check("demo", "the demo notes name each judging criterion (keyword check only)", not missing,
              f"missing: {missing}" if missing else "all four named"),
    ]


# ---- running, recording, gating ------------------------------------------------------------------------------
def run_all() -> list[Check]:
    checks: list[Check] = []
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        for fn in (check_autonomy, check_delegation, check_persistence, check_recovery, check_long_running,
                   check_demo):
            try:
                checks += fn(tmp)
            except Exception as e:  # a crashing probe is a failed check, never a crashed scorecard
                crit = fn.__name__.removeprefix("check_")
                checks.append(Check(crit, f"{crit} probes run without crashing", False,
                                    f"{type(e).__name__}: {str(e)[:100]}"))
    checks += check_stack()
    return checks


def scores(checks: list[Check]) -> dict[str, float]:
    out = {}
    for c in CRITERIA:
        mine = [x for x in checks if x.criterion == c]
        out[c] = sum(x.passed for x in mine) / len(mine) if mine else 0.0
    return out


def overall(checks: list[Check]) -> float:
    s = scores(checks)
    return sum(s.values()) / len(s)


def last_record(path: Path = HISTORY) -> dict | None:
    if not path.exists() or not path.read_text().strip():
        return None
    return json.loads(path.read_text().strip().splitlines()[-1])


def regressions(checks: list[Check], prev: dict | None) -> list[str]:
    if not prev:
        return []
    now = {c.name: c.passed for c in checks}
    return [n for n, was in prev["checks"].items() if was and not now.get(n, False)]


def record(checks: list[Check], label: str, path: Path = HISTORY) -> None:
    path.parent.mkdir(exist_ok=True)
    rec = {"at": time.time(), "label": label, "overall": round(overall(checks), 4),
           "criteria": {k: round(v, 3) for k, v in scores(checks).items()},
           "checks": {c.name: c.passed for c in checks}}
    with path.open("a") as f:
        f.write(json.dumps(rec) + "\n")


def render(checks: list[Check]) -> str:
    out = ["", "=== JUDGE SCORECARD (offline probes, no AI judge) ==="]
    for crit in CRITERIA:
        mine = [c for c in checks if c.criterion == crit]
        out.append(f"\n  {crit.replace('_', ' '):<14}{scores(checks)[crit]:>5.0%}")
        for c in mine:
            out.append(f"    [{'PASS' if c.passed else 'FAIL'}] {c.name}" + (f"  ({c.detail})" if c.detail else ""))
    out.append(f"\n  OVERALL {overall(checks):.0%}   ({sum(c.passed for c in checks)} of {len(checks)} checks)")
    return "\n".join(out)
