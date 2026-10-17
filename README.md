<!-- agent: claude-code  2026-10-17 -->
# A self-improving agent team that has to prove every change

Built at the Recursive Agents Hackathon (Cerebral Valley x Crusoe, 2026-10-17) on Crusoe Managed Inference.

**One sentence.** After each run the team proposes a change to its own rules or setup, and keeps it only if it
helps on tasks it trained on *and* does not hurt tasks it was checked against; then every kept change is removed
one at a time and deleted if the score does not fall.

## Two parts in one repo
- **`orchestrator/`** is the walk-away team: an orchestrator that spawns Researcher, Coder, Tester and Critic
  agents, keeps shared memory in a JSON file, recovers from failures and loops until the goal is done, with a web
  dashboard. Run it from inside that folder (`cd orchestrator && python main.py "your goal"`); see its README.
- **`src/rah/`** (everything below) is the proof layer: it makes a team improve itself and keeps a change only if it
  measurably helps on tasks it never saw. `uv run rah judge` scores the repo against the hackathon criteria
  (autonomy, delegation, persistence, recovery, long-running loop, stack, clear demo); `demo/run_demo.sh` plays it.

## What was built today (all of it)
Everything in this repository was written during the hackathon. The idea of "keep a change only if it helps on
held-out tasks" is old and common in machine learning; the code, tasks and harness here are new. No code,
tasks or data were copied from another project or from a public benchmark.

## Results (real runs on Crusoe Managed Inference, 2026-10-17)
All numbers are on **unseen test tasks** that no keep, reject or delete decision ever used. Each run is one run, on a
small suite (9 unseen dense tasks, 3 samples each), so treat the size of the gain as approximate.

| Builder model | Kept changes | Unseen test, before | Unseen test, after | Spend |
|---|---|---|---|---|
| `zai-org/GLM-5.3-Flash` | 1: allow a second attempt | **18.5%** | **93.7%** | $1.44 |
| `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | none (two full runs; every proposal rejected) | 79% to 84% | same | about $0.25 to $0.52 per run |

- **GLM-Flash:** round 1 kept "allow a second attempt" (train +70 points, checking +89). The removal check, which uses
  fresh samples, found that taking it out costs 74 points, so it stays. **Caveat:** GLM often ran out of tokens while
  thinking and returned no code. The kept change is mostly a retry that tells it to think less. It is a real change to the
  team's setup that the loop found and proved, but it fixes a truncation problem more than it teaches the model anything.
- **Nemotron Nano:** the gate kept nothing in two full runs (a third was stopped early); it rejected every proposal as a gain it could not tell from
  noise. We then scored one rejected change ("allow a second attempt") on unseen tasks only: 80.0% to 93.6% on the 9 dense
  tasks (standard error 9.2 points) and 97.4% to 99.3% on all 19 unseen tasks. That points the right way but is not proven,
  so the gate was cautious, not wrong. See `demo/confirm_rejected.py`.
- We found along the way that a reasoning model can spend its whole token budget thinking and return nothing. We fixed
  how the harness handles that (the builder is told to think less on a retry, and the proposer is told when it happened).

## Live demo page
`python3 demo/serve.py`, then open http://127.0.0.1:8765. A read-only page that follows `runs/decisions.jsonl` while
`uv run rah run ...` works: a card per decision (kept, rejected, deleted, proved), a clock, and a "goal complete"
banner with the before and after scores on unseen tasks. Press R to replay a finished run. The **Insights** tab charts
how the team improved: score by team version, why each proposal was kept or rejected, task-by-task results,
overconfidence, receipts and spend, all read from `runs/` (open it directly with `?run=RUN_ID&tab=ins`). Any run that is not a
real Crusoe run is labelled as an offline stand-in on the page.

## How this matches the hackathon theme
- **Walk away:** one command starts a run; `--resume RUN_ID` carries on from saved state after a stop.
- **Recovery:** a bad change is rejected by the gate and a useless one is deleted by the removal check; the team carries on.
- **Delegation:** three Crusoe models with three jobs (builder, verifier, proposer); the gate and monitor are plain code.
- **Recursion:** the team changes its own rules and settings, and every change has to survive being removed again.
- **Checked by code:** `uv run rah judge` scores the repo against the judging criteria with no AI judge.

## How it works
- **70 invented coding tasks** in three sets (34 base, 12 harder, 24 "dense" with 8 to 10 requirements each; the real
  runs use the 24 dense ones), graded by hidden tests run in a separate process (plain code, no AI judge).
  Three splits: `train` (the proposer sees failures), `val` (decides keep or reject), `test` (never used to
  decide anything; scored only before and after). One family, `money`, exists only in `test`, to show whether
  a learned rule carries over to a kind of task it never trained on.
- **Team, on three different Crusoe models:** a builder (writes the code *and its own tests*, which are its
  definition of done), a verifier (independent model that reviews the code), a monitor (plain code that stops
  loops and overspending), an analyst and a proposer.
- **Gate:** keep a change if train improves by 3+ points and val does not drop more than 2 points (paired,
  same tasks).
- **Removal check (ablation):** take out each kept change in turn; if the score does not fall by 2+ points,
  delete it. Every kept change carries a receipt with its measured effect.
- **Model swap:** swap the builder for another model and run the removal check again. Changes that survive are
  portable; the rest were quirks of the first model.
- **Overconfidence:** we report how often the team said "done" while the hidden tests disagreed.

## Run it
```bash
uv sync
uv run pytest -q                     # 184 quality tests, no key needed
uv run rah run --offline             # free dry run with a scripted stand-in (NOT a model result)
cp .env.example .env                 # add your own CRUSOE_API_KEY
uv run rah models                    # model ids your key can use
uv run rah run --k 3 --rounds 4      # real run
uv run rah run --swap-builder openai/gpt-oss-120b
```
Results from `--offline` are labelled as such and prove the wiring only.

## Honest limits
- The real runs use 24 dense tasks (9 train, 6 checking, 9 unseen); differences of a few points are noise (we use 3
  samples per task and paired comparisons, and report the spread). Each result above is a single run.
- The tasks are invented, not a public benchmark, so they have not been compared with published scores.
- The removal check takes out one change at a time, so two changes that only help together could be deleted.
- Tasks are small functions. This shows the method, not a claim about large codebases.
- Model ids and tool-calling support differ between Crusoe's docs and API; we do not rely on native tool calling.
