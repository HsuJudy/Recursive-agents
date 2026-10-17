from agents.base import call_model
from agents.researcher import Researcher
from agents.coder import Coder
from agents.tester import Tester
from agents.critic import Critic
from memory.store import SharedMemory
import json


class Orchestrator:
    def __init__(self, memory: SharedMemory):
        self.memory = memory
        self.agents = {
            "researcher": Researcher(memory),
            "coder": Coder(memory),
            "tester": Tester(memory),
            "critic": Critic(memory),
        }

    def plan(self) -> list:
        system = """You are the orchestrator of a recursive agent team.
Given a goal and current memory state, produce a short list of concrete next tasks.
Return ONLY valid JSON in this exact format:
{
  "tasks": [
    {"agent": "researcher|coder|tester|critic", "task": "clear description of what to do"}
  ],
  "done": false
}
Set "done": true only if the original goal is fully satisfied."""
        user = f"""Goal: {self.memory.data.get('goal')}

Current state:
- Tasks so far: {len(self.memory.data.get('tasks', []))}
- Completed: {len(self.memory.get_completed_tasks())}
- Recent progress: {self.memory.data.get('progress', [])[-3:]}
- Recent results: {[r.get('agent') for r in self.memory.data.get('results', [])[-3:]]}

What should happen next?"""
        raw = call_model(system, user, temperature=0.2)
        try:
            # Extract JSON if wrapped in markdown
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())
            return data
        except Exception as e:
            self.memory.add_error(f"Failed to parse plan: {e}\nRaw: {raw[:500]}")
            return {"tasks": [{"agent": "critic", "task": "Review current state and propose next concrete steps"}], "done": False}

    def execute_task(self, task: dict) -> str:
        agent_name = task.get("agent", "researcher")
        description = task.get("task", "")
        agent = self.agents.get(agent_name, self.agents["researcher"])
        try:
            result = agent.run(description)
            # Mark task complete in memory if we created one
            return result
        except Exception as e:
            self.memory.add_error(f"{agent_name} failed: {e}")
            return f"Error: {e}"

    def evaluate_completion(self) -> bool:
        plan = self.plan()
        if plan.get("done") is True:
            self.memory.mark_complete()
            return True
        # Add new tasks from the plan
        for t in plan.get("tasks", []):
            self.memory.add_task(t)
        return False
