"""Hill-climbing requests (enqueue only) and the human approval of a knowledge version.

Models: datapilot.contracts.api (ExperimentIn and AnalyzerIn -> ImprovementRequestOut,
ImprovementRequestList, KnowledgeApprovalIn -> KnowledgeApproved).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from datapilot import db
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

api = APIRouter()


@api.post("/experiments/run", response_model=ImprovementRequestOut)
def run_experiment(body: ExperimentIn) -> ImprovementRequestOut:
    params = body.model_dump(exclude={"requested_by"})
    with db.connect(db.Role.APP) as conn:
        row = improvement.enqueue(conn, "experiment", params, requested_by=body.requested_by)
        conn.commit()
    return ImprovementRequestOut.model_validate(row)


@api.post("/analyzer/run", response_model=ImprovementRequestOut)
def run_analyzer(body: AnalyzerIn) -> ImprovementRequestOut:
    with db.connect(db.Role.APP) as conn:
        row = improvement.enqueue(conn, "analyzer", {}, requested_by=body.requested_by)
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
