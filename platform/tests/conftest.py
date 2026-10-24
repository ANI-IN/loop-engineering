"""Shared test helpers.

Tests never run git against the real repository and never touch its configuration. Scans over the
repository walk the working tree directly (`scan`); a test that needs git builds a throwaway
repository in a temporary folder (`throwaway_repo`). platform/scripts/check_repo_guards.py is the
only code that reads the real repository's git data, and it only reads.
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
import tomllib
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
import stack_for_tests

from datapilot.settings import REPO

# Every test reaches only the tests' own database (Compose project datapilot-tests, its own port),
# never the live stack: see stack_for_tests.py and `make test-integration`.
stack_for_tests.use_test_database()


@pytest.fixture(autouse=True)
def _no_budget_switches_from_env_file(tmp_path_factory, monkeypatch) -> None:
    """Budget switches (the session limit, the reserve) never come from the repository's .env in
    a test; a test that needs one sets it."""
    from datapilot.observability import spend

    monkeypatch.setattr(spend, "ENV_FILE", tmp_path_factory.mktemp("env") / ".env")


@pytest.fixture(autouse=True)
def _no_planted_flags_from_the_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    """A planted-item flag or demo pacing exported in the shell (to rehearse a demo) never reaches
    a test: the suite checks the fixed paths, and a test that needs a flag sets it itself."""
    from datapilot.contracts import registries

    for flag in [*registries.planted().flags, "DEMO_PACING"]:
        monkeypatch.delenv(flag, raising=False)


@pytest.fixture(autouse=True)
def _plain_terminal_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """Command output in a test is plain text in every shell: under continuous integration
    (GITHUB_ACTIONS, FORCE_COLOR) Typer forces a terminal, and Rich would split an option such as
    --purpose with escape codes. A dumb terminal has no colour system, so Rich writes no codes."""
    monkeypatch.setenv("TERM", "dumb")
    monkeypatch.setenv("NO_COLOR", "1")


# No test reaches OpenAI or LangSmith unless it carries the `live` marker, which `make test`, the
# verification gate, and continuous integration deselect: the name lookup of either service fails
# in every other test, and the test fails even when the code under test swallows the error (the
# tracing client does, on its background thread). Tests use local stand-ins instead.
MODEL_AND_TRACING_HOSTS = re.compile(r"(^|\.)(openai\.com|langchain\.com|langsmith\.com)\.?$", re.I)
reached_hosts: list[tuple[str, str]] = []  # (test id, host name), cleared after each test
_running = {"test": "outside a test", "live": False}
_real_getaddrinfo = socket.getaddrinfo


def _guarded_getaddrinfo(host, *args, **kwargs):
    name = host.decode() if isinstance(host, bytes) else str(host or "")
    if MODEL_AND_TRACING_HOSTS.search(name) and not _running["live"]:
        reached_hosts.append((str(_running["test"]), name))
        raise OSError(f"{name}: a test without the live marker never reaches OpenAI or LangSmith")
    return _real_getaddrinfo(host, *args, **kwargs)


socket.getaddrinfo = _guarded_getaddrinfo


@pytest.fixture(autouse=True)
def _no_model_or_tracing_calls(request: pytest.FixtureRequest) -> Iterator[None]:
    _running["test"] = request.node.nodeid
    _running["live"] = request.node.get_closest_marker("live") is not None
    start = len(reached_hosts)
    yield
    reached = sorted({host for _, host in reached_hosts[start:]})
    del reached_hosts[start:]
    _running["test"], _running["live"] = "outside a test", False
    if reached:
        pytest.fail(f"the test reached {', '.join(reached)}; mark it live or use a stand-in")


@pytest.fixture
def select_pack(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[[str], None]]:
    """Select a domain pack for one test, as DATAPILOT_PACK in .env would."""
    from datapilot.settings import get_settings

    def select(pack: str) -> None:
        monkeypatch.setenv("DATAPILOT_PACK", pack)
        get_settings.cache_clear()

    yield select
    monkeypatch.undo()
    get_settings.cache_clear()


# Folders a scan never enters: git data, environments, caches, build tooling, local notes, and the
# agent worktrees (each is its own branch).
SKIPPED_DIRS = {
    ".git",
    ".venv",
    ".dev",
    ".claude",
    "research",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".import_linter_cache",
    "node_modules",
    "build",
    "dist",
    "test-results",
    "playwright-report",
}
# The internal files (named once, in the release list) never ship, so a published clone has none.
SKIPPED_FILES = {
    ".env",
    *tomllib.loads((REPO / "platform/config/release.toml").read_text(encoding="utf-8"))[
        "internal_files"
    ],
}


def _files(paths: tuple[str, ...]) -> Iterator[Path]:
    for rel in paths:
        start = REPO / rel
        if not start.exists():
            # os.walk over a missing folder yields nothing, so a renamed folder would turn every
            # scan of it into a check that passes having read nothing.
            raise FileNotFoundError(f"a scan names {rel}, which does not exist")
        if start.is_file():
            yield start
            continue
        for root, dirs, files in os.walk(start):
            dirs[:] = [d for d in dirs if d not in SKIPPED_DIRS]
            for name in files:
                if name not in SKIPPED_FILES:
                    yield Path(root) / name


def scan(pattern: str, *paths: str, flags: int = re.I) -> list[str]:
    """Lines matching `pattern` under `paths` (default: the whole tree), as "path:line:text",
    like `git grep -n` but reading the working tree, so it can never pass because git failed."""
    regex = re.compile(pattern, flags)
    hits = []
    for path in _files(paths or (".",)):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary or unreadable: not prose or code
        rel = path.relative_to(REPO).as_posix()
        hits += [
            f"{rel}:{n}:{line}" for n, line in enumerate(text.splitlines(), 1) if regex.search(line)
        ]
    return hits


@pytest.fixture
def repo_scan() -> Callable[..., list[str]]:
    return scan


@pytest.fixture
def throwaway_repo(tmp_path: Path) -> Callable[..., subprocess.CompletedProcess[str]]:
    """A git repository in a temporary folder, isolated from the user's global git settings.
    Returns a function that runs git in it."""
    env = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": str(tmp_path / "gitconfig"),
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args], cwd=repo, env=env, capture_output=True, text=True, check=check
        )

    git("init", "-q", "-b", "main")
    return git
