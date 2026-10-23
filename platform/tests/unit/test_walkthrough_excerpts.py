"""Walkthrough excerpts match the code: each "<path>, lines a-b" excerpt is exactly those lines.

The check lives in platform/tools/generators/render.py and runs with `make docs` and
`make docs-check`, so an excerpt can never drift from the file it quotes.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from datapilot.settings import PLATFORM, REPO

CODE = "\n".join(f"value_{n} = {n}" for n in range(1, 21)) + "\n"
FENCE = "```"


def _render():
    path = PLATFORM / "tools" / "generators" / "render.py"
    spec = importlib.util.spec_from_file_location("render_for_excerpts", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["render_for_excerpts"] = module
    spec.loader.exec_module(module)
    return module


def _page(*excerpts: str, explained: str = "") -> str:
    return (
        "# Demo walkthrough\n\n## What this code does\n\nText.\n\n"
        "## The code, explained\n\n" + "\n".join(excerpts) + explained + "\n"
        "## If you copy this into your repository\n\nText.\n"
    )


def _excerpt(heading: str, comment: str, body: list[str], lang: str = "python") -> str:
    lines = [heading, "", f"{FENCE}{lang}", comment, *body, FENCE, "", "Why it matters.", ""]
    return "\n".join(lines) + "\n"


def _lines(a: int, b: int) -> list[str]:
    return CODE.splitlines()[a - 1 : b]


def _problems(tmp_path: Path, page: str) -> list[str]:
    (tmp_path / "pkg").mkdir(exist_ok=True)
    (tmp_path / "pkg" / "code.py").write_text(CODE, encoding="utf-8")
    return _render().excerpt_problems_in("walkthrough.md", page, tmp_path)


def test_an_exact_excerpt_passes(tmp_path: Path) -> None:
    page = _page(_excerpt("### pkg/code.py, lines 3-7", "# pkg/code.py (lines 3-7)", _lines(3, 7)))
    assert _problems(tmp_path, page) == []


def test_a_heading_in_a_code_span_passes(tmp_path: Path) -> None:
    excerpt = _excerpt("### `pkg/code.py`, lines 1-2", "# pkg/code.py (lines 1-2)", _lines(1, 2))
    assert _problems(tmp_path, _page(excerpt)) == []


def test_an_sql_comment_line_passes(tmp_path: Path) -> None:
    excerpt = _excerpt("### pkg/code.py, lines 1-2", "-- pkg/code.py (lines 1-2)", _lines(1, 2))
    assert _problems(tmp_path, _page(excerpt)) == []


def test_lines_that_moved_fail(tmp_path: Path) -> None:
    page = _page(_excerpt("### pkg/code.py, lines 3-7", "# pkg/code.py (lines 3-7)", _lines(4, 8)))
    problems = _problems(tmp_path, page)
    assert len(problems) == 1
    assert "differs from pkg/code.py at line 3" in problems[0]


def test_an_excerpt_with_a_line_too_few_fails(tmp_path: Path) -> None:
    page = _page(_excerpt("### pkg/code.py, lines 3-7", "# pkg/code.py (lines 3-7)", _lines(3, 6)))
    problems = _problems(tmp_path, page)
    assert len(problems) == 1
    assert "4 lines, the range has 5" in problems[0]


def test_a_comment_line_that_disagrees_with_the_heading_fails(tmp_path: Path) -> None:
    page = _page(_excerpt("### pkg/code.py, lines 3-7", "# pkg/code.py (lines 3-8)", _lines(3, 7)))
    problems = _problems(tmp_path, page)
    assert len(problems) == 1
    assert "first line must be the comment" in problems[0]


def test_a_missing_comment_line_fails(tmp_path: Path) -> None:
    page = _page(_excerpt("### pkg/code.py, lines 3-7", _lines(3, 3)[0], _lines(4, 7)))
    assert any("first line must be the comment" in p for p in _problems(tmp_path, page))


def test_a_missing_file_fails(tmp_path: Path) -> None:
    page = _page(_excerpt("### pkg/gone.py, lines 1-2", "# pkg/gone.py (lines 1-2)", _lines(1, 2)))
    problems = _problems(tmp_path, page)
    assert len(problems) == 1
    assert "no file pkg/gone.py" in problems[0]


def test_a_range_past_the_end_of_the_file_fails(tmp_path: Path) -> None:
    excerpt = _excerpt(
        "### pkg/code.py, lines 19-22", "# pkg/code.py (lines 19-22)", _lines(19, 20)
    )
    problems = _problems(tmp_path, _page(excerpt))
    assert len(problems) == 1
    assert "has 20 lines" in problems[0]


def test_a_backwards_range_fails(tmp_path: Path) -> None:
    page = _page(_excerpt("### pkg/code.py, lines 7-3", "# pkg/code.py (lines 7-3)", _lines(3, 7)))
    assert any("range 7-3 is backwards" in p for p in _problems(tmp_path, page))


def test_a_path_outside_the_repository_fails(tmp_path: Path) -> None:
    page = _page(_excerpt("### ../code.py, lines 1-2", "# ../code.py (lines 1-2)", _lines(1, 2)))
    assert any("relative to the repository root" in p for p in _problems(tmp_path, page))


def test_a_heading_with_no_code_block_fails(tmp_path: Path) -> None:
    page = _page("### pkg/code.py, lines 1-2\n\nOnly words here.\n\n")
    problems = _problems(tmp_path, page)
    assert len(problems) == 1
    assert "no code block" in problems[0]


def test_a_code_block_with_no_excerpt_heading_fails(tmp_path: Path) -> None:
    stray = f"### What the guard does\n\n{FENCE}python\nvalue_1 = 1\n{FENCE}\n\n"
    problems = _problems(tmp_path, _page(explained=stray))
    assert len(problems) == 1
    assert "has no '<path>, lines a-b' heading" in problems[0]


def test_a_diagram_outside_the_code_section_is_not_an_excerpt(tmp_path: Path) -> None:
    page = _page(
        _excerpt("### pkg/code.py, lines 1-2", "# pkg/code.py (lines 1-2)", _lines(1, 2))
    ).replace("Text.\n\n## The code", f"{FENCE}mermaid\nsequenceDiagram\n{FENCE}\n\n## The code", 1)
    assert _problems(tmp_path, page) == []


def test_two_excerpts_are_each_checked(tmp_path: Path) -> None:
    page = _page(
        _excerpt("### pkg/code.py, lines 1-2", "# pkg/code.py (lines 1-2)", _lines(1, 2)),
        _excerpt("### pkg/code.py, lines 10-12", "# pkg/code.py (lines 10-12)", _lines(11, 13)),
    )
    problems = _problems(tmp_path, page)
    assert len(problems) == 1
    assert "lines 10-12" in problems[0]


def test_every_walkthrough_in_the_repository_matches_its_code() -> None:
    assert _render().excerpt_problems(REPO) == []


def test_the_repository_walkthroughs_hold_excerpts() -> None:
    render = _render()
    pages = render.excerpt_pages(REPO)
    sections = [p for p in pages if p.parts[-3].startswith("section-")]
    assert len(sections) == 4
    for page in sections:
        text = page.read_text(encoding="utf-8")
        assert render.excerpts_in(text), f"{page} has no excerpts"


def test_docs_check_fails_when_an_excerpt_drifts(tmp_path: Path, monkeypatch) -> None:
    render = _render()
    monkeypatch.setattr(render, "excerpt_problems", lambda _root: ["x a drifted excerpt"])
    assert render.main(["--check"]) == 1


def test_the_registry_code_ranges_are_the_walkthrough_excerpts() -> None:
    """make open-code opens what the walkthrough explains: the same ranges, section by section."""
    from datapilot.contracts import registries
    from datapilot.names import SECTIONS

    render = _render()
    for section in SECTIONS:
        page = REPO / section.folder / "demo" / "walkthrough.md"
        excerpts = render.excerpts_in(page.read_text(encoding="utf-8"))
        shown = {(e.path, f"{e.first}-{e.last}") for e in excerpts}
        named = {
            (ref.path, ref.lines)
            for demo in registries.demos().for_section(section.slug)
            for ref in demo.code
        }
        assert named == shown, section.slug
