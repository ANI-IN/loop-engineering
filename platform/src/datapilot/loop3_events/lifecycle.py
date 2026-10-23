"""Run lifecycle writes: every status change is checked against TRANSITIONS and recorded as a
status_changed run event in the same transaction. The console reads nothing else for live state."""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from datapilot.contracts import TERMINAL, RunEventKind, RunStatus, can_transition


class IllegalTransition(RuntimeError):
    pass


def record(conn: psycopg.Connection[Any], run_id: str, kind: RunEventKind, payload: dict) -> None:
    conn.execute(
        "INSERT INTO ops.run_events (run_id, kind, payload) VALUES (%s, %s, %s)",
        (run_id, kind.value, Jsonb(payload)),
    )


def current_status(conn: psycopg.Connection[Any], run_id: str, *, lock: bool = False) -> RunStatus:
    sql = "SELECT status FROM ops.runs WHERE run_id = %s" + (" FOR UPDATE" if lock else "")
    row = conn.execute(sql, (run_id,)).fetchone()
    if row is None:
        raise KeyError(f"no run {run_id}")
    return RunStatus(row["status"])


def transition(
    conn: psycopg.Connection[Any], run_id: str, new: RunStatus, *, by: str, **payload: Any
) -> RunStatus:
    """Move a run to `new`; returns the status it left. Raises IllegalTransition otherwise."""
    old = current_status(conn, run_id, lock=True)
    if not can_transition(old, new):
        raise IllegalTransition(f"run {run_id}: {old.value} -> {new.value} is not allowed")
    conn.execute(
        "UPDATE ops.runs SET status = %s, updated_at = now(), "
        "started_at = CASE WHEN %s AND started_at IS NULL THEN now() ELSE started_at END, "
        "finished_at = CASE WHEN %s THEN now() ELSE NULL END WHERE run_id = %s",
        (new.value, new is RunStatus.RUNNING, new in TERMINAL, run_id),
    )
    record(
        conn,
        run_id,
        RunEventKind.STATUS_CHANGED,
        {"from": old.value, "to": new.value, "by": by, **payload},
    )
    return old
