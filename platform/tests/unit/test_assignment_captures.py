"""The page the assignment verification writes beside each capture, zero tokens and no stack: the
"your output will differ" note comes before the first image or captured block, as the style guide
asks, and appears once."""

from __future__ import annotations

from pathlib import Path

import pytest

from datapilot.assignments import solutions

TRACE = "https://smith.langchain.com/o/example/projects/p/example/r/example?poll=true"


def _page(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, images: bool) -> list[str]:
    problem = None if images else "RuntimeError: no display"
    monkeypatch.setattr(solutions, "_terminal_image", lambda *_args, **_kwargs: problem)
    monkeypatch.setattr(solutions, "_console_image", lambda *_args, **_kwargs: problem)
    capture = solutions.Capture("reference-run-1", 0, f"a run\n  trace: {TRACE}\nPASS\n")
    solutions._write_capture("agent-loop", tmp_path, capture)
    return (tmp_path / "reference-run-1.md").read_text(encoding="utf-8").splitlines()


@pytest.mark.parametrize("images", [True, False])
def test_the_note_comes_before_the_first_image_and_appears_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, images: bool
) -> None:
    lines = _page(tmp_path, monkeypatch, images=images)
    assert lines.count(solutions.NOTE) == 1
    note = lines.index(solutions.NOTE)
    later = [i for i, line in enumerate(lines) if line.startswith(("![", "```", "No ", "- <"))]
    assert later and note < min(later)
    assert lines[note - 2].startswith("A verification pass of the live check")


def test_the_page_ends_with_the_trace_links_and_one_newline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lines = _page(tmp_path, monkeypatch, images=True)
    assert lines[-1] == f"- <{TRACE}>"
    text = (tmp_path / "reference-run-1.md").read_text(encoding="utf-8")
    assert text.endswith(">\n") and not text.endswith("\n\n")
