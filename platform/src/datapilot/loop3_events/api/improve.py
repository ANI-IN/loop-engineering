"""Hill-climbing requests (enqueue only) and the human approval of a knowledge version.

Models: datapilot.contracts.api (ExperimentIn and AnalyzerIn -> ImprovementRequestOut,
ImprovementRequestList, KnowledgeApprovalIn -> KnowledgeApproved). A demo's planted flags for its
own request come in the DataPilot-Planted header and are kept in the request's params; the runner
switches them on for that request alone.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from datapilot import db, planted
from datapilot.config import active_pack
from datapilot.contracts.api import (
    AnalyzerIn,
    ExperimentIn,
    ImprovementRequestList,
    ImprovementRequestOut,
    KnowledgeApprovalIn,
    KnowledgeApproved,
)
from datapilot.loop3_events import improvement
from datapilot.loop3_events.api.events import DemoName, PlantedFlags, requested_flags

api = APIRouter()


def _with_flags(params: dict[str, Any], flags: str | None, demo: str | None) -> dict[str, Any]:
    """The request's params, with the planted flags of the demo the DataPilot-Demo header names,
    only its own (requested_flags)."""
    chosen = requested_flags(flags, demo)
    return {**params, planted.REQUESTED_KEY: chosen} if chosen else params


@api.post("/experiments/run", response_model=ImprovementRequestOut)
def run_experiment(
    body: ExperimentIn, flags: PlantedFlags = None, demo: DemoName = None
) -> ImprovementRequestOut:
    params = _with_flags(body.model_dump(exclude={"requested_by"}), flags, demo)
    with db.connect(db.Role.APP) as conn:
        row = improvement.enqueue(conn, "experiment", params, requested_by=body.requested_by)
        conn.commit()
    return ImprovementRequestOut.model_validate(row)


@api.post("/analyzer/run", response_model=ImprovementRequestOut)
def run_analyzer(
    body: AnalyzerIn, flags: PlantedFlags = None, demo: DemoName = None
) -> ImprovementRequestOut:
    params = _with_flags({}, flags, demo)
    with db.connect(db.Role.APP) as conn:
        row = improvement.enqueue(conn, "analyzer", params, requested_by=body.requested_by)
        conn.commit()
    return ImprovementRequestOut.model_validate(row)


@api.post("/knowledge/{version}/approve", response_model=KnowledgeApproved)
def approve_knowledge(version: str, body: KnowledgeApprovalIn) -> KnowledgeApproved:
    """The human approval the promotion gate needs; activation is the gate's step."""
    with db.connect(db.Role.APP) as conn:
        row = conn.execute(
            "UPDATE ops.knowledge_versions SET status = 'approved', approved_by = %s, "
            "approved_at = now() WHERE pack = %s AND version = %s AND status = 'draft' "
            "RETURNING version, status, approved_by, approved_at",
            (body.approved_by, active_pack(), version),
        ).fetchone()
        if row is None:
            found = conn.execute(
                "SELECT status FROM ops.knowledge_versions WHERE pack = %s AND version = %s",
                (active_pack(), version),
            ).fetchone()
            if found is None:
                raise HTTPException(404, f"no knowledge version {version}")
            raise HTTPException(409, f"version {version} is {found['status']}, not draft")
        conn.commit()
    return KnowledgeApproved.model_validate(row)


@api.get("/improvement/requests", response_model=ImprovementRequestList)
def list_requests(all_sessions: bool = False, limit: int = 50) -> ImprovementRequestList:
    """Experiment and analyzer requests of the open session, newest first."""
    with db.connect(db.Role.APP) as conn:
        rows = conn.execute(
            "SELECT request_id, kind, params, status, session_id, requested_by, requested_at, "
            "started_at, finished_at, result FROM ops.improvement_requests "
            "WHERE %s OR session_id = (SELECT session_id FROM ops.live_sessions "
            "WHERE ended_at IS NULL) ORDER BY requested_at DESC LIMIT %s",
            (all_sessions, limit),
        ).fetchall()
    return ImprovementRequestList(requests=[ImprovementRequestOut.model_validate(r) for r in rows])
