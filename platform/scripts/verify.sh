#!/usr/bin/env bash
# The verification gate: every check that needs no database and no model, each run to the end,
# each result printed on its own line, and a failing exit if any one fails. Run it before every
# commit and every merge (make verify). Nothing here writes a tracked file.
set -uo pipefail

UV="${UV:-uv}"
cd "$(dirname "${BASH_SOURCE[0]}")/../.."

results=()
failed=0

run_check() {
  local name="$1"; shift
  local log
  log="$(mktemp)"
  if "$@" >"$log" 2>&1; then
    results+=("PASS  $name")
  else
    results+=("FAIL  $name")
    failed=$((failed + 1))
    echo "---- $name failed; last lines:"
    tail -n 15 "$log"
  fi
  rm -f "$log"
}

# The outline must build with no problems and match the committed slides/outline.md.
outline_check() {
  local built report
  built="$(mktemp)"
  report="$("$UV" run python slides/source/build.py "$built")" || { rm -f "$built"; echo "$report"; return 1; }
  echo "$report" | tail -n 3
  if ! echo "$report" | grep -qx "problems: 0"; then rm -f "$built"; return 1; fi
  if ! diff -q "$built" slides/outline.md >/dev/null; then
    echo "slides/outline.md is out of date: run make outline and commit it"
    rm -f "$built"; return 1
  fi
  rm -f "$built"
}

# Commit messages are read by the guards script, which resolves the git directory itself (an
# agent worktree under WSL has a .git file naming a C:/ path that git there cannot follow), fails
# when git fails, and skips the check in a public copy, where it is not a rule of a learner's commits.
commit_messages_check() {
  "$UV" run python platform/scripts/check_repo_guards.py --commit-messages
}

run_check "repository guards"            "$UV" run python platform/scripts/check_repo_guards.py
run_check "ruff check"                   "$UV" run ruff check .
run_check "ruff format"                  "$UV" run ruff format --check .
run_check "import contracts"             "$UV" run lint-imports
run_check "prose lint"                   "$UV" run python platform/scripts/lint_prose.py
run_check "style check, strict"          "$UV" run python platform/scripts/check_style.py --strict
run_check "naming check, course pages"   "$UV" run python platform/scripts/check_style.py --names-only
run_check "naming check, outline"        "$UV" run python platform/scripts/short_forms.py slides/outline.md
run_check "naming check, commit messages" commit_messages_check
run_check "docs check"                   "$UV" run python platform/tools/generators/render.py --check
run_check "outline check"                outline_check
run_check "unit tests"                   "$UV" run pytest -q -m "not integration and not live"

echo
echo "verification gate:"
printf '  %s\n' "${results[@]}"
if [ "$failed" -gt 0 ]; then
  echo "verification gate: $failed of ${#results[@]} checks FAILED; do not commit or merge"
  exit 1
fi
echo "verification gate: all ${#results[@]} checks passed"
