"""Run the continuous integration workflow's own commands in a clean clone, as GitHub runs them.

    uv run python platform/scripts/ci_local.py --repo CLONE          # every job, at CLONE's HEAD
    uv run python platform/scripts/ci_local.py --repo CLONE --job lint --job test

Run it in Linux (WSL) on the release commit before every push of the public repository: a push is
made only when this exits with 0. It clones the commit into a temporary folder (the whole history,
as the lint job fetches it), sets the git configuration that actions/checkout writes (gc.auto and
an authorization header, with a placeholder value), and runs each `run:` step of
.github/workflows/ci.yml in order with `bash -e`, as the runner does.

Each step gets a minimal environment, never this shell's: HOME, PATH, LANG, the variables GitHub
sets (GITHUB_ACTIONS, CI), and the step's own `env:`. So no API key, no .env setting, and no
UV_PROJECT_ENVIRONMENT reaches it, and no build-only or internal file is in the clone unless the
commit ships it. A step that uses an action (checkout, setup-uv) is reported and skipped: the clone
is the checkout, and uv is this machine's. The integration job starts the tests' own database
(Compose project datapilot-tests, port 55432), the same one `make test-integration` uses.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml

WORKFLOW = Path(".github/workflows/ci.yml")
# What actions/checkout leaves in the clone's own configuration; the value is a placeholder.
CHECKOUT_CONFIG = {
    "gc.auto": "0",
    "http.https://github.com/.extraheader": "AUTHORIZATION: basic placeholder",
}
GITHUB_ENV = {"GITHUB_ACTIONS": "true", "CI": "true"}
PASSED_THROUGH = ("HOME", "PATH", "LANG")


@dataclass
class Step:
    job: str
    name: str
    run: str | None  # None: an action, skipped
    env: dict[str, str]


def steps(workflow: Path, jobs: list[str] | None = None) -> list[Step]:
    """The workflow's steps in order, job by job; `jobs` keeps only those jobs, in the file's
    order, and an unknown job name is an error."""
    spec = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    names = list(spec["jobs"])
    unknown = sorted(set(jobs or []) - set(names))
    if unknown:
        raise SystemExit(f"x no such job in {workflow}: {', '.join(unknown)}")
    out = []
    for job in names:
        if jobs and job not in jobs:
            continue
        for step in spec["jobs"][job]["steps"]:
            run = step.get("run")
            run = None if run is None else str(run).lower() if isinstance(run, bool) else str(run)
            name = step.get("name") or (run.strip().splitlines()[0] if run else step["uses"])
            env = {k: str(v) for k, v in (step.get("env") or {}).items()}
            out.append(Step(job, name, run, env))
    return out


def environment(step: Step, parent: dict[str, str] | None = None) -> dict[str, str]:
    """The step's whole environment: nothing of the parent but HOME, PATH and LANG."""
    parent = os.environ if parent is None else parent
    env = {k: parent[k] for k in PASSED_THROUGH if k in parent}
    return {**env, **GITHUB_ENV, **step.env}


def clone(repo: Path, dest: Path) -> None:
    subprocess.run(["git", "clone", "--quiet", "--no-local", str(repo), str(dest)], check=True)
    for key, value in CHECKOUT_CONFIG.items():
        subprocess.run(["git", "-C", str(dest), "config", "--local", key, value], check=True)


def run(repo: Path, jobs: list[str] | None = None) -> int:
    with tempfile.TemporaryDirectory(prefix="ci-local-") as tmp:
        work = Path(tmp) / "checkout"
        clone(repo, work)
        head = subprocess.run(
            ["git", "-C", str(work), "log", "-1", "--format=%h %s"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        print(f"continuous integration, locally, at {head}")
        failed = []
        for step in steps(work / WORKFLOW, jobs):
            label = f"{step.job}: {step.name}"
            if step.run is None:
                print(f"  skip  {label} (an action)")
                continue
            done = subprocess.run(
                ["bash", "-e", "-c", step.run],
                cwd=work,
                env=environment(step),
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
