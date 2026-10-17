# agent: claude-code  2026-10-17
"""Scripted offline stand-in for the models. It proves the wiring and the gate logic and costs nothing.

It is NOT a model result. Every run that uses it is labelled `offline` in the output and the run id.
Behaviour: the builder solves a task correctly only if a rule in its prompt contains that family's keyword,
otherwise it submits a wrong answer with weak tests (so it says "done" while wrong).
"""
from __future__ import annotations

from .suite import load_suite

FAMILY_KEYWORD = {"edge": "empty", "mutation": "modify", "format": "whitespace", "ordering": "order",
                  "errors": "message", "dates": "calendar", "money": "decimal"}

PROPOSALS = [
    {"kind": "add_rule", "text": "Handle empty inputs and duplicate values explicitly before the main logic."},
    {"kind": "add_rule", "text": "Add a short comment above every line of code."},
    {"kind": "add_rule", "text": "Never modify an argument the caller passed in; build and return new objects."},
    {"kind": "add_rule", "text": "When sorting, always break ties first and rely on the general order afterwards."},
]

DECOY = "Prefer short variable names."


class OfflineModel:
    def __init__(self):
        self.tasks = load_suite()
        self.proposals = 0

    def __call__(self, model: str, messages: list[dict]) -> str:
        system = messages[0]["content"]
        user = next(m["content"] for m in reversed(messages) if m["role"] == "user")
        if "improve a coding team's harness" in system:
            p = PROPOSALS[self.proposals % len(PROPOSALS)]
            self.proposals += 1
            import json
            return json.dumps(p)
        if "analyse why a coding assistant fails" in system:
            return "- Edge cases are skipped\n- Inputs are modified in place\n- Tie-breaking is ignored"
        task = next((t for t in self.tasks if t.spec in user), None)
        if "You review code" in system:
            return '{"ok": false, "issue": "returns None"}' if "return None" in user else '{"ok": true, "issue": ""}'
        if task is None:
            return "```python\npass\n```"
        rules = system.lower()
        solved = FAMILY_KEYWORD[task.family] in rules
        if "ties first" in rules:  # the overfit rule: helps train ordering tasks, breaks everything in val
            solved = (task.family == "ordering" and task.split == "train") or (solved and task.split != "val")
        if solved:
            tests = "\n".join(task.tests[:2])
            return f"```python\n{task.reference}```\n```python\n{tests}\n```"
        return f"```python\ndef {task.entry}(*a, **k):\n    return None\n```\n```python\nassert True\n```"
