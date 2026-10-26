"""Zero-token checks on the deck's timings: every slide's minutes add up to the 240-minute class,
and each block starts and ends where the run of show in docs/instructor-guide.md says it does.

The minutes live in slides/source/build.py (APPROVED, one list per block) and in each slide's
`minutes`; the speaker notes' "Time:" lines and slides/outline.md are generated from them.

uv run pytest -q slides/tests
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

SLIDES_DIR = Path(__file__).resolve().parents[1]
REPO = SLIDES_DIR.parent
GUIDE = REPO / "docs" / "instructor-guide.md"
OUTLINE = SLIDES_DIR / "outline.md"
CLASS_MINUTES = 240
# A block heading of the run of show, such as "### Section 1: Agent loop (0:10-0:55)".
BLOCK_HEADING = re.compile(r"^### (?P<name>.+?) \((?P<start>\d:\d\d)-(?P<end>\d:\d\d)\)$", re.M)
TIME_LINE = re.compile(r"^Time: (?P<minutes>[\d.]+) minutes? \((?P<start>[\d:]+)-(?P<end>[\d:]+)\)")


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


outline_builder = _load("slides_outline_timing", SLIDES_DIR / "source" / "build.py")


def _clock(text: str) -> int:
    """Seconds from the class start for "h:mm" or "h:mm:ss"."""
    parts = [int(p) for p in text.split(":")]
    hours, minutes = parts[0], parts[1]
    seconds = parts[2] if len(parts) > 2 else 0
    return hours * 3600 + minutes * 60 + seconds


def _blocks() -> list[tuple[str, int, int]]:
    """(block name, start, end) in seconds, from the outline data, in class order."""
    out, t = [], 0
    for name in outline_builder.APPROVED:
        seconds = sum(int(round(s["minutes"] * 60)) for s in outline_builder.load(name))
        out.append((outline_builder.BLOCK_NAMES[name], t, t + seconds))
        t += seconds
    return out


def test_every_slide_minutes_add_up_to_the_class_length():
    minutes = [
        s["minutes"] for name in outline_builder.APPROVED for s in outline_builder.load(name)
    ]
    assert all(m > 0 for m in minutes), "every slide has time"
    assert sum(minutes) == CLASS_MINUTES


def test_each_block_matches_the_approved_minutes():
    for name, approved in outline_builder.APPROVED.items():
        assert [s["minutes"] for s in outline_builder.load(name)] == approved, name


def test_blocks_match_the_run_of_show_in_the_instructor_guide():
    guide = [
        (m["name"], _clock(m["start"]), _clock(m["end"]))
        for m in BLOCK_HEADING.finditer(GUIDE.read_text(encoding="utf-8"))
    ]
    assert guide == _blocks()
    assert guide[0][1] == 0 and guide[-1][2] == CLASS_MINUTES * 60


def test_outline_time_lines_are_contiguous_and_add_up():
    lines = [
        m
        for line in OUTLINE.read_text(encoding="utf-8").splitlines()
        if (m := TIME_LINE.match(line))
    ]
    assert len(lines) == sum(len(outline_builder.load(n)) for n in outline_builder.APPROVED)
    position = 0
    for m in lines:
        start, end = _clock(m["start"]), _clock(m["end"])
        assert start == position, f"a gap or overlap before {m.group(0)!r}"
        assert end - start == round(float(m["minutes"]) * 60)
        position = end
    assert position == CLASS_MINUTES * 60
