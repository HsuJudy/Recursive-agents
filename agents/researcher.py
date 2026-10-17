from agents.base import call_model
from memory.store import SharedMemory


class Researcher:
    def __init__(self, memory: SharedMemory):
        self.memory = memory

    def run(self, task: str) -> str:
        system = """You are a focused research agent. Gather information, analyze it, and return clear, structured findings.
Be concise and factual. Always return your answer in markdown with clear sections."""
        user = f"Research task: {task}\n\nContext from memory:\n{self._context()}"
        result = call_model(system, user)
        self.memory.add_result({"agent": "researcher", "task": task, "output": result})
        self.memory.add_progress(f"Researcher completed: {task[:80]}")
        return result

    def _context(self) -> str:
        return f"Goal: {self.memory.data.get('goal')}\nRecent results: {self.memory.data.get('results', [])[-2:]}"
