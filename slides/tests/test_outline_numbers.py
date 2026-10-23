"""Zero-token checks on the "Numbers this section states" lists: no line may appear twice.

The lists come from each section module's NUMBERS and are copied into slides/outline.md by
slides/source/build.py. Both the data and the generated outline are checked.

uv run pytest -q slides/tests
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SLIDES_DIR = Path(__file__).resolve().parents[1]
OUTLINE = SLIDES_DIR / "outline.md"
HEADING = 'Numbers this section states (each gets a "Re-check after live runs" line in its notes):'


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


outline_builder = _load("slides_outline_numbers", SLIDES_DIR / "source" / "build.py")


def _numbers_lists(text: str) -> list[list[str]]:
    """Every bullet list that follows the numbers heading in the outline, in order."""
    lists: list[list[str]] = []
    current: list[str] | None = None
    for line in text.splitlines():
        if line.strip() == HEADING:
            current = []
            lists.append(current)
            continue
        if current is None:
            continue
        if line.startswith("- "):
            current.append(" ".join(line[2:].split()))
        elif line.strip() and current:
            current = None
    return lists


@pytest.mark.parametrize("section", sorted(outline_builder.SECTION_META))
def test_section_numbers_have_no_duplicate_line(section):
    numbers = outline_builder.load_module_numbers(section)
    assert numbers, f"{section} states no numbers"
    assert outline_builder.duplicate_numbers(numbers) == []


def test_generated_outline_numbers_have_no_duplicate_line():
    lists = _numbers_lists(OUTLINE.read_text(encoding="utf-8"))
    assert len(lists) == len(outline_builder.SECTION_META)
    for i, items in enumerate(lists, 1):
        assert items, f"numbers list {i} is empty"
        repeated = sorted({x for x in items if items.count(x) > 1})
        assert repeated == [], f"numbers list {i} repeats {repeated}"


def test_duplicate_numbers_finds_a_repeat():
    line = "Lease 30 seconds: from the worker settings."
    assert outline_builder.duplicate_numbers([line, "Other.", line]) == [line]
    assert outline_builder.duplicate_numbers([line, "Other."]) == []


def test_generated_outline_has_no_provisional_marker():
    text = OUTLINE.read_text(encoding="utf-8")
    assert outline_builder.PROVISIONAL.search(text) is None


def test_every_block_passes_the_provisional_check():
    for name in outline_builder.APPROVED:
        problems = outline_builder.check_block(name, outline_builder.load(name))
        assert [p for p in problems if "provisional" in p] == [], name
