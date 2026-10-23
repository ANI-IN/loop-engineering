#!/usr/bin/env bash
# Section 4 demos: Hill-climbing loop. Live runs against the OpenAI model in OPENAI_MODEL, traced to LangSmith.
#
# What it runs: `make demo NAME=<slug>` for each core demo of the section, in the order of
# platform/demos/registry.yaml (the list below); with --optional, the optional demos after them.
# One slug as the argument runs that demo alone. Between demos it waits for Enter when run in a
# terminal, so you can watch each one in the console.
#
# The most it can cost: an experiment runs the 25 dev items once and the 15 holdout items
# evaluation.holdout_repeats (3) times (platform/packs/datapilot_us/benchmark/, pack.yaml), so 70
# runs, plus the re-runs that confirm an apparent regression. Each is one verification-loop run,
# and a run stops at the token budget
# budgets.tokens_per_run (60,000 tokens) in platform/packs/datapilot_us/pack.yaml, checked before
# every model and tool call. At the gpt-6-luna output price in pack.yaml ($0.50 per million
# tokens), a run at the cap costs at most about $0.03, plus what its last model call adds past it.
# So one experiment costs at most about $2.10 at the caps, plus those re-runs. The analyzer team
# makes three model calls (failure analyst, rule writer, critic) for each of its analyzer.candidates
# (2) candidates, with no token cap of their own, and each candidate runs the 25 dev items once, so
# 50 more runs. The naive analyzer makes no model call. Cleared for the unattended level is one run. The spend ledger's stop
# line (build_budget in pack.yaml) stops all live work when it is reached.
# Provisional: calibration measures the real cost of three runs for the evidence page.
#
# How long: the class plan's target minutes are CORE_TARGET_MINUTES and OPTIONAL_TARGET_MINUTES
# below. Provisional: calibration measures three runs and the evidence page lists them.
#
# Before it: make up, then make check-data (setup/README.md). Planted bugs are whatever .env sets;
# the demo README says which flag each demo needs. Recovery: make reset NAME=hill-climbing-loop, then run
# the same demo again.
set -euo pipefail

# generated:demo-list
# Written by `make docs` from platform/demos/registry.yaml: edit the registry, not these lines.
SECTION="hill-climbing-loop"
CORE_DEMOS=(improve-baseline-experiment improve-naive-analyzer-blocked improve-analyzer-team-approve improve-candidate-experiment improve-cleared-unattended)
OPTIONAL_DEMOS=(improve-overbroad-rule-blocked)
# The class plan's target minutes, not measured times.
CORE_TARGET_MINUTES=19
OPTIONAL_TARGET_MINUTES=4
# /generated:demo-list

usage() {
  echo "usage: $0 [--optional] [demo slug]"
  echo "  core demos: ${CORE_DEMOS[*]}"
  echo "  optional demos: ${OPTIONAL_DEMOS[*]:-none}"
}

# The repository root is two folders up from this script, so it works from any folder.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

with_optional=0
only=""
for argument in "$@"; do
  case "$argument" in
    --optional) with_optional=1 ;;
    -h|--help) usage; exit 0 ;;
    -*) usage >&2; exit 2 ;;
    *) only="$argument" ;;
  esac
done

demos=("${CORE_DEMOS[@]}")
if [ "$with_optional" -eq 1 ]; then
  demos+=("${OPTIONAL_DEMOS[@]}")
fi
if [ -n "$only" ]; then
  if [[ " ${CORE_DEMOS[*]} ${OPTIONAL_DEMOS[*]} " != *" $only "* ]]; then
    echo "x $only is not a demo of this section" >&2
    usage >&2
    exit 2
  fi
  demos=("$only")
fi

# Checks first: the settings file exists (never read here) and the api answers.
if [ ! -f .env ]; then
  echo "x no .env at the repository root: run make setup and add the two keys" >&2
  exit 1
fi
api="${DATAPILOT_API_URL:-http://localhost:8000}"
if command -v curl >/dev/null 2>&1 && ! curl --silent --fail --max-time 5 "$api/health" >/dev/null; then
  echo "x the api does not answer at $api/health: run make up, then make ps" >&2
  exit 1
fi

echo "Demos for $SECTION: ${demos[*]}"
echo "Class plan target: $CORE_TARGET_MINUTES minutes for the core demos (not a measured time)"
echo "Watch them in the console: http://localhost:${CONSOLE_PORT:-8501}"
for index in "${!demos[@]}"; do
  if [ "$index" -gt 0 ] && [ -t 0 ]; then
    read -r -p "Press Enter for the next demo, ${demos[$index]} " _
  fi
  echo "+ make demo NAME=${demos[$index]}"
  make --no-print-directory demo NAME="${demos[$index]}"
done
