"""The event loop's interface to the hill-climbing loop: requests only.

The api records experiment and analyzer requests in ops.improvement_requests, tagged with the open
live session; the hill-climbing loop's runner claims them (ImprovementRunner) and writes its own
tables (ops.experiments, ops.promotion_decisions), carrying the request's session_id. Nothing here
runs an experiment or an analyzer.

The runner takes requests in the order they were made, whatever their kind, so an analyzer request
followed at once by an experiment on the candidate runs the experiment on the analyzer's new
version. One runner serves a database: it holds the advisory lock RUNNER_LOCK while it serves, a
second runner refuses to start, and a reset can tell a running request from one whose runner died.
"""

from __future__ import annotations

import uuid
from typing import Any, Literal, Protocol

import psycopg
from psycopg.types.json import Jsonb

from datapilot.loop3_events import sessions

Kind = Literal["experiment", "analyzer"]

CLAIM_SQL = """
UPDATE ops.improvement_requests SET status = 'running', started_at = now()
WHERE request_id = (
    SELECT request_id FROM ops.improvement_requests
    WHERE status = 'queued' AND kind = %s
    ORDER BY requested_at FOR UPDATE SKIP LOCKED LIMIT 1)
RETURNING request_id, kind, params, session_id
"""
CLAIM_NEXT_SQL = """
UPDATE ops.improvement_requests SET status = 'running', started_at = now()
WHERE request_id = (
    SELECT request_id FROM ops.improvement_requests
    WHERE status = 'queued'
    ORDER BY requested_at, request_id FOR UPDATE SKIP LOCKED LIMIT 1)
RETURNING request_id, kind, params, session_id
"""
# A fixed key of a Postgres advisory lock (any bigint no other code uses): held by the serving
# runner's own connection, so it is released the moment that process stops.
RUNNER_LOCK = 2_026_102_404


class ImprovementRunner(Protocol):
    """Implemented by the hill-climbing loop."""

    def run(self, request: dict[str, Any]) -> dict[str, Any]:
        """Run one claimed request; the returned dict is stored as its result."""
        ...


def enqueue(
    conn: psycopg.Connection[Any], kind: Kind, params: dict[str, Any], *, requested_by: str
) -> dict[str, Any]:
    session = sessions.open_session(conn)
    return conn.execute(
        "INSERT INTO ops.improvement_requests (request_id, kind, params, session_id, requested_by) "
        "VALUES (%s, %s, %s, %s, %s) "
        "RETURNING request_id, kind, params, status, session_id, requested_by, requested_at",
        (
            uuid.uuid4(),
            kind,
            Jsonb(params),
            session.session_id if session else None,
            requested_by,
        ),
    ).fetchone()


def claim(conn: psycopg.Connection[Any], kind: Kind) -> dict[str, Any] | None:
    return conn.execute(CLAIM_SQL, (kind,)).fetchone()


def claim_next(conn: psycopg.Connection[Any]) -> dict[str, Any] | None:
    """The oldest queued request of either kind."""
    return conn.execute(CLAIM_NEXT_SQL).fetchone()


def hold_runner_lock(conn: psycopg.Connection[Any]) -> bool:
    """Take the runner's lock on this connection for as long as it stays open; False when another
    runner holds it."""
    row = conn.execute("SELECT pg_try_advisory_lock(%s) AS got", (RUNNER_LOCK,)).fetchone()
    return bool(row["got"])


def runner_serving(conn: psycopg.Connection[Any]) -> bool:
    """True when a hill-climbing runner serves this database now (it holds the lock)."""
    if not hold_runner_lock(conn):
        return True
    conn.execute("SELECT pg_advisory_unlock(%s)", (RUNNER_LOCK,))
    return False


def finish(
    conn: psycopg.Connection[Any], request_id: str, *, result: dict[str, Any], failed: bool = False
) -> None:
    conn.execute(
        "UPDATE ops.improvement_requests SET status = %s, finished_at = now(), result = %s "
        "WHERE request_id = %s",
        ("failed" if failed else "done", Jsonb(result), request_id),
    )
