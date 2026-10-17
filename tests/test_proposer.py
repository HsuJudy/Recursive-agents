# agent: claude-code  2026-10-17
import pytest

from rah.config import Harness
from rah.proposer import ProposalRejected, copies_task_text, validate
from rah.suite import load_suite

TASKS = load_suite()


def test_rule_copying_task_wording_is_rejected():
    spec = TASKS[0].spec  # a train task
    copied = " ".join(spec.split()[3:14])
    assert copies_task_text(copied, TASKS)
    with pytest.raises(ProposalRejected):
        validate({"kind": "add_rule", "text": copied}, Harness(), TASKS)


def test_copying_a_held_out_task_is_also_rejected():
    test_task = next(t for t in TASKS if t.split == "test")
    copied = " ".join(test_task.spec.split()[2:12])
    assert copies_task_text(copied, TASKS)


def test_general_rule_is_accepted():
    ch = {"kind": "add_rule", "text": "Check empty inputs and boundary values before the main logic."}
    assert validate(ch, Harness(), TASKS) == ch


def test_overlong_or_malformed_proposals_rejected():
    with pytest.raises(ProposalRejected):
        validate({"kind": "add_rule", "text": "y" * 300}, Harness(), TASKS)
    with pytest.raises(ProposalRejected):
        validate({"kind": "set_team", "key": "nope", "value": 1}, Harness(), TASKS)
