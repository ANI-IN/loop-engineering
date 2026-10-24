"""Experiments and gate decisions in the ops schema, always tied to the open live session.

Experiments and gate decisions belong to the selected pack (DATAPILOT_PACK). Experiments record
the open live session (started only by make preflight; NoLiveSession when none is open). The
baseline for a comparison is a finished experiment started in that session; anything older raises
NoLiveBaseline. Nothing here ever reads results from another session.

A running experiment is written as it goes (OpsItemSink): its row first, then one per-example
entry as each item's runs finish, with the item's trace links, so the console's holdout ledger and
benchmark strip fill in live; the totals are written when it finishes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import UUID

import psycopg

from datapilot import db
from datapilot.config import active_pack
from datapilot.contracts import ItemResult, Split
from datapilot.contracts.live import NoLiveBaseline, NoLiveSession
from datapilot.loop4_hill_climbing.experiment import Confirmation, ExperimentResult
from datapilot.loop4_hill_climbing.gate import GateDecision, confirmation_from

OPEN_SESSION = "SELECT session_id FROM ops.live_sessions WHERE ended_at IS NULL"
INSERT_EXPERIMENT = """
INSERT INTO ops.experiments (experiment_id, session_id, pack, knowledge_version, split,
    holdout_repeats, concurrency, pass_count, total, per_example, started_at, finished_at,
    wall_seconds)
VALUES (%(experiment_id)s, %(session_id)s, %(pack)s, %(knowledge_version)s, %(split)s,
    %(holdout_repeats)s, %(concurrency)s, %(pass_count)s, %(total)s, %(per_example)s,
    %(started_at)s, %(finished_at)s, %(wall_seconds)s)
"""
APPEND_EXAMPLE = """
UPDATE ops.experiments SET per_example = per_example || %(entry)s::jsonb
WHERE experiment_id = %(experiment_id)s
"""
FINISH_EXPERIMENT = """
UPDATE ops.experiments
SET pass_count = %(pass_count)s, total = %(total)s, per_example = %(per_example)s,
    finished_at = %(finished_at)s, wall_seconds = %(wall_seconds)s,
    langsmith_url = %(langsmith_url)s
WHERE experiment_id = %(experiment_id)s
"""
LATEST_IN_SESSION = """
SELECT experiment_id, session_id, knowledge_version, per_example, started_at, wall_seconds
FROM ops.experiments
WHERE session_id = %(session_id)s AND pack = %(pack)s
  AND knowledge_version = %(knowledge_version)s AND finished_at IS NOT NULL
ORDER BY started_at DESC
LIMIT 1
"""
# The active version's experiment a candidate's gate compares it with, recorded as the gate starts,
# and read back by the background promotion (runner._decide_approved).
SET_GATE_BASELINE = """
UPDATE ops.experiments SET gate_baseline_id = %(baseline_id)s
WHERE experiment_id = %(experiment_id)s
"""
GATE_BASELINE = """
SELECT b.experiment_id, b.session_id, b.knowledge_version, b.per_example, b.started_at,
       b.wall_seconds
FROM ops.experiments c JOIN ops.experiments b ON b.experiment_id = c.gate_baseline_id
WHERE c.experiment_id = %(experiment_id)s AND b.session_id = %(session_id)s
  AND b.finished_at IS NOT NULL
"""
# Write one item's confirmation into the experiment's per-example data, in place, so the console
# ledger shows each step as it happens.
SET_CONFIRMATION = """
UPDATE ops.experiments
SET per_example = (
    SELECT jsonb_agg(
        CASE WHEN e ->> 'item_id' = %(item_id)s
             THEN jsonb_set(e, '{confirmation}', %(confirmation)s::jsonb) ELSE e END
        ORDER BY position)
    FROM jsonb_array_elements(per_example) WITH ORDINALITY AS x(e, position))
WHERE experiment_id = %(experiment_id)s
"""
# The confirming re-run of a holdout item that fell short when its family was judged for the
# unattended level, written beside the item the same way.
SET_CLEARANCE = """
UPDATE ops.experiments
SET per_example = (
    SELECT jsonb_agg(
        CASE WHEN e ->> 'item_id' = %(item_id)s
             THEN jsonb_set(e, '{clearance_rerun}', %(clearance)s::jsonb) ELSE e END
        ORDER BY position)
    FROM jsonb_array_elements(per_example) WITH ORDINALITY AS x(e, position))
WHERE experiment_id = %(experiment_id)s
"""
INSERT_DECISION = """
INSERT INTO ops.promotion_decisions (pack, candidate_version, active_version, verdict, reasons,
    sentence, approved_by)
VALUES (%(pack)s, %(candidate)s, %(active)s, %(verdict)s, %(reasons)s, %(sentence)s,
    %(approved_by)s)
RETURNING decision_id
"""


def open_session(conn: psycopg.Connection) -> UUID:
    row = conn.execute(OPEN_SESSION).fetchone()
    if row is None:
        raise NoLiveSession("no live session is open: run make preflight first")
    return row["session_id"]


def example_entry(experiment: ExperimentResult, item_id: str) -> dict[str, Any]:
    """One per-example entry: the item's result, its split, trace links, and deciding SQL."""
    entry: dict[str, Any] = {
        "split": experiment.splits_by_item[item_id].value,
        **experiment.results[item_id].model_dump(),
        "trace_urls": experiment.trace_links.get(item_id, []),
    }
    if experiment.untraced_runs.get(item_id):  # the trace sample left these runs out
        entry["runs_not_traced"] = experiment.untraced_runs[item_id]
    if item_id in experiment.final_sql:
        entry["final_sql"] = experiment.final_sql[item_id]
    if item_id in experiment.confirmations:
        entry["confirmation"] = experiment.confirmations[item_id].as_dict()
    return entry


def _split_name(experiment: ExperimentResult) -> str:
    return experiment.splits[0].value if len(experiment.splits) == 1 else "all"


def save_experiment(
    conn: psycopg.Connection,
    experiment: ExperimentResult,
    *,
    holdout_repeats: int,
    concurrency: int,
) -> None:
    per_example = [example_entry(experiment, item_id) for item_id in experiment.results]
    conn.execute(
        INSERT_EXPERIMENT,
        {
            "experiment_id": experiment.experiment_id,
            "session_id": experiment.session_id,
            "pack": active_pack(),
            "knowledge_version": experiment.knowledge_version,
            "split": _split_name(experiment),
            "holdout_repeats": holdout_repeats,
            "concurrency": concurrency,
            "pass_count": sum(r.passed for r in experiment.results.values()),
            "total": len(experiment.results),
            "per_example": json.dumps(per_example),
            "started_at": experiment.started_at,
            "finished_at": experiment.started_at + timedelta(seconds=experiment.wall_seconds),
            "wall_seconds": round(experiment.wall_seconds, 2),
        },
    )


@dataclass
class OpsItemSink:
    """Implements experiment.ItemSink: each write is its own committed transaction."""

    holdout_repeats: int
    concurrency: int

    def started(self, experiment: ExperimentResult) -> None:
        with db.connect(db.Role.APP) as conn:
            conn.execute(
                INSERT_EXPERIMENT,
                {
                    "experiment_id": experiment.experiment_id,
                    "session_id": experiment.session_id,
                    "pack": active_pack(),
                    "knowledge_version": experiment.knowledge_version,
                    "split": _split_name(experiment),
                    "holdout_repeats": self.holdout_repeats,
                    "concurrency": self.concurrency,
                    "pass_count": None,
                    "total": len(experiment.splits_by_item),
                    "per_example": "[]",
                    "started_at": experiment.started_at,
                    "finished_at": None,
                    "wall_seconds": None,
                },
            )
            conn.commit()

    def item_done(self, experiment: ExperimentResult, item_id: str) -> None:
        entry = json.dumps([example_entry(experiment, item_id)])
        with db.connect(db.Role.APP) as conn:
            conn.execute(
                APPEND_EXAMPLE, {"entry": entry, "experiment_id": experiment.experiment_id}
            )
            conn.commit()


def finish_experiment(
    conn: psycopg.Connection, experiment: ExperimentResult, *, langsmith_url: str | None = None
) -> None:
    """The totals of a streamed experiment, once its last item finished."""
    conn.execute(
        FINISH_EXPERIMENT,
        {
            "experiment_id": experiment.experiment_id,
            "pass_count": sum(r.passed for r in experiment.results.values()),
            "total": len(experiment.results),
            "per_example": json.dumps(
                [example_entry(experiment, item_id) for item_id in experiment.results]
            ),
            "finished_at": experiment.started_at + timedelta(seconds=experiment.wall_seconds),
            "wall_seconds": round(experiment.wall_seconds, 2),
            "langsmith_url": langsmith_url,
        },
    )


def _confirmation(entry: dict[str, Any]) -> Confirmation:
    return confirmation_from(entry["item_id"], entry["confirmation"])


def baseline_for(conn: psycopg.Connection, knowledge_version: str) -> ExperimentResult:
    """The latest finished experiment of `knowledge_version` started in the open live session."""
    session_id = open_session(conn)
    row = conn.execute(
        LATEST_IN_SESSION,
        {"session_id": session_id, "pack": active_pack(), "knowledge_version": knowledge_version},
    ).fetchone()
    if row is None:
        raise NoLiveBaseline(
            f"no experiment of {knowledge_version} was started in this live session: run the "
            "baseline experiment now"
        )
    return _result(row)


def record_gate_baseline(
    conn: psycopg.Connection, candidate: ExperimentResult, baseline: ExperimentResult
) -> None:
    conn.execute(
        SET_GATE_BASELINE,
        {"experiment_id": candidate.experiment_id, "baseline_id": baseline.experiment_id},
    )


def gate_baseline(conn: psycopg.Connection, candidate: ExperimentResult) -> ExperimentResult:
    """The experiment the candidate's gate compared it with, in the open live session; raises
    NoLiveBaseline when no gate recorded one, or the reset has removed it."""
    row = conn.execute(
        GATE_BASELINE,
        {"experiment_id": candidate.experiment_id, "session_id": open_session(conn)},
    ).fetchone()
    if row is None:
        raise NoLiveBaseline(
            f"no gate recorded the baseline of {candidate.knowledge_version}'s experiment in this "
            "live session"
        )
    return _result(row)


def _result(row: dict[str, Any]) -> ExperimentResult:
    examples = row["per_example"]
    return ExperimentResult(
        experiment_id=row["experiment_id"],
        session_id=row["session_id"],
        knowledge_version=row["knowledge_version"],
        splits=sorted({Split(e["split"]) for e in examples}),
        results={e["item_id"]: ItemResult.model_validate(e) for e in examples},
        splits_by_item={e["item_id"]: Split(e["split"]) for e in examples},
        started_at=row["started_at"],
        wall_seconds=float(row["wall_seconds"] or 0),
        trace_links={e["item_id"]: list(e.get("trace_urls") or []) for e in examples},
        untraced_runs={
            e["item_id"]: e["runs_not_traced"] for e in examples if e.get("runs_not_traced")
        },
        confirmations={e["item_id"]: _confirmation(e) for e in examples if "confirmation" in e},
        final_sql={e["item_id"]: e["final_sql"] for e in examples if e.get("final_sql")},
    )


@dataclass
class OpsStepSink:
    """Implements gate.StepSink: each step is committed at once, so the ledger shows it live."""

    conn: psycopg.Connection

    def step(self, experiment_id: UUID, confirmation: Confirmation) -> None:
        self.conn.execute(
            SET_CONFIRMATION,
            {
                "experiment_id": experiment_id,
                "item_id": confirmation.item_id,
                "confirmation": json.dumps(confirmation.as_dict()),
            },
        )
        self.conn.commit()


def save_clearance_rerun(
    conn: psycopg.Connection, experiment_id: UUID, item_id: str, passes: list[bool]
) -> None:
    conn.execute(
        SET_CLEARANCE,
        {
            "experiment_id": experiment_id,
            "item_id": item_id,
            "clearance": json.dumps({"runs": len(passes), "passes": sum(passes), "reruns": passes}),
        },
    )


def save_decision(conn: psycopg.Connection, decision: GateDecision) -> int:
    row = conn.execute(
        INSERT_DECISION,
        {
            "pack": active_pack(),
            "candidate": decision.candidate_version,
            "active": decision.active_version,
            "verdict": decision.verdict,
            "reasons": json.dumps(decision.reasons),
            "sentence": decision.sentence,
            "approved_by": decision.approved_by,
        },
    ).fetchone()
    assert row is not None
    return int(row["decision_id"])
