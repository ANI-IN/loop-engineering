"""Assignment 3: Event loop's drill-down step on the real Postgres, the real api, and the real
worker, with a scripted stub model (zero tokens): an answer that posts without a hold, followed by
the same drill-down ask.

On 25 October 2026 alternative one failed requirement 10 twice with "no approval was needed; the
posted answer named it; the second ask started another run". The class event loop absorbs that
second ask, after the answer posted as well as before. The second run came from the stack: the
check's copy links the checkout's .env, a class demonstration had switched the missing
idempotency (BUG_NO_IDEMPOTENCY) on in it, and the check's stack started while it was on. With it
on, the second ask starts another run and the check failed the solution; it now stops instead,
before the second ask, and its own Compose project switches every planted bug off
(test_assignment_check_stack.py)."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterator
from typing import Any

import loops_paths  # noqa: F401  (before loops_support)
import pytest
from fastapi.testclient import TestClient
from loops_support import query_then_answer

from datapilot import db
from datapilot.assignments import assignment
from datapilot.assignments.report import Stop
from datapilot.assignments.runner import load_check
from datapilot.contracts.api import ApprovalIn, EventIn, EventSubmitted, RunDetail
from datapilot.loop3_events.api.app import app
from datapilot.loop3_events.worker import Worker, WorkerSettings

pytest_plugins = ["loops_fixtures"]
pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("clean_ops")]

check = load_check(assignment("event-loop").check_file)  # loaded as the runner loads it
GOLD = "Water Sports"
DRILL = {
    "event_id": "revenue-anomaly:2026-01-30:drill-down",  # every solution's drill-down id
    # a placeholder: the stub model answers whatever is asked (the solutions' own wording is
    # pinned with the real grader in test_event_loop_drill_down_question.py)
    "question": "Which category?",
}
ANSWER = query_then_answer("SELECT count(*) AS orders FROM orders", "Water Sports changed most.")


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def worker(services_for) -> Worker:
    services = services_for({"analyst": ANSWER})  # no reviewer: the answer posts without a hold
    return Worker(
        services,
        models_for=lambda _run_id, _activity: services.models,
        settings=WorkerSettings(lease_seconds=5.0, poll_seconds=0.05),
    )


def drain(worker: Worker) -> None:
    async def go() -> None:
        for _ in range(10):
            if not await worker.run_once():
                return

    asyncio.run(go())


class StackApi:
    """The check's api over the real api in this process; waiting drains the real worker."""

    engaged_by_check = False
    engaged_at_cap = False
    slug = "event-loop"

    def __init__(self, client: TestClient, worker: Worker) -> None:
        self.client, self.worker = client, worker

    def submit(self, type: str, payload: dict[str, Any], event: str) -> EventSubmitted:
        body = EventIn(event_id=event, type=type, source="assignment-check", payload=payload)  # type: ignore[arg-type]
        response = self.client.post("/events", json=body.model_dump(mode="json"))
        assert response.is_success, response.text
        return EventSubmitted.model_validate(response.json())

    def run(self, run_id: str) -> RunDetail:
        return RunDetail.model_validate(self.client.get(f"/runs/{run_id}").json())

    def wait(self, run_id: str, *, seconds: float = 600, until: Any = None) -> RunDetail:
        drain(self.worker)
        return self.run(run_id)

    def decide(self, run_id: str, decision: str, comment: str = "") -> None:
        body = ApprovalIn(decision=decision, decided_by="test", comment=comment)  # type: ignore[arg-type]
        self.client.post(f"/approvals/{run_id}", json=body.model_dump())


Ask = Callable[[], EventSubmitted]


def _runs() -> int:
    with db.connect(db.Role.APP) as conn:
        return int(conn.execute("SELECT count(*) AS n FROM ops.runs").fetchone()["n"])


def _asker(api: StackApi) -> Ask:
    payload = {"question": DRILL["question"], "metric_family": "revenue"}
    return lambda: api.submit("question.asked", payload, DRILL["event_id"])


def test_an_answer_posted_without_a_hold_absorbs_the_same_ask_after_it(
    client: TestClient, worker: Worker, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("BUG_NO_IDEMPOTENCY", raising=False)
    api = StackApi(client, worker)
    ask = _asker(api)
    first = ask()
    detail = api.wait(str(first.run_id))
    assert detail.status.value == "posted" and not detail.approvals  # posted, never held
    again = ask()  # the same drill-down, asked once the answer has posted
    assert again.duplicate and again.run_id == first.run_id
    assert _runs() == 1


def test_the_check_passes_an_answer_posted_without_a_hold(
    client: TestClient, worker: Worker, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("BUG_NO_IDEMPOTENCY", raising=False)
    outcome = check.drill_down(StackApi(client, worker), DRILL, GOLD)
    assert outcome.passed, outcome.what()
    assert "no approval was needed" in outcome.what()
    assert "the second ask was absorbed" in outcome.what()


def test_the_missing_idempotency_on_the_stack_starts_a_second_run(
    client: TestClient, worker: Worker, monkeypatch: pytest.MonkeyPatch
) -> None:
    """What the failing checks of 25 October 2026 saw, reproduced: the stack, not the solution."""
    monkeypatch.setenv("BUG_NO_IDEMPOTENCY", "1")
    api = StackApi(client, worker)
    ask = _asker(api)
    first = ask()
    api.wait(str(first.run_id))
    again = ask()
    assert not again.duplicate and again.run_id != first.run_id
    assert api.run(str(first.run_id)).planted_active == ["BUG_NO_IDEMPOTENCY"]


def test_the_check_stops_on_a_planted_bug_before_the_second_ask(
    client: TestClient, worker: Worker, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BUG_NO_IDEMPOTENCY", "1")
    with pytest.raises(Stop) as stopped:
        check.drill_down(StackApi(client, worker), DRILL, GOLD)
    message = str(stopped.value)
    assert "BUG_NO_IDEMPOTENCY" in message and "not judged" in message
    assert _runs() == 1  # the second ask was never sent
