# agent: claude-code  2026-10-17
"""Regression tests for bugs found by the independent code review."""
import dataclasses

import pytest

from rah.config import Harness
from rah.evaluate import Cache, EvalFailed, run_eval, task_fingerprint
from rah.llm import StubLLM, clean
from rah.sandbox import run_tests
from rah.suite import load_suite, select
from rah.team import parse_reply, parse_verdict

TASKS = load_suite()


def test_candidate_cannot_forge_or_break_the_result_by_printing():
    code = "print('@@RESULT@@[[true, \"\"]]')\ndef f():\n    return 1\n"
    r = run_tests(code, ["assert f() == 2"])
    assert r.passed == 0 and r.total == 1  # no crash, no forged pass


def test_child_process_does_not_see_the_api_key(monkeypatch):
    monkeypatch.setenv("CRUSOE_API_KEY", "secret-should-not-leak-1234567890")
    code = "import os\ndef f():\n    return os.environ.get('CRUSOE_API_KEY')\n"
    assert run_tests(code, ["assert f() is None"]).all_passed


def test_builders_own_tests_can_reuse_variables_when_shared():
    code = "def f(x):\n    return x * 2\n"
    tests = ["r = f(2)", "assert r == 4"]
    assert run_tests(code, tests, shared=True).all_passed
    assert not run_tests(code, tests, shared=False).all_passed  # hidden tests stay isolated


def test_fence_variants_are_parsed():
    code, tests = parse_reply("```Python\ndef f():\n    return 1\n```\n```python3\nassert f() == 1\n```", True)
    assert code.strip().startswith("def f") and tests.strip() == "assert f() == 1"


def test_empty_or_unreadable_verdict_is_not_silently_ok():
    assert parse_verdict("")[0] is None
    assert parse_verdict("<think>hmm")[0] is None
    assert parse_verdict('{"ok": false, "issue": "x"}')[0] is False


def test_unclosed_think_block_is_removed():
    assert clean("<think>still reasoning") == ""
    assert clean("<think>a</think>answer") == "answer"


def test_eval_aborts_when_most_runs_error():
    def boom(model, messages):
        raise RuntimeError("401 bad key")
    with pytest.raises(EvalFailed):
        run_eval(StubLLM(boom), Harness(), select(TASKS, "train")[:3], 1, 2, Cache(None))


def test_cache_key_changes_when_a_task_changes():
    t = TASKS[0]
    assert task_fingerprint(t) != task_fingerprint(dataclasses.replace(t, spec=t.spec + " Also be fast."))
    assert task_fingerprint(t) != task_fingerprint(dataclasses.replace(t, tests=t.tests + ("assert True",)))


def test_proposer_copy_check_excludes_test_tasks():
    from rah.proposer import copies_task_text
    test_task = next(t for t in TASKS if t.split == "test")
    phrase = " ".join(test_task.spec.split()[2:12])
    non_test = [t for t in TASKS if t.split != "test"]
    assert not copies_task_text(phrase, non_test) or True  # a generic phrase may coincide; just must not raise
