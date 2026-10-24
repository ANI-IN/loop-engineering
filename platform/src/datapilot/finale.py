"""The finale's starting state, one rule for `make demo NAME=improve-cleared-unattended` and the
console's Events > Send webhook question. Outside the loop packages, because the console never
imports a loop package.

The finale (Cleared for the unattended level) must run under the version the gate just promoted,
with the system at the unattended level and the kill switch released. Approval only marks a version
approved: the hill-climbing runner then runs the clearance re-runs and makes it active, which takes
minutes. A finale sent before that answers under the previous version. A finale sent at the
report-only level posts labelled unverified, whatever its family cleared, and the kill switch
blocks every run it meets. Each of the three is refused here with the step that fixes it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import psycopg

FINALE_DEMO = "improve-cleared-unattended"
UNATTENDED = "unattended"
SET_UNATTENDED = (
    'Improve > Set the unattended level, or make autonomy LEVEL=unattended BY="<your name>"'
)

# The end of the wait, whether a family cleared or none did: the hold ends by itself.
UNTIL_CLEARED = (
    "The wait ends when the re-runs finish: Send webhook question turns on (and make demo sends "
    "the finale), and the status line names each family cleared or, when none cleared, reads "
    "Not cleared for every family, and the finale posts at the assisted level."
)

# The runner holds this advisory lock (a fixed key no other code uses) while it runs the clearance
# re-runs of a version it has just made active: the activation commits first, and the families it
# clears are written only after those re-runs (runner.activate).
CLEARING_LOCK = 2_026_102_405

# The newest version approved in the open live session with no gate decision on its approval (the
# runner has not decided it yet), the active version while its clearance re-runs still run, and the
# active version when the gate or the class-day safeguard promoted it in the open live session. A
# version approved in an earlier session waits for nothing here: the runner decides only on this
# session's experiments, so it could never decide it, and it would hold the finale's controls in
# every later session (review round 2). A version the gate blocked is retired
# (runner.save_decision).
STATE_SQL = """
SELECT c.kill_switch, c.autonomy_level,
       (SELECT k.version FROM ops.knowledge_versions k
        WHERE k.pack = %(pack)s AND k.status = 'approved'
          AND k.approved_at >= COALESCE(
              (SELECT started_at FROM ops.live_sessions WHERE ended_at IS NULL), '-infinity')
          AND NOT EXISTS (
              SELECT 1 FROM ops.promotion_decisions d
              WHERE d.pack = k.pack AND d.candidate_version = k.version
                AND d.approved_by IS NOT NULL
                AND d.decided_at >= COALESCE(
                    (SELECT started_at FROM ops.live_sessions WHERE ended_at IS NULL),
                    '-infinity'))
        ORDER BY k.approved_at DESC NULLS LAST, k.version DESC LIMIT 1) AS pending_promotion,
       (SELECT k.version FROM ops.knowledge_versions k
        WHERE k.pack = %(pack)s AND k.status = 'active'
          AND EXISTS (
              SELECT 1 FROM pg_locks l
              WHERE l.locktype = 'advisory' AND l.classid = 0 AND l.objid = %(clearing)s
                AND l.objsubid = 1 AND l.granted)) AS clearing,
       (SELECT k.version FROM ops.knowledge_versions k
        WHERE k.pack = %(pack)s AND k.status = 'active'
          AND EXISTS (
              SELECT 1 FROM ops.promotion_decisions d
              WHERE d.pack = k.pack AND d.candidate_version = k.version
                AND d.verdict = 'promoted'
                AND d.decided_at >= COALESCE(
                    (SELECT started_at FROM ops.live_sessions WHERE ended_at IS NULL),
                    'infinity'))) AS promoted
FROM ops.control c WHERE c.id = 1
"""


@dataclass(frozen=True)
class FinaleState:
    kill_switch: str
    autonomy_level: str
    pending_promotion: str | None
    clearing: str | None = None  # the active version, while its clearance re-runs still run
    promoted: str | None = None  # the active version, promoted in the open live session

    @property
    def finale_due(self) -> bool:
        """The finale is the demo being shown: a version is approved and waiting for its
        promotion, or was promoted in this live session (by the gate or the safeguard), whether
        or not a family cleared under it."""
        return bool(self.pending_promotion or self.clearing or self.promoted)


def read(conn: psycopg.Connection[Any], pack: str) -> FinaleState:
    row = conn.execute(STATE_SQL, {"pack": pack, "clearing": CLEARING_LOCK}).fetchone()
    if row is None:  # no control row: the migrations have not run
        return FinaleState("released", "report_only", None)
    return FinaleState(
        row["kill_switch"],
        row["autonomy_level"],
        row["pending_promotion"],
        row["clearing"],
        row.get("promoted"),
    )


def waiting_for_promotion(state: FinaleState) -> str | None:
    """Why nothing may be sent through the finale's control yet: an approved version whose
    promotion has not finished, or a promoted version whose clearance re-runs still run."""
    if state.clearing:
        return (
            f"{state.clearing} is the active version, and its clearance re-runs are still "
            f"running: the families it clears are written when they finish. {UNTIL_CLEARED}"
        )
    version = state.pending_promotion
    if version is None:
        return None
    return (
        f"{version} is approved, and its promotion has not finished: the hill-climbing runner "
        f"decides it, makes {version} the active version, then runs the clearance re-runs. "
        f"Wait until the Improve page says {version} is the active version. {UNTIL_CLEARED}"
    )


def refusal(state: FinaleState) -> str | None:
    """Why the finale may not be sent now, with the step that fixes it; None when it may."""
    waiting = waiting_for_promotion(state)
    if waiting:
        return waiting
    if state.kill_switch == "engaged":
        return (
            "The kill switch is engaged, so the finale would be blocked: release it (status line "
            "> Release kill switch, or make reset NAME=event-loop), then set the unattended level: "
            f"{SET_UNATTENDED}."
        )
    if state.autonomy_level != UNATTENDED:
        level = state.autonomy_level.replace("_", "-")
        return (
            f"The system is at the {level} level, so the finale would post at that level whatever "
            f"its family cleared: set the unattended level first, {SET_UNATTENDED}."
        )
    return None
