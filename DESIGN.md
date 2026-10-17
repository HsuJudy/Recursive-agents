<!-- agent: claude-code  2026-10-17 -->
# Design: a team that only keeps changes it can prove

**Track:** Version N+1 (with Done Means Done built in). **Platform:** Crusoe Managed Inference.

## Claim
After each run the team proposes a change to its own rules or setup. A change stays only if it lifts the score on
tasks it trained on and does not hurt tasks it was checked against. Every kept change is later removed one at a
time, and deleted if the score does not fall. Swap the builder model and the same check shows which changes were
only quirks of the old model.

## What is new here, and what is not
Not new: self-improving agents, prompt optimisation, held-out validation. Our twist: (1) **deletion** is a
first-class step, not only adding; (2) every change carries a **receipt** (measured effect); (3) a **model swap
re-audit** separates portable lessons from model-specific ones; (4) we measure the **overconfidence gap**: runs where
the team said "done" and the hidden tests disagreed.

## The team (three models, three jobs)
| Role | Does | Model (confirm with `rah models`) |
|---|---|---|
| Builder | writes the code and its own tests (its definition of done); retries if told to | Nemotron-3-Nano |
| Verifier | reviews code against the task, without seeing the builder's reasoning | DeepSeek-V4-Flash |
| Monitor | plain code: stops repeated errors and overspend | none |
| Analyst + Proposer | group failures from train tasks; propose exactly one change | DeepSeek-V4-Pro |
| Gate | plain code: applies the rules below | none |

What the harness can change about itself: a **rule** (max 200 characters, rejected if it copies task text) or a
**team setting** (self-tests on/off, verifier on/off, edge-case listing on/off, attempts 1 to 4).

## The eval suite
34 invented coding tasks, graded by hidden tests in a separate process. No AI judge.
- `train` 12: the proposer sees failures. `val` 6: decides keep or reject. `test` 16: never used to decide anything;
  scored only before and after. Family `money` is test-only (a kind of task never trained on).
- The suite checks itself: every reference answer passes, known-wrong answers fail, infinite loops are stopped.

## The loop
1. Score the starting harness. 2. Propose one change. 3. **Gate:** keep if train rises by at least 3 points and val
does not fall by more than 2 (paired, same tasks). 4. Repeat for N rounds. 5. **Removal check:** drop each kept change
in turn, oldest first; delete it if the score falls by less than 2 points. 6. Score unseen `test` before and after.
7. Optional: swap builder model, run step 5 again.

## Demo (3 minutes, live, terminal plus a read-only live page)
Baseline on unseen tasks, then the loop streaming keep/reject/delete lines, then before and after on unseen tasks,
the overconfidence number, then the model swap. Results are cached, so the live run replays quickly; a screen
recording is the fallback if Wi-Fi fails.

## Risks
| Risk | Handling |
|---|---|
| Baseline near 0% or 100% (no room to improve) | calibrate with a cheap run; swap in the harder task pack |
| Noise on a small suite | 3 samples per task, paired comparison, report spread, state limits |
| Proposer memorises tasks | train-only failure reports, copy check against all tasks, val gate |
| Spend or rate limits | call cap, per-run cost shown, card added for 600 requests/min |
| Rules say "new work only" | fresh repo today; README states what was built at the event |

## Work packages
| id | what | needs key | status |
|---|---|---|---|
| WP1 | eval suite, sandbox, team, loop, offline dry run, 87 tests | no | done |
| WP2 | independent code review of `src/` (report only) | no | in progress |
| WP3 | spare "hard pack" of extra tasks, in case baseline is too high | no | in progress |
| WP4 | demo script and 1-minute video plan | no | in progress |
| WP5 | `rah models`, baseline run, calibrate | yes | waiting for key |
| WP6 | full run, model swap, record demo, submit | yes | waiting for key |
