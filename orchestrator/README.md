# Recursive Agents System
A minimal but complete recursive agent framework for the Crusoe × Cerebral Valley Recursive Agents Hackathon.

## Goal
Build a team of agents you can walk away from. An orchestrator takes a high-level goal, spawns specialist sub-agents, tracks progress in shared memory, recovers from failures, and keeps looping until the goal is complete.

## Architecture
- **Orchestrator** — plans, delegates, monitors, re-plans
- **Specialist agents** — Researcher, Coder, Tester, Critic
- **Shared Memory** — persistent JSON store all agents can read/write
- **Continuous loop** — checks progress and continues until done

## Stack
- Python 3.10+
- Crusoe Managed Inference (OpenAI-compatible endpoint)
- NVIDIA Nemotron models
- Simple file-based shared memory

## Web Dashboard

Run the interactive dashboard:

```bash
pip install -r requirements.txt
export CRUSOE_API_KEY="your-key"
python app.py
```

Then open **http://localhost:5000**

Enter a goal and watch the orchestrator and specialist agents work in real time. Progress, tasks, and results update automatically.

## CLI Mode

```bash
python main.py "Your goal here"
```

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your Crusoe API key (or any OpenAI-compatible key):
```bash
export CRUSOE_API_KEY=paste-your-key-here
# Optional: override base URL or model
export CRUSOE_BASE_URL="https://api.inference.crusoecloud.com/v1/"
export MODEL_NAME="nvidia/nemotron-..."  # use the exact model string from Crusoe
```

3. Run with a goal:
```bash
python main.py "Research the top 3 approaches to recursive agents and write a short comparison"
```

## Project Structure
```
recursive-agents/
├── main.py                 # Entry point + main loop
├── config.py               # API settings
├── agents/
│   ├── orchestrator.py     # Planning + coordination
│   ├── researcher.py
│   ├── coder.py
│   ├── tester.py
│   └── critic.py
├── memory/
│   └── store.py            # Shared memory
├── examples/
│   └── demo_goal.txt
└── requirements.txt
```

## Demo Goals
- Research a topic and produce a structured report
- Write a small Python script and verify it
- Analyze requirements and produce an implementation plan

## Notes
- The system is designed to keep running with minimal human input.
- Shared memory persists across turns so agents can recover.
- Replace the model name with the exact Nemotron model available on Crusoe Managed Inference.
