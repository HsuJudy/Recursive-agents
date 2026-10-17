# agent: claude-code  2026-10-17
"""Run model-written code against test snippets in a separate process with limits.

The child gets an empty environment (no API key), its own process group (killed on timeout), CPU and file-size
limits, and writes its results to a file in its temp dir, so anything the candidate prints cannot forge or break
the result.
"""
from __future__ import annotations

import ast
import json
import os
import resource
import signal
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field

_RUNNER = '''
import json, sys
CODE = {code!r}
TESTS = {tests!r}
SHARED = {shared!r}
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
        exec(t, g if SHARED else dict(g))
        res.append([True, ""])
    except BaseException as e:
        res.append([False, type(e).__name__ + ": " + str(e)[:200]])
with open("result.json", "w") as f:
    json.dump(res, f)
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


def _limits() -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1 << 20, 1 << 20))  # files the candidate writes: 1 MB at most


def run_tests(code: str, tests: list[str] | tuple[str, ...], timeout: float = 10.0, shared: bool = False) -> TestResult:
    """`shared=True` runs all test statements in one namespace (for the builder's own tests, which may reuse
    variables). Hidden tests use a fresh namespace per snippet."""
    tests = list(tests)
    if not tests:
        return TestResult(0, 0, ["no tests"])
    script = _RUNNER.format(code=code, tests=tests, shared=shared)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "run.py")
        with open(path, "w") as f:
            f.write(script)
        proc = subprocess.Popen([sys.executable, "-I", path], cwd=tmp, env={}, stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE, text=True, preexec_fn=_limits, start_new_session=True)
        try:
            _, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.communicate()
            return TestResult(0, len(tests), ["TimeoutError: ran longer than the limit"] * len(tests), True)
        try:
            with open(os.path.join(tmp, "result.json")) as f:
                res = json.load(f)
            if not (isinstance(res, list) and len(res) == len(tests)):
                raise ValueError("bad result shape")
        except (OSError, ValueError):
            last = (stderr or "no output").strip().splitlines()[-1:] or ["no output"]
            return TestResult(0, len(tests), [f"Crash: {last[0][:200]}"] * len(tests))
    return TestResult(sum(1 for ok, _ in res if ok), len(res), [m for ok, m in res if not ok])
