"""Live sessions: every run belongs to the session open when it was received.

Only preflight starts a session (`make preflight PURPOSE=...`, once its checks pass); the console
reads the current one and never starts one. Starting a session ends the open one.
"""

from __future__ import annotations

import uuid
from typing import Any

import psycopg

from datapilot import db
from datapilot.contracts.live import LiveSession, NoLiveSession, SessionPurpose

# What the api answers (409) and make demo prints when a run is asked for with no session open.
NO_SESSION = (
    "No live session is open: run make preflight "
    "PURPOSE=class|rehearsal|thursday-review|development first"
)
_OPEN = (
    "SELECT session_id, purpose, started_at, started_by, timezone FROM ops.live_sessions "
    "WHERE ended_at IS NULL"
)


def start_session(purpose: SessionPurpose, started_by: str, timezone: str) -> LiveSession:
    with db.connect(db.Role.APP) as conn:
        conn.execute("UPDATE ops.live_sessions SET ended_at = now() WHERE ended_at IS NULL")
        row = conn.execute(
            "INSERT INTO ops.live_sessions (session_id, purpose, started_by, timezone) "
            "VALUES (%s, %s, %s, %s) "
            "RETURNING session_id, purpose, started_at, started_by, timezone",
            (uuid.uuid4(), SessionPurpose(purpose).value, started_by, timezone),
        ).fetchone()
        conn.commit()
    return LiveSession.model_validate(row)


def open_session(conn: psycopg.Connection[Any]) -> LiveSession | None:
    row = conn.execute(_OPEN).fetchone()
    return LiveSession.model_validate(row) if row else None


def current_session() -> LiveSession:
    with db.connect(db.Role.APP) as conn:
        session = open_session(conn)
    if session is None:
        raise NoLiveSession("no live session is open: run `make preflight` first")
    return session
