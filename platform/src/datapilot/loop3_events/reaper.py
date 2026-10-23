"""The reaper: a job whose lease expired goes back to the queue, or is dead after max_attempts.

Attempts are counted at claim, so a job that crashed its worker max_attempts times is dead.
"""

from __future__ import annotations

from typing import Any

import psycopg

from datapilot.contracts import RunStatus
from datapilot.loop3_events import lifecycle

REAP_SQL = """
UPDATE ops.jobs
SET status = CASE WHEN attempts >= max_attempts THEN 'dead' ELSE 'queued' END,
    lease_owner = NULL, lease_until = NULL, run_after = now(), updated_at = now(),
    last_error = 'lease expired'
WHERE status = 'running' AND lease_until < now()
RETURNING job_id, event_id, status, attempts
"""


def reap(conn: psycopg.Connection[Any]) -> list[dict[str, Any]]:
    reaped = conn.execute(REAP_SQL).fetchall()
    for job in reaped:
        run = conn.execute(
            "SELECT run_id, status FROM ops.runs WHERE event_id = %s", (job["event_id"],)
        ).fetchone()
        if run is None or run["status"] != RunStatus.RUNNING.value:
            continue
        if job["status"] == "dead":
            lifecycle.transition(
                conn,
                str(run["run_id"]),
                RunStatus.FAILED,
                by="reaper",
                reason=f"lease expired; attempts exhausted ({job['attempts']})",
            )
        else:
            lifecycle.transition(
                conn,
                str(run["run_id"]),
                RunStatus.QUEUED,
                by="reaper: expired lease, attempts left",
                attempts=job["attempts"],
            )
    return reaped
