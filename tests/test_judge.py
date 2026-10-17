# agent: claude-code  2026-10-17
"""The demo-readiness scorecard: every check passes, and the gate refuses a regression."""
from rah import judge


def test_every_check_passes():
    checks = judge.run_all()
    failing = [(c.name, c.detail) for c in checks if not c.passed]
    assert not failing, failing
    assert set(judge.scores(checks)) == set(judge.CRITERIA)


def test_gate_flags_a_check_that_used_to_pass(tmp_path):
    checks = [judge.Check("demo", "a", True, ""), judge.Check("demo", "b", True, "")]
    p = tmp_path / "h.jsonl"
    judge.record(checks, "first", p)
    worse = [judge.Check("demo", "a", True, ""), judge.Check("demo", "b", False, "")]
    assert judge.regressions(worse, judge.last_record(p)) == ["b"]
    assert judge.regressions(checks, judge.last_record(p)) == []
    assert judge.last_record(tmp_path / "none.jsonl") is None


def test_a_crashing_probe_is_a_failed_check_not_a_crash(monkeypatch):
    def check_autonomy(tmp):
        return 1 / 0

    monkeypatch.setattr(judge, "check_autonomy", check_autonomy)
    monkeypatch.setattr(judge, "check_delegation", lambda tmp: [])
    monkeypatch.setattr(judge, "check_persistence", lambda tmp: [])
    monkeypatch.setattr(judge, "check_recovery", lambda tmp: [])
    monkeypatch.setattr(judge, "check_long_running", lambda tmp: [])
    monkeypatch.setattr(judge, "check_demo", lambda tmp: [])
    checks = judge.run_all()
    assert any(c.criterion == "autonomy" and not c.passed for c in checks)
