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
    """Each rule set checks a block against its own plan. The sample module moved to design
    system 2 (27 October 2026), so the first plan is named explicitly here and the second plan's
    design block (10 minutes, 4 slides) is checked too."""
    slides = [_sample("insight")] * 7
    problems = outline.check_block_design("design", slides, outline.DESIGN_SYSTEM)
    assert any("add up to 21 minutes, the block has 15" in p for p in problems)
    assert any("7 slides, at most 6" in p for p in problems)
    problems = outline.check_block_design("design", slides, outline.DESIGN_SYSTEM_2)
    assert any("add up to 21 minutes, the block has 10" in p for p in problems)
    assert any("7 slides, at most 4" in p for p in problems)


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


# ------------------------------------------------------------------------------------------------
# Design system 2: the second rebuild (27 October 2026)


def _plan_keys(rules: str) -> list[str]:
    return [key for key, *_ in outline.PLANS[rules]]


def test_the_second_rebuild_is_chosen_only_when_every_block_follows_it(monkeypatch):
    """The gate stays green while the modules are on the first design system: design system 2 is
    built only when every block of its plan, the problem and foundations blocks too, sets it."""
    two = {key: outline.DESIGN_SYSTEM_2 for key in _plan_keys(outline.DESIGN_SYSTEM_2)}
    monkeypatch.setattr(outline, "rule_set", lambda name: two.get(name))
    assert outline.outline_rules()[0] == outline.DESIGN_SYSTEM_2
    assert outline.block_order() == _plan_keys(outline.DESIGN_SYSTEM_2)
    one = {key: outline.DESIGN_SYSTEM for key in _plan_keys(outline.DESIGN_SYSTEM)}
    mixed = {**one, "s1": outline.DESIGN_SYSTEM_2}
    monkeypatch.setattr(outline, "rule_set", lambda name: mixed.get(name))
    assert outline.outline_rules()[0] is None
    early = {**one, "problem": outline.DESIGN_SYSTEM_2}  # a new block written before the rest
    monkeypatch.setattr(outline, "rule_set", lambda name: early.get(name))
    assert outline.outline_rules()[0] is None
    monkeypatch.setattr(outline, "rule_set", lambda name: one.get(name))
    assert outline.outline_rules()[0] == outline.DESIGN_SYSTEM


def test_the_second_plan_holds_240_minutes_and_at_most_85_slides():
    plan = outline.BLOCK_PLAN_2
    assert sum(minutes for _k, _n, minutes, _c in plan) == 240
    assert sum(most for *_rest, most in plan) == outline.MAX_SLIDES == 85


def test_a_pattern_slide_holds_its_four_lines_and_a_pattern_diagram():
    slide = _sample("pattern")
    assert _problems(slide) == []
    extra = {**slide, "on_slide": [*slide["on_slide"], "- A bullet"]}
    assert any("holds only Definition:" in p for p in _problems(extra))
    missing = {**slide, "on_slide": [x for x in slide["on_slide"] if not x.startswith("Avoid")]}
    assert any("needs a line starting 'Avoid when:'" in p for p in _problems(missing))
    unsourced = {
        **slide,
        "on_slide": [outline.MARKER.sub("", x) for x in slide["on_slide"]],
    }
    assert any("only where sourced" in p for p in _problems(unsourced))
    long = {
        **slide,
        "on_slide": [
            "Use when: " + "x" * 60 if x.startswith("Use") else x for x in slide["on_slide"]
        ],
    }
    assert any("the Use when: line is one line" in p for p in _problems(long))
    full = {**slide, "figure": {"diagram": "agent-loop", "alt": "a full diagram"}}
    assert any("shows a pattern diagram" in p for p in _problems(full))
    concept = {**_sample("concept"), "figure": slide["figure"]}
    assert any("show it on a pattern slide" in p for p in _problems(concept))


def test_a_problem_slide_holds_a_lead_and_three_to_six_items_with_loop_tags():
    slide = _sample("problem")
    assert _problems(slide) == []
    seven = {**slide, "on_slide": [slide["on_slide"][0]] + [f"- Item {n}" for n in range(7)]}
    assert any("7 bullets, at most 6" in p for p in _problems(seven))
    tagged = {**slide, "on_slide": [*slide["on_slide"][:3], "- Item | Section 9"]}
    assert any("names a loop or a section" in p for p in _problems(tagged))
    assert outline.loop_tag("Section 2: Verification loop") == "s2"
    assert outline.loop_tag("Event loop") == "s3"
    assert outline.loop_tag("Section 2: Event loop") is None
    short_notes = {
        **slide,
        "notes": [
            "What to say: A short talk track." if x.startswith("What to say:") else x
            for x in slide["notes"]
        ],
    }
    assert any("want 300-400" in p for p in _problems(short_notes))


def test_a_payoff_slide_holds_before_after_level_four_loops_and_the_checks():
    slide = _sample("payoff")
    assert _problems(slide) == []
    shuffled = [x for x in slide["on_slide"] if not x.startswith("Loop: Section 2")]
    assert any("four Loop lines" in p for p in _problems({**slide, "on_slide": shuffled}))
    no_value = [
        "Before: the first answer" if x.startswith("Before:") else x for x in slide["on_slide"]
    ]
    assert any(
        "'Before: <label> | <value>'" in p for p in _problems({**slide, "on_slide": no_value})
    )


def test_the_scoreboard_field_is_a_recap_section_number():
    assert _problems(_sample("recap")) == []
    assert any("a scoreboard is" in p for p in _problems({**_sample("recap"), "scoreboard": 5}))
    assert any("a scoreboard is" in p for p in _problems({**_sample("checklist"), "scoreboard": 1}))
    assert set(outline.SCOREBOARD) == {1, 2, 3, 4}
    assert outline.SCOREBOARD[4].startswith("Correct: $64,015,091.21")


def test_the_evidence_diet_keeps_run_ids_dates_and_samples_off_concept_slides():
    slide = _sample("checklist")
    for line, words in (
        ("- Compare with run 9182df01 by hand", "a run id"),
        ("- Measured on 24 October 2026", "a date"),
        ("- Measured on October 24", "a date"),
        ("Sample: 21 runs per side", "a Sample line"),
    ):
        bad = {**slide, "on_slide": [*slide["on_slide"][:4], line]}
        assert any(words in p for p in _problems(bad)), line
    for kind in ("evidence", "demo", "payoff"):
        assert not any(
            "goes into the notes" in p or "go into the notes" in p for p in _problems(_sample(kind))
        ), kind
    # The first design system keeps its own rules: the diet is design system 2's.
    first = {
        **slide,
        "_rules": outline.DESIGN_SYSTEM,
        "on_slide": [*slide["on_slide"][:4], "- Measured on 24 October 2026"],
    }
    assert not any("a date" in p for p in _problems(first))
    assert not outline.RUN_ID.search("72,394,572.08 and fiscal year 2025 and deadbeef")


def test_a_mechanism_slide_labels_its_code_panel():
    slide = copy.deepcopy(
        next(s for s in SAMPLES if s["kind"] == "mechanism" and s["code"]["panel"] == "DataPilot")
    )
    unlabelled = {**slide, "code": {k: v for k, v in slide["code"].items() if k != "panel"}}
    assert any("the code names its panel" in p for p in _problems(unlabelled))
    named = {**slide, "code": {**slide["code"], "panel": "Pattern"}}
    assert any("no DataPilot names" in p for p in _problems(named))


def _section(kinds: list[str]) -> list[dict]:
    slides = []
    for kind in kinds:
        s = _sample(kind)
        s["_block"] = "s3"
        if kind == "recap":
            s["scoreboard"] = 3
        slides.append(s)
    return slides


def test_a_section_has_two_code_slides_one_insight_on_its_opener_and_its_scoreboard():
    good = _section(["opener", "pattern", "mechanism", "mechanism", "demo", "recap"])
    problems = outline.check_block_design("s3", good, outline.DESIGN_SYSTEM_2)
    assert not [p for p in problems if p.startswith("s3:") and "minutes" not in p], problems
    three = _section(["opener", "mechanism", "mechanism", "mechanism", "demo", "recap"])
    problems = outline.check_block_design("s3", three, outline.DESIGN_SYSTEM_2)
    assert any("3 code slides, at most 2" in p for p in problems)
    two_insights = _section(["opener", "comparison", "demo", "recap"])
    problems = outline.check_block_design("s3", two_insights, outline.DESIGN_SYSTEM_2)
    assert any("one insight per section, on its opener" in p for p in problems)
    no_board = _section(["opener", "demo", "recap"])
    no_board[-1]["scoreboard"] = 2
    problems = outline.check_block_design("s3", no_board, outline.DESIGN_SYSTEM_2)
    assert any("scoreboard of Section 3" in p for p in problems)


def test_structured_query_language_is_spelled_out_once_on_the_title_slide():
    title, agenda = _sample("title"), _sample("agenda")
    assert outline.spelled_out_problems("opening", [title, agenda]) == []
    spelled = {
        **agenda,
        "on_slide": ["1. Designing Structured Query Language agents", "2. b", "3. c"],
    }
    problems = outline.spelled_out_problems("opening", [title, spelled])
    assert any("spelled out once in the deck" in p for p in problems)
    bare = {**title, "on_slide": ["Module: Loop Engineering", "Turn questions into SQL"]}
    assert any(
        "the title slide spells out" in p for p in outline.spelled_out_problems("opening", [bare])
    )
    assert outline.spelled_out_problems("s1", [spelled])
