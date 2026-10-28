"""Zero-token checks on the timings in slides/source: every slide's minutes add up to the
240-minute class, and each block plan is contiguous.

slides/source is superseded (DECISIONS.md, 28 October 2026): slides/outline.md is now a transcript
of the owner's final deck, and the instructor guide's run of show is the deck's. So the checks
that the outline's "Timing:" lines and the guide's run of show came from these minutes went with
that decision; the outline check compares the outline with the deck, and
platform/scripts/check_slide_refs.py compares the guide's run of show with the outline. The
sources are built under one of two rule sets (slides/source/build.py). Under the first outline's
rules the minutes are fixed per position (APPROVED); under the design system each block has a
total (BLOCK_PLAN, the rebuild's block plan of 26 October 2026) and its slides add up to it.

uv run pytest -q slides/tests
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SLIDES_DIR = Path(__file__).resolve().parents[1]
CLASS_MINUTES = 240
# The rebuild's block plan as the lead fixed it (name, start, end, slides at most): the design
# system's BLOCK_PLAN must say the same.
REBUILD_PLAN = [
    ("Opening", "0:00", "0:10", 10),
    ("Designing text-to-SQL", "0:10", "0:25", 6),
    ("Section 1: Agent loop", "0:25", "1:03", 13),
    ("Section 2: Verification loop", "1:03", "1:45", 13),
    ("Break", "1:45", "1:55", 1),
    ("Section 3: Event loop", "1:55", "2:50", 13),
    ("Poll", "2:50", "2:55", 1),
    ("Break", "2:55", "3:05", 1),
    ("Section 4: Hill-climbing loop", "3:05", "3:48", 13),
    ("Closing", "3:48", "4:00", 10),
]


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


def test_the_outline_builds_under_one_rule_set():
    rules, sets = outline_builder.outline_rules()
    assert rules is not None, f"the block modules follow two rule sets: {sets}"


def test_every_slide_minutes_add_up_to_the_class_length():
    """Every slide has time, except the sources slides: a bibliography, not presented, which the
    owner's specification of 27 October 2026 gives zero minutes (design system 3's references
    tables, the same decision under that design system's name for them)."""
    slides = [s for name in outline_builder.block_order() for s in outline_builder.load(name)]
    listing = ("sources", "references")
    assert all(s["minutes"] > 0 for s in slides if s["kind"] not in listing), "every slide has time"
    assert all(s["minutes"] == 0 for s in slides if s["kind"] in listing)
    assert sum(s["minutes"] for s in slides) == CLASS_MINUTES


def test_each_block_matches_its_plan():
    """First outline: the approved minutes per position. Design system: each block's slides add
    up to its total, within its slide cap."""
    rules, _sets = outline_builder.outline_rules()
    if rules == outline_builder.FIRST_OUTLINE:
        for name, approved in outline_builder.APPROVED.items():
            assert [s["minutes"] for s in outline_builder.load(name)] == approved, name
        return
    for key, _name, minutes, most in outline_builder.PLANS[rules]:
        slides = outline_builder.load(key)
        assert sum(s["minutes"] for s in slides) == minutes, key
        assert len(slides) <= most, key


def test_the_design_system_plan_is_the_rebuild_plan():
    """BLOCK_PLAN holds the lead's block plan: names, contiguous clock times, slide caps."""
    plan = outline_builder.BLOCK_PLAN
    assert [name for _k, name, _m, _c in plan] == [row[0] for row in REBUILD_PLAN]
    assert [most for *_rest, most in plan] == [row[3] for row in REBUILD_PLAN]
    t = 0
    for (_key, name, minutes, _most), (_n, start, end, _c) in zip(plan, REBUILD_PLAN, strict=True):
        assert (_clock(start), _clock(end)) == (t, t + minutes * 60), name
        t += minutes * 60
    assert t == CLASS_MINUTES * 60
    assert outline_builder.MAX_SLIDES == 85


# The second rebuild's block plan as the lead fixed it, 27 October 2026 (the closing's cap is its
# 7 slides and at most 7 sources slides).
REBUILD_PLAN_2 = [
    ("Opening", "0:00", "0:05", 3),
    ("The problem", "0:05", "0:17", 4),
    ("Foundations", "0:17", "0:30", 5),
    ("Designing text-to-SQL", "0:30", "0:40", 4),
    ("Section 1: Agent loop", "0:40", "1:15", 13),
    ("Section 2: Verification loop", "1:15", "1:50", 13),
    ("Break", "1:50", "2:00", 1),
    ("Section 3: Event loop", "2:00", "2:48", 13),
    ("Poll", "2:48", "2:53", 1),
    ("Break", "2:53", "3:03", 1),
    ("Section 4: Hill-climbing loop", "3:03", "3:45", 13),
    ("Closing", "3:45", "4:00", 14),
]


def test_the_second_design_system_plan_is_the_second_rebuild_plan():
    plan = outline_builder.BLOCK_PLAN_2
    assert [name for _k, name, _m, _c in plan] == [row[0] for row in REBUILD_PLAN_2]
    assert [most for *_rest, most in plan] == [row[3] for row in REBUILD_PLAN_2]
    t = 0
    for (_key, name, minutes, _most), (_n, start, end, _c) in zip(
        plan, REBUILD_PLAN_2, strict=True
    ):
        assert (_clock(start), _clock(end)) == (t, t + minutes * 60), name
        t += minutes * 60
    assert t == CLASS_MINUTES * 60
    assert sum(most for *_rest, most in plan) <= outline_builder.MAX_SLIDES


def test_the_sources_slides_list_exactly_the_sources_the_deck_cites():
    """Every source a slide marks or a note names is on a sources slide, and every source on a
    sources slide is cited somewhere: the bibliography is neither short nor padded."""
    blocks = [(name, outline_builder.load(name)) for name in outline_builder.block_order()]
    cited, listed = outline_builder.cited_sources(blocks)
    if not listed:
        return
    assert set(cited) == set(listed), {
        "cited, not listed": sorted(set(cited) - set(listed)),
        "listed, not cited": sorted(set(listed) - set(cited)),
    }
