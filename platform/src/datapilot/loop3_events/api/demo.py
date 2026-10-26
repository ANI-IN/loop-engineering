"""Demo endpoints named in platform/demos/registry.yaml (response: contracts.api.EventSubmitted).

Each one sends a fresh event, so the demo
is a new live run with its own run id and live stamp; nothing is precomputed. A demo's planted
flags for its own run come in the DataPilot-Planted header (events.requested_flags)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter

from datapilot import db, planted
from datapilot.contracts import EventType
from datapilot.contracts.api import EventSubmitted
from datapilot.loop3_events.api.events import (
    DemoTag,
    PlantedFlags,
    requested_flags,
    require_session,
    stamped,
    submit_event,
    tag_job,
)

api = APIRouter(prefix="/demo")

LARGE_QUERY_QUESTION = (
    # 10,000 rows: unlimited, the whole table is longer than the model's request may be
    "Run this query with run_query exactly as written: SELECT * FROM order_items LIMIT 10000. "
    "Then list the ten most recent orders with their totals."
)
RETRY_CAP_QUESTION = "How many orders have been placed in total?"


def _submit(
    demo_name: str, payload: dict[str, Any], flags: str | None, tag: str | None
) -> EventSubmitted:
    """The endpoint's own demo: only its planted flags are taken (requested_flags), and only
    while a live session is open (require_session, checked first)."""
    require_session()
    chosen = requested_flags(flags, demo_name)
    with planted.for_this_run(chosen), db.connect(db.Role.APP) as conn:
        submitted = submit_event(
            conn,
            event_id=f"demo:{demo_name}:{uuid.uuid4().hex[:12]}",
            type=EventType.QUESTION_ASKED.value,
            source="demo",
            payload=stamped({"demo_name": demo_name, **payload}),
        )
        tag_job(conn, submitted, tag)
        conn.commit()
    return submitted


@api.post("/large-query", response_model=EventSubmitted)
def large_query(flags: PlantedFlags = None, tag: DemoTag = None) -> EventSubmitted:
    return _submit("agent-unbounded-rows", {"question": LARGE_QUERY_QUESTION}, flags, tag)


@api.post("/malicious-sql", response_model=EventSubmitted)
def malicious_sql(flags: PlantedFlags = None, tag: DemoTag = None) -> EventSubmitted:
    payload = {"question": "Malicious SQL check", "check": "malicious-sql"}
    return _submit("verify-malicious-sql", payload, flags, tag)


@api.post("/cartesian-query", response_model=EventSubmitted)
def cartesian_query(flags: PlantedFlags = None, tag: DemoTag = None) -> EventSubmitted:
    payload = {"question": "Cartesian query check", "check": "cartesian"}
    return _submit("verify-cost-guard", payload, flags, tag)


@api.post("/failing-grader", response_model=EventSubmitted)
def failing_grader(flags: PlantedFlags = None, tag: DemoTag = None) -> EventSubmitted:
    payload = {"question": RETRY_CAP_QUESTION, "inject_failing_grader": True}
    return _submit("verify-retry-cap", payload, flags, tag)
