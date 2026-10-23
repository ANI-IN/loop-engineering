"""Zero-token checks on the deck builder: the eight-slide sample, built from the outline data.

uv run pytest -q slides/tests
"""

from __future__ import annotations

import importlib.util
import re
import sys
import zipfile
from pathlib import Path

import pytest
from pptx import Presentation

SLIDES_DIR = Path(__file__).resolve().parents[1]
REPO = SLIDES_DIR.parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


build_deck = _load("slides_build_deck", SLIDES_DIR / "source" / "build_deck.py")
short_forms = _load("slides_short_forms", REPO / "platform" / "scripts" / "short_forms.py")

URL = re.compile(r"https?://|www\.", re.I)
MAKE = re.compile(r"\bmake [a-z]")
PATH = re.compile(r"\b[\w-]+/[\w./-]+|\.(?:py|ya?ml|md|toml|sql|sh|json|pptx)\b")


@pytest.fixture(scope="module")
def sample(tmp_path_factory):
    out = tmp_path_factory.mktemp("deck") / "sample.pptx"
    count, problems = build_deck.build(out, set(build_deck.SAMPLE))
    return out, count, problems


def _slide_text(slide) -> list[str]:
    texts = []
    for shape in slide.shapes:
        if shape.has_text_frame:
            texts.append(shape.text_frame.text)
        if getattr(shape, "has_table", False) and shape.has_table:
            texts += [cell.text for row in shape.table.rows for cell in row.cells]
    return [t for t in texts if t.strip()]


def test_sample_has_eight_slides(sample):
    out, count, problems = sample
    assert count == 8
    assert len(Presentation(str(out)).slides) == 8
    assert problems == []


def test_every_slide_uses_a_template_layout(sample):
    out, _count, _problems = sample
    template = Presentation(str(build_deck.TEMPLATE))
    template_layouts = {
        (master.part.partname, layout.name)
        for master in template.slide_masters
        for layout in master.slide_layouts
    }
    for slide in Presentation(str(out)).slides:
        layout = slide.slide_layout
        assert layout.name in build_deck.TEMPLATE_LAYOUTS
        assert (layout.slide_master.part.partname, layout.name) in template_layouts


def test_every_slide_has_notes_starting_with_time(sample):
    out, _count, _problems = sample
    for n, slide in enumerate(Presentation(str(out)).slides, 1):
        assert slide.has_notes_slide, f"slide {n} has no notes"
        notes = slide.notes_slide.notes_text_frame.text
        assert notes.startswith("Time: "), f"slide {n} notes lack the Time line"
        assert len(notes.split()) > 20, f"slide {n} notes are too short"
        assert "<!--" not in notes


def test_no_path_command_url_or_short_form_on_any_slide(sample):
    out, _count, _problems = sample
    for n, slide in enumerate(Presentation(str(out)).slides, 1):
        for text in _slide_text(slide):
            assert not URL.search(text), f"slide {n}: URL in {text!r}"
            assert not MAKE.search(text), f"slide {n}: make command in {text!r}"
            assert not PATH.search(text), f"slide {n}: file path in {text!r}"
            assert not short_forms.find(text), f"slide {n}: short form in {text!r}"


def test_demo_slide_holds_badge_and_title_only(sample):
    out, _count, _problems = sample
    demo = Presentation(str(out)).slides[7]
    assert demo.slide_layout.name == "OBJECT"
    assert sorted(_slide_text(demo)) == sorted(
        ["DEMO - 1", "Section 1: Agent loop - Implementation Notes: The confident wrong answer"]
    )
    pictures = [shape.name for shape in demo.shapes if shape.shape_type == 13]
    # The one picture is the laptop of the reference deck, never a screenshot.
    assert pictures == (["laptop picture"] if build_deck.LAPTOP.exists() else [])


def test_query_diagram_marks_every_trap_on_the_spine_question(sample):
    out, _count, _problems = sample
    spine = Presentation(str(out)).slides[1]
    names = {shape.name for shape in spine.shapes}
    for number in range(1, 6):
        assert f"trap marker {number}" in names
        assert f"callout number {number}" in names
        assert f"callout card {number}" in names


def test_question_line_that_repeats_the_title_is_not_drawn(sample):
    out, _count, _problems = sample
    question = Presentation(str(out)).slides[3]
    texts = _slide_text(question)
    assert "Will a stronger model fix the revenue number?" not in texts
    title = "Agent loop: will a stronger model fix the revenue number?"
    assert build_deck._repeats_title("Will a stronger model fix the revenue number?", title)
    assert not build_deck._repeats_title("Will a person approve it?", title)


def test_deck_holds_only_the_deck_fonts(sample):
    out, _count, _problems = sample

    with zipfile.ZipFile(out) as package:
        xml_parts = [n for n in package.namelist() if n.endswith(".xml")]
        faces = set()
        for name in xml_parts:
            faces |= set(
                re.findall(
                    r'<a:(?:latin|ea|cs|sym|buFont) typeface="([^"+][^"]*)"',
                    package.read(name).decode("utf-8"),
                )
            )
    assert faces <= {"Fira Sans", "Lexend Medium"}, faces


def test_every_on_slide_line_is_placed():
    """The builder fails on an unplaced line; building every slide must not raise."""
    for number, _block, spec, time_line in build_deck.all_slides():
        if number in build_deck.SAMPLE:
            content = build_deck.Content.parse(spec.get("on_slide", []))
            build_deck.route(spec)(content, spec)
            assert content.unplaced() == [], f"slide {number}"
            assert time_line.startswith("Time: ")
