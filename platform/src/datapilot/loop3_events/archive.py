"""The reset archive: what `make reset NAME=hill-climbing-loop` deleted or retired, kept in ops.

Before the hill-climbing reset deletes or retires a row of its knowledge and experiment state, it
copies the whole row, as JSON, into ops.reset_archive_rows under one ops.reset_archives entry for
that reset, stamped with the reset time and the live session open then (migration 015). An
experiment row carries its per-item results and confirmations, so an archived experiment is the
complete evidence of that experiment. `datapilot archive list` and `datapilot archive show <id>`
read it back. Run state (posts, approvals, run events, runs, jobs, events) is not archived: it is
cleared by every section's reset and may hold personal data from an export.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import psycopg

ARCHIVE_TABLE = "ops.reset_archive_rows"
# The archived tables and the SQL that turns a row's primary key into text.
KEYS = {
    "ops.experiments": "experiment_id::text",
    "ops.promotion_decisions": "decision_id::text",
    "ops.improvement_requests": "request_id::text",
    "ops.autonomy_policy": "metric_family",
    "ops.knowledge_versions": "pack || '/' || version",
    "ops.analyzer_candidates": "candidate_id::text",
}
NOUNS = {
    "ops.experiments": ("experiment", "experiments"),
    "ops.promotion_decisions": ("promotion decision", "promotion decisions"),
    "ops.improvement_requests": ("improvement request", "improvement requests"),
    "ops.autonomy_policy": ("unattended-level eligibility", "unattended-level eligibilities"),
    "ops.knowledge_versions": ("knowledge version", "knowledge versions"),
    "ops.analyzer_candidates": ("analyzer candidate", "analyzer candidates"),
}


@dataclass
class Archive:
    """One reset's archive entry, filled as the reset copies rows into it."""

    reset_id: uuid.UUID
    counts: dict[tuple[str, str], int] = field(default_factory=dict)  # (table, action) -> rows

    @property
    def total(self) -> int:
        return sum(self.counts.values())

    def describe(self) -> str:
        parts = []
        for (table, action), n in self.counts.items():
            if n:
                one, many = NOUNS[table]
                parts.append(f"{n} {one if n == 1 else many} {action}")
        return ", ".join(parts) or "nothing"


def open_archive(
    conn: psycopg.Connection[Any],
    *,
    section: str,
    pack: str,
    discarded_baseline: bool,
    reset_by: str,
) -> Archive:
    """The archive entry of one reset, stamped now with the open live session (if any)."""
    reset_id = uuid.uuid4()
    conn.execute(
        "INSERT INTO ops.reset_archives (reset_id, section, pack, discarded_baseline, session_id, "
        "reset_by) VALUES (%s, %s, %s, %s, "
        "(SELECT session_id FROM ops.live_sessions WHERE ended_at IS NULL), %s)",
        (reset_id, section, pack, discarded_baseline, reset_by),
    )
    return Archive(reset_id)


def keep(
    conn: psycopg.Connection[Any],
    archive: Archive,
    table: str,
    where: str,
    params: tuple[Any, ...] = (),
    *,
    action: str = "deleted",
) -> int:
    """Copy the rows of `table` matching `where` into the archive before the reset changes them.
    `table` is one of KEYS and `where` is the reset's own fixed SQL; values travel as parameters."""
    key = KEYS[table]
    copied = conn.execute(
        f"INSERT INTO {ARCHIVE_TABLE} (reset_id, source_table, row_key, action, row) "
        f"SELECT %s, %s, {key}, %s, to_jsonb(t) FROM {table} t WHERE {where}",
        (archive.reset_id, table, action, *params),
    ).rowcount
    archive.counts[(table, action)] = archive.counts.get((table, action), 0) + copied
    return copied


# --- reading the archive ------------------------------------------------------------------------
LIST_RESETS = """
SELECT a.reset_id, a.section, a.pack, a.discarded_baseline, a.session_id, a.reset_at, a.reset_by,
       count(r.archive_row_id) AS rows,
       count(r.archive_row_id) FILTER (WHERE r.source_table = 'ops.experiments') AS experiments
FROM ops.reset_archives a LEFT JOIN ops.reset_archive_rows r ON r.reset_id = a.reset_id
GROUP BY a.reset_id ORDER BY a.reset_at DESC, a.reset_id LIMIT %s
"""
ARCHIVED_EXPERIMENTS = """
SELECT r.row_key, r.row, a.reset_at, a.reset_id
FROM ops.reset_archive_rows r JOIN ops.reset_archives a ON a.reset_id = r.reset_id
WHERE r.source_table = 'ops.experiments' AND r.reset_id = ANY(%s)
ORDER BY a.reset_at DESC, r.row ->> 'started_at'
"""
ONE_EXPERIMENT = """
SELECT r.row, a.reset_id, a.reset_at, a.session_id AS reset_session, a.section, a.reset_by
FROM ops.reset_archive_rows r JOIN ops.reset_archives a ON a.reset_id = r.reset_id
WHERE r.source_table = 'ops.experiments' AND r.row_key = %s
ORDER BY a.reset_at DESC LIMIT 1
"""
DECISIONS_OF = """
SELECT r.row FROM ops.reset_archive_rows r
WHERE r.source_table = 'ops.promotion_decisions' AND r.reset_id = %s
  AND (r.row ->> 'candidate_version' = %s OR r.row ->> 'active_version' = %s)
ORDER BY (r.row ->> 'decision_id')::bigint
"""


@dataclass(frozen=True)
class ArchivedReset:
    reset_id: str
    section: str
    reset_at: datetime
    reset_by: str
    session_id: str | None
    rows: int
    experiments: list[dict[str, Any]]


def resets(conn: psycopg.Connection[Any], limit: int = 20) -> list[ArchivedReset]:
    """The newest archived resets with their experiments, newest first."""
    found = conn.execute(LIST_RESETS, (limit,)).fetchall()
    by_reset: dict[str, list[dict[str, Any]]] = {str(r["reset_id"]): [] for r in found}
    for row in conn.execute(ARCHIVED_EXPERIMENTS, ([r["reset_id"] for r in found],)).fetchall():
        by_reset[str(row["reset_id"])].append(summary(row["row"]))
    return [
        ArchivedReset(
            reset_id=str(r["reset_id"]),
            section=r["section"],
            reset_at=r["reset_at"],
            reset_by=r["reset_by"],
            session_id=str(r["session_id"]) if r["session_id"] else None,
            rows=int(r["rows"]),
            experiments=by_reset[str(r["reset_id"])],
        )
        for r in found
    ]


def summary(row: dict[str, Any]) -> dict[str, Any]:
    """An archived experiment row in brief: id, version, session, start, passes per split."""
    per_item = row.get("per_example") or []
    out: dict[str, Any] = {
        "experiment_id": row.get("experiment_id"),
        "knowledge_version": row.get("knowledge_version"),
        "session_id": row.get("session_id"),
        "started_at": row.get("started_at"),
    }
    for split in ("dev", "holdout"):
        mine = [e for e in per_item if e.get("split") == split]
        out[split] = (sum(bool(e.get("passed")) for e in mine), len(mine))
    out["confirmations"] = sum(1 for e in per_item if e.get("confirmation"))
    return out


def experiment(conn: psycopg.Connection[Any], experiment_id: str) -> dict[str, Any] | None:
    """One archived experiment: the whole row, the reset that archived it, and the promotion
    decisions of the same reset that name its knowledge version."""
    found = conn.execute(ONE_EXPERIMENT, (experiment_id,)).fetchone()
    if found is None:
        return None
    row, version = found["row"], found["row"].get("knowledge_version")
    decisions = conn.execute(DECISIONS_OF, (found["reset_id"], version, version)).fetchall()
    return {
        "row": row,
        "summary": summary(row),
        "reset_id": str(found["reset_id"]),
        "reset_at": found["reset_at"],
        "reset_by": found["reset_by"],
        "reset_session": str(found["reset_session"]) if found["reset_session"] else None,
        "decisions": [d["row"] for d in decisions],
    }


def experiment_lines(found: dict[str, Any]) -> list[str]:
    """What `datapilot archive show <experiment id>` prints."""
    brief = found["summary"]
    row = found["row"]
    out = [
        f"experiment {brief['experiment_id']} of {brief['knowledge_version']}, session "
        f"{brief['session_id']}, started {brief['started_at']}, finished {row.get('finished_at')}",
        f"archived by {found['reset_by']} at {found['reset_at'].isoformat(timespec='seconds')} "
        f"(reset archive {found['reset_id']}, live session {found['reset_session'] or 'none'})",
        f"dev passes {brief['dev'][0]} of {brief['dev'][1]}; holdout passes {brief['holdout'][0]} "
        f"of {brief['holdout'][1]}",
    ]
    for entry in row.get("per_example") or []:
        runs = entry.get("run_passes") or [entry.get("passed")]
        mark = "pass" if entry.get("passed") else "fail"
        line = (
            f"  {entry.get('split', ''):7} {entry.get('item_id')}: {mark} "
            f"({sum(bool(p) for p in runs)} of {len(runs)} runs)"
        )
        confirmation = entry.get("confirmation")
        if confirmation:
            line += f"; {(confirmation.get('steps') or ['confirmation'])[-1]}"
        out.append(line)
    for decision in found["decisions"]:
        out.append(
            f"decision {decision.get('decision_id')}: {decision.get('verdict')}, "
            f"{decision.get('sentence')}"
        )
    return out
