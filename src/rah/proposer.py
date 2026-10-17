# agent: claude-code  2026-10-17
"""Analyst + proposer. The analyst groups failures from TRAIN tasks only; the proposer suggests ONE change.

A proposal is rejected here (before it costs an eval) if it is malformed, too long, a duplicate, or copies text
from any task spec or test, including tasks the proposer must never learn from.
"""
from __future__ import annotations

import json
import re

from .config import MAX_RULE_CHARS, ChangeError, Harness, TEAM_CHOICES
from .evaluate import Eval
from .suite import Task

MAX_FAILURES_SHOWN = 6


class ProposalRejected(ValueError):
    pass


def failure_report(ev: Eval, tasks_by_id: dict, limit: int = MAX_FAILURES_SHOWN) -> str:
    """Plain-text digest of the worst TRAIN failures. Never includes val or test tasks."""
    scores = ev.task_scores()
    worst = sorted((i for i in scores if tasks_by_id[i].split == "train" and scores[i] < 1.0),
                   key=lambda i: scores[i])[:limit]
    parts = []
    for i in worst:
        t = tasks_by_id[i]
        o = next((o for o in ev.outcomes if o.task_id == i and o.score < 1.0), None)
        if not o:
            continue
        parts.append(f"### {t.id} (family: {t.family}, score {scores[i]:.2f})\nTask: {t.spec}\n"
                     f"Team said done: {o.claimed_done}. Failed checks: {'; '.join(o.hidden_errors[:3])}\n"
                     f"Code:\n{o.code[:700]}")
    return "\n\n".join(parts)


def _words(s: str) -> list[str]:
    return re.findall(r"[a-z0-9_']+", s.lower())


def copies_task_text(text: str, tasks: list[Task], n: int = 6) -> bool:
    """True if `text` shares any run of n consecutive words with a task spec or test."""
    w = _words(text)
    grams = {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}
    if not grams:
        return False
    for t in tasks:
        corpus = _words(t.spec) + [x for test in t.tests for x in _words(test)]
        if any(tuple(corpus[i:i + n]) in grams for i in range(len(corpus) - n + 1)):
            return True
    return False


def _json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        raise ProposalRejected("no JSON in proposal")
    try:
        return json.loads(m.group(0))
    except ValueError as e:
        raise ProposalRejected(f"bad JSON: {e}")


def validate(change: dict, h: Harness, all_tasks: list[Task]) -> dict:
    if change.get("kind") == "add_rule":
        text = str(change.get("text", "")).strip()
        if len(text) > MAX_RULE_CHARS:
            raise ProposalRejected(f"rule is {len(text)} characters; the limit is {MAX_RULE_CHARS}")
        if copies_task_text(text, all_tasks):
            raise ProposalRejected("rule copies text from a task (it must be a general rule)")
    try:
        h.with_change(change)
    except ChangeError as e:
        raise ProposalRejected(str(e))
    return change


def propose(llm, h: Harness, ev: Eval, all_tasks: list[Task], rejected: list[str] | None = None) -> dict:
    """Return one validated change. Raises ProposalRejected if the model's idea is not allowed."""
    by_id = {t.id: t for t in all_tasks}
    report = failure_report(ev, by_id)
    if not report:
        raise ProposalRejected("no failures on train tasks to learn from")
    themes = llm.chat(h.models["analyst"], [
        {"role": "system", "content": "You analyse why a coding assistant fails small tasks. Be concrete and brief."},
        {"role": "user", "content": f"Failures:\n{report}\n\nIn at most 5 bullet points, name the recurring "
                                    "mistake patterns. Describe patterns, not individual tasks."}],
        max_tokens=700).text
    options = {"add_rule": "a short general rule (max 200 characters) for the builder to follow",
               "set_team": f"change one team setting. Allowed: {json.dumps({k: list(v) for k, v in TEAM_CHOICES.items()})}"}
    avoid = ("\nAlready tried and rejected (do not repeat): " + "; ".join(rejected)) if rejected else ""
    reply = llm.chat(h.models["proposer"], [
        {"role": "system", "content": "You improve a coding team's harness by proposing exactly ONE change."},
        {"role": "user", "content": (
            f"Current rules: {[r['text'] for r in h.rules] or 'none'}\nCurrent team settings: {json.dumps(h.team)}\n"
            f"Notes: the verifier only helps when max_attempts >= 2 (a rejected answer is retried). "
            f"edge_cases makes the builder list tricky inputs before coding.\n\nMistake patterns:\n{themes}\n"
            f"{avoid}\n\nPropose ONE change. Allowed kinds: {json.dumps(options)}.\n"
            'Reply with JSON only, e.g. {"kind":"add_rule","text":"..."} or '
            '{"kind":"set_team","key":"max_attempts","value":2}. A rule must be general advice, never mention a '
            "specific task or copy task wording.")}], max_tokens=500, thinking=False).text
    return validate(_json(reply), h, all_tasks)
