"""Human controls: approvals, the kill switch, the autonomy level, and the demo restart control.

Models: datapilot.contracts.api (ApprovalIn -> ApprovalDecided, ControlState, ConsoleSettings,
KillSwitchIn -> KillSwitchState, AutonomyIn -> AutonomyState, RestartRequested).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from datapilot import business_date, db
from datapilot.business_date import today as business_day
from datapilot.config import pack_config
from datapilot.contracts import AutonomyLevel, RunStatus
from datapilot.contracts.api import (
    ApprovalDecided,
    ApprovalIn,
    AutonomyIn,
    AutonomyState,
    ConsoleSettings,
    ControlState,
    KillSwitchIn,
    KillSwitchState,
    RestartRequested,
)
from datapilot.loop3_events import approvals, killswitch, lifecycle
from datapilot.settings import get_settings

api = APIRouter()

# The worker commits a run's awaiting_approval status before it parks the job, so an approval can
# land while the job is still running: requeue it then too. Its worker's fenced finish then matches
# no row and the run resumes on the next claim, instead of staying parked with nothing to wake it.
REQUEUE_SQL = (
    "UPDATE ops.jobs SET status = 'queued', run_after = now(), attempts = 0, lease_owner = NULL, "
    "lease_until = NULL, updated_at = now() "
    "WHERE event_id = (SELECT event_id FROM ops.runs WHERE run_id = %s) "
    "AND status IN ('parked', 'running')"
)
CLOSE_SQL = (
    "UPDATE ops.jobs SET status = 'done', updated_at = now() "
    "WHERE event_id = (SELECT event_id FROM ops.runs WHERE run_id = %s) AND status = 'parked'"
)


@api.post("/approvals/{run_id}", response_model=ApprovalDecided)
def decide(run_id: str, body: ApprovalIn) -> ApprovalDecided:
    with db.connect(db.Role.APP) as conn:
        try:
            status = lifecycle.current_status(conn, run_id, lock=True)
        except KeyError as error:
            raise HTTPException(404, str(error)) from error
        if status is not RunStatus.AWAITING_APPROVAL:
            raise HTTPException(409, f"run {run_id} is {status.value}, not awaiting approval")
        try:
            kind = approvals.decide(
                conn, run_id, body.decision, by=body.decided_by, comment=body.comment
            )
        except approvals.NoOpenApproval as error:
            raise HTTPException(409, str(error)) from error
        if body.decision == "reject":
            by = f"api: POST /approvals/{run_id} reject"
            lifecycle.transition(conn, run_id, RunStatus.REJECTED, by=by)
            conn.execute(CLOSE_SQL, (run_id,))
        else:
            if kind == "held_answer":
                lifecycle.transition(
                    conn, run_id, RunStatus.ANSWERED, by="api: approval of a held answer"
                )
            conn.execute(REQUEUE_SQL, (run_id,))  # the worker resumes or posts the run
        conn.commit()
        new = lifecycle.current_status(conn, run_id)
    return ApprovalDecided(run_id=run_id, decision=body.decision, kind=kind, status=new)


@api.get("/control", response_model=ControlState)
def control() -> ControlState:
    """The status line: the kill switch (an armed switch disarms itself), the autonomy level."""
    with db.connect(db.Role.APP) as conn:
        row = conn.execute(
            "SELECT kill_switch, autonomy_level, changed_at, changed_by, reason, "
            "worker_restart_requested_at FROM ops.control WHERE id = 1"
        ).fetchone()
        row["kill_switch"] = killswitch.state(conn)
    row["autonomy_label"] = AutonomyLevel(row["autonomy_level"]).label
    return ControlState.model_validate(row)


@api.get("/console/settings", response_model=ConsoleSettings)
def console_settings() -> ConsoleSettings:
    """What the console needs from pack.yaml (console:) and the business date."""
    return ConsoleSettings(
        **pack_config()["console"],
        business_date=business_day(),
        business_date_label=business_date.status_label(),
    )


@api.post("/control/kill-switch", response_model=KillSwitchState)
def kill_switch(body: KillSwitchIn) -> KillSwitchState:
    with db.connect(db.Role.APP) as conn:
        try:
            state = killswitch.set_state(conn, body.action, by=body.by)
        except killswitch.KillSwitchRefused as error:
            raise HTTPException(409, str(error)) from error
        conn.commit()
    return KillSwitchState(kill_switch=state)


@api.post("/control/autonomy", response_model=AutonomyState)
def set_autonomy(body: AutonomyIn) -> AutonomyState:
    with db.connect(db.Role.APP) as conn:
        if killswitch.state(conn) == "engaged":
            raise HTTPException(409, "release the kill switch before changing the autonomy level")
        conn.execute(
            "UPDATE ops.control SET autonomy_level = %s, changed_at = now(), changed_by = %s, "
            "reason = 'set by a human' WHERE id = 1",
            (body.level.value, body.by),
        )
        conn.commit()
    return AutonomyState(autonomy_level=body.level, label=body.level.label)


@api.post("/control/restart-worker", response_model=RestartRequested)
def restart_worker() -> RestartRequested:
    if not get_settings().datapilot_allow_demo_controls:
        raise HTTPException(403, "demo controls are off (DATAPILOT_ALLOW_DEMO_CONTROLS)")
    with db.connect(db.Role.APP) as conn:
        row = conn.execute(
            "UPDATE ops.control SET worker_restart_requested_at = now() WHERE id = 1 "
            "RETURNING worker_restart_requested_at AS restart_requested_at"
        ).fetchone()
        conn.commit()
    return RestartRequested.model_validate(row)
