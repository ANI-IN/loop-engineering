"""Check the shell scripts, the Dockerfiles, and the Compose files of the repository.

Usage: python platform/scripts/check_shell_docker.py <check> [--root PATH]

The checks, each its own command so that continuous integration runs each as one step:

- `shellcheck`: ShellCheck (from shellcheck-py in the dev group, so `uv run` puts it on the path)
  on every shell script, at its strictest severity (style).
- `bash-n`: `bash -n` (read the script, run nothing) on every shell script, so a syntax error
  fails before any demo runs it.
- `hadolint`: hadolint from one pinned image (HADOLINT_IMAGE, tag and digest) on every
  Dockerfile, failing on any finding down to style.
- `build`: `docker build` of every Dockerfile from the build context Compose gives it (the
  repository root when no Compose service builds it), with no secret, no build argument, and a
  context whose .dockerignore leaves every .env file out. It prints each build's time.
- `compose`: `docker compose config --quiet` on every Compose file, for the default profile and
  each profile its services name, with the variables of .env.example and never a real .env (the
  services' env_file entries are not read). A Compose warning, such as a variable that is not set,
  fails the check too.

The files are found, not listed: the shell scripts are the tracked files ending in .sh or .bash,
or whose first line is a shebang for sh, bash, dash, or ksh; the Dockerfiles are the tracked files
named Dockerfile, Dockerfile.<name>, or <name>.Dockerfile; the Compose files are the tracked
compose.yaml, compose.yml, docker-compose.yaml, and docker-compose.yml. Tracked means `git
ls-files`, so a virtual environment or other untracked file is never checked; in a folder that is
not a git checkout, every file outside the dot folders counts.

Each check prints one line per file (or per profile), the tool's own output on a failure, and
exits 0 when everything passes, 1 on a finding, and 2 when its tool is missing. Nothing is
written to the repository; `build` adds a local image tagged CHECK_TAG.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_repo_guards import own_git_dir  # noqa: E402

REPO = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())

# hadolint 2.15.1, the index digest of the multi-platform image on Docker Hub (31 July 2026).
HADOLINT_IMAGE = (
    "hadolint/hadolint:v2.15.1"
    "@sha256:32dac94127fd60b7b7e3fbfc65e1383b9b5e25c9bfd7b8536de7a539fe68a12d"
)
# The local tag of the images `build` makes; one tag per Dockerfile, by its folder.
CHECK_TAG = "datapilot-check"
# The interpreters ShellCheck reads; a script for any other shell (zsh) is not a shell script here.
SHELLS = {"sh", "bash", "dash", "ksh"}
SHELL_SUFFIXES = {".sh", ".bash"}
COMPOSE_NAMES = {"compose.yaml", "compose.yml", "docker-compose.yaml", "docker-compose.yml"}
# The variables Compose reads in place of a real .env.
ENV_EXAMPLE = ".env.example"

EXIT_PASS, EXIT_FINDING, EXIT_TOOL_MISSING = 0, 1, 2


# Finding the files -------------------------------------------------------------------------------


def tracked_files(root: Path) -> list[str]:
    """The tracked files of the checkout at root, as POSIX paths relative to it. A folder that is
    not a git checkout (an unpacked archive, a scratch copy) gives every file under it instead,
    leaving out the folders whose name starts with a dot (.venv, .git) and __pycache__."""
    if not (root / ".git").exists():
        return sorted(
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file()
            and not any(
                part.startswith(".") or part == "__pycache__"
                for part in path.relative_to(root).parts[:-1]
            )
        )
    # The git directory is passed per process, as the repository guards do, so a worktree made on
    # Windows reads correctly under WSL; a git hook's own GIT_INDEX_FILE is dropped.
    environment = {
        **{name: value for name, value in os.environ.items() if name != "GIT_INDEX_FILE"},
        "GIT_DIR": str(own_git_dir(root)),
        "GIT_WORK_TREE": str(root),
    }
    found = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        capture_output=True,
        check=True,
        env=environment,
    )
    return sorted(name for name in found.stdout.decode("utf-8").split("\0") if name)


def shebang_interpreter(first_line: str) -> str | None:
    """The interpreter a shebang line names (`#!/bin/sh` gives sh, `#!/usr/bin/env bash` gives
    bash, `#!/usr/bin/env -S bash -e` gives bash), or None when the line is not a shebang."""
    if not first_line.startswith("#!"):
        return None
    words = first_line[2:].split()
    if not words:
        return None
    program = PurePosixPath(words[0]).name
    if program == "env":
        rest = [word for word in words[1:] if not word.startswith("-") and "=" not in word]
        return PurePosixPath(rest[0]).name if rest else None
    return program


def first_line(path: Path) -> str:
    try:
        with path.open("rb") as handle:
            return handle.readline(256).decode("utf-8", errors="replace").strip()
    except OSError:
        return ""


def shell_scripts(root: Path, files: Iterable[str]) -> list[str]:
    """The shell scripts among files: by their suffix, or by a shebang for a shell in SHELLS."""
    scripts = []
    for name in files:
        path = root / name
        if not path.is_file():
            continue
        by_suffix = PurePosixPath(name).suffix in SHELL_SUFFIXES
        if by_suffix or shebang_interpreter(first_line(path)) in SHELLS:
            scripts.append(name)
    return sorted(scripts)


def is_dockerfile(name: str) -> bool:
    base = PurePosixPath(name).name
    return base == "Dockerfile" or base.startswith("Dockerfile.") or base.endswith(".Dockerfile")


def dockerfiles(files: Iterable[str]) -> list[str]:
    return sorted(name for name in files if is_dockerfile(name))


def compose_files(files: Iterable[str]) -> list[str]:
    return sorted(name for name in files if PurePosixPath(name).name in COMPOSE_NAMES)


# Reading the Compose files -----------------------------------------------------------------------


def load_compose(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: a Compose file must be a mapping")
    return data


def compose_profiles(data: dict) -> list[str]:
    """Every profile a service of the Compose file names, sorted; the default profile is not one."""
    profiles: set[str] = set()
    for service in (data.get("services") or {}).values():
        if isinstance(service, dict):
            profiles.update(str(profile) for profile in service.get("profiles") or [])
    return sorted(profiles)


def build_contexts(root: Path, compose_name: str, data: dict) -> dict[str, str]:
    """For each Dockerfile a Compose service builds, its build context, both relative to root.
    A short `build: <folder>` means the Dockerfile named Dockerfile in that folder."""
    folder = (root / compose_name).parent
    contexts: dict[str, str] = {}
    for service in (data.get("services") or {}).values():
        if not isinstance(service, dict) or "build" not in service:
            continue
        build = service["build"]
        if isinstance(build, str):
            build = {"context": build}
        context = (folder / build.get("context", ".")).resolve()
        dockerfile = (context / build.get("dockerfile", "Dockerfile")).resolve()
        contexts[_relative(dockerfile, root)] = _relative(context, root)
    return contexts


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root.resolve()).as_posix() or "."


def env_file_problems(context: Path) -> list[str]:
    """Why a build context could carry a .env file into an image: no .dockerignore, or one that
    does not leave out `.env` and `.env.*`."""
    ignore = context / ".dockerignore"
    if not ignore.is_file():
        return [f"{_shown(ignore)} is missing: the build context would carry any .env file"]
    lines = {line.strip() for line in ignore.read_text(encoding="utf-8").splitlines()}
    return [
        f"{_shown(ignore)} does not leave out {pattern}: the build context would carry it"
        for pattern in (".env", ".env.*")
        if pattern not in lines
    ]


def _shown(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return str(path)


def compose_warnings(output: str) -> list[str]:
    """The warning lines Compose printed (`WARN[0000] ...` or `level=warning ...`)."""
    return [
        line.strip()
        for line in output.splitlines()
        if line.lstrip().startswith("WARN") or "level=warning" in line
    ]


# The commands ------------------------------------------------------------------------------------


def shellcheck_command(executable: str, scripts: list[str]) -> list[str]:
    return [executable, "--severity=style", "--color=never", "--external-sources", *scripts]


def hadolint_command() -> list[str]:
    """hadolint reads the Dockerfile on its standard input; inline `# hadolint ignore=` comments
    still apply."""
    return [
        "docker",
        "run",
        "--rm",
        "--interactive",
        "--network=none",
        HADOLINT_IMAGE,
        "hadolint",
        "--failure-threshold",
        "style",
        "--no-color",
        "-",
    ]


def build_tag(dockerfile: str) -> str:
    folder = PurePosixPath(dockerfile).parent.as_posix().replace("/", "-").replace("_", "-")
    return f"{CHECK_TAG}:{folder.lower() if folder != '.' else 'root'}"


def build_command(dockerfile: str, context: str) -> list[str]:
    """No --secret, no --build-arg: the image must build from the repository alone."""
    return [
        "docker",
        "build",
        "--progress=plain",
        "--file",
        dockerfile,
        "--tag",
        build_tag(dockerfile),
        context,
    ]


def compose_command(compose_file: Path, env_example: Path, profile: str | None) -> list[str]:
    """Compose reads its variables from .env.example only (--env-file replaces the .env beside the
    file) and does not read the services' env_file entries (--no-env-resolution)."""
    command = [
        "docker",
        "compose",
        "--file",
        str(compose_file),
        "--project-directory",
        str(compose_file.parent),
        "--env-file",
        str(env_example),
    ]
    if profile:
        command += ["--profile", profile]
    return command + ["config", "--quiet", "--no-env-resolution"]


# The checks --------------------------------------------------------------------------------------


def _need(tool: str, hint: str) -> str | None:
    found = shutil.which(tool)
    if found is None:
        print(f"x {tool} is not on the path: {hint}", file=sys.stderr)
    return found


def _run(command: list[str], root: Path, stdin: bytes | None = None) -> tuple[int, str]:
    result = subprocess.run(
        command,
        cwd=root,
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return result.returncode, result.stdout.decode("utf-8", errors="replace")


def _nothing_found(kind: str) -> int:
    print(f"x no {kind} found: the search is broken, or the repository lost them")
    return EXIT_FINDING


def check_shellcheck(root: Path, files: list[str]) -> int:
    scripts = shell_scripts(root, files)
    if not scripts:
        return _nothing_found("shell script")
    executable = _need("shellcheck", "run it with uv run (shellcheck-py is in the dev group)")
    if executable is None:
        return EXIT_TOOL_MISSING
    status, output = _run(shellcheck_command(executable, scripts), root)
    for script in scripts:
        print(f"  {script}")
    if status != 0:
        print(output.rstrip())
        print(f"x ShellCheck found problems in the {len(scripts)} shell scripts above")
        return EXIT_FINDING
    print(f"ShellCheck: {len(scripts)} shell scripts, no problems")
    return EXIT_PASS


def check_bash_syntax(root: Path, files: list[str]) -> int:
    scripts = shell_scripts(root, files)
    if not scripts:
        return _nothing_found("shell script")
    if _need("bash", "install bash") is None:
        return EXIT_TOOL_MISSING
    failed = 0
    for script in scripts:
        status, output = _run(["bash", "-n", script], root)
        if status == 0:
            print(f"  ok    {script}")
        else:
            failed += 1
            print(f"x syntax {script}\n{output.rstrip()}")
    if failed:
        print(f"x bash -n: {failed} of {len(scripts)} shell scripts do not parse")
        return EXIT_FINDING
    print(f"bash -n: {len(scripts)} shell scripts parse")
    return EXIT_PASS


def check_hadolint(root: Path, files: list[str]) -> int:
    found = dockerfiles(files)
    if not found:
        return _nothing_found("Dockerfile")
    if _need("docker", "install Docker Engine (hadolint runs from a pinned image)") is None:
        return EXIT_TOOL_MISSING
    failed = 0
    for dockerfile in found:
        status, output = _run(hadolint_command(), root, (root / dockerfile).read_bytes())
        if status == 0:
            print(f"  ok    {dockerfile}")
        else:
            failed += 1
            # hadolint names the standard input "-"; name the file instead.
            named = "\n".join(
                dockerfile + line[1:] if line.startswith("-:") else line
                for line in output.rstrip().splitlines()
            )
            print(f"x hadolint {dockerfile}\n{named}")
    if failed:
        print(f"x hadolint ({HADOLINT_IMAGE}): {failed} of {len(found)} Dockerfiles have findings")
        return EXIT_FINDING
    print(f"hadolint: {len(found)} Dockerfiles, no findings")
    return EXIT_PASS


def check_build(root: Path, files: list[str]) -> int:
    found = dockerfiles(files)
    if not found:
        return _nothing_found("Dockerfile")
    if _need("docker", "install Docker Engine") is None:
        return EXIT_TOOL_MISSING
    contexts: dict[str, str] = {}
    for compose_name in compose_files(files):
        contexts.update(build_contexts(root, compose_name, load_compose(root / compose_name)))
    failed = 0
    for dockerfile in found:
        context = contexts.get(dockerfile, ".")
        problems = env_file_problems(root / context)
        if problems:
            failed += 1
            print("\n".join(f"x {problem}" for problem in problems))
            continue
        started = time.monotonic()
        status, output = _run(build_command(dockerfile, context), root)
        seconds = time.monotonic() - started
        if status == 0:
            print(f"  ok    {dockerfile} (context {context}) built in {seconds:.0f} s")
        else:
            failed += 1
            print(output.rstrip())
            print(f"x {dockerfile} (context {context}) does not build ({seconds:.0f} s)")
    if failed:
        print(f"x docker build: {failed} of {len(found)} Dockerfiles failed")
        return EXIT_FINDING
    print(f"docker build: {len(found)} Dockerfiles build")
    return EXIT_PASS


def check_compose(root: Path, files: list[str]) -> int:
    found = compose_files(files)
    if not found:
        return _nothing_found("Compose file")
    if _need("docker", "install Docker Engine and the Compose plugin") is None:
        return EXIT_TOOL_MISSING
    env_example = root / ENV_EXAMPLE
    if not env_example.is_file():
        print(f"x {ENV_EXAMPLE} is missing: Compose would have no variables but the shell's")
        return EXIT_FINDING
    failed = 0
    for compose_name in found:
        path = root / compose_name
        for profile in [None, *compose_profiles(load_compose(path))]:
            shown = f"{compose_name}, profile {profile or 'default'}"
            status, output = _run(compose_command(path, env_example, profile), root)
            warnings = compose_warnings(output)
            if status == 0 and not warnings:
                print(f"  ok    {shown}")
            else:
                failed += 1
                print(f"x {shown}\n{output.rstrip()}")
    if failed:
        print(f"x docker compose config: {failed} Compose files or profiles do not validate")
        return EXIT_FINDING
    print(f"docker compose config: {len(found)} Compose files, every profile valid")
    return EXIT_PASS


CHECKS = {
    "shellcheck": check_shellcheck,
    "bash-n": check_bash_syntax,
    "hadolint": check_hadolint,
    "build": check_build,
    "compose": check_compose,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("check", choices=sorted(CHECKS))
    parser.add_argument("--root", type=Path, default=REPO, help="the checkout to check")
    arguments = parser.parse_args(argv)
    root = arguments.root.resolve()
    # Compose reads these when they are set; the check must not depend on the shell's.
    for variable in ("COMPOSE_FILE", "COMPOSE_PROFILES", "COMPOSE_ENV_FILES"):
        os.environ.pop(variable, None)
    return CHECKS[arguments.check](root, tracked_files(root))


if __name__ == "__main__":
    raise SystemExit(main())
