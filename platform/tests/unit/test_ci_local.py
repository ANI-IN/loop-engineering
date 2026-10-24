"""The local run of the continuous integration workflow: the workflow's own steps, each job in its
own clean clone, with no environment of the shell that started it (zero tokens; throwaway
repositories). Review round 3 (R3D-02) found four ways it passed where GitHub fails; each has a
test here."""

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
env:
  TOP: from-the-workflow
jobs:
  lint:
    runs-on: ubuntu-latest
    env:
      LEVEL: from-the-job
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: the clone is configured as actions/checkout leaves it
        run: test "$(git config --local gc.auto)" = 0
      - name: no key of the parent shell
        run: test -z "${OPENAI_API_KEY:-}" && test -z "${UV_PROJECT_ENVIRONMENT:-}"
      - name: a fresh home
        run: test -z "$(ls -A "$HOME")"
      - name: the variables GitHub sets
        run: test "$GITHUB_ACTIONS" = true && test "$CI" = true
      - name: the workflow's, the job's and the step's environment
        env:
          GREETING: hello
        run: |
          test "$GREETING" = hello && test "$LEVEL" = from-the-job
          test "$TOP" = from-the-workflow
      - name: no uncommitted file
        run: test ! -e notes.txt
      - name: the whole history when fetch-depth is 0
        run: test "$(git rev-list --count HEAD)" = 2
      - name: a working directory
        working-directory: sub
        run: test -e here.txt
      - name: leaves a file behind
        run: touch left-by-lint
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: STEP
"""


def _repo(root: Path, test_step: str, workflow: str = WORKFLOW) -> Path:
    root.mkdir()
    (root / "sub").mkdir()
    (root / "sub" / "here.txt").write_text("x\n", encoding="utf-8")
    path = root / ".github" / "workflows" / "ci.yml"
    path.parent.mkdir(parents=True)
    path.write_text(workflow.replace("STEP", test_step), encoding="utf-8")
    git = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@example.com"]
    subprocess.run([*git, "init", "-q", "-b", "main"], check=True)
    subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "zero"], check=True)
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
    assert "  skip  lint: actions/checkout@v4 (the clone is the checkout, depth 0)" in out
    assert out.count("  PASS  ") == 10 and "every step passed" in out


@linux_only
def test_a_failing_step_fails_the_run_and_names_it(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path / "release", "echo the reason; exit 3")
    assert ci_local.main(["--repo", str(repo)]) == 1
    out = capsys.readouterr().out
    assert "  FAIL  test: echo the reason; exit 3 (exit 3)" in out
    assert "        the reason" in out and "do not push" in out


@linux_only
def test_each_job_has_its_own_clone(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path / "release", "test ! -e left-by-lint")
    assert ci_local.main(["--repo", str(repo)]) == 0, capsys.readouterr().out


@linux_only
def test_a_job_without_fetch_depth_gets_one_commit(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path / "release", 'test "$(git rev-list --count HEAD)" = 1')
    assert ci_local.main(["--repo", str(repo), "--job", "test"]) == 0, capsys.readouterr().out


@linux_only
def test_shell_bash_fails_on_a_failing_pipe_as_on_github(tmp_path: Path, capsys) -> None:
    piped = WORKFLOW.replace("      - run: STEP", "      - shell: bash\n        run: false | true")
    repo = _repo(tmp_path / "release", "", piped)
    assert ci_local.main(["--repo", str(repo), "--job", "test"]) == 1
    assert "  FAIL  test: false | true (exit 1)" in capsys.readouterr().out


@linux_only
def test_a_step_without_a_shell_runs_as_bash_e(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path / "release", "false | true")
    assert ci_local.main(["--repo", str(repo), "--job", "test"]) == 0


@linux_only
def test_a_uv_pin_other_than_this_machines_fails(tmp_path: Path, capsys) -> None:
    pinned = WORKFLOW.replace(
        "      - run: STEP",
        "      - uses: astral-sh/setup-uv@v6\n"
        '        with:\n          version: "0.0.1"\n'
        "      - run: true",
    )
    repo = _repo(tmp_path / "release", "", pinned)
    assert ci_local.main(["--repo", str(repo), "--job", "test"]) == 1
    assert "the workflow pins uv 0.0.1; this machine has" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("change", "named"),
    [
        ("      - run: STEP", "      - if: false\n        run: true"),
        ("      - run: STEP", "      - uses: actions/cache@v4"),
        (
            "    steps:\n      - uses: actions/checkout@v4\n      - run: STEP",
            "    services:\n      db:\n        image: postgres\n    steps:\n      - run: true",
        ),
    ],
)
def test_what_ci_local_cannot_run_as_github_does_fails(
    tmp_path: Path, capsys, change: str, named: str
) -> None:
    workflow = tmp_path / "ci.yml"
    workflow.write_text(WORKFLOW.replace(change, named), encoding="utf-8")
    test_job = ci_local.jobs(workflow, ["test"])[0]
    assert test_job.unsupported or any(s.unsupported for s in test_job.steps)


def test_an_unknown_job_is_refused(tmp_path: Path) -> None:
    workflow = tmp_path / "ci.yml"
    workflow.write_text(WORKFLOW, encoding="utf-8")
    with pytest.raises(SystemExit, match="no such job"):
        ci_local.jobs(workflow, ["deploy"])


def test_a_step_keeps_nothing_of_the_parent_but_path_lang_and_uvs_folders() -> None:
    step = ci_local.Step("lint", "x", "true", {"A": "1"})
    parent = {
        "HOME": "/h",
        "PATH": "/bin",
        "UV_CACHE_DIR": "/c",
        "OPENAI_API_KEY": "sk-x",
        "LANGSMITH_API_KEY": "y",
    }
    assert ci_local.environment(step, Path("/fresh"), parent) == {
        "PATH": "/bin",
        "UV_CACHE_DIR": "/c",
        "HOME": "/fresh",
        "GITHUB_ACTIONS": "true",
        "CI": "true",
        "A": "1",
    }


def test_the_real_workflow_runs_every_job_as_github_does_and_names_no_secret() -> None:
    real = REPO / ".github" / "workflows" / "ci.yml"
    found = ci_local.jobs(real)
    assert [j.name for j in found] == ["lint", "test", "integration"]
    assert not any(j.unsupported or any(s.unsupported for s in j.steps) for j in found)
    assert [j.fetch_depth for j in found] == [0, 1, 1]
    assert found[2].compose_projects == ["datapilot-tests"] and found[0].compose_projects == []
    assert "secrets." not in real.read_text(encoding="utf-8")
