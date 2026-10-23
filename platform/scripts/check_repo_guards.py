"""Repository guards: run in CI and before every merge (`make guards`).

Fails when:
1. the shared git configuration holds core.worktree or any key outside ALLOWED_CONFIG
   (read from the config file directly; no git command touches the configuration);
2. any commit on any branch has an author other than ANI-IN, or carries a co-author line;
3. a .env file is tracked.

This is the only code that reads the real repository's git data, and it only reads (`git log`,
`git ls-files`). Tests use throwaway repositories in temporary folders.

    uv run python platform/scripts/check_repo_guards.py [--repo PATH]
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

OWNER_NAME = "ANI-IN"
OWNER_EMAIL = "44803072+ANI-IN@users.noreply.github.com"

# Every key the shared configuration may hold, with why. A key added here needs a reason.
ALLOWED_CONFIG = {
    "core.repositoryformatversion": "set by git init",
    "core.filemode": "set by git init",
    "core.bare": "set by git init",
    "core.logallrefupdates": "set by git init",
    "core.symlinks": "set by git init on Windows",
    "core.ignorecase": "set by git init on Windows",
    "core.longpaths": "Windows paths in the agent worktrees",
    "core.autocrlf": "line endings; .gitattributes decides",
    "user.name": "the repository's author: ANI-IN",
    "user.email": "the repository's author: the ANI-IN noreply address",
}
# Keys allowed under any name, such as a remote or a branch, once the owner confirms one.
ALLOWED_CONFIG_PATTERNS = (
    r"remote\.[\w.-]+\.(url|fetch|pushurl)",
    r"branch\.[\w./-]+\.(remote|merge)",
)
CO_AUTHOR = re.compile(r"^co-authored-by:", re.I | re.M)


def _native(path: str) -> str:
    """A worktree written on Windows records "C:/..." paths; under WSL they live at /mnt/c/..."""
    drive = re.match(r"^([A-Za-z]):[/\\](.*)$", path)
    if drive and sys.platform != "win32":
        return f"/mnt/{drive.group(1).lower()}/{drive.group(2).replace(chr(92), '/')}"
    return path


def own_git_dir(repo: Path) -> Path:
    """This checkout's git directory: .git itself, or the worktree's folder it points to."""
    dot_git = repo / ".git"
    if dot_git.is_dir():
        return dot_git
    return Path(_native(dot_git.read_text(encoding="utf-8").split("gitdir:", 1)[1].strip()))


def common_git_dir(repo: Path) -> Path:
    """The shared git directory, also from inside a worktree (where .git is a file)."""
    gitdir = own_git_dir(repo)
    commondir = gitdir / "commondir"
    if commondir.is_file():
        return (gitdir / commondir.read_text(encoding="utf-8").strip()).resolve()
    return gitdir


def config_keys(config_file: Path) -> list[str]:
    """Every key in a git config file, as section[.subsection].name, lower-cased."""
    keys, section = [], ""
    for raw in config_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";")):
            continue
        header = re.fullmatch(r'\[([\w.-]+)(?:\s+"([^"]*)")?\]', line)
        if header:
            section = header.group(1).lower() + (f".{header.group(2)}" if header.group(2) else "")
            continue
        name = line.split("=", 1)[0].strip().lower()
        keys.append(f"{section}.{name}")
    return keys


def config_problems(config_file: Path) -> list[str]:
    problems = []
    for key in config_keys(config_file):
        if key in ALLOWED_CONFIG or any(re.fullmatch(p, key) for p in ALLOWED_CONFIG_PATTERNS):
            continue
        reason = " (breaks git for every other checkout)" if key == "core.worktree" else ""
        problems.append(f"git config key '{key}' is not allowed{reason}")
    return problems


def _git(repo: Path, *args: str, git_dir: Path | None = None) -> str:
    """Read-only git. The git directory is passed per process, so a worktree created on Windows
    reads correctly under WSL; nothing is written to any configuration."""
    env = {**os.environ, "GIT_DIR": str(git_dir or own_git_dir(repo)), "GIT_WORK_TREE": str(repo)}
    result = subprocess.run(["git", *args], cwd=repo, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"x git {args[0]} failed: {result.stderr.strip()}")
    return result.stdout


def commit_problems(repo: Path) -> list[str]:
    problems = []
    log_format = "--format=%H%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%B%x1e"
    log = _git(repo, "log", "--all", log_format, git_dir=common_git_dir(repo))
    for record in filter(None, (r.strip() for r in log.split("\x1e"))):
        sha, author, email, committer, committer_email, body = record.split("\x1f", 5)
        if (author, email) != (OWNER_NAME, OWNER_EMAIL):
            problems.append(f"commit {sha[:10]} author {author} <{email}>")
        if (committer, committer_email) != (OWNER_NAME, OWNER_EMAIL):
            problems.append(f"commit {sha[:10]} committer {committer} <{committer_email}>")
        if CO_AUTHOR.search(body):
            problems.append(f"commit {sha[:10]} has a co-author line")
    return problems


def tracked_env_problems(repo: Path) -> list[str]:
    tracked = [p for p in _git(repo, "ls-files").splitlines() if Path(p).name == ".env"]
    return [f"{p} is tracked; it must never be committed" for p in tracked]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Repository guards")
    parser.add_argument("--repo", type=Path, default=REPO)
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    problems = config_problems(common_git_dir(repo) / "config")
    problems += commit_problems(repo)
    problems += tracked_env_problems(repo)
    for problem in problems:
        print(f"x {problem}")
    print(f"repository guards: {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
