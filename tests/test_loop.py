# agent: claude-code  2026-10-17
"""End-to-end gate and ablation behaviour, using the scripted offline stand-in (no key, no cost)."""
from rah.config import Harness
from rah.evaluate import Cache, run_eval
from rah.llm import StubLLM
from rah.loop import Log, ablate, improve
from rah.stub import DECOY, OfflineModel
from rah.suite import load_suite, select

TASKS = load_suite()


def _run(rounds=4):
    llm = StubLLM(OfflineModel())
    h0 = Harness().with_change({"kind": "add_rule", "text": DECOY})
    log = Log("test", path=None, emit=lambda s: None)
    h1, ev1 = improve(llm, h0, TASKS, rounds, 1, Cache(None), log)
    h2, _ = ablate(llm, h1, TASKS, 1, Cache(None), log, ev=ev1)
    return h0, h1, h2, log


def test_good_rules_kept_overfit_rejected_decoy_deleted():
    _, h1, h2, log = _run()
    acts = [(d.action, d.text) for d in log.decisions]
    kept = [t for a, t in acts if a == "keep"]
    rejected = [t for a, t in acts if a == "reject"]
    deleted = [t for a, t in acts if a == "delete"]
    assert len(kept) == 2 and len(rejected) == 2
    assert any("ties" in t for t in rejected), "the rule that hurts val must be rejected by the gate"
    assert deleted == [DECOY], "the useless seeded rule must be deleted by the ablation"
    assert {r["text"] for r in h2.rules} == set(kept)
    assert all(h2.receipts[u].get("ablation_worth", 0) > 0 for u in h2.units())


def test_val_split_decides_and_test_split_is_never_scored_in_the_loop():
    llm = StubLLM(OfflineModel())
    seen = []
    log = Log("t", path=None, emit=lambda s: None)
    orig = run_eval

    import rah.loop as loop

    def spy(llm_, h, tasks, *a, **k):
        seen.extend(t.split for t in tasks)
        return orig(llm_, h, tasks, *a, **k)

    loop.run_eval = spy
    try:
        loop.improve(llm, Harness(), TASKS, 2, 1, Cache(None), log)
    finally:
        loop.run_eval = orig
    assert "test" not in set(seen)


def test_failure_report_only_shows_train_tasks():
    from rah.proposer import failure_report
    llm = StubLLM(OfflineModel())
    ev = run_eval(llm, Harness(), select(TASKS, "train", "val"), 1, 4, Cache(None))
    rep = failure_report(ev, {t.id: t for t in TASKS})
    val_ids = [t.id for t in TASKS if t.split != "train"]
    assert rep and not any(f"### {i} " in rep for i in val_ids)
