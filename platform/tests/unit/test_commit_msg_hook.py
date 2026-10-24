"""The commit-msg hook refuses a message with shorthand or a co-author line and accepts a clean one;
it runs no git."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from datapilot.settings import PLATFORM

HOOK = PLATFORM / "scripts" / "hooks" / "commit-msg"

pytestmark = pytest.mark.skipif(
    sys.platform == "win32" or shutil.which("bash") is None,
    reason="runs in Linux or WSL, as CI does",
)


def _run(tmp_path: Path, message: str) -> subprocess.CompletedProcess[str]:
    message_file = tmp_path / "COMMIT_EDITMSG"
    message_file.write_text(message, encoding="utf-8")
    return subprocess.run(
        ["bash", str(HOOK), str(message_file)], capture_output=True, text=True, check=False
    )


def test_shorthand_in_a_message_is_refused(tmp_path: Path) -> None:
    result = _run(tmp_path, "merge: evidence pages, docs and section pages\n")
    assert result.returncode == 1
    assert "shorthand 'docs'" in result.stdout + result.stderr


def test_a_clean_message_passes(tmp_path: Path) -> None:
    result = _run(tmp_path, "docs(evidence): the documentation pages pass the style check\n")
    assert result.returncode == 0, result.stdout + result.stderr


def test_an_installed_copy_finds_the_checker(tmp_path: Path) -> None:
    hooks = tmp_path / "repo" / ".git" / "hooks"
    scripts = tmp_path / "repo" / "platform" / "scripts"
    hooks.mkdir(parents=True)
    scripts.mkdir(parents=True)
    shutil.copy(HOOK, hooks / "commit-msg")
    for name in ("short_forms.py",):
        shutil.copy(PLATFORM / "scripts" / name, scripts / name)
    config = tmp_path / "repo" / "platform" / "config"
    config.mkdir()
    shutil.copy(PLATFORM / "config" / "course.toml", config / "course.toml")
    message_file = tmp_path / "message"
    message_file.write_text("fix: the repo pages\n", encoding="utf-8")
    result = subprocess.run(
        ["bash", str(hooks / "commit-msg"), str(message_file)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "shorthand 'repo'" in result.stdout + result.stderr


@pytest.mark.parametrize(
    "trailer",
    [
        "Co-Authored-By: Someone <someone@example.com>",
        "co-authored-by: Someone <someone@example.com>",
        "CO-AUTHORED-BY: Someone <someone@example.com>",
    ],
)
def test_a_co_author_line_is_refused_in_any_case(tmp_path: Path, trailer: str) -> None:
    result = _run(tmp_path, f"fix(gate): the console shows the gate line\n\n{trailer}\n")
    assert result.returncode == 1
    assert "co-author line" in result.stdout + result.stderr


def test_the_co_author_trailer_named_in_prose_is_not_a_trailer(tmp_path: Path) -> None:
    message = "fix(hook): refuse a message with a line that starts co-authored-by:\n"
    result = _run(tmp_path, message)
    assert result.returncode == 0, result.stdout + result.stderr
