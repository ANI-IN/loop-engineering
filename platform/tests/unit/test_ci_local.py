"""The local run of the continuous integration workflow: the workflow's own steps, in a clean clone,
with no environment of the shell that started it (zero tokens; throwaway repositories)."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
REPO = SCRIPTS.parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ci_local = _load("ci_local", SCRIPTS / "ci_local.py")

WORKFLOW = """\
name: ci
on: [push]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: the clone is configured as actions/checkout leaves it
        run: test "$(git config --local gc.auto)" = 0
      - name: no key of the parent shell
        run: test -z "${OPENAI_API_KEY:-}" && test -z "${UV_PROJECT_ENVIRONMENT:-}"
      - name: the variables GitHub sets
        run: test "$GITHUB_ACTIONS" = true && test "$CI" = true
      - name: a step's own environment
        env:
          GREETING: hello
        run: test "$GREETING" = hello
      - name: no uncommitted file
        run: test ! -e notes.txt
  test:
    runs-on: ubuntu-latest
    steps:
      - run: STEP
"""


def _repo(root: Path, last_step: str) -> Path:
    root.mkdir()
    workflow = root / ".github" / "workflows" / "ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(WORKFLOW.replace("STEP", last_step), encoding="utf-8")
    git = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@example.com"]
    subprocess.run([*git, "init", "-q", "-b", "main"], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "one"], check=True)
    (root / "notes.txt").write_text("not committed\n", encoding="utf-8")
    return root


linux_only = pytest.mark.skipif(sys.platform == "win32", reason="the runner's commands are Linux")


@linux_only
def test_every_step_runs_in_a_clean_clone_without_the_shells_secrets(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-not-a-real-key")
    monkeypatch.setenv("UV_PROJECT_ENVIRONMENT", "/somewhere/else")
    repo = _repo(tmp_path / "release", "true")
    assert ci_local.main(["--repo", str(repo)]) == 0, capsys.readouterr().out
    out = capsys.readouterr().out
    assert "  skip  lint: actions/checkout@v4 (an action)" in out
    assert out.count("  PASS  ") == 6 and "every step passed" in out


@linux_only
def test_a_failing_step_fails_the_run_and_names_it(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path / "release", "echo the reason; exit 3")
    assert ci_local.main(["--repo", str(repo)]) == 1
    out = capsys.readouterr().out
    assert "  FAIL  test: echo the reason; exit 3 (exit 3)" in out
    assert "        the reason" in out and "do not push" in out


@linux_only
def test_one_job_can_run_alone(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path / "release", "exit 1")
    assert ci_local.main(["--repo", str(repo), "--job", "lint"]) == 0
    assert "test:" not in capsys.readouterr().out


def test_an_unknown_job_is_refused(tmp_path: Path) -> None:
    workflow = tmp_path / "ci.yml"
    workflow.write_text(WORKFLOW, encoding="utf-8")
    with pytest.raises(SystemExit, match="no such job"):
        ci_local.steps(workflow, ["deploy"])


def test_a_step_keeps_nothing_of_the_parent_but_home_path_and_lang() -> None:
    step = ci_local.Step("lint", "x", "true", {"A": "1"})
    parent = {"HOME": "/h", "PATH": "/bin", "OPENAI_API_KEY": "sk-x", "LANGSMITH_API_KEY": "y"}
    assert ci_local.environment(step, parent) == {
        "HOME": "/h",
        "PATH": "/bin",
        "GITHUB_ACTIONS": "true",
        "CI": "true",
        "A": "1",
    }


def test_the_real_workflow_has_steps_for_every_job_and_no_secret() -> None:
    real = REPO / ".github" / "workflows" / "ci.yml"
    found = ci_local.steps(real)
    assert {s.job for s in found} == {"lint", "test", "integration"}
    assert "secrets." not in real.read_text(encoding="utf-8")
