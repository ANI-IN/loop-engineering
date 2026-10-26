"""Zero-token checks on the outline builder's design-system rules (slides/design-system.md): the
sample module passes them, and each rule refuses what it should.

uv run pytest -q slides/tests
"""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

SLIDES_DIR = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


outline = _load("slides_outline_design_rules", SLIDES_DIR / "source" / "build.py")
SAMPLES = outline.load_design("samples")


def _sample(kind: str) -> dict:
    return copy.deepcopy(next(s for s in SAMPLES if s["kind"] == kind))


def _problems(slide: dict) -> list[str]:
    return outline.check_slide_design("test", slide, outline.sources_count())


def test_the_samples_cover_every_type_and_pass_every_rule():
    assert {s["kind"] for s in SAMPLES} == set(outline.KINDS)
    assert outline.check_block_design("samples", SAMPLES) == []


def test_a_concept_type_slide_takes_at_most_four_bullets_and_sixty_words():
    slide = _sample("insight")
    slide["on_slide"] += [f"- Point {n}" for n in range(1, 6)]
    assert any("5 bullets, at most 4" in p for p in _problems(slide))
    slide = _sample("insight")
    slide["on_slide"][0] = "Insight: " + "word " * 70
    assert any("words on the slide, want 15-60" in p for p in _problems(slide))


def test_a_diagram_slide_holds_a_one_line_title_and_the_diagram_only():
    """The lead's decisions of 26 October 2026: a full diagram takes the whole content area; the
    slide has no idea line and no points (they go into the notes), and a title of one line."""
    slide = _sample("concept")
    assert slide["on_slide"] == [] and _problems(slide) == []
    for line in ("Idea: the agent sees the warehouse only through its tools", "- A point"):
        bad = {**slide, "on_slide": [line]}
        assert any("holds its title and the diagram only" in p for p in _problems(bad)), line
    long_title = {**slide, "title": "The agent loop: one analyst, four tools, and hard stops"}
    assert any("title is one line" in p for p in _problems(long_title))


def test_every_section_opener_carries_its_insight():
    slide = _sample("opener")
    without = {**slide, "on_slide": [x for x in slide["on_slide"] if not x.startswith("Insight:")]}
    assert any("needs a line starting 'Insight:'" in p for p in _problems(without))


def test_an_insight_slide_without_screenshot_markers_uses_bullets_not_numbers():
    slide = _sample("insight")
    plain = {**slide, "image": None, "on_slide": [*slide["on_slide"]]}
    assert any("evidence lines are bullets" in p for p in _problems(plain))
    assert not any("evidence lines are bullets" in p for p in _problems(slide)), "markers"


def test_the_make_rule_catches_every_makefile_target_and_not_prose():
    """A make command on a slide or in a non-demo note is "make" and a real target; prose such as
    "make the" or "make sure" is not a command."""
    targets = outline.make_targets()
    assert {"demo", "reset", "outline", "verify", "test", "test-stack"} <= set(targets)
    for target in targets:
        assert outline.NO_REPO.search(f"run make {target} now"), target
        assert outline.NOTE_REPO.search(f"run make {target} now"), target
    assert outline.NO_REPO.search("make demo NAME=agent-simple-question")
    for prose in ("make the agent return", "make sure it posts", "make them right"):
        assert not outline.NO_REPO.search(prose), prose
        assert not outline.NOTE_REPO.search(prose), prose
    assert outline.make_command([]) == r"\bmake [a-z]", "no Makefile: every make word is caught"


def test_an_insight_line_goes_only_on_a_type_that_draws_the_callout():
    assert {"insight", "opener", "evidence", "comparison", "pitfalls"} == outline.INSIGHT_KINDS
    slide = _sample("checklist")
    slide["on_slide"].append("Insight: A lesson that would fall to plain text here.")
    assert any("drawn as the Insight callout only on" in p for p in _problems(slide))
    assert any(line.startswith("Insight:") for line in _sample("opener")["on_slide"])
    assert _problems(_sample("opener")) == []


def test_the_notes_labels_come_in_the_standard_order():
    slide = _sample("insight")
    slide["notes"][0], slide["notes"][1] = slide["notes"][1], slide["notes"][0]
    assert any("in order" in p for p in _problems(slide))
    slide = _sample("insight")
    slide["notes"].insert(1, "Timing: 3 minutes (0:00-0:03)")
    assert any("Timing is generated" in p for p in _problems(slide))


def test_what_to_say_has_its_word_range():
    slide = _sample("mechanism")
    slide["notes"] = [
        "What to say: Too short." if line.startswith("What to say:") else line
        for line in slide["notes"]
    ]
    assert any("What to say has 2 words, want 150-300" in p for p in _problems(slide))


def test_a_demo_slide_gives_each_demo_as_a_full_group():
    slide = _sample("demo")
    slide["notes"] = [line for line in slide["notes"] if not line.startswith("While it runs:")]
    assert any("a DEMO slide's notes give each demo" in p for p in _problems(slide))


def test_demo_notes_quote_the_registry_moment_after_the_expected_output():
    notes = _sample("demo")["notes"]
    moments = outline.registry_moments()
    for i, line in enumerate(notes):
        if line.startswith("Expected output:"):
            assert notes[i + 1].startswith("Guaranteed moment: ")
            assert notes[i + 1].removeprefix("Guaranteed moment: ") in moments.values()


def test_only_a_demo_slide_carries_a_link_and_markers_name_a_source():
    slide = _sample("insight")
    slide["on_slide"].append("Link: Demo page on GitHub | " + outline.GITHUB + "/tree/main/docs")
    assert any("only a DEMO slide carries a link" in p for p in _problems(slide))
    slide = _sample("insight")
    slide["on_slide"][1] += " [^999]"
    assert any("source marker [999]" in p for p in _problems(slide))


def test_code_markers_match_the_numbered_callouts():
    slide = _sample("mechanism")
    slide["on_slide"] = [line for line in slide["on_slide"] if not line.startswith("3.")]
    assert any("code markers [1, 2, 3] differ" in p for p in _problems(slide))


def test_a_block_adds_up_to_its_minutes_within_its_slide_cap():
    slides = [_sample("insight")] * 7
    problems = outline.check_block_design("design", slides)
    assert any("add up to 21 minutes, the block has 15" in p for p in problems)
    assert any("7 slides, at most 6" in p for p in problems)


def test_timing_follows_the_purpose_line():
    notes = outline.with_timing(["Purpose: x.", "What to say: y."], 3, 12 * 60)
    assert notes[1] == "Timing: 3 minutes (0:12-0:15)"


def test_mixed_rule_sets_build_no_outline(monkeypatch, capsys):
    """While some blocks are rewritten and some are not, the outline is not built."""
    sets = {name: outline.FIRST_OUTLINE for name in outline.APPROVED}
    sets["design"] = outline.DESIGN_SYSTEM
    monkeypatch.setattr(outline, "rule_set", lambda name: sets.get(name))
    assert outline.outline_rules()[0] is None
    assert outline.render("unused-path") == 1
    assert "problems: 1" in capsys.readouterr().out
