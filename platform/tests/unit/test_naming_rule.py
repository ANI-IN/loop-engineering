"""The naming rule: short forms are found in prose and ignored in code."""

from __future__ import annotations

import importlib.util
import sys

import pytest

from datapilot.settings import PLATFORM


@pytest.fixture(scope="module")
def short_forms():
    spec = importlib.util.spec_from_file_location(
        "short_forms", PLATFORM / "scripts" / "short_forms.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["short_forms"] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "text",
    [
        "Revenue in FY2025 was up.",
        "Revenue in FY 25 was up.",
        "The run posts at L2.",
        "Run D1.3 next.",
        "Hand in A2 by Thursday.",
        "We covered S1 today.",
        "Orders after 8 pm ET count tomorrow.",
        "Exports with PII need approval.",
        "Track MRR weekly.",
        "This is a HITL step.",
    ],
)
def test_short_forms_in_prose_are_found(short_forms, text: str) -> None:
    assert short_forms.find(text)


@pytest.mark.parametrize(
    "text",
    [
        "Run `make demo NAME=agent-confident-wrong-answer` now.",
        "The flag `BUG_NAIVE_GUARD=1` turns it on.",
        "Use `L2` only in code.",
        "GET /runs returns the run list.",
        "SELECT the rows, then GET the page.",
        "Revenue in fiscal year 2025, Eastern time, with human approval for personal data.",
        "Print the guide on `A4` paper.",
    ],
)
def test_code_and_ordinary_words_are_not_short_forms(short_forms, text: str) -> None:
    assert short_forms.find(text) == []


def test_commit_message_comments_and_fences_are_skipped(short_forms) -> None:
    text = "feat: add the reviewer\n# L2 in a comment line\n```\nFY2025\n```\n"
    assert short_forms.check_text(text) == []


def test_no_file_uses_an_old_short_evidence_name(repo_scan) -> None:
    """Evidence pages are named section-N-<slug>.md; the old s1.md to s4.md names never come back,
    even inside code spans or paths (the prose check skips those)."""
    hits = repo_scan(r"(^|[^-\w])s[1-4]\.md\b", flags=0)
    assert [line for line in hits if "test_naming_rule.py" not in line] == []
