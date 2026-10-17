<!-- agent: claude-code  2026-10-17 -->
# Demo pack: live run-of-show, video script, fallback, Q&A, checklist

Everything in square brackets, like [BASELINE %], is a placeholder. Fill it in from the real run. Do not say a number out loud that is not filled in from a real result.

Words used here: **harness** = the team's rules and settings file. **Cache** = a saved copy of earlier model answers, so a replay costs nothing and is fast. **Test tasks** = 16 tasks the team never learns from; they are only scored before and after.

## 0. Rules to remember
- Only show what was built today. Say it once: "Everything you see was written at this event."
- The demo is a terminal. No dashboard, no slides with charts. Big font, dark background.
- Every command below is real and checked against `src/rah/cli.py`. The flags that exist: `--offline`, `--k`, `--rounds`, `--workers`, `--harness`, `--builder`, `--swap-builder`.

## 1. Live run-of-show (3:00)

Before you start: cache is warm, terminal is in `/Users/creator/Atlas/_index/code/crusoe-recursive-agents`, font is large, Wi-Fi is on.

IMPORTANT (read before the first warm-up): a real run overwrites `harness.yaml` with the improved version when it finishes. The next run then starts from that improved file, so its cache keys differ and it will NOT replay cleanly. So: before the warm-up run `cp harness.yaml harness.start.yaml`; before every rehearsal and the live demo run `cp harness.start.yaml harness.yaml`. (If you are unsure, use `--harness harness.start.yaml` on the command; that flag exists.)

| Time | Beat | Type this | Say this |
|---|---|---|---|
| 0:00 to 0:20 | The problem | `clear` then `uv run rah models` | "AI agents say 'done' when they are not. And when they try to improve themselves, nobody checks if the change really helped. Here are the three Crusoe models our team uses." (If Wi-Fi is slow, skip the command and just talk.) |
| 0:20 to 0:40 | Start the real run | `uv run rah run --k 3 --rounds 4 --harness harness.start.yaml` | "One command. First it scores the team on 16 tasks it will never learn from. That is our honest starting line: [BASELINE %]." |
| 0:40 to 1:20 | The loop | (same run, it prints as it goes; do not type) | "Now the team proposes one change to its own rules, tests it, and a plain-code gate decides. Keep means it helped on practice tasks and did not hurt the checking tasks. Watch for keep, reject, delete. This rule was [KEPT / REJECTED] because [TRAIN DELTA] and [VAL DELTA]." |
| 1:20 to 1:50 | Deletion | (same run) | "Here is the part we care about most. After the loop, we take each kept change out, one at a time. If the score does not drop, it gets deleted. [N DELETED] changes were just deleted. Most self-improving agents only ever add." |
| 1:50 to 2:20 | The result table | (same run prints `=== RESULT ===`) Point at the TEST row with your finger or cursor. | "On tasks it never saw: [BASELINE %] before, [AFTER %] after, a change of [CHANGE pts]. On a whole new kind of task, money, it went from [MONEY BEFORE %] to [MONEY AFTER %]. Every kept change shows its receipt: what it earned, and what it costs to remove." |
| 2:20 to 2:40 | Overconfidence | (point at the "said 'done' but was wrong" row) | "This row is how often the team said 'done' and the hidden tests disagreed: [OVERCONF BEFORE %] before, [OVERCONF AFTER %] after." |
| 2:40 to 3:00 | Model swap + close | `uv run rah run --k 3 --rounds 4 --harness harness.start.yaml --swap-builder [MODEL ID]` (only if it was warmed; otherwise just point at the saved result and say it) | "Swap the builder model and run the same removal check. [N PORTABLE] changes still earn their place; [N SPECIFIC] were quirks of the first model. Spend for the whole run: [COST $]. Thank you." |

Timing note: a fully cached run replays in seconds to a minute or two; a live run of this size will not fit 3 minutes. For the stage, always use the warmed cache (Section 3, step 0). If the replay is much faster than the narration, slow down and talk; do not add commands.

Q&A (1 to 2 minutes): keep the terminal open on the result table.

## 2. One-minute video script (with audio)

Record the terminal screen plus your voice. Record last, after one full clean run. Aim for 150 words of narration; leave pauses.

| Time | On screen | Narration |
|---|---|---|
| 0:00 to 0:08 | Terminal, clear, the title line `A self-improving agent team that has to prove every change` (from README, shown with `head -1 README.md`) | "AI agents say 'done' when they are not, and self-improving agents rarely prove that a change helped. We built a team that has to." |
| 0:08 to 0:16 | Type `uv run rah run --k 3 --rounds 4`; first line prints the run id and "34 tasks" | "One command, 34 invented coding tasks, graded by hidden tests. No AI judge." |
| 0:16 to 0:26 | The baseline line: `unseen test baseline: [BASELINE %]` | "First we score the team on 16 tasks it will never learn from: [BASELINE %]. That is the honest starting line." |
| 0:26 to 0:38 | Loop lines streaming: keep / reject | "Then it proposes one change at a time to its own rules or setup. A plain-code gate keeps a change only if it helps practice tasks and does not hurt the checking tasks." |
| 0:38 to 0:46 | Delete lines from the removal check | "Then the part we are proudest of: every kept change is taken out again, and deleted if the score does not fall." |
| 0:46 to 0:54 | The RESULT table, TEST row and money row highlighted | "On unseen tasks: [BASELINE %] to [AFTER %]. On a brand-new kind of task: [MONEY BEFORE %] to [MONEY AFTER %]." |
| 0:54 to 1:00 | The model swap lines, then the spend line | "Swap the builder model and the same check shows which lessons are portable. Whole run: [COST $]. Built today on Crusoe." |

Video checks: audio is audible, font is readable on a phone, no `.env` or key visible, length is under 60 seconds, file under the upload limit.

## 3. Fallback plan if Wi-Fi or the API fails (do these in order)

Cached results replay from `runs/cache.jsonl` (the code reads it automatically; no flag needed).

0. Prevention: warm the cache with one full run the night before and again at the venue. Back up the cache: `cp runs/cache.jsonl runs/cache.backup.jsonl`.
1. Say nothing alarming. Say: "Wi-Fi is slow, so I will replay the saved run; the answers are the real saved model answers."
2. Make sure the starting file is the original: `cp harness.start.yaml harness.yaml`.
3. Run the same command as the warm-up, with the same flags: `uv run rah run --k 3 --rounds 4`. Same flags matter: the cache is matched on exact settings, so a different `--k`, `--rounds` or harness will try to call the API.
4. If it still tries to reach the API and hangs: stop it (Ctrl+C), restore `cp runs/cache.backup.jsonl runs/cache.jsonl`, repeat step 2 and 3.
5. If the cache is missing or broken: run `uv run rah run --offline`. It is a free scripted stand-in and prints the label "OFFLINE stand-in, not a model result". You must say that out loud. It shows the wiring only, never claim its numbers as model results.
6. If the terminal itself fails: play the one-minute demo video (Section 2) full screen and narrate over it. Have the file on the laptop and on a phone.
7. Never fake a result. If asked, say which fallback you used.

## 4. Likely judge questions and honest short answers

**Is this novel?**
Partly. Self-improving agents, prompt tuning and held-out checking are all known ideas, and we say so in the README. What we added: deletion is a first-class step (every kept change must survive being removed); every change carries a receipt with its measured effect; a model swap separates portable lessons from model quirks; and we measure how often the team says "done" while hidden tests disagree.

**Why only 34 tasks?**
We had hours, not weeks, and each task needs a hand-written reference answer and hidden tests that we check for correctness. 34 is small, so we use 3 tries per task, compare the same tasks before and after, and report the spread. Differences of a few points are noise, and we say that. More tasks is the first thing we would add.

**How do you know it is not overfitting?**
Three guards. The change is judged on tasks the proposer never sees (the checking set). The final score is on 16 test tasks that never influenced any decision. One kind of task, money, exists only in the test set. Also, a rule is rejected if it copies task text. Limit: with 34 tasks we can reduce overfitting, not rule it out. Test result: [BASELINE %] to [AFTER %] (spread [SPREAD]).

**What does the model swap show?**
We keep the kept changes, swap the builder to [MODEL ID], and run the removal check again. A change that still earns its place is portable; one that no longer helps was a quirk of the first model. Result: [N PORTABLE] portable, [N SPECIFIC] specific. Limit: one swap on one suite, so a hint, not proof.

**Did you build this today? What is reused?**
All code, tasks and harness were written at the event. The general idea (held-out validation) is old. No code or data copied from another project or public benchmark.

**What are the limits?**
Tasks are small functions, not large codebases. The removal check takes out one change at a time, so two changes that only help together could be wrongly deleted. We do not rely on native tool calling because model support differed between docs and API.

**What does it cost?**
[COST $] for the full run, [CALLS] model calls. A replay from cache costs nothing.

**What is the future potential?**
Plug in a team's own real tasks as the suite, and the same loop gives them a harness whose every rule has a receipt and can be audited again whenever the model changes. [Fill in one concrete next step you really plan.]

**Is that a dashboard?**
No. It is a terminal command; the output is text.

## 5. Pre-demo checklist

Do these in order. Tick each one.

- [ ] `.env` exists with `CRUSOE_API_KEY` set (copy from `.env.example`). Never show `.env` on screen or in the video.
- [ ] Billing card is added on the Crusoe account (needed for the higher request rate). Alexandra does this herself; the agent cannot.
- [ ] `uv run rah models` prints model ids; the builder, verifier, proposer ids in `harness.yaml` are in that list.
- [ ] `uv run pytest -q` passes (87 tests).
- [ ] `cp harness.yaml harness.start.yaml` done BEFORE the first real run.
- [ ] Cache warmed: one full `uv run rah run --k 3 --rounds 4` finished. Optionally also one with `--swap-builder [MODEL ID]`.
- [ ] `runs/cache.jsonl` exists and is backed up to `runs/cache.backup.jsonl`.
- [ ] `cp harness.start.yaml harness.yaml` done again, then a rehearsal replay with the exact demo command finishes fast with no API errors.
- [ ] Placeholders in Sections 1, 2 and 4 are filled from the real result, and the spoken numbers match the screen.
- [ ] Terminal font size large (readable from the back of the room, around 20 to 24 pt), dark theme, notifications off, battery charged, charger plugged in.
- [ ] Terminal opened in the project folder and `clear`ed.
- [ ] Wi-Fi tested at the venue; phone hotspot ready as a backup.
- [ ] One-minute video recorded with audio, under 60 seconds, watched once start to finish, copy on laptop and phone.
- [ ] Video and repo submitted before the deadline [DEADLINE TIME].
- [ ] Practised the 3-minute run twice with a timer.
