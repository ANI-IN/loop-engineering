"""The api contract: every request and response model of the DataPilot api, defined once.

The api routers (datapilot.loop3_events.api) and the console's client both import these models,
and ENDPOINTS lists every endpoint with its models, so the console client and the contract test
(the integration test named test_api_contract) read one table. Responses forbid unknown fields,
so any drift between the api and this module fails the contract test.

Times are UTC ISO 8601 strings with an offset; the console formats them in the browser.

| Method | Path | Request | Response | What it does |
|---|---|---|---|---|
| GET | /health | - | Health | the process answers and the ops schema is reachable |
| POST | /events | EventIn | EventSubmitted | one event in, at most once; duplicates are absorbed |
| GET | /runs | - | RunList | the open session's runs, newest first (all_sessions, limit) |
| GET | /runs/{run_id} | - | RunDetail | one run with its run events, approvals, and posts |
| GET | /sessions/current | - | SessionOut | the open live session (404 when none is open) |
| POST | /approvals/{run_id} | ApprovalIn | ApprovalDecided | approve or reject a held run |
| GET | /control | - | ControlState | kill switch, autonomy level, and why |
| POST | /control/kill-switch | KillSwitchIn | KillSwitchState | arm, engage, or release |
| POST | /control/autonomy | AutonomyIn | AutonomyState | set the level (409 while engaged) |
| POST | /control/restart-worker | - | RestartRequested | demo control (403 unless enabled) |
| GET | /console/settings | - | ConsoleSettings | pack console limits and the business date |
| POST | /experiments/run | ExperimentIn | ImprovementRequestOut | enqueue an experiment |
| POST | /analyzer/run | AnalyzerIn | ImprovementRequestOut | enqueue the analyzer team |
| GET | /improvement/requests | - | ImprovementRequestList | the open session's requests |
| POST | /knowledge/{version}/approve | KnowledgeApprovalIn | KnowledgeApproved | approve a draft |
| POST | /demo/large-query | - | EventSubmitted | the unbounded rows demo question |
| POST | /demo/malicious-sql | - | EventSubmitted | the defense layers on malicious SQL |
| POST | /demo/cartesian-query | - | EventSubmitted | the cost guard on a cartesian join |
| POST | /demo/failing-grader | - | EventSubmitted | a question with the injected failing grader |
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from datapilot.contracts.autonomy import AutonomyLevel
from datapilot.contracts.lifecycle import EventType, RunEventKind, RunStatus
from datapilot.contracts.live import SessionPurpose


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Response(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- requests ---------------------------------------------------------------------------------
class EventIn(Request):
    event_id: str = Field(min_length=1, max_length=200)
    type: EventType
    source: str = "api"
    payload: dict[str, Any] = Field(default_factory=dict)


class ApprovalIn(Request):
    decision: Literal["approve", "reject"]  # never edit: the approver releases or refuses
    decided_by: str = "console"
    comment: str = ""


class KillSwitchIn(Request):
    action: Literal["arm", "engage", "release"]
    by: str = "console"


class AutonomyIn(Request):
    level: AutonomyLevel
    by: str = "console"


class ExperimentIn(Request):
    knowledge_version: str | None = None  # None: the version named by target
    target: Literal["active", "candidate"] = "active"
    plus_rule: str | None = None  # a pre-authored rule added to the target (the over-broad rule)
    split: Literal["dev", "holdout", "all"] = "all"
    requested_by: str = "console"


class AnalyzerIn(Request):
    requested_by: str = "console"


REFUSED_APPROVERS = frozenset({"", "console"})


def approver_name(name: str | None) -> str | None:
    """The person's name an approval records, or None: an empty name or "console" approves nothing
    (owner's decision, 27 October 2026). A production system takes a signed-in identity instead."""
    cleaned = (name or "").strip()
    return None if cleaned.casefold() in REFUSED_APPROVERS else cleaned


class KnowledgeApprovalIn(Request):
    approved_by: str  # no default: the console asks the approver for their name

    @field_validator("approved_by")
    @classmethod
    def _a_persons_name(cls, value: str) -> str:
        named = approver_name(value)
        if named is None:
            raise ValueError("the approval needs a person's name, not an empty name or 'console'")
        return named


# --- responses --------------------------------------------------------------------------------
class Health(Response):
    status: Literal["ok"]


class EventSubmitted(Response):
    event_id: str
    run_id: UUID
    job_id: int | None
    duplicate: bool
    duplicates_ignored: int
    created_at: datetime


class LiveStampOut(Response):
    """contracts.live.LiveStamp.to_browser()."""

    run_id: UUID
    started_at_utc: str
    trace_url: str | None


class SessionOut(Response):
    session_id: UUID
    purpose: SessionPurpose
    started_at: datetime
    started_by: str
    timezone: str
    started_at_utc: str


class RunSummary(Response):
    run_id: UUID
    event_id: str | None
    session_id: UUID | None
    demo_name: str | None
    question: str | None
    metric_family: str | None
    status: RunStatus
    autonomy_level_applied: AutonomyLevel | None
    knowledge_version: str | None
    model: str | None
    planted_active: list[str]
    tokens_in: int
    tokens_out: int
    cost_usd: float
    langsmith_url: str | None
    # when LangSmith refused the run's trace for its monthly limit, as the worker saw it
    trace_refused_at: datetime | None = None
    answer: dict[str, Any] | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    duplicates_ignored: int
    live_stamp: LiveStampOut | None


class RunList(Response):
    session: SessionOut | None
    runs: list[RunSummary]


class RunEvent(Response):
    id: int
    ts: datetime
    kind: RunEventKind
    payload: dict[str, Any]


class ApprovalRecord(Response):
    approval_id: int
    kind: Literal["tool_call", "held_answer"]
    requested_at: datetime
    action: str
    sql: str | None
    row_estimate: int | None
    reason: str
    decision: Literal["approve", "reject"] | None
    decided_by: str | None
    decided_at: datetime | None
    comment: str | None


class PostRecord(Response):
    post_id: int
    channel: str
    label: str
    body: dict[str, Any]
    posted_at: datetime


class RunDetail(RunSummary):
    events: list[RunEvent]
    approvals: list[ApprovalRecord]
    posts: list[PostRecord]


class ApprovalDecided(Response):
    run_id: UUID
    decision: Literal["approve", "reject"]
    kind: Literal["tool_call", "held_answer"]
    status: RunStatus


class ControlState(Response):
    kill_switch: Literal["released", "armed", "engaged"]
    autonomy_level: AutonomyLevel
    autonomy_label: str
    changed_at: datetime
    changed_by: str
    reason: str | None
    worker_restart_requested_at: datetime | None


class KillSwitchState(Response):
    kill_switch: Literal["released", "armed", "engaged"]


class AutonomyState(Response):
    autonomy_level: AutonomyLevel
    label: str


class RestartRequested(Response):
    restart_requested_at: datetime


class ConsoleSettings(Response):
    kill_switch_disarm_seconds: float
    strips_per_lane: int
    poll_seconds: float
    business_date: date
    business_date_label: str


class ImprovementRequestOut(Response):
    request_id: UUID
    kind: Literal["experiment", "analyzer"]
    params: dict[str, Any]
    status: Literal["queued", "running", "done", "failed"]
    session_id: UUID | None
    requested_by: str
    requested_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: dict[str, Any] | None = None


class ImprovementRequestList(Response):
    requests: list[ImprovementRequestOut]


class KnowledgeApproved(Response):
    version: str
    status: Literal["approved"]
    approved_by: str
    approved_at: datetime


# --- the endpoint table -------------------------------------------------------------------------
@dataclass(frozen=True)
class Endpoint:
    method: Literal["GET", "POST"]
    path: str  # FastAPI form, such as /runs/{run_id}
    request: type[Request] | None
    response: type[Response]
    summary: str


ENDPOINTS: tuple[Endpoint, ...] = (
    Endpoint("GET", "/health", None, Health, "the process answers"),
    Endpoint("POST", "/events", EventIn, EventSubmitted, "submit one event, at most once"),
    Endpoint("GET", "/runs", None, RunList, "the open session's runs"),
    Endpoint("GET", "/runs/{run_id}", None, RunDetail, "one run in full"),
    Endpoint("GET", "/sessions/current", None, SessionOut, "the open live session"),
    Endpoint("POST", "/approvals/{run_id}", ApprovalIn, ApprovalDecided, "approve or reject"),
    Endpoint("GET", "/control", None, ControlState, "the status line"),
    Endpoint("POST", "/control/kill-switch", KillSwitchIn, KillSwitchState, "the kill switch"),
    Endpoint("POST", "/control/autonomy", AutonomyIn, AutonomyState, "the autonomy level"),
    Endpoint("POST", "/control/restart-worker", None, RestartRequested, "restart the worker"),
    Endpoint("GET", "/console/settings", None, ConsoleSettings, "console limits, business date"),
    Endpoint("POST", "/experiments/run", ExperimentIn, ImprovementRequestOut, "an experiment"),
    Endpoint("POST", "/analyzer/run", AnalyzerIn, ImprovementRequestOut, "the analyzer team"),
    Endpoint("GET", "/improvement/requests", None, ImprovementRequestList, "requests"),
    Endpoint(
        "POST", "/knowledge/{version}/approve", KnowledgeApprovalIn, KnowledgeApproved, "approve"
    ),
    Endpoint("POST", "/demo/large-query", None, EventSubmitted, "the unbounded rows demo"),
    Endpoint("POST", "/demo/malicious-sql", None, EventSubmitted, "the malicious SQL demo"),
    Endpoint("POST", "/demo/cartesian-query", None, EventSubmitted, "the cost guard demo"),
    Endpoint("POST", "/demo/failing-grader", None, EventSubmitted, "the retry cap demo"),
)


def endpoint(method: str, path: str) -> Endpoint:
    """The table entry for a concrete request path, such as ("GET", "/runs/1234")."""
    parts = path.split("?")[0].strip("/").split("/")
    for entry in ENDPOINTS:
        pattern = entry.path.strip("/").split("/")
        if entry.method != method.upper() or len(pattern) != len(parts):
            continue
        if all(p == q or p.startswith("{") for p, q in zip(pattern, parts, strict=True)):
            return entry
    raise KeyError(f"no endpoint {method} {path} in datapilot.contracts.api.ENDPOINTS")
