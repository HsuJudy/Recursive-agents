# agent: claude-code  2026-10-17
"""The eval suite must itself be trustworthy: references pass, wrong answers fail, splits are as designed."""
from collections import Counter

import pytest

from rah.sandbox import run_tests, split_statements
from rah.suite import load_suite, select

TASKS = load_suite()


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.id)
def test_reference_passes_every_hidden_test(task):
    r = run_tests(task.reference, task.tests)
    assert r.all_passed, r.errors


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.id)
def test_known_bad_answers_fail(task):
    wrong = f"def {task.entry}(*a, **k):\n    return None\n"
    assert run_tests(wrong, task.tests).score < 1.0
    assert run_tests("def broken(:\n", task.tests).passed == 0


def test_infinite_loop_is_stopped():
    t = TASKS[0]
    assert run_tests(f"def {t.entry}(*a, **k):\n    while True: pass\n", t.tests, timeout=1).timed_out


def test_split_sizes():
    c = Counter(t.split for t in TASKS)
    assert c == {"train": 12, "val": 6, "test": 16}


def test_ids_unique_and_each_task_has_enough_tests():
    assert len({t.id for t in TASKS}) == len(TASKS)
    assert all(len(t.tests) >= 3 for t in TASKS)
    assert all(t.entry in t.spec for t in TASKS)


def test_money_family_is_test_only():
    assert {t.split for t in TASKS if t.family == "money"} == {"test"}
    assert all(t.family != "money" for t in select(TASKS, "train", "val"))


def test_split_statements():
    assert split_statements("assert 1\nassert 2") == ["assert 1", "assert 2"]
    assert split_statements("assert (") is None
