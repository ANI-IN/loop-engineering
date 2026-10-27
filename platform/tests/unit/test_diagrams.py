"""The diagrams: every Excalidraw source has a current SVG and PNG, and every source follows the
canvas and naming rules. Zero cost: no browser, no network, no model; the renders are compared by
the SHA-256 recorded in each folder's renders.json (platform/tools/diagrams/export_diagrams.py)."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType

import pytest

from datapilot.contracts.lifecycle import TRANSITIONS
from datapilot.settings import PLATFORM

TOOLS = PLATFORM / "tools" / "diagrams"


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses look their module up by name
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def exporter() -> ModuleType:
    return _load("export_diagrams", TOOLS / "export_diagrams.py")


@pytest.fixture(scope="module")
def short_forms() -> ModuleType:
    return _load("short_forms", PLATFORM / "scripts" / "short_forms.py")


@pytest.fixture(scope="module")
def sources(exporter: ModuleType) -> list[Path]:
    found = exporter.sources()
    assert found, "no diagram sources found"
    return found


def _scene(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _texts(path: Path) -> list[str]:
    return [e["text"] for e in _scene(path)["elements"] if e["type"] == "text"]


def test_every_source_has_a_current_svg_and_png(exporter: ModuleType) -> None:
    assert exporter.problems() == [], "run platform/tools/diagrams/export_diagrams.py"


def test_the_check_notices_a_changed_source(exporter: ModuleType, tmp_path: Path) -> None:
    folder = tmp_path / "docs" / "diagrams"
    folder.mkdir(parents=True)
    source = folder / "example.excalidraw"
    source.write_text('{"elements": []}\n', encoding="utf-8")
    (folder / "example.svg").write_text("<svg/>\n", encoding="utf-8")
    (folder / "example.png").write_bytes(b"png")
    manifest = {
        "excalidraw": exporter.EXCALIDRAW_VERSION,
        "renders": {
            "example": {
                "source": exporter.sha256(source),
                "svg": exporter.sha256(folder / "example.svg"),
                "png": exporter.sha256(folder / "example.png"),
            }
        },
    }
    exporter.write_manifest(folder, manifest)
    assert exporter.problems(tmp_path) == []
    source.write_text('{"elements": [1]}\n', encoding="utf-8")
    (folder / "example.png").write_bytes(b"edited by hand")
    assert exporter.problems(tmp_path) == [
        "docs/diagrams/example.excalidraw: changed since its last render",
        "docs/diagrams/example.png: not the recorded render",
    ]


def test_the_check_notices_a_missing_render_or_record(exporter: ModuleType, tmp_path: Path) -> None:
    folder = tmp_path / "docs" / "diagrams"
    folder.mkdir(parents=True)
    (folder / "drawn.excalidraw").write_text('{"elements": []}\n', encoding="utf-8")
    (folder / "drawn.svg").write_text("<svg/>\n", encoding="utf-8")
    entry = {"source": exporter.sha256(folder / "drawn.excalidraw")}
    entry |= {"svg": exporter.sha256(folder / "drawn.svg"), "png": "0" * 64}
    manifest = {"excalidraw": exporter.EXCALIDRAW_VERSION, "renders": {"drawn": entry}}
    manifest["renders"]["deleted"] = entry
    exporter.write_manifest(folder, manifest)
    (folder / "new.excalidraw").write_text('{"elements": []}\n', encoding="utf-8")
    assert exporter.problems(tmp_path) == [
        "docs/diagrams/drawn.excalidraw: no .png",
        "docs/diagrams/new.excalidraw: never rendered",
        "docs/diagrams/renders.json: deleted has no source",
    ]


def test_every_source_parses_as_a_scene_with_its_panel_first(exporter: ModuleType) -> None:
    assert exporter.parse_problems() == []


def test_the_parse_check_names_each_source_that_is_not_a_scene(
    exporter: ModuleType, tmp_path: Path
) -> None:
    folder = tmp_path / "docs" / "diagrams"
    folder.mkdir(parents=True)
    panel = '{"elements": [{"type": "rectangle", "width": 1920, "height": 540}]}\n'
    for name, text in {
        "broken": '{"elements": [\n',
        "empty": '{"elements": []}\n',
        "list": "[]\n",
        "no-panel": '{"elements": [{"type": "text"}]}\n',
        "no-size": '{"elements": [{"type": "rectangle"}]}\n',
        "good": panel,
    }.items():
        (folder / f"{name}.excalidraw").write_text(text, encoding="utf-8")
    found = exporter.parse_problems(tmp_path)
    assert [line.split(":")[0] for line in found] == [
        "docs/diagrams/broken.excalidraw",
        "docs/diagrams/empty.excalidraw",
        "docs/diagrams/list.excalidraw",
        "docs/diagrams/no-panel.excalidraw",
        "docs/diagrams/no-size.excalidraw",
    ]
    assert "does not parse as JSON" in found[0]
    assert found[1].endswith("holds no list of elements")
    assert found[3].endswith("its first element is not the panel rectangle")
    assert found[4].endswith("its panel has no width and height")
    assert exporter.deck_sources(tmp_path) == [folder / "good.excalidraw"]


def test_the_export_page_pins_one_exact_excalidraw_version(exporter: ModuleType) -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", exporter.EXCALIDRAW_VERSION)
    assert exporter.page_version() == exporter.EXCALIDRAW_VERSION
    for folder in exporter.diagram_folders():
        assert exporter.read_manifest(folder)["excalidraw"] == exporter.EXCALIDRAW_VERSION


def test_every_svg_embeds_its_font(sources: list[Path]) -> None:
    for source in sources:
        svg = source.with_suffix(".svg").read_text(encoding="utf-8")
        assert "@font-face" in svg and "data:font/woff2;base64," in svg, source.name


# A slide diagram is 1920 by 791, the shape of the deck's diagram panel of 12.13 by 5.0 inches,
# where 40 pixels are 18.2 points; a page-only reference diagram is 1920 by 1080 with labels of 20
# pixels or more. The deck rebuild of 26 October 2026 set the 18-point rule, first on a 1920 by 848
# canvas (a panel of 12 by 5.3 inches), then on 1920 by 791 once the real panel was measured;
# before it every diagram was a 1920 by 1080 panel with labels of 20 pixels or more. The second
# deck rebuild of 27 October 2026 added the pattern diagram, 1920 by 540, the shape of a pattern
# slide's panel of 12.13 by 3.41 inches, with the same 40-pixel labels. The third deck rebuild
# (design system 3, 27 October 2026) added the concept diagram, 1920 by 712, the shape of a
# concept slide's panel of 12.13 by 4.5 inches, with the same 40-pixel labels.
MIN_LABEL = {791: 40, 712: 40, 540: 40, 1080: 20}


def test_every_diagram_is_a_slide_pattern_or_page_panel_with_labels_of_its_minimum_size(
    sources: list[Path],
) -> None:
    for source in sources:
        elements = _scene(source)["elements"]
        panel = elements[0]
        height = panel["height"]
        assert (panel["x"], panel["y"], panel["width"]) == (0, 0, 1920), source.name
        assert height in MIN_LABEL, source.name
        assert panel["backgroundColor"] == "#F0F3F6", source.name
        for element in elements:
            if element["type"] == "text":
                assert element["fontSize"] >= MIN_LABEL[height], (source.name, element["text"])
            points = element.get("points") or [[0, 0], [element["width"], element["height"]]]
            xs = [element["x"] + p[0] for p in points]
            ys = [element["y"] + p[1] for p in points]
            assert min(xs) >= 0 and max(xs) <= 1920, element["id"]
            assert min(ys) >= 0 and max(ys) <= height, element["id"]


# docs/diagrams/README.md, "Diagram style": the values every source must keep.
STYLE_FILLS = {
    "#3896D2",  # Agent loop
    "#0097A7",  # Verification loop
    "#FFAB40",  # Event loop
    "#EEFF41",  # Hill-climbing loop
    "#FFFFFF",
    "#EEEEEE",
    "#F0F3F6",
    "transparent",
}
STYLE_STROKES = {"#212121", "#78909C", "transparent"}


def test_every_element_follows_the_diagram_style(sources: list[Path]) -> None:
    """Roughness 0, Nunito for labels and the code font for code, dark text, three stroke widths,
    one arrow style, and fills from the four loop colours and the neutrals only."""
    for source in sources:
        for element in _scene(source)["elements"]:
            where = (source.name, element["id"])
            assert element["roughness"] == 0, where
            if element["type"] == "text":
                assert element["fontFamily"] in (6, 8), where  # Nunito, Comic Shanns
                assert element["strokeColor"] == "#212121", where
                continue
            assert element["strokeWidth"] in (2, 3, 4), where
            assert element["strokeColor"] in STYLE_STROKES, where
            assert element["backgroundColor"] in STYLE_FILLS, where
            if element["type"] in ("arrow", "line"):
                assert element["strokeWidth"] == 3 and element["strokeStyle"] == "solid", where
            if element["type"] == "arrow":
                assert element["endArrowhead"] == "triangle", where
                assert element["startArrowhead"] in (None, "triangle"), where


def test_the_four_loop_map_has_one_variant_per_section(sources: list[Path]) -> None:
    """Each variant keeps every label of the map and mutes the other loops: no fill in another
    loop's colour, and the highlighted loop's colour still there."""
    by_name = {s.stem: s for s in sources}
    full = sorted(_texts(by_name["four-loops"]))
    colours = {
        "agent": "#3896D2",
        "verification": "#0097A7",
        "event": "#FFAB40",
        "hill-climbing": "#EEFF41",
    }
    for loop, colour in colours.items():
        variant = by_name[f"four-loops-{loop}-loop"]
        assert sorted(_texts(variant)) == full, variant.name
        fills = {e["backgroundColor"] for e in _scene(variant)["elements"]}
        assert colour in fills, variant.name
        assert not fills & (set(colours.values()) - {colour}), variant.name


def test_every_page_png_is_its_panel_at_scale_2(exporter: ModuleType, sources: list[Path]) -> None:
    """The export page takes the scale from getDimensions; before 26 October 2026 it set only
    appState.exportScale, which this Excalidraw build ignores, so every PNG came out at scale 1."""
    for source in sources:
        panel = _scene(source)["elements"][0]
        png = source.with_suffix(".png").read_bytes()
        assert exporter.png_size(png) == (panel["width"] * 2, panel["height"] * 2), source.name


def test_the_png_size_comes_from_the_header(exporter: ModuleType) -> None:
    header = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR" + (5760).to_bytes(4, "big")
    assert exporter.png_size(header + (2373).to_bytes(4, "big") + b"\x08\x06") == (5760, 2373)
    with pytest.raises(ValueError):
        exporter.png_size(b"GIF89a" + bytes(30))


def test_the_deck_scene_leaves_out_only_the_panel_fill(exporter: ModuleType) -> None:
    source = exporter.REPO / "docs" / "diagrams" / "four-loops.excalidraw"
    scene = _scene(source)
    deck = exporter.deck_scene(scene)
    panel = deck["elements"][0]
    assert panel["backgroundColor"] == "transparent" and panel["strokeColor"] == "transparent"
    assert (panel["width"], panel["height"]) == (1920, 791), "the export keeps the panel's size"
    assert deck["elements"][1:] == scene["elements"][1:]
    assert scene["elements"][0]["backgroundColor"] == "#F0F3F6", "the source is unchanged"


def test_the_deck_check_notices_a_missing_or_stale_export(
    exporter: ModuleType, tmp_path: Path
) -> None:
    folder = tmp_path / "docs" / "diagrams"
    folder.mkdir(parents=True)
    panel = {"x": 0, "y": 0, "width": 1920, "height": 791}
    slide = folder / "slide.excalidraw"
    slide.write_text(json.dumps({"elements": [panel]}), encoding="utf-8")
    page = folder / "page.excalidraw"
    page.write_text(json.dumps({"elements": [{**panel, "height": 1080}]}), encoding="utf-8")
    step = folder / "slide-step-1.excalidraw"
    step.write_text(json.dumps({"elements": [panel]}), encoding="utf-8")
    assert exporter.deck_sources(tmp_path) == [slide], "slide diagrams only, no step frames"
    assert exporter.deck_problems(tmp_path) == [], "no deck assets folder: nothing to check"
    patterns = folder / "patterns"
    patterns.mkdir()
    pattern = patterns / "pattern.excalidraw"
    pattern.write_text(json.dumps({"elements": [{**panel, "height": 540}]}), encoding="utf-8")
    assert exporter.deck_sources(tmp_path) == [slide, pattern], "pattern diagrams go to the deck"
    pattern.unlink()

    deck = tmp_path / exporter.DECK.relative_to(exporter.REPO)
    deck.mkdir(parents=True)
    rel = deck.relative_to(tmp_path).as_posix()
    assert exporter.deck_problems(tmp_path) == [f"{rel}/slide.png: never exported for the deck"]
    (deck / "slide.png").write_bytes(b"png")
    entry = {
        "from": "docs/diagrams/slide.excalidraw",
        "source": exporter.sha256(slide),
        "png": exporter.sha256(deck / "slide.png"),
    }
    exporter.write_deck_manifest(deck, {"excalidraw": "0.18.1", "renders": {"slide": entry}})
    assert exporter.deck_problems(tmp_path) == []
    assert exporter.deck_stale(tmp_path) == []
    slide.write_text(json.dumps({"elements": [panel, {}]}), encoding="utf-8")
    (deck / "stray.png").write_bytes(b"png")
    assert exporter.deck_problems(tmp_path) == [
        f"{rel}/slide.png: its source changed since the export",
        f"{rel}/stray.png: not recorded in renders.json",
    ]
    assert exporter.deck_stale(tmp_path) == [slide]


def test_step_frames_count_up_from_one_and_end_at_the_full_diagram(sources: list[Path]) -> None:
    by_name = {s.stem: s for s in sources}
    for name in by_name:
        found = re.fullmatch(r"(.+)-step-(\d+)", name)
        if not found:
            continue
        base, step = found.group(1), int(found.group(2))
        assert base in by_name, name
        assert step == 1 or f"{base}-step-{step - 1}" in by_name, name
        last = max(
            int(m.group(1)) for n in by_name if (m := re.fullmatch(rf"{base}-step-(\d+)", n))
        )
        if step == last:
            assert _scene(by_name[name])["elements"] == _scene(by_name[base])["elements"], name


def test_every_label_follows_the_naming_rule(sources: list[Path], short_forms: ModuleType) -> None:
    """Each diagram is a page: no short forms, no shorthand, and SQL, API, UTC, and the other
    technical terms spelled out on their first use."""
    for source in sources:
        text = "\n".join(_texts(source))
        assert short_forms.check_short_forms(text, markdown=False) == [], source.name
        assert short_forms.check_shorthand(text, markdown=False) == [], source.name
        assert short_forms.check_first_use(text, markdown=False) == [], source.name


def test_the_run_lifecycle_names_the_writer_of_every_transition(exporter: ModuleType) -> None:
    source = exporter.REPO / "docs" / "diagrams" / "run-lifecycle.excalidraw"
    text = "\n".join(_texts(source))
    for number, ((frm, to), by) in enumerate(TRANSITIONS.items(), start=1):
        assert f"{number:>2}  {frm.value} to {to.value}, {by}" in text


PATTERNS = [
    "pattern-agent-loop",
    "pattern-tool-design",
    "pattern-progressive-disclosure",
    "pattern-structured-output",
    "pattern-defence-in-depth",
    "pattern-parse-allowlist",
    "pattern-least-privilege",
    "pattern-bounded-retry",
    "pattern-idempotency-key",
    "pattern-lease-queue",
    "pattern-durable-approval",
    "pattern-autonomy-levels",
    "pattern-eval-driven",
    "pattern-dev-holdout",
    "pattern-goodhart",
    "pattern-promotion-gate",
    # The third deck rebuild (27 October 2026) adds one per technique where none fitted.
    "pattern-row-cap",
    "pattern-stops-envelope",
    "pattern-value-lookup",
    "pattern-judge-two-databases",
    "pattern-agents-propose",
    "pattern-autonomy-per-family",
]


def test_the_pattern_diagrams_are_generic_neutral_pattern_panels(
    exporter: ModuleType, sources: list[Path]
) -> None:
    """The second deck rebuild's sixteen pattern diagrams (27 October 2026), in
    docs/diagrams/patterns/: each on the 1920 by 540 pattern panel, with 3 to 7 filled shapes, no
    loop colour (docs/diagrams/patterns/README.md, "The fill rule"), and no name from DataPilot,
    since each teaches the pattern for any agent."""
    folder = exporter.REPO / "docs" / "diagrams" / "patterns"
    found = sorted(s.stem for s in sources if s.parent == folder)
    assert found == sorted(PATTERNS)
    readme = (folder / "README.md").read_text(encoding="utf-8")
    loop_fills = {"#3896D2", "#0097A7", "#FFAB40", "#EEFF41"}
    for name in PATTERNS:
        assert f"](./{name}.svg)" in readme, f"{name}: not shown in the README"
        elements = _scene(folder / f"{name}.excalidraw")["elements"]
        assert (elements[0]["width"], elements[0]["height"]) == (1920, 540), name
        shapes = [
            e
            for e in elements[1:]
            if e["type"] in ("rectangle", "ellipse", "diamond")
            and e["backgroundColor"] != "transparent"
        ]
        assert 3 <= len(shapes) <= 7, (name, len(shapes))
        assert not {e["backgroundColor"] for e in elements} & loop_fills, name
        text = " ".join(_texts(folder / f"{name}.excalidraw")).lower()
        for word in ("datapilot", "analyst", "schema scout", "harbor"):
            assert word not in text, (name, word)
