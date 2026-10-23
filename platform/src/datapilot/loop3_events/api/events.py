"""POST /events: one event in, at most once.

The insert is idempotent (ON CONFLICT (event_id) DO NOTHING); a repeated event is recorded in
ops.event_duplicates and returns the original run. A new event gets its job row and its run in the
same transaction, so a crash can never leave an event without a job.
"""

from __future__ import annotations

import uuid
from typing import Any

import psycopg
from fastapi import APIRouter, Header
from psycopg.types.json import Jsonb

from datapilot import db, planted
from datapilot.config import pack_config
from datapilot.contracts import RunEventKind, RunStatus
from datapilot.contracts.api import EventIn, EventSubmitted
from datapilot.loop3_events import lifecycle, router, sessions
from datapilot.observability.spend import ACTIVITY_HEADER

api = APIRouter()


def submit_event(
    conn: psycopg.Connection[Any],
    *,
    event_id: str,
    type: str,
    source: str,
    payload: dict[str, Any],
) -> EventSubmitted:
    if planted.planted("BUG_NO_IDEMPOTENCY"):
        event_id = f"{event_id}#{uuid.uuid4().hex[:8]}"  # planted: every delivery looks new
    route = router.route(type, payload)
    inserted = conn.execute(
        "INSERT INTO ops.events (event_id, source, type, payload) VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (event_id) DO NOTHING RETURNING event_id",
        (event_id, source, type, Jsonb(payload)),
    ).fetchone()
    if inserted is None:
        conn.execute("INSERT INTO ops.event_duplicates (event_id) VALUES (%s)", (event_id,))
        run = conn.execute(
            "SELECT r.run_id, r.job_id, r.created_at, "
            "(SELECT count(*) FROM ops.event_duplicates d WHERE d.event_id = r.event_id) AS dups "
            "FROM ops.runs r WHERE r.event_id = %s",
            (event_id,),
        ).fetchone()
        return EventSubmitted(
            event_id=event_id,
            run_id=run["run_id"],
            job_id=run["job_id"],
            duplicate=True,
            duplicates_ignored=int(run["dups"]),
            created_at=run["created_at"],
        )
    job = conn.execute(
        "INSERT INTO ops.jobs (event_id, queue) VALUES (%s, %s) RETURNING job_id",
        (event_id, route.queue),
    ).fetchone()
    session = sessions.open_session(conn)
    question = router.question_for(type, payload)
    families = list(pack_config()["autonomy"]["metric_families"])
    run = conn.execute(
        "INSERT INTO ops.runs (run_id, job_id, event_id, demo_name, question, metric_family, "
        "status, planted_active, session_id) VALUES (%s, %s, %s, %s, %s, %s, 'received', %s, %s) "
        "RETURNING run_id, created_at",
        (
            uuid.uuid4(),
            job["job_id"],
            event_id,
            payload.get("demo_name"),
            question,
            router.metric_family(question, payload, families),
            planted.active(),
            session.session_id if session else None,
        ),
    ).fetchone()
    run_id = str(run["run_id"])
    lifecycle.record(
        conn, run_id, RunEventKind.STATUS_CHANGED, {"from": None, "to": "received", "by": "api"}
    )
    lifecycle.transition(conn, run_id, RunStatus.QUEUED, by="api: POST /events")
    return EventSubmitted(
        event_id=event_id,
        run_id=run_id,
        job_id=job["job_id"],
        duplicate=False,
        duplicates_ignored=0,
        created_at=run["created_at"],
    )


@api.post("/events", response_model=EventSubmitted)
def post_event(
    event: EventIn,
    spend_activity: str | None = Header(None, alias=ACTIVITY_HEADER, max_length=100),
) -> EventSubmitted:
    """The caller may name the ledger activity of the work in a header; it is kept on the job, so
    the worker records the run's model calls under it."""
    with db.connect(db.Role.APP) as conn:
        submitted = submit_event(
            conn,
            event_id=event.event_id,
            type=event.type.value,
            source=event.source,
            payload=event.payload,
        )
        if spend_activity and spend_activity.strip() and not submitted.duplicate:
            conn.execute(
                "UPDATE ops.jobs SET spend_activity = %s WHERE job_id = %s",
                (spend_activity.strip(), submitted.job_id),
            )
        conn.commit()
    return submitted
