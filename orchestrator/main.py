#!/usr/bin/env python3
"""
Recursive Agents System — Crusoe × Cerebral Valley Hackathon
Build a team of agents you can walk away from.
"""

import sys
import time
from memory.store import SharedMemory
from agents.orchestrator import Orchestrator
from config import MAX_ITERATIONS


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py \"Your high-level goal\"")
        print("Example: python main.py \"Research recursive agent architectures and write a short comparison\"")
        sys.exit(1)

    goal = " ".join(sys.argv[1:])
    print(f"\n🎯 Goal: {goal}\n")

    memory = SharedMemory()
    memory.set_goal(goal)
    orchestrator = Orchestrator(memory)

    iteration = 0
    while iteration < MAX_ITERATIONS and not memory.is_goal_complete():
        iteration += 1
        print(f"\n--- Iteration {iteration} ---")

        # Plan next steps
        plan_result = orchestrator.plan()
        if plan_result.get("done"):
            memory.mark_complete()
            break

        # Execute pending tasks (limit to a few per iteration to stay responsive)
        pending = memory.get_pending_tasks()
        if not pending:
            # Force a critic pass if nothing is pending
            orchestrator.execute_task({
                "agent": "critic",
                "task": "Review progress toward the goal and propose the next concrete task"
            })
        else:
            for task in pending[:3]:  # max 3 tasks per iteration
                print(f"  → {task['agent']}: {task['task'][:100]}")
                orchestrator.execute_task(task)
                memory.update_task(task["id"], {"status": "completed"})
                time.sleep(0.5)  # light rate-limit courtesy

        # Check if we're done
        if orchestrator.evaluate_completion():
            break

    print("\n" + "=" * 50)
    if memory.is_goal_complete():
        print("✅ Goal complete.")
    else:
        print(f"⏹️  Stopped after {iteration} iterations (max={MAX_ITERATIONS}).")

    print(f"\nShared memory saved to: {memory.path}")
    print(f"Results collected: {len(memory.data.get('results', []))}")
    print(f"Tasks processed: {len(memory.data.get('tasks', []))}")


if __name__ == "__main__":
    main()
