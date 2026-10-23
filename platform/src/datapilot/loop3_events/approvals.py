"""Human approval: the durable checkpointer that keeps a paused run, and the approval records.

A run paused by the approval middleware lives in its checkpoint (thread_id = run_id) in schema lg,
so it survives a worker restart; the approval resumes it with Command(resume={"decisions": [...]}).
Decisions are approve or reject only.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal

import psycopg
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.types import Checkpointer
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from datapilot import db
from datapilot.contracts import RunEventKind
from datapilot.loop2_verification.loop import ApprovalRequest
from datapilot.loop3_events import lifecycle
from datapilot.planted import planted

Decision = Literal["approve", "reject"]
# The checkpoint stores the answer envelope; name the types it may restore.
SERDE = JsonPlusSerializer(
    allowed_msgpack_modules=[
        ("datapilot.contracts.answer", "AnswerEnvelope"),
        ("datapilot.contracts.answer", "AnswerStatus"),
        ("datapilot.contracts.agents", "SchemaBrief"),
        ("datapilot.contracts.agents", "TableHint"),
        ("datapilot.contracts.agents", "ReviewVerdict"),
        ("datapilot.contracts.agents", "ReviewOutcome"),
    ]
)


@asynccontextmanager
async def checkpointer(url: str | None = None) -> AsyncIterator[Checkpointer]:
    """One per worker process."""
    if planted("BUG_MEMORY_CHECKPOINTER"):
        yield InMemorySaver(serde=SERDE)  # planted: process memory, lost when the worker restarts
        return
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    kwargs = {
        "autocommit": True,
        "prepare_threshold": 0,
        "row_factory": dict_row,
        "options": "-c search_path=lg",  # the saver has no schema option
    }
    pool = AsyncConnectionPool(url or db.url_for(db.Role.APP), kwargs=kwargs, open=False)
    await pool.open()
    try:
        saver = AsyncPostgresSaver(pool, serde=SERDE)  # type: ignore[arg-type]
        await saver.setup()
        yield saver
    finally:
        await pool.close()


def request(conn: psycopg.Connection[Any], run_id: str, approval: ApprovalRequest) -> None:
    conn.execute(
        "INSERT INTO ops.approvals (run_id, kind, action, sql, row_estimate, reason) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (
            run_id,
            approval.kind,
            approval.action,
            approval.sql,
            approval.row_estimate,
            approval.reason,
        ),
    )
    lifecycle.record(
        conn,
        run_id,
        RunEventKind.APPROVAL_REQUESTED,
        {
            "kind": approval.kind,
            "action": approval.action,
            "sql": approval.sql,
            "row_estimate": approval.row_estimate,
            "reason": approval.reason,
        },
    )


class NoOpenApproval(LookupError):
    pass


def decide(
    conn: psycopg.Connection[Any], run_id: str, decision: Decision, *, by: str, comment: str = ""
) -> str:
    """Record the decision on the run's open approval; returns the approval's kind."""
    row = conn.execute(
        "UPDATE ops.approvals SET decision = %s, decided_by = %s, decided_at = now(), "
        "comment = %s WHERE run_id = %s AND decision IS NULL RETURNING kind",
        (decision, by, comment or None, run_id),
    ).fetchone()
    if row is None:
        raise NoOpenApproval(f"run {run_id} has no open approval")
    lifecycle.record(
        conn,
        run_id,
        RunEventKind.APPROVAL_DECIDED,
        {"decision": decision, "by": by, "kind": row["kind"], "comment": comment},
    )
    return str(row["kind"])


def latest(conn: psycopg.Connection[Any], run_id: str) -> dict[str, Any] | None:
    return conn.execute(
        "SELECT kind, decision, comment FROM ops.approvals WHERE run_id = %s "
        "ORDER BY approval_id DESC LIMIT 1",
        (run_id,),
    ).fetchone()


def approved(conn: psycopg.Connection[Any], run_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM ops.approvals WHERE run_id = %s AND decision = 'approve' LIMIT 1", (run_id,)
    ).fetchone()
    return row is not None
