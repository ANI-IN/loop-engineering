"""The run lifecycle and the run-event kinds: the contract between every loop and the console.

Each transition lists the component that writes it. ops.runs.status and ops.run_events kinds are
constrained to these values by migration 001 (a test keeps the SQL and this module equal).
"""

from __future__ import annotations

from enum import StrEnum


class RunStatus(StrEnum):
    RECEIVED = "received"
    QUEUED = "queued"
    RUNNING = "running"
    VERIFYING = "verifying"
    AWAITING_APPROVAL = "awaiting_approval"
    ANSWERED = "answered"
    POSTED = "posted"
    REJECTED = "rejected"
    FAILED = "failed"
    ESCALATED = "escalated"
    BLOCKED_BUDGET = "blocked_budget"
    BLOCKED_KILLSWITCH = "blocked_killswitch"


TERMINAL: frozenset[RunStatus] = frozenset(
    {
        RunStatus.POSTED,
        RunStatus.REJECTED,
        RunStatus.FAILED,
        RunStatus.ESCALATED,
        RunStatus.BLOCKED_BUDGET,
        RunStatus.BLOCKED_KILLSWITCH,
    }
)

# (from, to) -> the component that writes the transition.
TRANSITIONS: dict[tuple[RunStatus, RunStatus], str] = {
    (RunStatus.RECEIVED, RunStatus.QUEUED): "api: POST /events, with the job row",
    (RunStatus.QUEUED, RunStatus.RUNNING): "worker: claim",
    (RunStatus.QUEUED, RunStatus.BLOCKED_BUDGET): "worker: budget check before claim",
    (RunStatus.QUEUED, RunStatus.BLOCKED_KILLSWITCH): "worker: kill switch check at claim",
    (RunStatus.RUNNING, RunStatus.QUEUED): "reaper: expired lease, attempts left",
    (RunStatus.RUNNING, RunStatus.VERIFYING): "worker: agent returned an answer envelope",
    (RunStatus.RUNNING, RunStatus.AWAITING_APPROVAL): "worker: human approval interrupt",
    (RunStatus.RUNNING, RunStatus.ESCALATED): "worker: retry, call, or token limit reached",
    (RunStatus.RUNNING, RunStatus.FAILED): "worker or reaper: error, or attempts exhausted",
    (RunStatus.RUNNING, RunStatus.BLOCKED_BUDGET): "worker: token budget exhausted mid-run",
    (RunStatus.RUNNING, RunStatus.BLOCKED_KILLSWITCH): "worker: kill switch before a model call",
    (RunStatus.VERIFYING, RunStatus.RUNNING): "worker: a grader failed, retry within the cap",
    (RunStatus.VERIFYING, RunStatus.ANSWERED): "worker: every grader passed",
    (RunStatus.VERIFYING, RunStatus.AWAITING_APPROVAL): "worker: reviewer concern persists",
    (RunStatus.VERIFYING, RunStatus.ESCALATED): "worker: final-answer grader failed at the cap",
    (RunStatus.VERIFYING, RunStatus.BLOCKED_KILLSWITCH): "worker: kill switch while verifying",
    (RunStatus.VERIFYING, RunStatus.FAILED): "worker or reaper: error while verifying",
    (RunStatus.AWAITING_APPROVAL, RunStatus.RUNNING): "worker: approval resumed the run",
    (RunStatus.AWAITING_APPROVAL, RunStatus.ANSWERED): "api: approval of a held answer",
    (RunStatus.AWAITING_APPROVAL, RunStatus.REJECTED): "api: POST /approvals/{run_id} reject",
    (RunStatus.AWAITING_APPROVAL, RunStatus.BLOCKED_KILLSWITCH): "api: kill switch engaged",
    (RunStatus.ANSWERED, RunStatus.POSTED): "worker: posted to the channel per autonomy policy",
    (RunStatus.ANSWERED, RunStatus.AWAITING_APPROVAL): "worker: autonomy policy needs approval",
}


def can_transition(current: RunStatus, new: RunStatus) -> bool:
    return (current, new) in TRANSITIONS


class RunEventKind(StrEnum):
    STATUS_CHANGED = "status_changed"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_FINISHED = "tool_call_finished"
    GRADER_RESULT = "grader_result"
    REVIEWER_VERDICT = "reviewer_verdict"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_DECIDED = "approval_decided"
    BUDGET_BLOCKED = "budget_blocked"
    KILLSWITCH_BLOCKED = "killswitch_blocked"


class EventType(StrEnum):
    QUESTION_ASKED = "question.asked"
    DIGEST_REQUESTED = "digest.requested"
    EXPORT_REQUESTED = "export.requested"
