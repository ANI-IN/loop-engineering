"""The page the assignment verification writes beside each capture, zero tokens and no stack: the
"your output will differ" note comes before the first image or captured block, as the style guide
asks, and appears once."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from datapilot.assignments import solutions

ORGANIZATION = "0a1b2c3d-1111-2222-3333-444455556666"
TRACE_ID = "9e25c630-7a2f-4371-b628-8f37d4921d5f"
TRACE = (
    f"https://smith.langchain.com/o/{ORGANIZATION}/projects/p/"
    f"7ce7a82b-8edc-4fb1-b6bc-d13fe6070f5e/r/{TRACE_ID}?poll=true"
)


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


def test_the_page_ends_with_the_trace_ids_and_one_newline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The captures ship with the solutions, so they name each trace by its id and never the
    build's LangSmith organization (this replaced the list of trace links)."""
    lines = _page(tmp_path, monkeypatch, images=True)
    assert lines[-1] == f"- {TRACE_ID}"
    text = (tmp_path / "reference-run-1.md").read_text(encoding="utf-8")
    assert text.endswith(f"{TRACE_ID}\n") and not text.endswith("\n\n")
    assert "smith.langchain.com" not in text


def test_the_captured_text_keeps_the_trace_id_and_drops_the_organization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _page(tmp_path, monkeypatch, images=True)
    text = (tmp_path / "reference-run-1.txt").read_text(encoding="utf-8")
    assert f"trace: trace id {TRACE_ID}, in the build's private LangSmith project" in text
    assert ORGANIZATION not in text and "smith.langchain.com" not in text


ORGANIZATION_LINK = re.compile(r"smith\.langchain\.com/o/[0-9a-f-]{8,}")


def test_no_captured_solution_file_names_the_builds_langsmith_organization() -> None:
    """Every text file in the solutions' captured folders, which the release publishes with the
    solutions at the Thursday review."""
    from datapilot.settings import REPO

    files = [
        p
        for p in REPO.glob("section-*/assignment/solution/**/*")
        if p.is_file() and p.suffix in {".md", ".txt", ".py", ".yaml", ".patch"}
    ]
    named = [
        str(p.relative_to(REPO)) for p in files if ORGANIZATION_LINK.search(p.read_text("utf-8"))
    ]
    assert not named, named
