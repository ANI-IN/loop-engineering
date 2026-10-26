"""Zero-token check of the outline builder's duplicate finder for "Numbers this section states".

The first outline copied each section's NUMBERS list into slides/outline.md. The rebuilt deck runs
on the design system, where each number's evidence is in its slide's notes and the outline prints
no such list (DECISIONS.md, 26 October 2026, the deck rebuild), so the checks of those lists were
removed with them; the helper they used is still tested here.

uv run pytest -q slides/tests
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SLIDES_DIR = Path(__file__).resolve().parents[1]
OUTLINE = SLIDES_DIR / "outline.md"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


outline_builder = _load("slides_outline_numbers", SLIDES_DIR / "source" / "build.py")


def test_duplicate_numbers_finds_a_repeat():
    line = "Lease 30 seconds: from the worker settings."
    assert outline_builder.duplicate_numbers([line, "Other.", line]) == [line]
    assert outline_builder.duplicate_numbers([line, "Other."]) == []


def test_generated_outline_has_no_provisional_marker():
    text = OUTLINE.read_text(encoding="utf-8")
    assert outline_builder.PROVISIONAL.search(text) is None


def test_every_block_passes_the_provisional_check():
    for name in outline_builder.block_order():
        problems = outline_builder.check(name, outline_builder.load(name))
        assert [p for p in problems if "provisional" in p] == [], name
