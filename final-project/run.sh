#!/usr/bin/env bash
# Final project: your own domain pack, checked and then measured live.
#
#   final-project/run.sh <pack>            the pack check, with the database, and nothing live
#   final-project/run.sh <pack> --live     then a live session and the baseline experiment
#
# What it runs: use-in-your-repo/check_pack.py <pack> --database (no model call); with --live, it
# confirms the DATAPILOT_PACK setting (.env) selects the pack, then make up, make preflight
# PURPOSE=development, and make demo NAME=improve-baseline-experiment.
#
# The most it can cost (--live only): every model run stops at budgets.tokens_per_run in your
# pack.yaml (60,000 tokens in the template). At the gpt-6-luna output price in pack.yaml ($0.50 per
# million tokens) a run at the cap costs about $0.03, plus what its last model call adds past it.
# Preflight makes five runs; the baseline experiment makes three per holdout item and one per dev
# item, and the script prints that count before it starts.
#
# How long: not measured; it depends on your benchmark. Every run goes 8 at a time
# (evaluation.concurrency). Recovery: make reset NAME=hill-climbing-loop, then run it again.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PACK="${1:-}"
LIVE="${2:-}"
if [[ -z "$PACK" || ! -f "platform/packs/$PACK/pack.yaml" ]]; then
  echo "x usage: final-project/run.sh <pack> [--live], with platform/packs/<pack>/pack.yaml" >&2
  exit 2
fi

echo "== the pack check: platform/packs/$PACK (no model calls)"
uv run python use-in-your-repo/check_pack.py "$PACK" --database

if [[ "$LIVE" != "--live" ]]; then
  echo "pack check passed; run it again with --live for the live session and the baseline"
  exit 0
fi

SELECTED="$(uv run python -c "from datapilot.config import active_pack; print(active_pack())")"
if [[ "$SELECTED" != "$PACK" ]]; then
  echo "x DATAPILOT_PACK selects \"$SELECTED\", not \"$PACK\": set DATAPILOT_PACK=$PACK in .env first" >&2
  exit 1
fi

RUNS="$(uv run python -c "
from datapilot.loop4_hill_climbing.pack_files import load_benchmark
items = load_benchmark('$PACK')
print(sum(3 if i.split.value == 'holdout' else 1 for i in items))
")"
echo "== live: five canary runs, then a baseline experiment of $RUNS runs, with your key"

make up
make preflight PURPOSE=development
make demo NAME=improve-baseline-experiment
echo "baseline experiment started: read the holdout ledger on the Improve page (the hill-climbing-runner service serves it)"
