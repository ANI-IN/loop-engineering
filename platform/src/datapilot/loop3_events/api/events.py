"""POST /events: one event in, at most once.

The insert is idempotent (ON CONFLICT (event_id) DO NOTHING); a repeated event is recorded in
ops.event_duplicates and returns the original run. A new event gets its job row and its run in the
same transaction, so a crash can never leave an event without a job.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

import psycopg
from fastapi import APIRouter, Header, HTTPException
from psycopg.types.json import Jsonb

from datapilot import db, planted
from datapilot.config import pack_config
from datapilot.contracts import RunEventKind, RunStatus, registries
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


# A demo's planted flags for its own run or request: the header requested_flags reads.
PlantedFlags = Annotated[str | None, Header(alias=planted.PLANTED_HEADER, max_length=500)]
# The tag of a demo's run that only a worker restarted for that demo claims (planted.TAG_HEADER).
DemoTag = Annotated[str | None, Header(alias=planted.TAG_HEADER, pattern=r"^[a-z0-9-]{1,80}$")]
# The demo a hill-climbing request's planted flags belong to (planted.DEMO_HEADER).
DemoName = Annotated[str | None, Header(alias=planted.DEMO_HEADER, max_length=100)]


@api.post("/events", response_model=EventSubmitted)
def post_event(
    event: EventIn,
    spend_activity: str | None = Header(None, alias=ACTIVITY_HEADER, max_length=100),
    planted_flags: PlantedFlags = None,
    demo_tag: DemoTag = None,
) -> EventSubmitted:
    """The caller may name the ledger activity of the work in a header; it is kept on the job, so
    the worker records the run's model calls under it. A demo may name planted flags for this run
    alone in another header (requested_flags), only its own and only on its own fixed event: the
    payload's demo_name names it (own_event_only)."""
    require_session()
    if planted.REQUESTED_KEY in event.payload:
        raise HTTPException(
            422,
            f"the payload key {planted.REQUESTED_KEY!r} is the api's own: name planted flags for "
            f"a demo's run in the {planted.PLANTED_HEADER} header",
        )
    demo = event.payload.get("demo_name")
    flags = requested_flags(planted_flags, demo if isinstance(demo, str) else None)
    if flags:
        own_event_only(str(demo), event)
    with planted.for_this_run(flags), db.connect(db.Role.APP) as conn:
        submitted = submit_event(
            conn,
            event_id=event.event_id,
            type=event.type.value,
            source=event.source,
            payload=stamped(event.payload),
        )
        if spend_activity and spend_activity.strip() and not submitted.duplicate:
            conn.execute(
                "UPDATE ops.jobs SET spend_activity = %s WHERE job_id = %s",
                (spend_activity.strip(), submitted.job_id),
            )
        tag_job(conn, submitted, demo_tag)
        conn.commit()
    return submitted


def require_session() -> None:
    """A run asked for over HTTP belongs to the open live session, so with none open it is
    refused (409) first, before the planted header checks and any model call. The scheduler's own
    jobs call submit_event directly and run with or without one, as before."""
    with db.connect(db.Role.APP) as conn:
        session = sessions.open_session(conn)
    if session is None:
        raise HTTPException(409, sessions.NO_SESSION)


def requested_flags(value: str | None, demo: str | None) -> list[str]:
    """The planted flags a demo names for its own run in the DataPilot-Planted header: refused
    for a flag the planted registry does not know, unless demo controls are allowed, and for any
    flag that is not the named demo's own for one run (planted.allowed_for). The caller switches
    them on while the api takes the request (planted.for_this_run)."""
    from datapilot.settings import get_settings

    try:
        chosen = planted.from_header(value)
    except KeyError as error:
        raise HTTPException(422, str(error).strip("'\"")) from None
    if chosen and not get_settings().datapilot_allow_demo_controls:
        raise HTTPException(
            403, "planted flags for one run need demo controls: DATAPILOT_ALLOW_DEMO_CONTROLS=1"
        )
    try:
        return planted.allowed_for(chosen, demo)
    except planted.NotTheDemos as error:
        raise HTTPException(403, str(error)) from None


def own_event_only(demo_name: str, event: EventIn) -> None:
    """The payload's demo_name is the client's own claim, so planted flags on POST /events are
    taken only for that demo's own fixed event: its registry question or digest, as make demo
    sends it (demos.own_events). Any other question or event under its name is refused (403)."""
    demo = registries.demos().by_id(demo_name)
    # imported here: demos imports the scheduler, which imports this module (submit_event)
    from datapilot.loop3_events import demos

    if not demos.is_own_event(demo, event.type.value, event.payload):
        raise HTTPException(
            403,
            f"planted flags on POST /events are taken only for the own event of {demo_name}, as "
            f"make demo NAME={demo_name} sends it; this event is not it",
        )


def tag_job(conn: psycopg.Connection[Any], submitted: EventSubmitted, tag: str | None) -> None:
    """The demo tag is a demo control: ignored unless demo controls are allowed, so no client
    can place its own run on a worker restarted for a demo while they are off."""
    from datapilot.settings import get_settings

    if not get_settings().datapilot_allow_demo_controls:
        return
    if tag and not submitted.duplicate:
        conn.execute("UPDATE ops.jobs SET demo_tag = %s WHERE job_id = %s", (tag, submitted.job_id))


def stamped(payload: dict[str, Any]) -> dict[str, Any]:
    """The payload with the flags switched on for this request, which the worker switches on
    again for this run alone; unchanged when there are none."""
    requested = planted.this_run()
    return {**payload, planted.REQUESTED_KEY: requested} if requested else payload
