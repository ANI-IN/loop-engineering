"""Prose lint for course documents: banned words and phrases, and emoji.

Usage: python platform/scripts/lint_prose.py [PATH ...]   (default: the course documents)
A line ending with `<!-- lint-prose: allow -->` is skipped (for quoting the banned list itself).
Exact titles of cited sources are allowed even when they contain a banned word: list them under
[prose].allowed_titles in platform/config/course.toml.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

REPO = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
CONFIG_FILE = REPO / "platform" / "config" / "course.toml"

# Every Markdown page of the course; section folders are found by name.
DEFAULT_TARGETS = [
    "README.md",
    "setup",
    "docs",
    "final-project",
    "slides",
    "use-in-your-repo",
    "guide",
] + sorted(p.name for p in REPO.glob("section-*") if p.is_dir())

BANNED_WORDS = [
    r"seamless(?:ly)?",
    r"robust",
    r"powerful",
    r"leverag\w*",
    r"unlock\w*",
    r"unleash\w*",
    r"supercharg\w*",
    r"game-changer",
    r"cutting-edge",
    r"state-of-the-art",
    r"revolutioni[sz]\w*",
    r"transformative",
    r"delv(?:e|es|ed|ing)",
    r"elevat(?:e|es|ed|ing)",
    r"empower\w*",
    r"journey",
    r"landscape",
    r"ecosystem",
    r"next-level",
    r"world-class",
    r"best-in-class",
    r"effortless\w*",
    r"synergy",
    r"holistic",
]
# Words that only make sense on the day they were written: say "today", "in class", "this session",
# or "this run" instead.
TIME_WORDS = [
    r"tonight",
    r"tomorrow",
    r"yesterday",
    r"last night",
    r"this evening",
    r"this morning",
]
BANNED_PHRASES = [
    r"paradigm shift",
    r"in today['’]s",
    r"it['’]s important to note",
    r"dive deep",
    r"deep dive",
    r"harness the power",
    r"a testament to",
]


def _allowed_titles() -> list[str]:
    if not CONFIG_FILE.is_file():
        return []
    with CONFIG_FILE.open("rb") as handle:
        return list(tomllib.load(handle).get("prose", {}).get("allowed_titles", []))


ALLOWED_TITLES = _allowed_titles()
ALLOW_MARKER = "<!-- lint-prose: allow -->"

_BANNED = re.compile(
    r"\b(?:" + "|".join(BANNED_WORDS + TIME_WORDS + BANNED_PHRASES) + r")\b", re.IGNORECASE
)
# Pictographic emoji and the emoji variation selector. Status symbols such as ✓ ✗ ⚠ ⏳ are allowed.
_EMOJI = re.compile("[\U0001f000-\U0001faff️]")


def _documents(targets: list[str]) -> list[Path]:
    files: list[Path] = []
    for target in targets:
        path = Path(target) if Path(target).is_absolute() else REPO / target
        if path.is_dir():
            files.extend(
                sorted(
                    p
                    for p in path.rglob("*.md")
                    # engineering-notes/ quotes instructions verbatim: never edited.
                    # (the module's private notes folder, if it keeps one)
                    if ".venv" not in p.parts and "engineering-notes" not in p.parts
                )
            )
        elif path.is_file():
            files.append(path)
    return files


def lint_text(text: str) -> list[tuple[int, str]]:
    problems: list[tuple[int, str]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if line.rstrip().endswith(ALLOW_MARKER):
            continue
        checked = line
        for title in ALLOWED_TITLES:
            checked = checked.replace(title, "")
        for match in _BANNED.finditer(checked):
            problems.append((number, f"banned word or phrase: '{match.group(0)}'"))
        if _EMOJI.search(checked):
            problems.append((number, "emoji"))
    return problems


def main(argv: list[str]) -> int:
    files = _documents(argv or DEFAULT_TARGETS)
    count = 0
    for path in files:
        for number, message in lint_text(path.read_text(encoding="utf-8")):
            shown = path.relative_to(REPO) if path.is_relative_to(REPO) else path
            print(f"x {shown}:{number}: {message}")
            count += 1
    print(f"{len(files)} files checked, {count} problems")
    return 1 if count else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
