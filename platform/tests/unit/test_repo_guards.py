"""The repository guards, exercised on throwaway repositories in temporary folders: strict in the
course's build repository, and in a public copy limited to what holds for a learner's commits."""

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


def test_an_overridden_committer_fails(guards, throwaway_repo) -> None:
    _commit(throwaway_repo, "feat: first")
    # The owner as author, someone else as committer: the identity override the build forbids.
    override = ["-c", "committer.name=x", "-c", "committer.email=x@x"]
    throwaway_repo(*override, "commit", "-q", "--allow-empty", "-m", "fix: second")
    problems = guards.commit_problems(_repo(throwaway_repo))
    assert len(problems) == 1 and "committer x <x@x>" in problems[0], problems


def test_a_tracked_env_file_fails(guards, throwaway_repo) -> None:
    repo = _repo(throwaway_repo)
    (repo / ".env").write_text("OPENAI_API_KEY=\n", encoding="utf-8")
    throwaway_repo("add", "-f", ".env")
    _commit(throwaway_repo, "chore: oops")
    assert guards.tracked_env_problems(repo) != []


# A public copy is told apart by the release list's build-only files, which never ship. A made-up
# name stands for them here, so this file never names a real build-only file and still ships.
BUILD_ONLY = "tools/build-machine.sh"


def _layout(repo: Path, *, build: bool) -> None:
    listed = repo / "platform" / "config" / "release.toml"
    listed.parent.mkdir(parents=True, exist_ok=True)
    listed.write_text(f'build_only = ["{BUILD_ONLY}"]\n', encoding="utf-8")
    if build:
        (repo / BUILD_ONLY).parent.mkdir(parents=True, exist_ok=True)
        (repo / BUILD_ONLY).write_text("echo build machine\n", encoding="utf-8")


def _learner_commit(throwaway_repo) -> Path:
    _commit(throwaway_repo, "feat: first")
    # A learner's own work: another author, and a message with shorthand.
    _commit(throwaway_repo, "fix: the repo config, e.g. the port", name="Learner", email="l@x")
    return _repo(throwaway_repo)


def test_the_build_repository_keeps_the_author_rule_strict(guards, throwaway_repo, capsys) -> None:
    repo = _learner_commit(throwaway_repo)
    _layout(repo, build=True)
    assert guards.build_repository(repo)
    assert guards.main(["--repo", str(repo)]) == 1
    out = capsys.readouterr().out
    assert "author Learner <l@x>" in out and "committer Learner <l@x>" in out
    assert "skipped" not in out


def test_a_public_copy_skips_the_build_rules_for_a_learner_commit(
    guards, throwaway_repo, capsys
) -> None:
    repo = _learner_commit(throwaway_repo)
    _layout(repo, build=False)
    assert not guards.build_repository(repo)
    assert guards.main(["--repo", str(repo)]) == 0
    out = capsys.readouterr().out
    assert "commit authors: skipped in a public copy" in out and BUILD_ONLY in out
    assert "repository guards: 0 problems" in out
    assert guards.main(["--repo", str(repo), "--commit-messages"]) == 0
    assert "commit messages: skipped in a public copy" in capsys.readouterr().out


def test_a_public_copy_still_refuses_a_tracked_env_file(guards, throwaway_repo, capsys) -> None:
    repo = _learner_commit(throwaway_repo)
    _layout(repo, build=False)
    (repo / ".env").write_text("OPENAI_API_KEY=\n", encoding="utf-8")
    throwaway_repo("add", "-f", ".env")
    _commit(throwaway_repo, "chore: oops", name="Learner", email="l@x")
    assert guards.main(["--repo", str(repo)]) == 1
    assert ".env is tracked" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("http.https://github.com/.extraheader", "AUTHORIZATION: basic not-a-real-token"),
        ("gc.auto", "0"),
        ("core.precomposeunicode", "true"),
    ],
)
def test_a_clone_or_continuous_integration_key_is_allowed_only_in_a_public_copy(
    guards, throwaway_repo, key: str, value: str
) -> None:
    _commit(throwaway_repo, "feat: first")
    throwaway_repo("config", key, value)
    config = guards.common_git_dir(_repo(throwaway_repo)) / "config"
    assert guards.config_problems(config, public_copy=True) == []
    assert guards.config_problems(config) == [f"git config key '{key.lower()}' is not allowed"]
    throwaway_repo("config", "core.worktree", "/mnt/c/somewhere/else")
    assert any("core.worktree" in p for p in guards.config_problems(config, public_copy=True))


# Ordinary local git settings a learner may have in a copy of the course: the one `git pull` itself
# suggests, an editor, an alias, a credential helper, and so on. None of them breaks a checkout.
LEARNER_SETTINGS = [
    ("pull.rebase", "false"),
    ("core.editor", "code --wait"),
    ("core.hookspath", ".husky"),
    ("push.autosetupremote", "true"),
    ("merge.ff", "only"),
    ("rebase.autostash", "true"),
    ("fetch.prune", "true"),
    ("init.defaultbranch", "main"),
    ("color.ui", "auto"),
    ("alias.st", "status"),
    ("credential.helper", "store"),
    ("diff.tool", "vscode"),
    ("branch.autosetuprebase", "always"),
    ("remote.origin.tagopt", "--no-tags"),
    ("http.postbuffer", "524288000"),
    ("gc.auto", "0"),
    ("user.signingkey", "ABCDEF"),
    ("commit.gpgsign", "true"),
]


def test_a_public_copy_allows_every_ordinary_local_git_setting(
    guards, throwaway_repo, capsys
) -> None:
    repo = _learner_commit(throwaway_repo)
    _layout(repo, build=False)
    for key, value in LEARNER_SETTINGS:
        throwaway_repo("config", key, value)
    config = guards.common_git_dir(repo) / "config"
    assert guards.config_problems(config, public_copy=True) == []
    assert guards.main(["--repo", str(repo)]) == 0
    assert "repository guards: 0 problems" in capsys.readouterr().out
    # What protects the learner still holds: a worktree setting breaks the checkout.
    throwaway_repo("config", "core.worktree", "/mnt/c/somewhere/else")
    assert guards.main(["--repo", str(repo)]) == 1
    assert "core.worktree" in capsys.readouterr().out


@pytest.mark.parametrize(("key", "value"), LEARNER_SETTINGS)
def test_the_build_repository_keeps_the_configuration_allow_list_strict(
    guards, throwaway_repo, key: str, value: str
) -> None:
    _commit(throwaway_repo, "feat: first")
    throwaway_repo("config", key, value)
    config = guards.common_git_dir(_repo(throwaway_repo)) / "config"
    assert guards.config_problems(config) == [f"git config key '{key}' is not allowed"]


def test_the_commit_message_check_reads_the_history_itself(guards, throwaway_repo, capsys) -> None:
    _commit(throwaway_repo, "feat: first")
    repo = _repo(throwaway_repo)
    _layout(repo, build=True)
    assert guards.main(["--repo", str(repo), "--commit-messages"]) == 0
    _commit(throwaway_repo, "fix: the repo pages")
    assert guards.main(["--repo", str(repo), "--commit-messages"]) == 1
    assert "shorthand 'repo'" in capsys.readouterr().out


def test_the_commit_message_check_fails_when_git_fails(guards, tmp_path: Path) -> None:
    # Not a repository at all: a pipe from git log would hand the checker nothing and pass.
    _layout(tmp_path, build=True)
    (tmp_path / ".git").mkdir()
    with pytest.raises(SystemExit, match="failed"):
        guards.main(["--repo", str(tmp_path), "--commit-messages"])


def test_windows_worktree_paths_resolve_under_wsl(guards, monkeypatch) -> None:
    monkeypatch.setattr(guards.sys, "platform", "linux")
    assert (
        guards._native("C:/Users/x/repo/.git/worktrees/a") == "/mnt/c/Users/x/repo/.git/worktrees/a"
    )
    monkeypatch.setattr(guards.sys, "platform", "win32")
    assert guards._native("C:/Users/x") == "C:/Users/x"
