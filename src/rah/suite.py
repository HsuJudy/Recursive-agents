# agent: claude-code  2026-10-17
"""The eval suite: small coding tasks, each graded by hidden tests (plain code, no AI judge).

Splits (the proposer only ever sees `train`):
  train  - failures here are shown to the analyst/proposer
  val    - decides keep/reject (the gate) and the ablation
  test   - never used to decide anything; reported only before and after
"""
from __future__ import annotations

from dataclasses import dataclass

SPLITS = ("train", "val", "test")


@dataclass(frozen=True)
class Task:
    id: str
    family: str
    split: str
    spec: str  # what the builder sees
    entry: str  # function name the tests call
    tests: tuple[str, ...]  # hidden; each is a Python snippet that must not raise
    reference: str  # known-good solution (used to validate the suite itself)


def load_suite() -> list[Task]:
    from .suite_data import TASKS

    return list(TASKS)


def select(tasks: list[Task], *splits: str) -> list[Task]:
    return [t for t in tasks if t.split in splits]
