# agent: claude-code  2026-10-17
"""The dense-C suite must be as trustworthy as the others: references pass, wrong answers fail, splits are right."""
from collections import Counter

import pytest

from rah.dense_c import DENSE_C
from rah.sandbox import run_tests
from rah.suite_data import TASKS as BASE_TASKS
from rah.suite_hard import HARD_TASKS


@pytest.mark.parametrize("task", DENSE_C, ids=lambda t: t.id)
def test_reference_passes_every_hidden_test(task):
    r = run_tests(task.reference, task.tests)
    assert r.all_passed, r.errors


@pytest.mark.parametrize("task", DENSE_C, ids=lambda t: t.id)
def test_known_bad_answers_fail(task):
    wrong = f"def {task.entry}(*a, **k):\n    return None\n"
    assert run_tests(wrong, task.tests).score < 1.0
    assert run_tests("def broken(:\n", task.tests).passed == 0


def test_ids_unique_and_no_clash_with_other_suites():
    ids = [t.id for t in DENSE_C]
    assert ids == [f"DC{i}" for i in range(1, 9)]
    assert len(set(ids)) == len(ids)
    others = list(BASE_TASKS) + list(HARD_TASKS)
    assert not set(ids) & {t.id for t in others}
    entries = [t.entry for t in DENSE_C]
    assert len(set(entries)) == len(entries)
    assert not set(entries) & {t.entry for t in others}


def test_split_sizes_and_families():
    assert Counter(t.split for t in DENSE_C) == {"train": 3, "val": 2, "test": 3}
    assert [t.split for t in DENSE_C] == ["train"] * 3 + ["val"] * 2 + ["test"] * 3
    assert Counter(t.family for t in DENSE_C) == {"ordering": 4, "dates": 4}


def test_each_task_has_enough_tests_and_entry_in_spec():
    assert all(10 <= len(t.tests) <= 14 for t in DENSE_C)
    assert all(t.entry in t.spec for t in DENSE_C)
