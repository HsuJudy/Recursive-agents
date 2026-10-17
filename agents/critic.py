from agents.base import call_model
from memory.store import SharedMemory


class Critic:
    def __init__(self, memory: SharedMemory):
        self.memory = memory

    def run(self, task: str) -> str:
        system = """You are a critic agent. Evaluate the quality of work so far.
Identify gaps, risks, and concrete next steps. Be direct and constructive."""
        user = f"Critique task: {task}\n\nFull context:\n{self._context()}"
        result = call_model(system, user)
        self.memory.add_result({"agent": "critic", "task": task, "output": result})
        self.memory.add_progress(f"Critic completed: {task[:80]}")
        return result

    def _context(self) -> str:
        return str({
            "goal": self.memory.data.get("goal"),
            "tasks": self.memory.data.get("tasks", []),
            "results_count": len(self.memory.data.get("results", [])),
            "status": self.memory.data.get("status"),
        })
