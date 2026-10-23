"""The kill switch: a guarded control (arm, then engage) that stops every run.

It is checked at claim, before every model call (a before_model jump to end), and before every tool
call (a short-circuit with a ToolMessage). Engaging it ends in-flight runs as blocked by the kill
switch, blocks runs waiting for approval, and drops the system to the report-only level, which
stays until a human raises it again after release.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Literal

import psycopg
from langchain.agents.middleware import AgentMiddleware, hook_config

from datapilot import db
from datapilot.config import pack_config
from datapilot.contracts import DemotionReason, RunEventKind, RunStatus
from datapilot.loop1_agent.guard import RunGuard, StopReason, stopped_message
from datapilot.loop3_events import autonomy, lifecycle
from datapilot.planted import planted

Action = Literal["arm", "engage", "release"]
_NEXT: dict[Action, tuple[set[str], str]] = {
    "arm": ({"released"}, "armed"),
    "engage": ({"armed"}, "engaged"),
    "release": ({"released", "armed", "engaged"}, "released"),
}


class KillSwitchRefused(RuntimeError):
    pass


def state(conn: psycopg.Connection[Any]) -> str:
    """The switch state; an armed switch counts as released once pack.yaml
    console.kill_switch_disarm_seconds pass without an engage."""
    row = conn.execute(
        "SELECT kill_switch, now() - changed_at > make_interval(secs => %s) AS stale "
        "FROM ops.control WHERE id = 1",
        (float(pack_config()["console"]["kill_switch_disarm_seconds"]),),
    ).fetchone()
    if row["kill_switch"] == "armed" and row["stale"]:
        return "released"
    return str(row["kill_switch"])


def engaged() -> bool:
    with db.connect(db.Role.APP) as conn:
        return state(conn) == "engaged"


def set_state(conn: psycopg.Connection[Any], action: Action, *, by: str) -> str:
    allowed, new = _NEXT[action]
    current = state(conn)
    if current not in allowed:
        raise KillSwitchRefused(f"cannot {action} the kill switch while it is {current}")
    conn.execute(
        "UPDATE ops.control SET kill_switch = %s, changed_at = now(), changed_by = %s, "
        "reason = %s WHERE id = 1",
        (new, by, f"kill switch {action}"),
    )
    if new == "engaged":
        autonomy.demote(conn, DemotionReason.KILL_SWITCH, by=by)
        held = conn.execute(
            "SELECT run_id FROM ops.runs WHERE status = 'awaiting_approval'"
        ).fetchall()
        for row in held:
            run_id = str(row["run_id"])
            lifecycle.transition(conn, run_id, RunStatus.BLOCKED_KILLSWITCH, by="api: kill switch")
            lifecycle.record(conn, run_id, RunEventKind.KILLSWITCH_BLOCKED, {"at": "approval"})
            conn.execute(
                "UPDATE ops.jobs SET status = 'done', updated_at = now() WHERE event_id = "
                "(SELECT event_id FROM ops.runs WHERE run_id = %s) AND status = 'parked'",
                (run_id,),
            )
    return new


class KillSwitchMiddleware(AgentMiddleware):
    """Stops the agent loop at its next model or tool call once the switch is engaged."""

    def __init__(self, guard: RunGuard, is_engaged: Callable[[], bool] = engaged) -> None:
        super().__init__()
        self.guard = guard
        self.is_engaged = is_engaged

    def _check(self) -> bool:
        if planted("BUG_KILLSWITCH_AT_CLAIM_ONLY"):
            return False  # planted: the switch is checked at claim only, never in flight
        if self.is_engaged():
            self.guard.stop(StopReason.KILL_SWITCH, "the kill switch is engaged")
            return True
        return False

    @hook_config(can_jump_to=["end"])
    def before_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        return {"jump_to": "end"} if self._check() else None

    @hook_config(can_jump_to=["end"])
    async def abefore_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        return self.before_model(state, runtime)

    def wrap_tool_call(self, request: Any, handler: Callable[[Any], Any]) -> Any:
        if self._check():
            return stopped_message(request, "Run stopped: the kill switch is engaged.")
        return handler(request)

    async def awrap_tool_call(self, request: Any, handler: Callable[[Any], Awaitable[Any]]) -> Any:
        if self._check():
            return stopped_message(request, "Run stopped: the kill switch is engaged.")
        return await handler(request)
