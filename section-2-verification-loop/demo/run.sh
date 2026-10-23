#!/usr/bin/env bash
# Section 2 demos: Verification loop. Live runs against the OpenAI model in OPENAI_MODEL, traced to LangSmith.
#
# What it runs: `make demo NAME=<slug>` for each core demo of the section, in the order of
# platform/demos/registry.yaml (the list below); with --optional, the optional demos after them.
# One slug as the argument runs that demo alone. Between demos it waits for Enter when run in a
# terminal, so you can watch each one in the console.
#
# The most it can cost: malicious SQL and the cost guard make no model call; they send fixed
# statements through the defense layers. The retry cap and every grader passes, still wrong each
# start one run, and a run stops at the token budget, retries and the reviewer included:
# budgets.tokens_per_run (60,000 tokens) in platform/packs/datapilot_us/pack.yaml, checked before
# every model and tool call. At the gpt-6-luna output price in pack.yaml ($0.50 per million
# tokens), a run at the cap costs at most about $0.03, plus what its last model call adds past it.
# With the missing retry cap on, the retry-cap run loops until that budget stops it.
# Provisional: calibration measures the real cost of three runs for the evidence page.
#
# How long: the class plan's target minutes are CORE_TARGET_MINUTES and OPTIONAL_TARGET_MINUTES
# below. Provisional: calibration measures three runs and the evidence page lists them.
#
# Before it: make up, then make check-data (setup/README.md). Planted bugs are whatever .env sets;
# the demo README says which flag each demo needs. Recovery: make reset NAME=verification-loop, then run
# the same demo again.
set -euo pipefail

# generated:demo-list
# Written by `make docs` from platform/demos/registry.yaml: edit the registry, not these lines.
SECTION="verification-loop"
CORE_DEMOS=(verify-malicious-sql verify-retry-cap verify-graders-pass-still-wrong)
OPTIONAL_DEMOS=(verify-cost-guard)
# The class plan's target minutes, not measured times.
CORE_TARGET_MINUTES=12
OPTIONAL_TARGET_MINUTES=3
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
