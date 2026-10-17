from agents.base import call_model
from memory.store import SharedMemory


class Tester:
    def __init__(self, memory: SharedMemory):
        self.memory = memory

    def run(self, task: str) -> str:
        system = """You are a testing agent. Review code or results and identify issues.
Suggest concrete fixes. Be specific about what is broken or missing."""
        user = f"Testing task: {task}\n\nContext:\n{self._context()}"
        result = call_model(system, user)
        self.memory.add_result({"agent": "tester", "task": task, "output": result})
        self.memory.add_progress(f"Tester completed: {task[:80]}")
        return result

    def _context(self) -> str:
        return f"Goal: {self.memory.data.get('goal')}\nLatest results: {self.memory.data.get('results', [])[-3:]}"
