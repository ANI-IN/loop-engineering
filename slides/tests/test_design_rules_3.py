"""Zero-token checks on the outline builder's rules of design system 3 (slides/design-system.md,
"The third rebuild"): the sample module samples3 passes them, and each rule refuses what it should.

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


outline = _load("slides_outline_design_rules_3", SLIDES_DIR / "source" / "build.py")
SAMPLES = outline.load_design("samples3")


def _sample(kind: str, **match) -> dict:
    return copy.deepcopy(
        next(
            s for s in SAMPLES if s["kind"] == kind and all(s.get(k) == v for k, v in match.items())
        )
    )


def _problems(slide: dict, block: str = "") -> list[str]:
    return outline.check_slide_design_3("test", slide, outline.sources_count(), block)


def _has(problems: list[str], text: str) -> bool:
    return any(text in p for p in problems)


def test_samples3_cover_every_type_and_pass_every_rule():
    assert {s["kind"] for s in SAMPLES} == set(outline.KINDS_3)
    assert {s.get("variant") for s in SAMPLES if s["kind"] == "logistics"} == set(outline.VARIANTS)
    assert outline.check_block_design("samples3", SAMPLES) == []
    assert all(s["_rules"] == outline.DESIGN_SYSTEM_3 for s in SAMPLES)


def test_the_block_plan_of_design_system_3_is_240_minutes_and_at_most_90_slides():
    plan = outline.BLOCK_PLAN_3
    assert sum(minutes for _k, _n, minutes, _m in plan) == 240
    assert sum(most for _k, _n, _minutes, most in plan) <= outline.MAX_SLIDES_3
    assert "foundations" not in [key for key, *_ in plan]
    assert outline.PLANS[outline.DESIGN_SYSTEM_3] is plan


def test_a_title_is_one_line_of_at_most_60_characters():
    slide = _sample("costs")
    slide["title"] = "Why this matters: " + "a very long title " * 4
    assert _has(_problems(slide), "a title is one line of at most 60 characters")


def test_a_failure_story_holds_five_full_sentence_steps_after_an_illustrative_lead():
    slide = _sample("failure")
    assert _problems(slide) == []
    long = copy.deepcopy(slide)
    long["on_slide"][1] = "1. " + "word " * 17 + "end."
    assert _has(_problems(long), "at most 16")
    lead = copy.deepcopy(slide)
    lead["on_slide"][0] = "Lead: A question about revenue."
    assert _has(_problems(lead), "An illustrative")
    four = copy.deepcopy(slide)
    four["on_slide"] = four["on_slide"][:-1]
    assert _has(_problems(four), "five numbered steps")
    fragment = copy.deepcopy(slide)
    fragment["on_slide"][2] = "2. the agent guesses"
    assert _has(_problems(fragment), "full sentence")


def test_a_question_slide_asks_why_not_and_gives_two_or_three_reasons():
    slide = _sample("question")
    assert _problems(slide) == []
    title = {**slide, "title": "Agent loop: Give the agent everything"}
    assert _has(_problems(title), "Why not")
    many = copy.deepcopy(slide)
    many["on_slide"].append("4. A fourth reason")
    assert _has(_problems(many), "2 or 3 numbered reasons")
    no_key = copy.deepcopy(slide)
    no_key["on_slide"] = [x for x in no_key["on_slide"] if not x.startswith("Key idea:")]
    assert _has(_problems(no_key), "Key idea:")


def test_a_technique_slide_holds_three_to_five_lines_of_60_to_100_words():
    slide = _sample("technique")
    assert _problems(slide) == []
    short = copy.deepcopy(slide)
    short["on_slide"] = ["- One line.", "- Two lines.", "- Three lines.", short["on_slide"][-1]]
    assert _has(_problems(short), "want 60-100")
    title = {**slide, "title": "Tools decide what the agent sees"}
    assert _has(_problems(title), "N) Name")
    figure = copy.deepcopy(slide)
    figure["figure"]["diagram"] = "agent-loop"
    assert _has(_problems(figure), "pattern diagram")


def test_a_problem_row_names_its_label_and_a_known_icon():
    slide = _sample("problem")
    assert _problems(slide) == []
    icon = copy.deepcopy(slide)
    icon["on_slide"][1] = "- **Monday:** a wrong answer | rocket"
    assert _has(_problems(icon), "is not one of")
    form = copy.deepcopy(slide)
    form["on_slide"][1] = "- Monday: a wrong answer"
    assert _has(_problems(form), "'- **Label:** text | icon'")


def test_a_quote_names_a_listed_source_and_a_slide_holds_two_to_four():
    slide = _sample("quotes")
    assert _problems(slide) == []
    missing = copy.deepcopy(slide)
    missing["on_slide"][1] = "Quote: a quote | 9999"
    assert _has(_problems(missing), "not in the sources list")
    one = copy.deepcopy(slide)
    one["on_slide"] = one["on_slide"][:2]
    assert _has(_problems(one), "2 to 4 quotes")


def test_a_costs_slide_holds_two_panels_of_two_to_four_points():
    slide = _sample("costs")
    assert _problems(slide) == []
    one = copy.deepcopy(slide)
    one["on_slide"] = [x for x in one["on_slide"] if x != "Panel: What a failure costs"]
    assert _has(_problems(one), "two Panel lines")


def test_a_table_holds_at_most_ten_rows_and_a_glossary_pairs_its_columns():
    slide = _sample("table", title="Business rules: The rules in plain words")
    assert _problems(slide, "problem") == []
    long = copy.deepcopy(slide)
    long["on_slide"][3:3] = ["| Extra | Row |"] * 3
    assert _has(_problems(long, "problem"), "at most 10")
    glossary = _sample("table", title="Glossary: The terms used in every section")
    glossary["on_slide"][1] = "| Term | Meaning | Word | Meaning |"
    assert _has(_problems(glossary, "problem"), "two term-meaning pairs")


def test_teaching_notes_count_250_to_400_words_in_all():
    slide = _sample("concept")
    slide["notes"] = [
        "Purpose: Short.",
        "What to say: Too short to teach anything.",
        "The point to land: One.",
        "Example: Two.",
        "Ask the room: Three?",
        "Misconceptions: Four.",
        "Transition: Five.",
    ]
    assert _has(_problems(slide), "want 250-400")
    table = _sample("table", title="Business rules: The rules in plain words")
    table["notes"] = slide["notes"]
    assert _has(_problems(table, "problem"), "want 250-400")
    assert not _has(_problems(table, "s1"), "want 250-400"), "the full form outside the problem"


def test_do_lines_are_instructions_on_any_slide_and_open_a_demo_run_sheet():
    """Round 1's ruling 23: a "Do:" line may stand in the full notes form on any slide, outside
    the label order and the spoken word count; it holds a command only with allow_commands."""
    slide = _sample("technique")
    slide["notes"].insert(2, "Do: Point at the panel's second box while you say it.")
    assert _problems(slide) == []
    command = copy.deepcopy(slide)
    command["notes"][2] = "Do: Run make reset NAME=agent-loop before this slide."
    assert _has(_problems(command), "path or command")
    assert not _has(_problems({**command, "allow_commands": True}), "path or command")
    demo = _sample("demo")
    demo["notes"][1:1] = ["Do: Open the console on the run board.", "Do: Check the kill switch."]
    assert _problems(demo) == []


def test_a_references_date_has_no_hyphen_to_break():
    import sources

    dated = next(iter(sources.DATES))
    shown = outline.reference_date(dated)
    assert "-" not in shown and shown.split()[1] in outline.MONTHS
    undated = next(n for n in range(1, len(sources.ENTRIES) + 1) if n not in sources.DATES)
    assert outline.reference_date(undated) == sources.ENTRIES[undated - 1][5]


def test_a_note_cites_a_source_as_source_and_its_marker():
    slide = _sample("question")
    slide["notes"][1] = slide["notes"][1].replace("Source [^4]", "Source 4")
    assert _has(_problems(slide), "Source [^n]")


def test_the_insight_callout_and_a_key_idea_off_its_types_are_refused():
    slide = _sample("agenda")
    slide["on_slide"].append("Key idea: not here")
    assert _has(_problems(slide), "a Key idea is drawn on")
    slide = _sample("costs")
    slide["on_slide"].append("Insight: the old callout")
    assert _has(_problems(slide), "no Insight callout")


def test_the_agenda_holds_four_loops_and_one_star():
    slide = _sample("agenda")
    assert _problems(slide) == []
    star = copy.deepcopy(slide)
    star["on_slide"][-1] = "Now: 5"
    assert _has(_problems(star), "'Now: 1' to 'Now: 4'")
    three = copy.deepcopy(slide)
    three["on_slide"] = three["on_slide"][:3]
    assert _has(_problems(three), "the four loops, 1. to 4.")


def test_a_copied_slide_fills_its_slots_in_order():
    slide = _sample("logistics", variant="success")
    assert _problems(slide) == []
    short = {**slide, "on_slide": slide["on_slide"][:-1]}
    assert _has(_problems(short), "fills 9 text slots")
    unknown = {**slide, "variant": "welcome"}
    assert _has(_problems(unknown), "names its variant")
    poll = _sample("poll")
    no_question = {**poll, "on_slide": poll["on_slide"][:2]}
    assert _has(_problems(no_question), "one Question: line")
    assert outline.copied_key({"kind": "break", "minutes": 5}) == "break:5"
    assert outline.copied_key({"kind": "break", "minutes": 10}) == "break:10"


def test_the_scoreboard_belongs_to_the_evidence_slide():
    slide = _sample("design_callout")
    slide["scoreboard"] = 1
    assert _has(_problems(slide), "an evidence slide's section number")


def test_sources_are_numbered_by_first_citation_on_the_slide_then_in_the_notes():
    slides = [
        {"kind": "costs", "on_slide": ["- A point[^30]"], "notes": ["What to say: Source [^7]."]},
        {"kind": "quotes", "on_slide": ["Quote: words | 5", "- again[^30]"], "notes": []},
        {"kind": "references", "on_slide": [], "notes": ["What to say: Source [^99]."]},
    ]
    order = outline.citation_order(slides)
    assert order == {30: 1, 7: 2, 5: 3}
    assert outline.cite("A claim[^5] and [^30]", order) == "A claim[3] and [1]"
    assert outline.cite("Source [^7]", order, "{}") == "Source 2"
    many = {n: n for n in range(1, 14)}
    first, second = outline.reference_rows(many, 1), outline.reference_rows(many, 2)
    # In order of first citation, split between the two tables by height, 12 rows at most each.
    assert [k for k, _n in first + second] == list(range(1, 14))
    assert 1 <= len(first) <= 12 and 1 <= len(second) <= 12
    weights = [outline.reference_weight(n) for n in range(1, 14)]
    split = len(first)
    best = min(max(sum(weights[:k]), sum(weights[k:])) for k in range(1, 13))
    assert max(sum(weights[:split]), sum(weights[split:])) == best
    few = {n: n for n in range(1, 6)}
    assert len(outline.reference_rows(few, 1)) == 5 and outline.reference_rows(few, 2) == []


def test_the_deck_cites_at_most_24_sources_on_two_references_slides():
    slides = [
        {
            "kind": "costs",
            "minutes": 240,
            "on_slide": [f"- p[^{n}]" for n in range(1, 26)],
            "notes": [],
        }
    ]
    problems = outline.deck_problems_3([("x", slides)])
    assert _has(problems, "at most 24")
    assert _has(problems, "two references slides")


def test_a_section_runs_in_the_reference_rhythm():
    slides = [_sample("agenda")] * 2
    assert _has(outline.section_problems_3("s1", slides), "12 slides run")


def test_the_title_slide_spells_out_structured_query_language():
    title = _sample("title")
    assert outline.spelled_out_problems("samples3", [title]) == []
    plain = {**title, "on_slide": title["on_slide"][:2]}
    assert outline.spelled_out_problems("samples3", [plain])
