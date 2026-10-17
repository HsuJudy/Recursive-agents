# agent: claude-code  2026-10-17
"""The self-improvement loop. Every change must earn its place twice:

  GATE      keep a proposed change only if train improves and val does not drop (paired, same tasks).
  ABLATION  then remove each kept change in turn; if the score does not fall, the change is deleted.
  AUDIT     swap the builder model and run the ablation again: what survives is portable, the rest was
            a quirk of the old model.

The `test` split is never touched here. It is scored only before and after (see cli.py).
"""
from __future__ import annotations

import copy
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from .config import Harness
from .evaluate import Cache, Eval, paired_delta, run_eval
from .proposer import ProposalRejected, propose
from .suite import Task, select

MIN_TRAIN_GAIN = 0.03  # a change must lift train by at least this (mean score, 0..1)
VAL_TOLERANCE = 0.02  # val may move this much against us before we call it a drop (noise allowance)
MIN_ABLATION_DROP = 0.02  # removing a kept change must cost at least this, or the change is deleted

PATIENCE = 3  # stop early after this many rounds in a row with nothing kept: the loop is stuck, not working

RUNS = Path(__file__).resolve().parents[2] / "runs"


@dataclass
class Decision:
    round: int
    action: str  # keep | reject | delete | retain
    unit: str
    text: str
    reason: str
    numbers: dict = field(default_factory=dict)
    at: float = field(default_factory=time.time)

    def line(self) -> str:
        n = "  ".join(f"{k} {v:+.2f}" if isinstance(v, float) else f"{k} {v}" for k, v in self.numbers.items())
        return f"[{self.action.upper():7}] {self.text[:90]}  ({self.reason}{'; ' + n if n else ''})"


class Log:
    def __init__(self, run_id: str, path: Path | None = None, emit=print):
        self.run_id, self.emit, self.decisions = run_id, emit, []
        self.path = path if path is not None else RUNS / "decisions.jsonl"

    def add(self, d: Decision) -> None:
        self.decisions.append(d)
        self.emit(d.line())
        if self.path:
            self.path.parent.mkdir(exist_ok=True)
            with self.path.open("a") as f:
                f.write(json.dumps({"run": self.run_id, **d.__dict__}) + "\n")


def _dev(tasks: list[Task]) -> list[Task]:
    return select(tasks, "train", "val")


def resume_state(run_id: str, runs_dir: Path = RUNS) -> tuple[Harness, int, list[str]]:
    """Rebuild where a stopped run was: latest saved harness, rounds already done, texts already rejected."""
    vdir = runs_dir / "versions" / run_id
    files = [(int(p.stem[1:]), p) for p in vdir.glob("v*.yaml") if p.stem[1:].isdigit()]
    if not files:
        raise FileNotFoundError(f"nothing saved for run {run_id} in {vdir}")
    h = Harness.load(max(files)[1])
    done, rejected = 0, []
    path = runs_dir / "decisions.jsonl"
    for line in path.read_text().splitlines() if path.exists() else []:
        d = json.loads(line)
        if d.get("run") == run_id and d.get("round", 0) > 0:
            done = max(done, d["round"])
            if d["action"] == "reject":
                rejected.append(d["text"][:60])
    return h, done, rejected


def improve(llm, h: Harness, tasks: list[Task], rounds: int, k: int, cache: Cache | None, log: Log,
            workers: int = 8, base_ev: Eval | None = None, save_dir: Path | None = None,
            start_round: int = 0, rejected: list[str] | None = None,
            patience: int = PATIENCE) -> tuple[Harness, Eval]:
    """`start_round` and `rejected` let a stopped run carry on (see resume_state). `patience` is the stop rule."""
    dev = _dev(tasks)
    cur, cur_ev = h, base_ev or run_eval(llm, h, dev, k, workers, cache)
    log.emit(f"baseline: train {cur_ev.mean('train'):.2f}  val {cur_ev.mean('val'):.2f}  "
             f"overconfident runs {cur_ev.overconfidence():.0%}")
    rejected = list(rejected or [])
    misses = 0  # rounds in a row with nothing kept
    for r in range(start_round + 1, rounds + 1):
        if misses >= patience:
            log.emit(f"stopping early: {misses} rounds in a row with nothing kept (patience {patience})")
            break
        try:
            change = propose(llm, cur, cur_ev, tasks, rejected)
        except ProposalRejected as e:
            log.add(Decision(r, "reject", "proposal", "(proposal)", f"not allowed: {e}"))
            rejected.append(str(e)[:60])
            misses += 1
            continue
        text = change.get("text") or f"team.{change.get('key')} = {change.get('value')}"
        cand = cur.with_change(change)
        unit = f"rule:{cand.rules[-1]['id']}" if change["kind"] == "add_rule" else f"team:{change['key']}"
        cand_ev = run_eval(llm, cand, dev, k, workers, cache)
        d_tr, se_tr = paired_delta(cand_ev, cur_ev, "train")
        d_va, se_va = paired_delta(cand_ev, cur_ev, "val")
        nums = {"train": d_tr, "val": d_va}
        if d_tr >= max(MIN_TRAIN_GAIN, se_tr) and d_va >= -VAL_TOLERANCE:  # gain must also beat its own noise
            cand.receipts[unit] = {"round": r, "train_delta": round(d_tr, 3), "train_se": round(se_tr, 3),
                                   "val_delta": round(d_va, 3), "val_se": round(se_va, 3),
                                   "builder": cand.models["builder"]}
            log.add(Decision(r, "keep", unit, text, "train improved, val held", nums))
            cur, cur_ev = cand, cand_ev
            misses = 0
            if save_dir:
                cur.save(save_dir / f"v{cur.version}.yaml")
        else:
            why = "train gain too small or within noise" if d_tr < max(MIN_TRAIN_GAIN, se_tr) else "val dropped (overfit to train)"
            log.add(Decision(r, "reject", unit, text, why, nums))
            rejected.append(text[:60])
            misses += 1
    return cur, cur_ev


FRESH = 1000  # sample numbers for the removal check, so it uses new runs and not the gate's cached ones


def ablate(llm, h: Harness, tasks: list[Task], k: int, cache: Cache | None, log: Log, workers: int = 8,
           label: str = "ablation") -> tuple[Harness, Eval]:
    """Remove each change in turn (oldest first). If the score does not fall, delete it for good.
    Uses fresh samples, so it is independent evidence and not a re-read of the gate's numbers."""
    dev = _dev(tasks)
    cur = copy.deepcopy(h)
    cur_ev = run_eval(llm, cur, dev, k, workers, cache, sample_offset=FRESH)
    for unit in list(h.units()):
        if unit not in cur.units():
            continue
        text = cur.describe(unit)
        without = cur.without_unit(unit)
        wo_ev = run_eval(llm, without, dev, k, workers, cache, sample_offset=FRESH)
        drop, se = paired_delta(cur_ev, wo_ev, "train", "val")  # how much the change is worth
        nums = {"worth": drop}
        if drop >= MIN_ABLATION_DROP:
            cur.receipts.setdefault(unit, {})[f"{label}_worth"] = round(drop, 3)
            cur.receipts[unit][f"{label}_builder"] = cur.models["builder"]
            log.add(Decision(0, "retain", unit, text, f"{label}: removing it lowers the score", nums))
        else:
            log.add(Decision(0, "delete", unit, text, f"{label}: removing it does not hurt", nums))
            cur, cur_ev = without, wo_ev
    return cur, cur_ev
