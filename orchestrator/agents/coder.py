from agents.base import call_model
from memory.store import SharedMemory


class Coder:
    def __init__(self, memory: SharedMemory):
        self.memory = memory

    def run(self, task: str) -> str:
        system = """You are a coding agent. Write clean, working Python code.
Always return complete, runnable code in a markdown code block.
Prefer simple, correct solutions over complex ones."""
        user = f"Coding task: {task}\n\nContext:\n{self._context()}"
        result = call_model(system, user)
        self.memory.add_result({"agent": "coder", "task": task, "output": result})
        self.memory.add_progress(f"Coder completed: {task[:80]}")
        return result

    def _context(self) -> str:
        return f"Goal: {self.memory.data.get('goal')}"
