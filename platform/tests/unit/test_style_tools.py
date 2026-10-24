"""The style tools run on this repository, and the checker's templates match docs/STYLE.md."""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "platform" / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module  # dataclasses look their module up by name
    spec.loader.exec_module(module)
    return module


def test_style_check_has_no_errors() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "check_style.py")],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_prose_lint_is_clean() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "lint_prose.py")],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_templates_match_the_style_guide() -> None:
    check_style = _load("check_style")
    text = (REPO / "docs" / "STYLE.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```markdown skeleton:([a-z-]+)\n(.*?)```", text, re.S)
    found = {kind: re.findall(r"^## (.+)$", body, re.M) for kind, body in blocks}
    assert found == check_style.TEMPLATES


def test_section_names_come_from_the_config() -> None:
    check_style = _load("check_style")
    sections = check_style.CONFIG["sections"]
    assert check_style.NAMES["Section"] == {s["number"]: s["name"] for s in sections}
    for section in sections:
        assert (REPO / f"section-{section['number']}-{section['slug']}").is_dir()


@pytest.mark.parametrize(
    "line",
    [
        "Done ✅",  # check mark button
        "Fails ❌",  # cross mark
        "New ✨",  # sparkles
        "Star ⭐",  # star
        "Launch \U0001f680",  # rocket
        "Waiting ⌛",  # hourglass done
        "Warning ⚠️",  # the warning sign drawn as an emoji
    ],
)
def test_the_prose_lint_finds_common_symbol_emoji(line: str) -> None:
    assert _load("lint_prose").lint_text(line) == [(1, "emoji")]


def test_a_folder_that_vanishes_during_the_walk_does_not_end_the_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    check_style = _load("check_style")
    (tmp_path / "docs" / "gone").mkdir(parents=True)
    (tmp_path / "docs" / "page.md").write_text("# Page\n", encoding="utf-8")
    (tmp_path / "docs" / "gone" / "old.md").write_text("# Old\n", encoding="utf-8")
    (tmp_path / ".venv" / "lib").mkdir(parents=True)
    real_scandir = os.scandir
    entered = []

    def scandir(path="."):
        entered.append(Path(path).name)
        if Path(path).name == "gone":  # deleted by another process after it was listed
            raise FileNotFoundError(path)
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", scandir)
    files = [p.relative_to(tmp_path).as_posix() for p in check_style.default_files(tmp_path)]
    assert files == ["docs/page.md"]
    assert check_style.diagram_problems(tmp_path) == []
    assert ".venv" not in entered and "lib" not in entered, "dot folders are never entered"


def test_the_plain_status_symbols_are_allowed() -> None:
    line = "pass ✓, fail ✗, warning ⚠, waiting ⏳"
    assert _load("lint_prose").lint_text(line) == []
