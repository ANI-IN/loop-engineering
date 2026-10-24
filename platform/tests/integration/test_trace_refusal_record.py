"""A trace LangSmith refused for its monthly limit lands on the run's row, and the api's run record
carries it (tests' Postgres, no tokens). The worker runs a question with a scripted model; the
SDK's refusal line for that run then reaches the process's refusal log, as it does on the SDK's
background thread after a run posted."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Iterator

import loops_paths  # noqa: F401  (before loops_support)
import pytest
from fastapi.testclient import TestClient
from loops_support import query_then_answer

from datapilot.loop3_events import trace_refusals
from datapilot.loop3_events.api.app import app
from datapilot.loop3_events.worker import Worker, WorkerSettings
from datapilot.observability import background

pytest_plugins = ["loops_fixtures"]
pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("clean_ops")]

LIMIT = 'HTTPError(429, \'{"detail":"Monthly unique traces usage limit exceeded"}\')'


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def refusals(monkeypatch: pytest.MonkeyPatch) -> background.RefusalLog:
    log = background.RefusalLog()
    monkeypatch.setattr(background, "_refusals", log)
    return log


def _posted_run(client: TestClient, services_for) -> str:
    sent = client.post(
        "/events",
        json={
            "event_id": f"test:{uuid.uuid4().hex}",
            "type": "question.asked",
            "payload": {"question": "How many orders are there?"},
        },
    )
    assert sent.status_code == 200, sent.text
    services = services_for(
        {"analyst": query_then_answer("SELECT count(*) AS orders FROM orders", "2000 orders.")}
    )
    worker = Worker(
        services,
        models_for=lambda _run_id, _activity: services.models,
        settings=WorkerSettings(poll_seconds=0.05),
    )
    assert asyncio.run(worker.run_once())
    return str(sent.json()["run_id"])


def _sdk_refusal(run_id: str) -> logging.LogRecord:
    child = uuid.uuid4()
    text = f"Failed to multipart ingest runs: {LIMIT}trace={run_id},id={run_id}; "
    text += f"trace={run_id},id={child}"
    return logging.LogRecord(background.SDK_LOGGER, logging.WARNING, "", 0, text, None, None)


def test_a_refused_trace_lands_on_the_runs_row(client, services_for, refusals) -> None:
    refused, kept = _posted_run(client, services_for), _posted_run(client, services_for)
    record = client.get(f"/runs/{refused}").json()
    assert record["status"] == "posted" and record["trace_refused_at"] is None

    recorder = trace_refusals.record_refusals()
    refusals.filter(_sdk_refusal(refused))
    assert recorder.flush(timeout=10) and recorder.failed == 0
    first = client.get(f"/runs/{refused}").json()["trace_refused_at"]
    assert first is not None
    assert client.get(f"/runs/{kept}").json()["trace_refused_at"] is None

    refusals.filter(_sdk_refusal(refused))  # a later refusal keeps the first one's time
    assert recorder.flush(timeout=10)
    assert client.get(f"/runs/{refused}").json()["trace_refused_at"] == first
    listed = {r["run_id"]: r for r in client.get("/runs?all_sessions=true").json()["runs"]}
    assert listed[refused]["trace_refused_at"] == first
