# agent: claude-code  2026-10-17
import pytest

from rah.config import ChangeError, Harness


def test_add_and_remove_rule_roundtrip(tmp_path):
    h = Harness().with_change({"kind": "add_rule", "text": "Check empty input first."})
    assert h.units() == ["rule:R1"] and h.version == 1
    p = tmp_path / "h.yaml"
    h.save(p)
    assert Harness.load(p).to_dict() == h.to_dict()
    assert h.without_unit("rule:R1").units() == []


def test_rule_over_200_characters_is_refused():
    with pytest.raises(ChangeError):
        Harness().with_change({"kind": "add_rule", "text": "x" * 201})


def test_duplicate_and_unknown_changes_refused():
    h = Harness().with_change({"kind": "add_rule", "text": "A rule."})
    with pytest.raises(ChangeError):
        h.with_change({"kind": "add_rule", "text": "a RULE."})
    with pytest.raises(ChangeError):
        h.with_change({"kind": "delete_everything"})
    with pytest.raises(ChangeError):
        h.with_change({"kind": "set_team", "key": "max_attempts", "value": 99})


def test_team_setting_is_a_unit_and_reverts_to_default():
    h = Harness().with_change({"kind": "set_team", "key": "verifier", "value": True})
    assert h.units() == ["team:verifier"]
    assert h.without_unit("team:verifier").team["verifier"] is False


def test_changes_never_mutate_the_original():
    h = Harness()
    h.with_change({"kind": "add_rule", "text": "x"})
    assert h.rules == [] and h.version == 0
