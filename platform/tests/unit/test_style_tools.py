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


@pytest.mark.parametrize(
    ("line", "phrase"),
    [
        ("In today's fast-paced world, agents fail.", "In today's"),
        ("It is important to note that the guard runs first.", "It is important to note"),
        ("Let us dive into the verification loop.", "dive into"),
        ("A deep-dive on graders.", "deep-dive"),
        ("The kill switch is a game changer.", "game changer"),
        ("In conclusion, the router is a table.", "In conclusion"),
        ("Needless to say, the lease expires.", "Needless to say"),
        ("At the end of the day the reviewer reads the answer.", "At the end of the day"),
        ("This will unlock faster reviews.", "unlock"),
    ],
)
def test_the_prose_lint_finds_filler_phrases(line: str, phrase: str) -> None:
    assert _load("lint_prose").lint_text(line) == [(1, f"banned word or phrase: '{phrase}'")]


@pytest.mark.parametrize(
    "line",
    [
        "The worker calls `pg_advisory_unlock` when the job ends.",
        "The reaper can unlock the lease of a dead worker.",
        "Each claim takes a row lock; commit unlocks the row.",
    ],
)
def test_the_prose_lint_allows_the_technical_uses_of_unlock(line: str) -> None:
    assert _load("lint_prose").lint_text(line) == []


def test_an_allowed_use_spares_only_itself() -> None:
    line = "Commit unlocks the row and unlocks new ideas."
    assert _load("lint_prose").lint_text(line) == [(1, "banned word or phrase: 'unlocks'")]


def test_the_prose_lint_reads_the_slide_sources() -> None:
    lint_prose = _load("lint_prose")
    assert "slides/source/opening.py" in lint_prose.SLIDE_SOURCES
    assert all(name.endswith(".py") for name in lint_prose.SLIDE_SOURCES)


def test_the_prose_lint_reports_file_line_and_phrase(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    page = tmp_path / "page.md"
    page.write_text("# Page\n\nNeedless to say, it works ✨\n", encoding="utf-8")
    assert _load("lint_prose").main([str(page)]) == 1
    output = capsys.readouterr().out
    assert f"x {page}:3: banned word or phrase: 'Needless to say'" in output
    assert f"x {page}:3: emoji" in output


def test_the_plain_status_symbols_are_allowed() -> None:
    line = "pass ✓, fail ✗, warning ⚠, waiting ⏳"
    assert _load("lint_prose").lint_text(line) == []
