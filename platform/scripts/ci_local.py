"""Run the continuous integration workflow's own commands in clean clones, as GitHub runs them.

    uv run python platform/scripts/ci_local.py --repo CLONE          # every job, at CLONE's HEAD
    uv run python platform/scripts/ci_local.py --repo CLONE --job lint --job test

Run it in Linux (WSL) on the release commit before every push of the public repository: a push is
made only when this exits with 0. It reads .github/workflows/ci.yml from that commit and, for each
job, as a runner would:

- clones the commit afresh, at the depth the job's actions/checkout step asks for (`fetch-depth`,
  1 when absent, 0 for the whole history), and sets the git configuration the checkout writes
  (gc.auto and an authorization header, with a placeholder value);
- refuses a setup-uv step whose pinned version differs from this machine's uv;
- runs each `run:` step with the shell GitHub uses: `bash -e` by default, and `bash --noprofile
  --norc -eo pipefail` for `shell: bash`; in its `working-directory`; with the workflow's, the
  job's and the step's `env:`.

Each step gets a minimal environment, never this shell's: PATH, LANG, a fresh empty HOME, the
variables GitHub sets (GITHUB_ACTIONS, CI), and uv's own cache and Python folders, so nothing is
downloaded again. No API key, no .env setting and no UV_PROJECT_ENVIRONMENT reaches a step, and no
build-only or internal file is in a clone unless the commit ships it. A key or an action this
script does not run as GitHub does (`if:`, a matrix, a service container, another action) fails
the run rather than being skipped.

A job that starts a Compose project (`docker compose -p NAME`, the integration job's tests'
database on port 55432) holds the lock `make test-integration` holds, and starts from an empty
volume, as a fresh runner does: the project is taken down with its volumes before the job and
after it. The next `make test-stack` builds the tests' database again.
"""

from __future__ import annotations

import argparse
import fcntl
import os
import re
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import yaml

WORKFLOW = Path(".github/workflows/ci.yml")
# What actions/checkout leaves in the clone's own configuration; the value is a placeholder.
CHECKOUT_CONFIG = {
    "gc.auto": "0",
    "http.https://github.com/.extraheader": "AUTHORIZATION: basic placeholder",
}
GITHUB_ENV = {"GITHUB_ACTIONS": "true", "CI": "true"}
PASSED_THROUGH = ("PATH", "LANG")
CHECKOUT, SETUP_UV = "actions/checkout", "astral-sh/setup-uv"
JOB_KEYS = {"runs-on", "steps", "env", "name", "timeout-minutes"}
STEP_KEYS = {"name", "run", "uses", "with", "env", "shell", "working-directory", "id"}
SHELLS = {
    None: ["bash", "-e", "-c"],
    "bash": ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c"],
}
TEST_LOCK = Path("/tmp/datapilot-tests-database.lock")  # the Makefile's TEST_LOCK
# Every way a step can name the Compose project its commands act on: the option in any spelling
# (-p NAME, -pNAME, -p=NAME, --project-name NAME or =NAME, quoted or a variable), of docker compose
# or docker-compose, and COMPOSE_PROJECT_NAME set on the line or in a workflow, job, or step env:.
# A compose command is docker, then anything on the same command (extra spaces, global options
# such as --context), then compose; docker-compose matches too.
COMPOSE_COMMAND = re.compile(r"\bdocker\b[^\n;&|]*?\bcompose\b")
# What separates one shell command from the next in a step's run text.
COMMAND_BREAK = re.compile(r"[\n;&|]")
PROJECT_OPTION = re.compile(r"\s(?:-p|--project-name)(?:=|\s*)(['\"]?)([^\s'\"]+)\1")
INLINE_PROJECT = re.compile(r"\bCOMPOSE_PROJECT_NAME=(['\"]?)([^\s'\"]*)\1")
# A compose command naming no project acts on compose.yaml's own name: the class project.
NO_PROJECT = "none named (compose.yaml's own name, datapilot)"
# The one Compose project a job may take down with its volumes: the tests' own (the Makefile's
# TEST_STACK). The class project, datapilot, holds the class database and is never touched.
TESTS_PROJECT = "datapilot-tests"


class ProjectRefused(RuntimeError):
    """A workflow names a Compose project ci_local would take down that is not the tests' own."""


def refused_projects(projects: list[str]) -> list[str]:
    return [project for project in projects if project != TESTS_PROJECT]


@dataclass
class Step:
    job: str
    name: str
    run: str | None  # None: an action
    env: dict[str, str]
    uses: str | None = None
    shell: str | None = None
    directory: str | None = None
    with_: dict[str, str] = field(default_factory=dict)
    unsupported: list[str] = field(default_factory=list)  # what ci_local cannot run as GitHub does


@dataclass
class Job:
    name: str
    steps: list[Step]
    unsupported: list[str] = field(default_factory=list)

    @property
    def fetch_depth(self) -> int:
        """The checkout's depth: 1 when absent, as actions/checkout; 0 is the whole history."""
        for step in self.steps:
            if step.uses and step.uses.split("@")[0] == CHECKOUT:
                return int(step.with_.get("fetch-depth", 1))
        return 1

    @property
    def compose_projects(self) -> list[str]:
        return sorted({project for step in self.steps for project in step_projects(step)})


def step_projects(step: Step) -> list[str]:
    """The Compose projects a step names; a variable, an empty name, or a compose command that
    names none is returned as it stands, so refused_projects refuses it.

    Each compose command is judged on its own: its project is its own option, else a
    COMPOSE_PROJECT_NAME= set on that same command, else the step's env:, else none named, which
    is compose.yaml's own name. A project another command named never covers it."""
    run = (step.run or "").replace("\\\n", " ")  # a continued line is one command
    found = [name for _quote, name in INLINE_PROJECT.findall(run)]
    from_env = step.env.get("COMPOSE_PROJECT_NAME")
    if from_env is not None:
        found.append(from_env)
    for command in COMMAND_BREAK.split(run):
        compose = COMPOSE_COMMAND.search(command)
        if compose is None:
            continue
        named = [name for _quote, name in PROJECT_OPTION.findall(command[compose.end() :])]
        inline = INLINE_PROJECT.findall(command[: compose.start()])
        if not named and not inline and from_env is None:
            found.append(NO_PROJECT)
        found += named
    return [name or NO_PROJECT for name in found]


def _text(value: object) -> str:
    return (
        str(value).lower() if isinstance(value, bool) else str(value)
    )  # YAML reads `true` as bool


def jobs(workflow: Path, only: list[str] | None = None) -> list[Job]:
    """The workflow's jobs in the file's order; `only` keeps those jobs, and an unknown name is an
    error. Workflow, job and step `env:` are merged into each step's environment."""
    spec = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    names = list(spec["jobs"])
    unknown = sorted(set(only or []) - set(names))
    if unknown:
        raise SystemExit(f"x no such job in {workflow}: {', '.join(unknown)}")
    top_env = {k: _text(v) for k, v in (spec.get("env") or {}).items()}
    out = []
    for name in names:
        if only and name not in only:
            continue
        body = spec["jobs"][name]
        job_env = {**top_env, **{k: _text(v) for k, v in (body.get("env") or {}).items()}}
        found = []
        for raw in body["steps"]:
            run = None if raw.get("run") is None else _text(raw["run"])
            label = raw.get("name") or (run.strip().splitlines()[0] if run else raw["uses"])
            step = Step(
                job=name,
                name=label,
                run=run,
                env={**job_env, **{k: _text(v) for k, v in (raw.get("env") or {}).items()}},
                uses=raw.get("uses"),
                shell=raw.get("shell"),
                directory=raw.get("working-directory"),
                with_={k: _text(v) for k, v in (raw.get("with") or {}).items()},
                unsupported=sorted(set(raw) - STEP_KEYS),
            )
            if step.shell not in SHELLS:
                step.unsupported.append(f"shell: {step.shell}")
            if step.uses and step.uses.split("@")[0] not in (CHECKOUT, SETUP_UV):
                step.unsupported.append(f"the action {step.uses}")
            found.append(step)
        extra = sorted(set(body) - JOB_KEYS)
        if spec.get("defaults") or body.get("defaults"):
            extra.append("defaults")
        out.append(Job(name, found, extra))
    return out


def environment(step: Step, home: Path, parent: dict[str, str] | None = None) -> dict[str, str]:
    """The step's whole environment: of the parent only PATH, LANG, and uv's own folders."""
    parent = os.environ if parent is None else parent
    env = {k: parent[k] for k in PASSED_THROUGH if k in parent}
    for key in ("UV_CACHE_DIR", "UV_PYTHON_INSTALL_DIR"):
        if key in parent:
            env[key] = parent[key]
    return {**env, "HOME": str(home), **GITHUB_ENV, **step.env}


def uv_folders() -> dict[str, str]:
    """This machine's uv cache and Python folders, so a fresh HOME downloads nothing again."""
    out = {}
    for key, args in (
        ("UV_CACHE_DIR", ["cache", "dir"]),
        ("UV_PYTHON_INSTALL_DIR", ["python", "dir"]),
    ):
        done = subprocess.run(["uv", *args], capture_output=True, text=True)
        if done.returncode == 0 and done.stdout.strip():
            out[key] = done.stdout.strip()
    return out


def uv_version() -> str:
    done = subprocess.run(["uv", "--version"], capture_output=True, text=True, check=True)
    return done.stdout.split()[1]


def clone(repo: Path, dest: Path, depth: int) -> None:
    deep = [] if depth == 0 else ["--depth", str(depth)]
    subprocess.run(
        ["git", "clone", "--quiet", "--no-local", *deep, repo.as_uri(), str(dest)], check=True
    )
    for key, value in CHECKOUT_CONFIG.items():
        subprocess.run(["git", "-C", str(dest), "config", "--local", key, value], check=True)


@contextmanager
def empty_compose_projects(projects: list[str], work: Path):
    """Hold the tests' database lock, and run the job on empty volumes, as a fresh runner does."""
    if not projects:
        yield
        return
    if refused := refused_projects(projects):
        raise ProjectRefused(
            f"not taken down: Compose project {', '.join(refused)} is not the tests' own "
            f"({TESTS_PROJECT}); ci_local empties only that one"
        )
    with TEST_LOCK.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        down = [
            ["docker", "compose", "-p", p, "down", "--volumes", "--remove-orphans"]
            for p in projects
        ]
        try:
            for command in down:
                subprocess.run(command, cwd=work, capture_output=True, check=True)
            yield
        finally:
            for command in down:
                subprocess.run(command, cwd=work, capture_output=True)


def run_job(repo: Path, job: Job, root: Path, parent: dict[str, str]) -> list[str]:
    """Run one job in its own clone; the labels of its failed steps."""
    failed = []
    if job.unsupported:
        print(f"  FAIL  {job.name}: not run as GitHub runs it: {', '.join(job.unsupported)}")
        return [f"{job.name}: {', '.join(job.unsupported)}"]
    if refused := refused_projects(job.compose_projects):
        print(
            f"  FAIL  {job.name}: names Compose project {', '.join(refused)}, which ci_local "
            f"never takes down (only {TESTS_PROJECT}, the tests' own)"
        )
        return [f"{job.name}: Compose project {', '.join(refused)}"]
    work, home = root / job.name / "checkout", root / job.name / "home"
    home.mkdir(parents=True)
    clone(repo, work, job.fetch_depth)
    with empty_compose_projects(job.compose_projects, work):
        for step in job.steps:
            label = f"{job.name}: {step.name}"
            if step.unsupported:
                failed.append(label)
                print(f"  FAIL  {label}: not run as GitHub runs it: {', '.join(step.unsupported)}")
                continue
            if step.uses and step.uses.split("@")[0] == SETUP_UV:
                pinned, have = step.with_.get("version"), uv_version()
                if pinned and pinned != have:
                    failed.append(label)
                    print(
                        f"  FAIL  {label}: the workflow pins uv {pinned}; this machine has {have}"
                    )
                else:
                    print(f"  PASS  {label} (uv {have})")
                continue
            if step.run is None:
                print(f"  skip  {label} (the clone is the checkout, depth {job.fetch_depth})")
                continue
            done = subprocess.run(
                [*SHELLS[step.shell], step.run],
                cwd=work / (step.directory or "."),
                env=environment(step, home, parent),
                capture_output=True,
                text=True,
            )
            if done.returncode == 0:
                print(f"  PASS  {label}")
            else:
                failed.append(label)
                print(f"  FAIL  {label} (exit {done.returncode})")
                tail = (done.stdout + done.stderr).strip().splitlines()[-30:]
                print("\n".join(f"        {line}" for line in tail))
    return failed


def run(repo: Path, only: list[str] | None = None) -> int:
    parent = {**os.environ, **uv_folders()}
    with tempfile.TemporaryDirectory(prefix="ci-local-") as tmp:
        root = Path(tmp)
        head = subprocess.run(
            ["git", "-C", str(repo), "log", "-1", "--format=%h %s"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        workflow = root / "ci.yml"
        workflow.write_bytes(
            subprocess.run(
                ["git", "-C", str(repo), "show", f"HEAD:{WORKFLOW.as_posix()}"],
                capture_output=True,
                check=True,
            ).stdout
        )
        print(f"continuous integration, locally, at {head}")
        failed = [f for job in jobs(workflow, only) for f in run_job(repo, job, root, parent)]
        if failed:
            print(f"continuous integration, locally: {len(failed)} steps FAILED; do not push")
            return 1
        print("continuous integration, locally: every step passed")
        return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", type=Path, default=Path("."), help="a git repository; its HEAD")
    ap.add_argument("--job", action="append", help="run only this job (repeatable)")
    a = ap.parse_args(argv)
    if sys.platform == "win32":
        print("x run this in Linux (WSL), where the runner's commands run as on GitHub")
        return 2
    return run(a.repo.resolve(), a.job)


if __name__ == "__main__":
    sys.exit(main())
