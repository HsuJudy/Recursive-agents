# agent: claude-code  2026-10-17
"""The harder suite must be as trustworthy as the main one: references pass, wrong answers fail, splits are right."""
from collections import Counter

import pytest

from rah.sandbox import run_tests
from rah.suite_data import TASKS as BASE_TASKS
from rah.suite_hard import HARD_TASKS


@pytest.mark.parametrize("task", HARD_TASKS, ids=lambda t: t.id)
def test_reference_passes_every_hidden_test(task):
    r = run_tests(task.reference, task.tests)
    assert r.all_passed, r.errors


@pytest.mark.parametrize("task", HARD_TASKS, ids=lambda t: t.id)
def test_known_bad_answers_fail(task):
    wrong = f"def {task.entry}(*a, **k):\n    return None\n"
    assert run_tests(wrong, task.tests).score < 1.0
    assert run_tests("def broken(:\n", task.tests).passed == 0


def test_ids_unique_and_no_clash_with_base_suite():
    ids = [t.id for t in HARD_TASKS]
    assert ids == [f"H{i}" for i in range(1, 13)]
    assert len(set(ids)) == len(ids)
    assert not set(ids) & {t.id for t in BASE_TASKS}
    assert not {t.entry for t in HARD_TASKS} & {t.entry for t in BASE_TASKS}


def test_split_sizes_and_families():
    assert Counter(t.split for t in HARD_TASKS) == {"train": 6, "val": 3, "test": 3}
    assert Counter(t.family for t in HARD_TASKS) == {"edge": 4, "errors": 4, "format": 4}
    for fam in ("edge", "errors", "format"):
        assert Counter(t.split for t in HARD_TASKS if t.family == fam) == {"train": 2, "val": 1, "test": 1}


def test_each_task_has_enough_tests_and_entry_in_spec():
    assert all(5 <= len(t.tests) <= 11 for t in HARD_TASKS)
    assert all(t.entry in t.spec for t in HARD_TASKS)
