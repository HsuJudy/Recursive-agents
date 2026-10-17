#!/usr/bin/env bash
# agent: claude-code  2026-10-17
# One-command demo of the judging criteria. Default is the free offline stand-in (labelled, NOT a model result).
#   demo/run_demo.sh            offline, no key, about 30 seconds
#   MODE=real demo/run_demo.sh  real run on Crusoe (needs CRUSOE_API_KEY in .env; costs money)
set -euo pipefail
cd "$(dirname "$0")/.."
FLAG="--offline"; [ "${MODE:-offline}" = "real" ] && FLAG=""
PAUSE="${PAUSE:-1}"
OUT="$(mktemp)"
banner() { printf '\n\033[1m== %s ==\033[0m\n' "$1"; sleep "$PAUSE"; }

banner "1. AUTONOMY + LONG-RUNNING LOOP: one command, then nobody touches it"
uv run rah run $FLAG --k 1 --rounds 2 | tee "$OUT"
RUN_ID=$(sed -n 's/^run \([^:]*\):.*/\1/p' "$OUT" | head -1)

banner "2. RECOVERY + PERSISTENCE: pretend the laptop died after round 2; pick up from saved state"
ls runs/versions/"$RUN_ID"
uv run rah run $FLAG --k 1 --rounds 4 --resume "$RUN_ID"

banner "3. DELEGATION: three models, three jobs (builder, verifier, proposer)"
grep -A4 '^models:' harness.yaml

banner "4. THE JUDGES' CHECKLIST, scored by code (no AI judge)"
uv run rah judge --no-record
