"""Runs and the live session, as the console reads them. Every run carries its live stamp.

Models: datapilot.contracts.api (SessionOut, RunList, RunSummary, RunDetail).
"""

from __future__ import annotations

from typing import Any

import psycopg
from fastapi import APIRouter, HTTPException

from datapilot import db
from datapilot.contracts.api import RunDetail, RunList, RunSummary, SessionOut
from datapilot.contracts.live import LiveSession, LiveStamp
from datapilot.loop3_events import sessions

api = APIRouter()

RUN_COLUMNS = (
    "r.run_id, r.event_id, r.session_id, r.demo_name, r.question, r.metric_family, r.status, "
    "r.autonomy_level_applied, r.knowledge_version, r.model, r.planted_active, r.tokens_in, "
    "r.tokens_out, r.cost_usd, r.langsmith_url, r.answer, r.created_at, r.started_at, "
    "r.finished_at, (SELECT count(*) FROM ops.event_duplicates d WHERE d.event_id = r.event_id) "
    "AS duplicates_ignored"
)


def live_stamp(run: dict[str, Any]) -> LiveStamp | None:
    if run["session_id"] is None:
        return None
    return LiveStamp(
        run_id=run["run_id"],
        session_id=run["session_id"],
        started_at=run["started_at"] or run["created_at"],
        trace_url=run["langsmith_url"],
    )


def _with_stamp(run: dict[str, Any]) -> dict[str, Any]:
    stamp = live_stamp(run)
    return {**run, "live_stamp": stamp.to_browser() if stamp else None}


def session_out(session: LiveSession) -> SessionOut:
    return SessionOut(**session.model_dump(), started_at_utc=session.to_browser()["started_at_utc"])


@api.get("/sessions/current", response_model=SessionOut)
def current_session() -> SessionOut:
    with db.connect(db.Role.APP) as conn:
        session = sessions.open_session(conn)
    if session is None:
        raise HTTPException(404, "No live session is open: run `make preflight` first.")
    return session_out(session)


@api.get("/runs", response_model=RunList)
def list_runs(all_sessions: bool = False, limit: int = 50) -> RunList:
    """The current session's runs, newest first; all_sessions=true for every run."""
    with db.connect(db.Role.APP) as conn:
        session = sessions.open_session(conn)
        if all_sessions:
            rows = conn.execute(
                f"SELECT {RUN_COLUMNS} FROM ops.runs r ORDER BY r.created_at DESC LIMIT %s",
                (limit,),
            ).fetchall()
        elif session is None:
            rows = []
        else:
            rows = conn.execute(
                f"SELECT {RUN_COLUMNS} FROM ops.runs r WHERE r.session_id = %s "
                "ORDER BY r.created_at DESC LIMIT %s",
                (session.session_id, limit),
            ).fetchall()
    return RunList(
        session=session_out(session) if session else None,
        runs=[RunSummary.model_validate(_with_stamp(r)) for r in rows],
    )


@api.get("/runs/{run_id}", response_model=RunDetail)
def get_run(run_id: str) -> RunDetail:
    with db.connect(db.Role.APP) as conn:
        try:
            run = conn.execute(
                f"SELECT {RUN_COLUMNS} FROM ops.runs r WHERE r.run_id = %s", (run_id,)
            ).fetchone()
        except psycopg.errors.InvalidTextRepresentation as error:
            raise HTTPException(404, f"no run {run_id}") from error
        if run is None:
            raise HTTPException(404, f"no run {run_id}")
        events = conn.execute(
            "SELECT id, ts, kind, payload FROM ops.run_events WHERE run_id = %s ORDER BY id",
            (run_id,),
        ).fetchall()
        approvals = conn.execute(
            "SELECT approval_id, kind, requested_at, action, sql, row_estimate, reason, decision, "
            "decided_by, decided_at, comment FROM ops.approvals WHERE run_id = %s "
            "ORDER BY approval_id",
            (run_id,),
        ).fetchall()
        posts = conn.execute(
            "SELECT post_id, channel, label, body, posted_at FROM ops.posts WHERE run_id = %s "
            "ORDER BY post_id",
            (run_id,),
        ).fetchall()
    return RunDetail.model_validate(
        {**_with_stamp(run), "events": events, "approvals": approvals, "posts": posts}
    )
