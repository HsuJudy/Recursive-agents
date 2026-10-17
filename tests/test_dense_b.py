# agent: claude-code  2026-10-17
"""The dense_b suite must be trustworthy: references pass, wrong answers fail, splits are right."""
from collections import Counter

import pytest

from rah.dense_b import DENSE_B
from rah.sandbox import run_tests
from rah.suite_data import TASKS as BASE_TASKS
from rah.suite_hard import HARD_TASKS


@pytest.mark.parametrize("task", DENSE_B, ids=lambda t: t.id)
def test_reference_passes_every_hidden_test(task):
    r = run_tests(task.reference, task.tests)
    assert r.all_passed, r.errors


@pytest.mark.parametrize("task", DENSE_B, ids=lambda t: t.id)
def test_known_bad_answers_fail(task):
    wrong = f"def {task.entry}(*a, **k):\n    return None\n"
    assert run_tests(wrong, task.tests).score < 1.0
    assert run_tests("def broken(:\n", task.tests).passed == 0


def test_ids_unique_and_no_clash_with_other_suites():
    ids = [t.id for t in DENSE_B]
    assert ids == [f"DB{i}" for i in range(1, 9)]
    assert len(set(ids)) == len(ids)
    others = BASE_TASKS + HARD_TASKS
    assert not set(ids) & {t.id for t in others}
    assert not {t.entry for t in DENSE_B} & {t.entry for t in others}
    assert len({t.entry for t in DENSE_B}) == len(DENSE_B)


def test_split_sizes_and_families():
    assert Counter(t.split for t in DENSE_B) == {"train": 3, "val": 2, "test": 3}
    assert [t.split for t in DENSE_B] == ["train"] * 3 + ["val"] * 2 + ["test"] * 3
    assert Counter(t.family for t in DENSE_B) == {"errors": 4, "format": 4}


def test_each_task_has_enough_tests_and_entry_in_spec():
    assert all(10 <= len(t.tests) <= 20 for t in DENSE_B)
    assert all(t.entry in t.spec for t in DENSE_B)
