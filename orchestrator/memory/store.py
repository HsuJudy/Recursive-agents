import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from config import MEMORY_PATH


class SharedMemory:
    """Simple persistent shared memory for agents."""

    def __init__(self, path: str = MEMORY_PATH):
        self.path = path
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r") as f:
                    return json.load(f)
            except Exception:
                return self._empty()
        return self._empty()

    def _empty(self) -> Dict[str, Any]:
        return {
            "goal": None,
            "plan": [],
            "tasks": [],
            "results": [],
            "progress": [],
            "errors": [],
            "status": "idle",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

    def save(self) -> None:
        self.data["updated_at"] = datetime.utcnow().isoformat()
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)

    def set_goal(self, goal: str) -> None:
        self.data["goal"] = goal
        self.data["status"] = "planning"
        self.save()

    def add_task(self, task: Dict[str, Any]) -> None:
        task["id"] = len(self.data["tasks"]) + 1
        task["status"] = "pending"
        task["created_at"] = datetime.utcnow().isoformat()
        self.data["tasks"].append(task)
        self.save()

    def update_task(self, task_id: int, updates: Dict[str, Any]) -> None:
        for task in self.data["tasks"]:
            if task.get("id") == task_id:
                task.update(updates)
                task["updated_at"] = datetime.utcnow().isoformat()
                break
        self.save()

    def add_result(self, result: Dict[str, Any]) -> None:
        result["timestamp"] = datetime.utcnow().isoformat()
        self.data["results"].append(result)
        self.save()

    def add_progress(self, message: str) -> None:
        entry = {"message": message, "timestamp": datetime.utcnow().isoformat()}
        self.data["progress"].append(entry)
        self.save()

    def add_error(self, error: str) -> None:
        entry = {"error": error, "timestamp": datetime.utcnow().isoformat()}
        self.data["errors"].append(entry)
        self.save()

    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        return [t for t in self.data["tasks"] if t.get("status") == "pending"]

    def get_completed_tasks(self) -> List[Dict[str, Any]]:
        return [t for t in self.data["tasks"] if t.get("status") == "completed"]

    def is_goal_complete(self) -> bool:
        return self.data.get("status") == "complete"

    def mark_complete(self) -> None:
        self.data["status"] = "complete"
        self.add_progress("Goal marked as complete by orchestrator.")
        self.save()
