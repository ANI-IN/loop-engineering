"""The Assignment 3: Event loop check's live step, zero tokens and no database: when the drill-down
run holds for approval, the check approves it, as an instructor would, waits for the posted answer,
and judges that posted answer against gold. A held answer is never judged, and a run that never
posts fails. The api here is a test double, in a unit test only; the check itself always runs
live against the real api."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from datapilot.assignments import assignment
from datapilot.assignments.runner import load_check
from datapilot.contracts import RunStatus
from datapilot.contracts.api import EventSubmitted, RunDetail

GOLD = "Water Sports"
DRILL = {"event_id": "revenue-anomaly:2026-01-30:drill-down", "question": "Which category?"}
NOW = datetime(2026, 10, 23, tzinfo=UTC)


check = load_check(assignment("event-loop").check_file)  # loaded as the runner loads it


def _envelope(text: str) -> dict[str, Any]:
    return {"answer_text": text, "rows_preview": []}


class Api:
    """The api as the check sees it: submit, wait, run, and decide."""

    def __init__(
        self,
        *,
        hold: bool,
        held_text: str = "",
        posted_text: str | None = None,
        end: RunStatus = RunStatus.POSTED,
        absorbed: bool = True,
    ) -> None:
        self.run_id = uuid.uuid4()
        self.hold, self.held_text, self.posted_text = hold, held_text, posted_text
        self.end, self.absorbed = end, absorbed
        self.asks = 0
        self.decisions: list[str] = []

    def submit(self, type: str, payload: dict[str, Any], event: str) -> EventSubmitted:
        self.asks += 1
        again = self.asks > 1
        return EventSubmitted(
            event_id=event,
            run_id=self.run_id if self.absorbed or not again else uuid.uuid4(),
            job_id=None,
            duplicate=again and self.absorbed,
            duplicates_ignored=0,
            created_at=NOW,
        )

    def _detail(self, status: RunStatus, *, open_approval: bool) -> dict[str, Any]:
        approvals = []
        if self.hold:
            decided = None if open_approval else (self.decisions or [None])[-1]
            approvals.append(
                {
                    "approval_id": 1,
                    "kind": "held_answer",
                    "requested_at": NOW,
                    "action": f"post the answer: {self.held_text}",
                    "sql": None,
                    "row_estimate": None,
                    "reason": "the reviewer held the answer",
                    "decision": decided,
                    "decided_by": None if decided is None else "make check-assignment",
                    "decided_at": None if decided is None else NOW,
                    "comment": None,
                }
            )
        posts = []
        if status is RunStatus.POSTED and self.posted_text is not None:
            posts.append(
                {
                    "post_id": 7,
                    "channel": "analytics",
                    "label": "unverified",
                    "body": {"answer": _envelope(self.posted_text), "level": "report_only"},
                    "posted_at": NOW,
                }
            )
        answer_text = self.posted_text if status is RunStatus.POSTED else self.held_text
        return {
            "run_id": self.run_id,
            "event_id": DRILL["event_id"],
            "session_id": None,
            "demo_name": None,
            "question": DRILL["question"],
            "metric_family": "revenue",
            "status": status,
            "autonomy_level_applied": None,
            "knowledge_version": "v1",
            "model": "the class model",
            "planted_active": [],
            "tokens_in": 0,
            "tokens_out": 0,
            "cost_usd": 0.0,
            "langsmith_url": None,
            "answer": {"envelope": _envelope(answer_text or "")},
            "created_at": NOW,
            "started_at": NOW,
            "finished_at": NOW,
            "duplicates_ignored": 0,
            "live_stamp": None,
            "events": [],
            "approvals": approvals,
            "posts": posts,
        }

    def _now(self) -> RunDetail:
        if self.hold and not self.decisions:
            status, open_approval = RunStatus.AWAITING_APPROVAL, True
        else:
            status, open_approval = self.end, False
        return RunDetail.model_validate(self._detail(status, open_approval=open_approval))

    def wait(self, run_id: str, *, seconds: float = 600, until: Any = None) -> RunDetail:
        assert run_id == str(self.run_id)
        return self._now()

    def run(self, run_id: str) -> RunDetail:
        return self._now()

    def decide(self, run_id: str, decision: str, comment: str = "") -> None:
        assert run_id == str(self.run_id)
        self.decisions.append(decision)


def test_a_held_answer_is_approved_and_the_posted_answer_is_judged() -> None:
    api = Api(hold=True, held_text="Water Sports led the rise", posted_text="Water Sports led it")
    outcome = check.drill_down(api, DRILL, GOLD)
    assert api.decisions == ["approve"]
    assert outcome.passed
    assert "approved by the check" in outcome.what()
    assert outcome.fix() == ""


def test_a_held_answer_naming_gold_does_not_count_when_the_post_does_not() -> None:
    api = Api(hold=True, held_text="Water Sports led the rise", posted_text="Footwear led it")
    outcome = check.drill_down(api, DRILL, GOLD)
    assert api.decisions == ["approve"]
    assert not outcome.passed
    assert "posted answer did not name it" in outcome.what()


@pytest.mark.parametrize("end", [RunStatus.REJECTED, RunStatus.FAILED, RunStatus.ESCALATED])
def test_a_run_that_never_posts_fails(end: RunStatus) -> None:
    api = Api(hold=True, held_text="Water Sports led the rise", end=end)
    outcome = check.drill_down(api, DRILL, GOLD)
    assert api.decisions == ["approve"]
    assert not outcome.passed
    assert f"never posted (status {end.value})" in outcome.what()
    assert "post" in outcome.fix()


def test_an_answer_posted_without_a_hold_is_judged_as_posted() -> None:
    api = Api(hold=False, posted_text="Water Sports led it")
    outcome = check.drill_down(api, DRILL, GOLD)
    assert api.decisions == []
    assert outcome.passed
    assert "approved by the check" not in outcome.what()
    assert "no approval was needed" in outcome.what()


def test_a_second_ask_that_starts_another_run_fails() -> None:
    api = Api(hold=False, posted_text="Water Sports led it", absorbed=False)
    outcome = check.drill_down(api, DRILL, GOLD)
    assert not outcome.passed
    assert "deterministic event id" in outcome.fix()


def test_the_check_never_rejects() -> None:
    source = assignment("event-loop").check_file.read_text(encoding="utf-8")
    assert "reject_all" not in source
