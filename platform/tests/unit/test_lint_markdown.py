"""The Markdown lint (platform/scripts/lint_markdown.py with .pymarkdown.yaml): it reads the
configuration strictly, fails on a Markdown fault, and each per-file allow entry is still needed."""

from __future__ import annotations

import fnmatch
import importlib.util
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "platform" / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lint_markdown = _load("lint_markdown")
check_links = sys.modules["check_links"]


def _root(tmp_path: Path, pages: dict[str, str]) -> Path:
    shutil.copy(REPO / lint_markdown.CONFIG_NAME, tmp_path / lint_markdown.CONFIG_NAME)
    for rel, text in pages.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text, encoding="utf-8")
    return tmp_path


def test_a_clean_page_passes_with_the_configuration_read_strictly(tmp_path: Path) -> None:
    root = _root(tmp_path, {"page.md": "# Title\n\nText.\n\n- one\n- two\n"})
    assert lint_markdown.main(["--root", str(root), "page.md"]) == 0


@pytest.mark.parametrize(
    ("text", "rule"),
    [
        ("# Title\n\nText.  \nMore text. \n", "MD009"),  # a trailing space
        ("# Title\n\n### Skipped level\n", "MD001"),
        ("# Title\nText.\n", "MD022"),
        ("# Title\n\n```\ncode\n```\n", "MD040"),  # a code fence with no language
        ("# Title\n\nText.\n\n\n\nMore.\n", "MD012"),
        ("# Title\n\n<span>x</span>\n", "MD033"),  # HTML outside the allowed elements
    ],
)
def test_a_markdown_fault_fails_with_its_rule(
    tmp_path: Path, capfd: pytest.CaptureFixture[str], text: str, rule: str
) -> None:
    root = _root(tmp_path, {"page.md": text})
    assert lint_markdown.main(["--root", str(root), "page.md"]) == 1
    assert "page.md:" in capfd.readouterr().out
    done = subprocess.run(
        lint_markdown.command(["page.md"]), cwd=root, capture_output=True, text=True
    )
    assert rule in done.stdout


def test_a_missing_configuration_is_an_error(tmp_path: Path) -> None:
    (tmp_path / "page.md").write_text("# Title\n", encoding="utf-8")
    assert lint_markdown.main(["--root", str(tmp_path), "page.md"]) == 2


def test_the_configuration_keeps_the_course_conventions(tmp_path: Path) -> None:
    """The settings in .pymarkdown.yaml: the folded answers, the source anchors, an outline-length
    line, the glossary box title, two callouts in a row, and a requirement list that goes on."""
    page = (
        "# Title\n\n> **Terms on this page**\n>\n> - **Term**: what it means.\n\n"
        + ("A line " * 30).strip()
        + '\n\n- <a id="source-1"></a>**[1]** A source.\n\n'
        "1. A question?\n\n   <details><summary>Answer</summary>\n\n   The answer.\n\n"
        "   </details>\n\n"
        "> [!CHECKPOINT]\n> One.\n\n> [!IFDIFFERENT]\n> Two.\n\n"
        "Requirements, again:\n\n8. The eighth.\n9. The ninth.\n"
    )
    root = _root(tmp_path, {"page.md": page})
    assert lint_markdown.main(["--root", str(root), "page.md"]) == 0


def test_the_files_are_the_shipped_markdown_files() -> None:
    files = check_links.shipped_markdown(REPO)
    assert "README.md" in files and "slides/outline.md" in files
    internal = tomllib.loads((REPO / "platform/config/release.toml").read_text())["internal_files"]
    assert internal and not set(files) & set(internal)  # the build's own files never ship
    release = check_links.release_list(REPO)
    assert all(check_links.ships(f, release) for f in files)
    assert not any(f.startswith((".dev/", "research/")) for f in files)


def test_files_are_grouped_by_their_allowed_rules() -> None:
    found = lint_markdown.groups(["README.md", "slides/outline.md", "guide/chapters/1-x.md"])
    assert found[()] == ["README.md"]
    assert found[("md024", "md032", "md034")] == ["slides/outline.md"]
    assert found[("md001",)] == ["guide/chapters/1-x.md"]
    assert lint_markdown.command(["a.md"], ["md001"])[-4:] == [
        "--disable-rules",
        "md001",
        "scan",
        "a.md",
    ]


@pytest.mark.slow
@pytest.mark.parametrize("pattern", sorted(lint_markdown.PER_FILE_ALLOW))
def test_every_per_file_allow_entry_is_still_needed(pattern: str) -> None:
    """Each entry names a reason, matches a shipped file, and each of its rules still fires there:
    an entry that no longer allows anything goes, as the placeholder allow list's entries do."""
    rules = lint_markdown.PER_FILE_ALLOW[pattern]
    assert all(reason.strip() for reason in rules.values())
    files = [f for f in check_links.shipped_markdown(REPO) if fnmatch.fnmatchcase(f, pattern)]
    assert files, f"{pattern} matches no shipped Markdown file"
    done = subprocess.run(
        [sys.executable, "-m", "pymarkdown", "--strict-config", "scan", *files],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    unused = [rule for rule in rules if f"{rule.upper()}:" not in done.stdout]
    assert unused == [], f"no longer needed for {pattern}: drop them"
