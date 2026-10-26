#!/usr/bin/env bash
# Section 3 demos: Event loop. Live runs against the OpenAI model in OPENAI_MODEL, traced to LangSmith.
#
# What it runs: `make demo NAME=<slug>` for each core demo of the section, in the order of
# platform/demos/registry.yaml (the list below); with --optional, the optional demos after them.
# One slug as the argument runs that demo alone. Between demos it waits for Enter when run in a
# terminal, so you can watch each one in the console.
#
# The most it can cost: each demo starts one run, except duplicate events, which starts one
# question run and one digest run (three and two with the missing idempotency and the random
# digest id on). A run stops at the token budget
# budgets.tokens_per_run (60,000 tokens) in platform/packs/datapilot_us/pack.yaml, checked before
# every model and tool call. At the gpt-6-luna output price in pack.yaml ($0.50 per million
# tokens), a run at the cap costs at most about $0.03, plus what its last model call adds past it: the cap is
# checked before each call, so one call that carries a large result can go far past it.
#
# How long: the class plan's target minutes are CORE_TARGET_MINUTES and OPTIONAL_TARGET_MINUTES
# below. The measured times and costs are on the section's evidence page (docs/evidence/)
# and in the demo README.
#
# Before it: make up, make check-data, then make preflight PURPOSE=development (setup/README.md).
# With PLANTED=1 in front, each demo with a planted code bug (PLANTED_DEMOS below) runs its planted
# half: its planted bugs on for its own runs only, never written to .env. A demo with none runs as
# it is, and the script says so. A demo whose only half is planted runs that half
# either way. --list prints the make commands and runs none.
# The demo README says which flag each demo needs. Recovery: make reset NAME=event-loop, then run
# the same demo again.
set -euo pipefail

# generated:demo-list
# Written by `make docs` from platform/demos/registry.yaml: edit the registry, not these lines.
SECTION="event-loop"
CORE_DEMOS=(events-webhook-question events-approval-survives-restart events-duplicate-events events-kill-switch-in-flight)
OPTIONAL_DEMOS=(events-digest-now)
# The demos with a planted code bug: PLANTED=1 in front of this script runs their planted half.
PLANTED_DEMOS=(events-approval-survives-restart events-duplicate-events events-kill-switch-in-flight)
# The class plan's target minutes, not measured times.
CORE_TARGET_MINUTES=15
OPTIONAL_TARGET_MINUTES=3
# /generated:demo-list

usage() {
  echo "usage: $0 [--optional] [--list] [--addresses] [demo slug]"
  echo "  core demos: ${CORE_DEMOS[*]}"
  echo "  optional demos: ${OPTIONAL_DEMOS[*]:-none}"
}

# The repository root is two folders up from this script, so it works from any folder.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

with_optional=0
list_only=0
addresses_only=0
only=""
for argument in "$@"; do
  case "$argument" in
    --optional) with_optional=1 ;;
    --list) list_only=1 ;;
    --addresses) addresses_only=1 ;;
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

in_list() {
  local wanted="$1"
  shift
  [[ " $* " == *" $wanted "* ]]
}

# The PLANTED value for one demo's make command: 1 with PLANTED=1 in front of this script, for a
# demo with a planted code bug; empty otherwise, so a PLANTED=1 in the environment never reaches a
# demo that has no planted bug (make demo refuses it there).
planted_for() {
  if [ "${PLANTED:-}" = "1" ] && in_list "$1" "${PLANTED_DEMOS[@]+"${PLANTED_DEMOS[@]}"}"; then
    echo 1
  fi
}

command_for() {
  local planted
  planted="$(planted_for "$1")"
  echo "make demo NAME=$1${planted:+ PLANTED=1}"
}

if [ "$list_only" -eq 1 ]; then
  for demo in "${demos[@]}"; do
    command_for "$demo"
  done
  exit 0
fi

# The api and console addresses as the settings read them, from the shell or .env, so an
# API_PORT, CONSOLE_PORT, or DATAPILOT_API_URL moved in .env moves this check as it moves make.
read_addresses='from datapilot.settings import get_settings as g
from datapilot.loop4_hill_climbing.preflight import settings_console_url as c
print(g().datapilot_api_url); print(c(g()))'
addresses="$("${UV:-uv}" run --quiet python -c "$read_addresses" 2>/dev/null || true)"
api="$(sed -n 1p <<<"$addresses")"
console="$(sed -n 2p <<<"$addresses")"
api="${api:-http://localhost:8000}"
console="${console:-http://localhost:8501/}"
if [ "$addresses_only" -eq 1 ]; then
  echo "$api"
  echo "$console"
  exit 0
fi

# Checks first: the settings file exists (this script never reads it) and the api answers.
if [ ! -f .env ]; then
  echo "x no .env at the repository root: run make setup and add the two keys" >&2
  exit 1
fi
if command -v curl >/dev/null 2>&1 && ! curl --silent --fail --max-time 5 "$api/health" >/dev/null; then
  echo "x the api does not answer at $api/health: run make up, then make ps" >&2
  exit 1
fi

echo "Demos for $SECTION: ${demos[*]}"
echo "Class plan target: $CORE_TARGET_MINUTES minutes for the core demos (not a measured time)"
echo "Watch them in the console: $console"
for index in "${!demos[@]}"; do
  if [ "$index" -gt 0 ] && [ -t 0 ]; then
    read -r -p "Press Enter for the next demo, ${demos[$index]} " _
  fi
  demo="${demos[$index]}"
  planted="$(planted_for "$demo")"
  if [ "${PLANTED:-}" = "1" ] && [ -z "$planted" ]; then
    echo "  $demo has no planted bug: it runs as it is"
  fi
  echo "+ $(command_for "$demo")"
  make --no-print-directory demo NAME="$demo" PLANTED="$planted"
done
