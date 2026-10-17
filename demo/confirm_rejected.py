# agent: claude-code  2026-10-17
"""Was the gate right? Score a change the gate REJECTED on the unseen test split, which no decision ever used.

  uv run python demo/confirm_rejected.py
Compares the starting harness with the same harness plus `max_attempts = 2` on unseen test tasks only.
"""
from rah.config import Harness
from rah.evaluate import Cache, paired_delta, run_eval
from rah.llm import CrusoeLLM
from rah.suite import load_suite, select

llm, cache = CrusoeLLM(), Cache()
h0 = Harness.load("harness.yaml")
h1 = h0.with_change({"kind": "set_team", "key": "max_attempts", "value": 2})
for name in ("dense", "all"):
    tasks = select(load_suite(name), "test")
    a = run_eval(llm, h0, tasks, 6, 16, cache)
    b = run_eval(llm, h1, tasks, 6, 16, cache)
    d, se = paired_delta(b, a, "test")
    print(f"unseen test, suite={name:5} n={len(tasks):2} tasks x6 samples: "
          f"start {a.mean():.1%}  with 2 attempts {b.mean():.1%}  change {d*100:+.1f} pts (std. error {se*100:.1f})")
print(f"spend ${llm.cost():.3f}")
