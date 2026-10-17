# agent: claude-code  2026-10-17
"""The agent team for one task: builder (writes code and its own tests), verifier (independent model), monitor.

The builder's own tests are its definition of done. The hidden tests are the truth. The gap between the two
("said done, but was wrong") is measured on every run.
"""
from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field

from .config import Harness
from .llm import PRICES, CallCapExceeded
from .sandbox import run_tests, split_statements
from .suite import Task

FORMAT = (
    "Reply with exactly two fenced python blocks and nothing else that matters:\n"
    "1) the solution (only the function and any imports it needs);\n"
    "2) your own tests for it, as plain `assert` lines, no imports of the solution (it is already loaded)."
)
FORMAT_NO_TESTS = "Reply with one fenced python block: the solution (only the function and any imports it needs)."
TOKEN_BUDGET = 14000  # completion tokens per task before the monitor stops the run


@dataclass
class Outcome:
    task_id: str
    sample: int
    code: str = ""
    attempts: int = 0
    self_pass: bool | None = None  # builder's own tests passed (None = no self tests)
    verifier_ok: bool | None = None
    claimed_done: bool = False
    stop_reason: str = ""
    score: float = 0.0
    hidden_errors: list = field(default_factory=list)
    usage: list = field(default_factory=list)  # (model, prompt_tokens, completion_tokens)
    error: str = ""

    @property
    def cost(self) -> float:
        return sum(p * PRICES.get(m, (0, 0))[0] / 1e6 + c * PRICES.get(m, (0, 0))[1] / 1e6 for m, p, c in self.usage)

    @property
    def overconfident(self) -> bool:
        return self.claimed_done and self.score < 1.0

    def to_dict(self) -> dict:
        d = {k: getattr(self, k) for k in ("task_id", "sample", "attempts", "self_pass", "verifier_ok",
                                           "claimed_done", "stop_reason", "score", "error")}
        d["cost"] = round(self.cost, 6)
        d["overconfident"] = self.overconfident
        d["hidden_errors"] = self.hidden_errors[:3]
        d["code"] = self.code
        return d


def parse_reply(text: str, want_tests: bool) -> tuple[str | None, str | None]:
    blocks = re.findall(r"```(?:python|py)?[ \t]*\n(.*?)```", text, flags=re.S)
    if not blocks:
        return (text.strip() or None), None
    code, tests = blocks[0], (blocks[1] if len(blocks) > 1 else None)
    if want_tests and tests is None:  # tests mixed into the one block: pull the asserts out
        try:
            tree = ast.parse(code)
            asserts = [n for n in tree.body if isinstance(n, ast.Assert)]
            if asserts:
                tests = "\n".join(ast.get_source_segment(code, n) or "" for n in asserts)
                code = "\n".join(ast.get_source_segment(code, n) or "" for n in tree.body
                                 if not isinstance(n, ast.Assert))
        except SyntaxError:
            pass
    return code, tests


def parse_verdict(text: str) -> tuple[bool, str]:
    m = re.search(r"\{.*\}", text, flags=re.S)
    if m:
        try:
            d = json.loads(m.group(0))
            return bool(d.get("ok")), str(d.get("issue", ""))[:300]
        except (ValueError, AttributeError):
            pass
    return True, "unparseable verdict (treated as ok)"


BUILDER_TEMPERATURE = 0.4  # above 0 so repeated samples of the same task can differ (that spread is the noise)


def _call(llm, out: Outcome, model: str, messages: list, max_tokens: int = 3000, temperature: float = 0.0) -> str:
    r = llm.chat(model, messages, max_tokens=max_tokens, temperature=temperature)
    out.usage.append((model, r.prompt_tokens, r.completion_tokens))
    return r.text


def run_task(llm, h: Harness, task: Task, sample: int = 0) -> Outcome:
    out = Outcome(task.id, sample)
    team = h.team
    want_tests = team["self_tests"]
    user = f"Task:\n{task.spec}\n\n{FORMAT if want_tests else FORMAT_NO_TESTS}"
    try:
        if team["edge_cases"]:
            edge = _call(llm, out, h.models["builder"], [
                {"role": "system", "content": h.system_prompt()},
                {"role": "user", "content": f"Task:\n{task.spec}\n\nList the 6 trickiest inputs for this task, "
                                            "each with the exact expected output, one per line. No code."}], 800,
                         BUILDER_TEMPERATURE)
            user += f"\n\nEdge cases to handle:\n{edge}"
        messages = [{"role": "system", "content": h.system_prompt()}, {"role": "user", "content": user}]
        last_problem = None
        for attempt in range(1, team["max_attempts"] + 1):
            out.attempts = attempt
            text = _call(llm, out, h.models["builder"], messages, temperature=BUILDER_TEMPERATURE)
            code, tests_src = parse_reply(text, want_tests)
            problem = None
            out.self_pass = None
            if code is None:
                problem = "No code block was found."
            else:
                out.code = code
                if want_tests:
                    stmts = split_statements(tests_src) if tests_src else None
                    if not stmts:
                        out.self_pass, problem = False, "Your tests were missing or not valid Python."
                    else:
                        r = run_tests(code, stmts)
                        out.self_pass = r.all_passed
                        if not r.all_passed:
                            problem = f"Your own tests failed: {r.errors[0]}"
            out.verifier_ok = None
            if problem is None and team["verifier"]:
                v = _call(llm, out, h.models["verifier"], [
                    {"role": "system", "content": "You review code against a task. You have not seen the author's "
                                                  "reasoning. Check every requirement in the task text."},
                    {"role": "user", "content": f"Task:\n{task.spec}\n\nCode:\n```python\n{code}\n```\n\n"
                                                'Reply with JSON only: {"ok": true or false, "issue": "the first '
                                                'requirement it breaks, or empty"}'}], 600)
                out.verifier_ok, issue = parse_verdict(v)
                if not out.verifier_ok:
                    problem = f"A reviewer found a problem: {issue}"
            if problem is None:
                out.claimed_done = True
                break
            # monitor (plain code): stop on a repeated problem or an overspent budget
            if problem == last_problem:
                out.stop_reason = "loop: same problem twice"
                break
            if sum(c for _, _, c in out.usage) > TOKEN_BUDGET:
                out.stop_reason = "budget: token limit"
                break
            last_problem = problem
            if attempt < team["max_attempts"]:
                messages += [{"role": "assistant", "content": text},
                             {"role": "user", "content": f"{problem}\nFix it and reply in the same format."}]
        else:
            out.stop_reason = out.stop_reason or "attempts used up"
        if not out.claimed_done and not out.stop_reason:
            out.stop_reason = "gave up"
    except CallCapExceeded:
        raise
    except Exception as e:  # a model or network failure is a failed run, not a crash of the whole suite
        out.error = f"{type(e).__name__}: {str(e)[:160]}"
        out.stop_reason = "error"
    if out.code:
        r = run_tests(out.code, task.tests)
        out.score, out.hidden_errors = r.score, r.errors
    return out
