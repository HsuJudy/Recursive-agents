# agent: claude-code  2026-10-17
"""Run model-written code against test snippets in a separate process with a time limit."""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field

MARK = "@@RESULT@@"

_RUNNER = '''
import json, sys
CODE = {code!r}
TESTS = {tests!r}
g = {{"__name__": "candidate"}}
load_err = None
try:
    exec(compile(CODE, "candidate.py", "exec"), g)
except BaseException as e:
    load_err = type(e).__name__ + ": " + str(e)[:200]
res = []
for t in TESTS:
    if load_err:
        res.append([False, load_err])
        continue
    try:
        exec(t, dict(g))
        res.append([True, ""])
    except BaseException as e:
        res.append([False, type(e).__name__ + ": " + str(e)[:200]])
sys.__stdout__.write("\\n{mark}" + json.dumps(res))
'''


@dataclass
class TestResult:
    passed: int
    total: int
    errors: list[str] = field(default_factory=list)  # one message per failed test
    timed_out: bool = False

    @property
    def score(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def all_passed(self) -> bool:
        return self.total > 0 and self.passed == self.total


def split_statements(src: str) -> list[str] | None:
    """Split a block of test code into its top-level statements; None if it is not valid Python."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    return [ast.get_source_segment(src, node) or "" for node in tree.body]


def run_tests(code: str, tests: list[str] | tuple[str, ...], timeout: float = 10.0) -> TestResult:
    tests = list(tests)
    if not tests:
        return TestResult(0, 0, ["no tests"])
    script = _RUNNER.format(code=code, tests=tests, mark=MARK)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "run.py")
        with open(path, "w") as f:
            f.write(script)
        try:
            proc = subprocess.run(
                [sys.executable, "-I", path], cwd=tmp, capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            return TestResult(0, len(tests), ["TimeoutError: ran longer than the limit"] * len(tests), True)
    out = proc.stdout or ""
    if MARK not in out:
        err = (proc.stderr or "no output").strip().splitlines()[-1:] or ["no output"]
        return TestResult(0, len(tests), [f"Crash: {err[0][:200]}"] * len(tests))
    res = json.loads(out.split(MARK, 1)[1])
    return TestResult(sum(1 for ok, _ in res if ok), len(res), [m for ok, m in res if not ok])
