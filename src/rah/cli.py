# agent: claude-code  2026-10-17
"""Command line: run the whole self-improvement pipeline and print the before/after table.

  uv run rah models                       list the model ids the Crusoe key can use
  uv run rah run --offline                free dry run with the scripted stand-in (not a model result)
  uv run rah run --k 3 --rounds 4         real run on Crusoe
  uv run rah run --swap-builder MODEL     ...then swap the builder model and re-audit every kept change
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .config import Harness
from .evaluate import Cache, Eval, run_eval
from .llm import CrusoeLLM, StubLLM
from .loop import RUNS, Log, ablate, improve
from .stub import DECOY, OfflineModel
from .suite import load_suite, select

ROOT = Path(__file__).resolve().parents[2]


def _row(label: str, a: float, b: float) -> str:
    return f"  {label:<26}{a:>8.0%}{b:>10.0%}{(b - a) * 100:>+9.0f} pts"


def table(before: Eval, after: Eval, h0: Harness, h1: Harness, label: str, cost: float, calls: int) -> str:
    out = [f"\n=== RESULT ({label}) ===", f"  {'':<26}{'before':>8}{'after':>10}{'change':>13}"]
    out.append(_row("train tasks (seen)", before.mean("train"), after.mean("train")))
    out.append(_row("val tasks (gate)", before.mean("val"), after.mean("val")))
    out.append(_row("TEST tasks (never seen)", before.mean("test"), after.mean("test")))
    fams = sorted({t.family for t in before.tasks.values() if t.split == "test"})
    for f in fams:
        tag = " (new kind of task)" if f == "money" else ""
        out.append(_row(f"   test / {f}{tag}", before.mean("test", family=f), after.mean("test", family=f)))
    out.append(_row("said 'done' but was wrong", before.overconfidence("test"), after.overconfidence("test")))
    nv = sum(o.verifier_unusable for o in after.outcomes)
    if nv:
        out.append(f"  note: the verifier gave no readable verdict in {nv} runs (treated as ok)")
    out.append(f"\n  kept changes: {len(h1.units())}   (started with {len(h0.units())})")
    for u in h1.units():
        r = h1.receipts.get(u, {})
        out.append(f"   - {h1.describe(u)}   [train {r.get('train_delta', 0):+.2f}, val {r.get('val_delta', 0):+.2f},"
                   f" removal costs {r.get('ablation_worth', 0):.2f}]")
    out.append(f"\n  model calls: {calls}   spend: ${cost:.3f}")
    return "\n".join(out)


def cmd_models(_):
    llm = CrusoeLLM()
    for m in llm.client.models.list().data:
        print(m.id)


def cmd_run(a):
    tasks = load_suite()
    h0 = Harness.load(a.harness) if Path(a.harness).exists() else Harness()
    if a.builder:
        h0 = h0.with_models(builder=a.builder)
    if a.offline:
        llm, cache, label = StubLLM(OfflineModel()), Cache(None), "OFFLINE stand-in, not a model result"
        if not h0.rules:
            h0 = h0.with_change({"kind": "add_rule", "text": DECOY})  # a seeded useless rule, so deletion is visible
        run_id = f"offline-{int(time.time())}"
    else:
        llm, cache, label = CrusoeLLM(), Cache(), "real run on Crusoe Managed Inference"
        run_id = f"real-{int(time.time())}"
    log = Log(run_id)
    print(f"run {run_id}: {len(tasks)} tasks, k={a.k}, rounds={a.rounds}, builder={h0.models['builder']}")
    test = select(tasks, "test")
    before_test = run_eval(llm, h0, test, a.k, a.workers, cache)
    print(f"unseen test baseline: {before_test.mean():.0%}  (cost so far ${llm.cost():.3f})")
    vdir = RUNS / "versions" / run_id
    vdir.mkdir(parents=True, exist_ok=True)
    h0.save(vdir / "v0.yaml")
    h1, ev1 = improve(llm, h0, tasks, a.rounds, a.k, cache, log, a.workers, save_dir=vdir)
    h2, _ = ablate(llm, h1, tasks, a.k, cache, log, a.workers)
    after_test = run_eval(llm, h2, test, a.k, a.workers, cache)
    before = run_eval(llm, h0, select(tasks, "train", "val"), a.k, a.workers, cache)
    after = run_eval(llm, h2, select(tasks, "train", "val"), a.k, a.workers, cache)
    merged_b = Eval(0, before.tasks | before_test.tasks, before.outcomes + before_test.outcomes)
    merged_a = Eval(h2.version, after.tasks | after_test.tasks, after.outcomes + after_test.outcomes)
    h2.save(vdir / "final.yaml")
    if not a.offline:
        h2.save(ROOT / "harness.improved.yaml")  # never overwrite the starting harness: the cache is keyed on it
    print(table(merged_b, merged_a, h0, h2, label, llm.cost(), llm.calls))
    if a.swap_builder:
        print(f"\n=== MODEL SWAP: builder -> {a.swap_builder} ===")
        h3 = h2.with_models(builder=a.swap_builder)
        h4, _ = ablate(llm, h3, tasks, a.k, cache, log, a.workers, label="swap")
        kept = [h4.describe(u) for u in h4.units()]
        print(f"  portable (still earn their place): {kept or 'none'}")
        print(f"  specific to the old model (deleted): {[h3.describe(u) for u in h3.units() if u not in h4.units()] or 'none'}")
    (RUNS / f"{run_id}.json").write_text(json.dumps({
        "run": run_id, "label": label, "before_test": merged_b.mean("test"), "after_test": merged_a.mean("test"),
        "cost": llm.cost(), "calls": llm.calls, "decisions": [d.__dict__ for d in log.decisions]}, indent=1))


def main(argv=None):
    p = argparse.ArgumentParser(prog="rah")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("models").set_defaults(fn=cmd_models)
    r = sub.add_parser("run")
    r.add_argument("--offline", action="store_true")
    r.add_argument("--k", type=int, default=3, help="samples per task")
    r.add_argument("--rounds", type=int, default=4)
    r.add_argument("--workers", type=int, default=8)
    r.add_argument("--harness", default=str(ROOT / "harness.yaml"))
    r.add_argument("--builder", help="override the builder model id")
    r.add_argument("--swap-builder", help="after the run, swap the builder to this model and re-audit")
    r.set_defaults(fn=cmd_run)
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main(sys.argv[1:])
