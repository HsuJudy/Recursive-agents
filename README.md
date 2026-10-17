<!-- agent: claude-code  2026-10-17 -->
# A self-improving agent team that has to prove every change

Built at the Recursive Agents Hackathon (Cerebral Valley x Crusoe, 2026-10-17) on Crusoe Managed Inference.

**One sentence.** After each run the team proposes a change to its own rules or setup, and keeps it only if it
helps on tasks it trained on *and* does not hurt tasks it was checked against; then every kept change is removed
one at a time and deleted if the score does not fall.

## What was built today (all of it)
Everything in this repository was written during the hackathon. The idea of "keep a change only if it helps on
held-out tasks" is old and common in machine learning; the code, tasks and harness here are new. No code,
tasks or data were copied from another project or from a public benchmark.

## How it works
- **34 invented coding tasks**, graded by hidden tests run in a separate process (plain code, no AI judge).
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
uv run pytest -q                     # 87 quality tests, no key needed
uv run rah run --offline             # free dry run with a scripted stand-in (NOT a model result)
cp .env.example .env                 # add your own CRUSOE_API_KEY
uv run rah models                    # model ids your key can use
uv run rah run --k 3 --rounds 4      # real run
uv run rah run --swap-builder openai/gpt-oss-120b
```
Results from `--offline` are labelled as such and prove the wiring only.

## Honest limits
- 34 tasks is a small suite; differences of a few points are noise (we use 3 samples per task and paired
  comparisons, and report the spread).
- The removal check takes out one change at a time, so two changes that only help together could be deleted.
- Tasks are small functions. This shows the method, not a claim about large codebases.
- Model ids and tool-calling support differ between Crusoe's docs and API; we do not rely on native tool calling.
