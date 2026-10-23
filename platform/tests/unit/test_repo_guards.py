"""The repository guards, exercised on throwaway repositories in temporary folders."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from datapilot.settings import PLATFORM


@pytest.fixture(scope="module")
def guards():
    spec = importlib.util.spec_from_file_location(
        "check_repo_guards", PLATFORM / "scripts" / "check_repo_guards.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["check_repo_guards"] = module
    spec.loader.exec_module(module)
    return module


def _commit(git, message: str, name: str = "ANI-IN", email: str | None = None) -> None:
    email = email or "44803072+ANI-IN@users.noreply.github.com"
    git("config", "user.name", name)
    git("config", "user.email", email)
    git("commit", "-q", "--allow-empty", "-m", message)


def _repo(git) -> Path:
    return Path(git("rev-parse", "--show-toplevel").stdout.strip())


def test_a_clean_repository_passes(guards, throwaway_repo) -> None:
    _commit(throwaway_repo, "feat: first")
    repo = _repo(throwaway_repo)
    assert guards.config_problems(guards.common_git_dir(repo) / "config") == []
    assert guards.commit_problems(repo) == []
    assert guards.tracked_env_problems(repo) == []


def test_core_worktree_in_shared_config_fails(guards, throwaway_repo) -> None:
    _commit(throwaway_repo, "feat: first")
    config = guards.common_git_dir(_repo(throwaway_repo)) / "config"
    throwaway_repo("config", "core.worktree", "/mnt/c/somewhere/else")
    problems = guards.config_problems(config)
    assert any("core.worktree" in p for p in problems)


def test_a_foreign_author_or_co_author_line_fails(guards, throwaway_repo) -> None:
    _commit(throwaway_repo, "feat: first")
    _commit(throwaway_repo, "fix: second", name="x", email="x@x")
    _commit(throwaway_repo, "fix: third\n\nCo-Authored-By: Someone <a@b.c>")
    problems = guards.commit_problems(_repo(throwaway_repo))
    assert any("author x <x@x>" in p for p in problems)
    assert any("co-author" in p for p in problems)


def test_a_tracked_env_file_fails(guards, throwaway_repo) -> None:
    repo = _repo(throwaway_repo)
    (repo / ".env").write_text("OPENAI_API_KEY=\n", encoding="utf-8")
    throwaway_repo("add", "-f", ".env")
    _commit(throwaway_repo, "chore: oops")
    assert guards.tracked_env_problems(repo) != []


def test_windows_worktree_paths_resolve_under_wsl(guards, monkeypatch) -> None:
    monkeypatch.setattr(guards.sys, "platform", "linux")
    assert (
        guards._native("C:/Users/x/repo/.git/worktrees/a") == "/mnt/c/Users/x/repo/.git/worktrees/a"
    )
    monkeypatch.setattr(guards.sys, "platform", "win32")
    assert guards._native("C:/Users/x") == "C:/Users/x"
