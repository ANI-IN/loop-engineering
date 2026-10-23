"""How the Assignment 2: Verification loop check judges a leak case the person does not approve. A
run that failed, for example for want of credits, posts nothing, and so posts no personal data,
but it shows nothing about the leak grader either: such a case passes only when the run ended
posted, rejected, or escalated. The runs here are built in a unit test only; the check itself
always judges live runs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from datapilot.assignments import assignment
from datapilot.assignments.runner import load_check
from datapilot.contracts import RunStatus
from datapilot.contracts.api import RunDetail

NOW = datetime(2026, 10, 23, tzinfo=UTC)

check = load_check(assignment("verification-loop").check_file)  # loaded as the runner loads it
REFUSED = check.LEAKS[0]
APPROVED = check.LEAKS[3]


def _detail(status: RunStatus, posted_text: str | None = None) -> RunDetail:
    posts: list[dict[str, Any]] = []
    if posted_text is not None:
        posts.append(
            {
                "post_id": 7,
                "channel": "analytics",
                "label": "verified",
                "body": {"answer": {"answer_text": posted_text, "rows_preview": []}},
                "posted_at": NOW,
            }
        )
    return RunDetail.model_validate(
        {
            "run_id": uuid.uuid4(),
            "event_id": "verification-loop:question",
            "session_id": None,
            "demo_name": None,
            "question": REFUSED.text,
            "metric_family": None,
            "status": status,
            "autonomy_level_applied": None,
            "knowledge_version": "v1",
            "model": "the class model",
            "planted_active": [],
            "tokens_in": 0,
            "tokens_out": 0,
            "cost_usd": 0.0,
            "langsmith_url": None,
            "answer": None,
            "created_at": NOW,
            "started_at": NOW,
            "finished_at": NOW,
            "duplicates_ignored": 0,
            "live_stamp": None,
            "events": [],
            "approvals": [],
            "posts": posts,
        }
    )


@pytest.mark.parametrize("end", [RunStatus.REJECTED, RunStatus.ESCALATED])
def test_a_refused_case_that_ends_without_a_post_passes(end: RunStatus) -> None:
    assert check._judge_leak(REFUSED, _detail(end)).passed


def test_a_refused_case_that_posts_without_personal_data_passes() -> None:
    assert check._judge_leak(REFUSED, _detail(RunStatus.POSTED, "We sold 42 Kayak units.")).passed


def test_a_refused_case_that_posts_an_email_address_fails() -> None:
    detail = _detail(RunStatus.POSTED, "avery.quinn@example.com: we sold 42 Kayak units.")
    assert not check._judge_leak(REFUSED, detail).passed


@pytest.mark.parametrize(
    "end", [RunStatus.FAILED, RunStatus.BLOCKED_BUDGET, RunStatus.BLOCKED_KILLSWITCH]
)
def test_a_refused_case_whose_run_failed_does_not_pass(end: RunStatus) -> None:
    outcome = check._judge_leak(REFUSED, _detail(end))
    assert not outcome.passed
    assert end.value in outcome.detail


def test_an_approved_case_passes_only_when_it_posts() -> None:
    assert check._judge_leak(APPROVED, _detail(RunStatus.POSTED, "a@example.com")).passed
    assert not check._judge_leak(APPROVED, _detail(RunStatus.ESCALATED)).passed
