#!/usr/bin/env bash
# The verification gate: every check that needs no database and no model, each run to the end,
# each result printed on its own line, and a failing exit if any one fails. Run it before every
# commit and every merge (make verify). Nothing here writes a tracked file.
set -uo pipefail

UV="${UV:-uv}"
cd "$(dirname "${BASH_SOURCE[0]}")/../.." || exit 1

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

# The outline must match the owner's final deck (DECISIONS.md, 28 October 2026): generated again
# from a temporary copy of the deck and compared byte for byte; where the deck is absent, checked
# whole against the fingerprint it records.
outline_check() {
  "$UV" run python platform/scripts/check_outline.py
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
run_check "Markdown linter"              "$UV" run python platform/scripts/lint_markdown.py
run_check "relative links and anchors"   "$UV" run python platform/scripts/check_links.py
run_check "data files and schemas"       "$UV" run python platform/scripts/check_repo_files.py data schemas structure
run_check "make targets on pages"        "$UV" run python platform/scripts/check_repo_files.py make-targets
run_check "shell scripts"                bash -c "$UV run python platform/scripts/check_shell_docker.py shellcheck && $UV run python platform/scripts/check_shell_docker.py bash-n"
run_check "workflows (actionlint)"       "$UV" run actionlint
run_check "diagram exports"              "$UV" run python platform/tools/diagrams/export_diagrams.py --check
run_check "image check"                  "$UV" run python platform/scripts/check_images.py
run_check "unit tests"                   "$UV" run pytest -q -m "not integration and not live"

echo
echo "verification gate:"
printf '  %s\n' "${results[@]}"
if [ "$failed" -gt 0 ]; then
  echo "verification gate: $failed of ${#results[@]} checks FAILED; do not commit or merge"
  exit 1
fi
echo "verification gate: all ${#results[@]} checks passed"
