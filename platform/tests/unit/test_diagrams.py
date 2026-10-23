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


def test_the_export_page_pins_one_exact_excalidraw_version(exporter: ModuleType) -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", exporter.EXCALIDRAW_VERSION)
    assert exporter.page_version() == exporter.EXCALIDRAW_VERSION
    for folder in exporter.diagram_folders():
        assert exporter.read_manifest(folder)["excalidraw"] == exporter.EXCALIDRAW_VERSION


def test_every_svg_embeds_its_font(sources: list[Path]) -> None:
    for source in sources:
        svg = source.with_suffix(".svg").read_text(encoding="utf-8")
        assert "@font-face" in svg and "data:font/woff2;base64," in svg, source.name


def test_every_diagram_is_a_1920_by_1080_panel_with_labels_of_20_pixels_or_more(
    sources: list[Path],
) -> None:
    for source in sources:
        elements = _scene(source)["elements"]
        panel = elements[0]
        assert (panel["x"], panel["y"], panel["width"], panel["height"]) == (0, 0, 1920, 1080)
        assert panel["backgroundColor"] == "#F0F3F6", source.name
        for element in elements:
            if element["type"] == "text":
                assert element["fontSize"] >= 20, (source.name, element["text"])
            points = element.get("points") or [[0, 0], [element["width"], element["height"]]]
            xs = [element["x"] + p[0] for p in points]
            ys = [element["y"] + p[1] for p in points]
            assert min(xs) >= 0 and max(xs) <= 1920, element["id"]
            assert min(ys) >= 0 and max(ys) <= 1080, element["id"]


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
