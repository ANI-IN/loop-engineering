"""The image check: size, blank areas, clipped edges, and alt text, on images drawn in the test."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_images.py"
BACKGROUND = (236, 240, 243)


def _load():
    spec = importlib.util.spec_from_file_location("check_images", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["check_images"] = module  # dataclasses look their module up by name
    spec.loader.exec_module(module)
    return module


check_images = _load()


def _page(width: int, height: int, *, content: tuple[float, float] = (0.1, 0.9)) -> Image.Image:
    """A page background with lines of 'text' (short dark strokes) between two height fractions."""
    image = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(image)
    top, bottom = int(content[0] * height), int(content[1] * height)
    for y in range(top, bottom, 12):
        for x in range(width // 20, width - width // 20, 9):
            draw.rectangle((x, y, x + 4, min(y + 7, bottom - 1)), fill=(20, 30, 40))
    return image


def _cut_line(image: Image.Image, at_top: bool) -> Image.Image:
    """A line of 'text' whose strokes run off the top or the bottom edge."""
    width, height = image.size
    draw = ImageDraw.Draw(image)
    rows = (0, 5) if at_top else (height - 6, height - 1)
    for x in range(width // 20, width - width // 20, 9):
        draw.rectangle((x, rows[0], x + 4, rows[1]), fill=(20, 30, 40))
    return image


def _save(root: Path, relative: str, image: Image.Image) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return path


def _kinds(root: Path) -> list[str]:
    return sorted(problem.kind for problem in check_images.check(root)[1])


def test_a_full_size_screenshot_with_margins_passes(tmp_path: Path) -> None:
    _save(tmp_path, "docs/images/board.png", _page(2560, 1440))
    assert check_images.check(tmp_path) == (1, [])


def test_a_screenshot_at_device_scale_factor_one_is_too_small(tmp_path: Path) -> None:
    _save(tmp_path, "section-1-agent-loop/demo/expected/board.png", _page(1280, 720))
    assert _kinds(tmp_path) == ["size"]


def test_terminal_renders_and_diagrams_have_their_own_minimum(tmp_path: Path) -> None:
    _save(tmp_path, "docs/images/run-1-terminal.png", _page(1878, 400))
    _save(tmp_path, "section-1-agent-loop/diagrams/agent-loop.png", _page(1920, 1080))
    assert check_images.check(tmp_path) == (2, [])
    assert check_images.image_kind("a/run-1-terminal.png") == "terminal"
    assert check_images.image_kind("section-1-agent-loop/diagrams/agent-loop.png") == "diagram"


def test_an_oversized_image_is_reported_without_decoding_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(check_images, "MAXIMUM_PIXELS", 1000)
    _save(tmp_path, "docs/images/long-terminal.png", _page(100, 100))
    problems = check_images.check(tmp_path)[1]
    assert [p.kind for p in problems] == ["size"]
    assert "split or crop it" in problems[0].detail


def test_a_large_blank_band_fails(tmp_path: Path) -> None:
    _save(tmp_path, "docs/images/half-empty.png", _page(2560, 1440, content=(0.1, 0.5)))
    problems = check_images.check(tmp_path)[1]
    assert [p.kind for p in problems] == ["blank area"]
    assert "rows are one colour" in problems[0].detail


def test_a_diagram_step_may_leave_room_for_the_next_step(tmp_path: Path) -> None:
    half = _page(1920, 1080, content=(0.1, 0.5))
    _save(tmp_path, "docs/diagrams/four-loops-step-1.png", half)
    _save(tmp_path, "docs/diagrams/four-loops.png", half)
    problems = check_images.check(tmp_path)[1]
    assert [(p.path, p.kind) for p in problems] == [("docs/diagrams/four-loops.png", "blank area")]


def test_text_cut_by_the_bottom_edge_fails(tmp_path: Path) -> None:
    _save(tmp_path, "docs/images/cut.png", _cut_line(_page(2560, 1440), at_top=False))
    problems = check_images.check(tmp_path)[1]
    assert [p.kind for p in problems] == ["clipped edge"]
    assert problems[0].detail.startswith("bottom edge")


def test_text_cut_by_the_top_edge_fails(tmp_path: Path) -> None:
    _save(tmp_path, "docs/images/cut.png", _cut_line(_page(2560, 1440), at_top=True))
    problems = check_images.check(tmp_path)[1]
    assert [p.detail.split(":")[0] for p in problems] == ["top edge"]


def test_panels_and_borders_touching_an_edge_pass(tmp_path: Path) -> None:
    image = _page(2560, 1440)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 300, 1439), fill=(40, 50, 60))  # a full-height sidebar
    # A panel whose border runs along the bottom edge.
    draw.rectangle((900, 1200, 1700, 1439), outline=(20, 30, 40), width=3)
    draw.rectangle((2540, 0, 2559, 1439), fill=(200, 200, 200))  # a scroll bar
    _save(tmp_path, "docs/images/panels.png", image)
    assert check_images.check(tmp_path) == (1, [])


def test_an_image_reference_without_alt_text_fails(tmp_path: Path) -> None:
    _save(tmp_path, "docs/images/board.png", _page(2560, 1440))
    (tmp_path / "docs" / "page.md").write_text(
        "# Page\n\n![](images/board.png)\n\n![The board](images/board.png)\n", encoding="utf-8"
    )
    problems = check_images.check(tmp_path)[1]
    assert [(p.kind, p.detail) for p in problems] == [("alt text", "no alt text at docs/page.md:3")]


def test_an_html_image_without_alt_text_fails(tmp_path: Path) -> None:
    _save(tmp_path, "docs/images/board.png", _page(2560, 1440))
    (tmp_path / "README.md").write_text(
        '# Page\n\n<img src="docs/images/board.png" alt=" ">\n', encoding="utf-8"
    )
    assert _kinds(tmp_path) == ["alt text"]


def test_image_references_in_fenced_code_are_not_read(tmp_path: Path) -> None:
    _save(tmp_path, "docs/images/board.png", _page(2560, 1440))
    (tmp_path / "docs" / "page.md").write_text(
        "# Page\n\n```markdown\n![](images/board.png)\n```\n", encoding="utf-8"
    )
    assert check_images.check(tmp_path) == (1, [])


def test_the_report_counts_each_kind_and_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _save(tmp_path, "docs/images/small.png", _page(1280, 720))
    assert check_images.main(["--root", str(tmp_path)]) == 1
    output = capsys.readouterr().out
    assert "x docs/images/small.png: size: 1280x720, below 2560x1440" in output
    assert output.strip().endswith("1 images checked, 1 with problems; problems by kind: size 1")


def test_a_clean_folder_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _save(tmp_path, "docs/images/board.png", _page(2560, 1440))
    assert check_images.main(["--root", str(tmp_path)]) == 0
    assert "problems by kind: none" in capsys.readouterr().out
