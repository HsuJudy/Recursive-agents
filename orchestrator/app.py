#!/usr/bin/env python3
"""
Web dashboard for the Recursive Agents system.
Run with: python app.py
"""

import threading
import time
from flask import Flask, render_template, request, jsonify
from memory.store import SharedMemory
from agents.orchestrator import Orchestrator
from config import MAX_ITERATIONS

app = Flask(__name__)

# Global state for the current run
current_thread = None
running = False


def agent_loop(goal: str):
    global running
    memory = SharedMemory()
    memory.set_goal(goal)
    orchestrator = Orchestrator(memory)

    iteration = 0
    try:
        while iteration < MAX_ITERATIONS and not memory.is_goal_complete():
            iteration += 1
            memory.add_progress(f"Iteration {iteration} started")

            plan_result = orchestrator.plan()
            if plan_result.get("done"):
                memory.mark_complete()
                break

            pending = memory.get_pending_tasks()
            if not pending:
                orchestrator.execute_task({
                    "agent": "critic",
                    "task": "Review progress toward the goal and propose the next concrete task"
                })
            else:
                for task in pending[:2]:  # keep it responsive
                    orchestrator.execute_task(task)
                    memory.update_task(task["id"], {"status": "completed"})
                    time.sleep(0.3)

            orchestrator.evaluate_completion()

        if not memory.is_goal_complete():
            memory.add_progress(f"Stopped after {iteration} iterations")
    except Exception as e:
        memory.add_error(str(e))
        memory.add_progress(f"Error: {e}")
    finally:
        running = False


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/start", methods=["POST"])
def start():
    global current_thread, running
    data = request.get_json() or {}
    goal = data.get("goal", "").strip()
    if not goal:
        return jsonify({"error": "goal required"}), 400
    if running:
        return jsonify({"error": "already running"}), 400

    running = True
    current_thread = threading.Thread(target=agent_loop, args=(goal,), daemon=True)
    current_thread.start()
    return jsonify({"status": "started"})


@app.route("/api/state")
def state():
    memory = SharedMemory()
    return jsonify({
        "status": memory.data.get("status", "idle"),
        "goal": memory.data.get("goal"),
        "tasks": memory.data.get("tasks", []),
        "results": memory.data.get("results", []),
        "progress": memory.data.get("progress", []),
        "errors": memory.data.get("errors", []),
        "running": running,
    })


if __name__ == "__main__":
    print("Recursive Agents Dashboard")
    print("Open http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
