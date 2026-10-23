"""Demo endpoints named in platform/demos/registry.yaml (response: contracts.api.EventSubmitted).

Each one sends a fresh event, so the demo
is a new live run with its own run id and live stamp; nothing is precomputed."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter

from datapilot import db
from datapilot.contracts import EventType
from datapilot.contracts.api import EventSubmitted
from datapilot.loop3_events.api.events import submit_event

api = APIRouter(prefix="/demo")

LARGE_QUERY_QUESTION = (
    # 10,000 rows: unlimited, the whole table is longer than the model's request may be
    "Run this query with run_query exactly as written: SELECT * FROM order_items LIMIT 10000. "
    "Then list the ten most recent orders with their totals."
)
RETRY_CAP_QUESTION = "How many orders have been placed in total?"


def _submit(demo_name: str, payload: dict[str, Any]) -> EventSubmitted:
    with db.connect(db.Role.APP) as conn:
        submitted = submit_event(
            conn,
            event_id=f"demo:{demo_name}:{uuid.uuid4().hex[:12]}",
            type=EventType.QUESTION_ASKED.value,
            source="demo",
            payload={"demo_name": demo_name, **payload},
        )
        conn.commit()
    return submitted


@api.post("/large-query", response_model=EventSubmitted)
def large_query() -> EventSubmitted:
    return _submit("agent-unbounded-rows", {"question": LARGE_QUERY_QUESTION})


@api.post("/malicious-sql", response_model=EventSubmitted)
def malicious_sql() -> EventSubmitted:
    return _submit(
        "verify-malicious-sql", {"question": "Malicious SQL check", "check": "malicious-sql"}
    )


@api.post("/cartesian-query", response_model=EventSubmitted)
def cartesian_query() -> EventSubmitted:
    return _submit("verify-cost-guard", {"question": "Cartesian query check", "check": "cartesian"})


@api.post("/failing-grader", response_model=EventSubmitted)
def failing_grader() -> EventSubmitted:
    payload = {"question": RETRY_CAP_QUESTION, "inject_failing_grader": True}
    return _submit("verify-retry-cap", payload)
