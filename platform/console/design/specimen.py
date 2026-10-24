"""Specimen data for the style tile only, shaped like ops.runs and ops.run_events.

No console page imports this module: pages show only live runs of the open live session
(datapilot.contracts.live). This data exists to draw the design, never to stand in for a demo.

Nothing here touches a database or a model. `seed_board()` gives a board with a strip in every
lane; `next_event(tick, ...)` appends one stub event per second so a strip moves across the board.
The console pages read the same shapes from Postgres in the next milestone.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

import yaml

from datapilot.contracts.lifecycle import RunEventKind, RunStatus
from datapilot.contracts.live import LiveSession, LiveStamp, SessionPurpose
from datapilot.settings import PLATFORM

_NAMESPACE = uuid.UUID("6f1d2c4e-0000-4000-8000-00000000d351")
TRACE_BASE = "https://smith.langchain.com/o/specimen/projects/p/datapilot"


def run_id(name: str) -> str:
    """A stable uuid per specimen run, so strip identity survives reruns."""
    return str(uuid.uuid5(_NAMESPACE, name))


def new_session() -> LiveSession:
    return LiveSession(
        session_id=uuid.uuid5(_NAMESPACE, "session"),
        purpose=SessionPurpose.REHEARSAL,
        started_at=datetime.now(UTC) - timedelta(minutes=12),
        started_by="instructor",
        timezone="UTC",
    )


def trace_list_url(knowledge_version: str) -> str:
    """The LangSmith trace list filtered by knowledge version (never a comparison view)."""
    flt = f'and(eq(metadata_key, "knowledge_version"), eq(metadata_value, "{knowledge_version}"))'
    return f"{TRACE_BASE}?filter={quote(flt)}"


@dataclass
class SpecimenRun:
    run_id: str
    question: str
    metric_family: str
    status: RunStatus = RunStatus.RECEIVED
    step: str = ""
    duplicates_absorbed: int = 0
    tokens: int = 0
    approval: dict[str, Any] | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def stamp(self, session: LiveSession) -> dict[str, str | None]:
        """The live stamp as the components receive it: a UTC ISO time and the trace link."""
        return LiveStamp(
            run_id=uuid.UUID(self.run_id),
            session_id=session.session_id,
            started_at=self.started_at,
            trace_url=f"{TRACE_BASE}/r/{self.run_id}",
        ).to_browser()


def _event(event_id: int, run: str, kind: RunEventKind, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": event_id,
        "run_id": run,
        "ts": datetime.now(UTC).isoformat(timespec="seconds"),
        "kind": str(kind),
        "payload": payload,
    }


EXPORT_SQL = (
    "SELECT c.customer_id, c.email, c.first_name, c.city\n"
    "FROM warehouse.customers_marketable AS c\n"
    "WHERE c.state = 'CA'\n"
    "ORDER BY c.customer_id"
)

# Runs that sit still on the board: one per lane that a moving strip does not cover.
_STILL: list[tuple[str, str, str, RunStatus, dict[str, Any]]] = [
    (
        "export-ca",
        "Export the California customers who may receive marketing, with their email addresses.",
        "customers",
        RunStatus.AWAITING_APPROVAL,
        {"step": "412 rows of personal data"},
    ),
    ("digest", "Daily KPI digest", "revenue", RunStatus.POSTED, {"duplicates": 2}),
    (
        "orders-week",
        "Orders last week by state",
        "orders",
        RunStatus.BLOCKED_KILLSWITCH,
        {"step": "Stopped before the model call"},
    ),
    (
        "aov-q3",
        "Average order value in the third fiscal quarter",
        "revenue",
        RunStatus.FAILED,
        {"step": "Statement timeout"},
    ),
    (
        "top-skus",
        "Top 20 products by units",
        "products",
        RunStatus.BLOCKED_BUDGET,
        {"step": "Daily token budget reached"},
    ),
    (
        "refund-list",
        "Delete test orders",
        "orders",
        RunStatus.REJECTED,
        {"step": "Rejected at human approval"},
    ),
    (
        "cancel-rate",
        "Cancellation rate by month",
        "orders",
        RunStatus.ESCALATED,
        {"step": "Retry cap reached after 3 attempts"},
    ),
]

# The moving strip: one event per second, Queued to Done in six steps.
_CYCLE: list[tuple[RunEventKind, dict[str, Any]]] = [
    (RunEventKind.STATUS_CHANGED, {"from": "received", "to": "queued"}),
    (RunEventKind.STATUS_CHANGED, {"from": "queued", "to": "running"}),
    (RunEventKind.TOOL_CALL_STARTED, {"tool": "run_query"}),
    (RunEventKind.TOOL_CALL_FINISHED, {"tool": "run_query", "duration_ms": 840, "rows": 1}),
    (RunEventKind.STATUS_CHANGED, {"from": "running", "to": "verifying"}),
    (RunEventKind.GRADER_RESULT, {"grader": "final_answer", "passed": True}),
    (RunEventKind.STATUS_CHANGED, {"from": "verifying", "to": "answered"}),
    (RunEventKind.STATUS_CHANGED, {"from": "answered", "to": "posted"}),
]

_MOVING_QUESTIONS = [
    ("Net revenue in fiscal year 2025", "revenue"),
    ("New customers in October, Eastern time", "customers"),
    ("Orders shipped to Texas last fiscal quarter", "orders"),
]


@dataclass
class Board:
    runs: dict[str, SpecimenRun] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    tokens_today: int = 61_200

    def add(self, run: SpecimenRun) -> None:
        self.runs[run.run_id] = run
        self.order.append(run.run_id)

    def apply(self, event: dict[str, Any]) -> None:
        run = self.runs[event["run_id"]]
        kind, payload = event["kind"], event["payload"]
        if kind == RunEventKind.STATUS_CHANGED:
            run.status = RunStatus(payload["to"])
            run.step = ""
        elif kind == RunEventKind.TOOL_CALL_STARTED:
            run.step = payload["tool"]
            run.tokens += 900
            self.tokens_today += 900
        elif kind == RunEventKind.GRADER_RESULT:
            run.step = "Graders passed"
        elif kind == RunEventKind.KILLSWITCH_BLOCKED:
            run.status = RunStatus.BLOCKED_KILLSWITCH
            run.step = "Stopped at its next step"
        elif kind == RunEventKind.APPROVAL_DECIDED:
            run.approval = None
        run.events.append(event)
        self.events.append(event)


def seed_board() -> Board:
    board = Board()
    event_id = 1
    for name, question, family, status, extra in _STILL:
        run = SpecimenRun(run_id(name), question, family, status, step=extra.get("step", ""))
        run.started_at = datetime.now(UTC) - timedelta(minutes=10 - event_id)
        run.duplicates_absorbed = extra.get("duplicates", 0)
        if status is RunStatus.AWAITING_APPROVAL:
            run.approval = {
                "action": "Export 412 rows of personal data to the marketing list",
                "sql": EXPORT_SQL,
                "row_estimate": 412,
                "reason": "The result contains personal data: email and first name.",
            }
        board.add(run)
        board.apply(
            _event(
                event_id,
                run.run_id,
                RunEventKind.STATUS_CHANGED,
                {"from": "received", "to": str(status)},
            )
        )
        run.step = extra.get("step", "")
        event_id += 1
    return board


def next_event(board: Board, tick: int, *, kill_engaged: bool) -> dict[str, Any] | None:
    """The stub event for this second, already applied to the board. None while stopped."""
    cycle_index, step_index = divmod(tick, len(_CYCLE))
    name = f"moving-{cycle_index}"
    rid = run_id(name)
    event_id = len(board.events) + 1
    if kill_engaged:
        run = board.runs.get(rid)
        if run is None or run.status in {RunStatus.BLOCKED_KILLSWITCH, RunStatus.POSTED}:
            return None
        event = _event(event_id, rid, RunEventKind.KILLSWITCH_BLOCKED, {"at": run.step or "claim"})
        board.apply(event)
        return event
    if rid not in board.runs:
        question, family = _MOVING_QUESTIONS[cycle_index % len(_MOVING_QUESTIONS)]
        board.add(SpecimenRun(rid, question, family))
    run = board.runs[rid]
    if run.status in {RunStatus.BLOCKED_KILLSWITCH}:
        return None
    kind, payload = _CYCLE[step_index]
    event = _event(event_id, rid, kind, payload)
    board.apply(event)
    return event


def decide(board: Board, rid: str, decision: str) -> None:
    """Apply a human approval decision to the held run."""
    run = board.runs[rid]
    event_id = len(board.events) + 1
    board.apply(_event(event_id, rid, RunEventKind.APPROVAL_DECIDED, {"decision": decision}))
    target = RunStatus.RUNNING if decision == "approve" else RunStatus.REJECTED
    board.apply(
        _event(
            event_id + 1,
            rid,
            RunEventKind.STATUS_CHANGED,
            {"from": str(run.status), "to": str(target)},
        )
    )
    run.step = "Resumed after approval" if decision == "approve" else "Rejected at human approval"


# --- Annotated SQL: the confident wrong answer under knowledge version v1 ---------------------

WRONG_SQL = [
    "SELECT SUM(o.total_cents) / 100.0 AS net_revenue",
    "FROM warehouse.orders AS o",
    "JOIN warehouse.customers AS c ON c.customer_id = o.customer_id",
    "WHERE o.order_ts >= '2025-01-01'",
    "  AND o.order_ts <  '2026-01-01'",
]

# Each note names one trap and marks every fragment it explains: (line index, exact text).
WRONG_SQL_NOTES = [
    {
        "trap": "Net revenue",
        "marks": [(0, "o.total_cents")],
        "text": "total_cents includes tax and shipping. Net revenue is subtotal minus discount.",
    },
    {
        "trap": "Internal accounts",
        "marks": [(2, "JOIN warehouse.customers AS c")],
        "text": "The join adds no filter, so internal accounts (email at harborpine.com) stay in.",
    },
    {
        "trap": "Cancelled orders",
        "marks": [(3, "WHERE")],
        "text": "No filter on status, so cancelled orders (status 5) stay in the total.",
    },
    {
        "trap": "Eastern time",
        "marks": [(3, "o.order_ts"), (4, "o.order_ts")],
        "text": "order_ts is stored in UTC. Convert it to Eastern time before comparing dates.",
    },
    {
        "trap": "Fiscal year",
        "marks": [(3, "'2025-01-01'"), (4, "'2026-01-01'")],
        "text": "Fiscal year 2025 runs from February 1, 2024 to January 31, 2025, not the "
        "calendar year.",
    },
]

# --- Holdout ledger: knowledge version v1 against the candidate ---------------------------------
# Real holdout items (platform/packs/datapilot_us/benchmark/holdout.yaml); the pass counts out of
# 3 runs are specimen values: (item id, baseline passes, candidate passes).

HOLDOUT_FILE = PLATFORM / "packs" / "datapilot_us" / "benchmark" / "holdout.yaml"

_LEDGER_PASSES = [
    ("net-revenue-fiscal-2026", 0, 3),
    ("business-day-orders-november-2025", 1, 3),
    ("app-average-order-value-fiscal-2026", 0, 2),
    ("top-customers-fiscal-2026", 0, 3),
    ("average-list-price-active", 3, 3),
    ("orders-black-friday-2025", 3, 1),
    ("web-orders-calendar-2024", 2, 2),
]


def holdout_questions() -> dict[str, str]:
    items = yaml.safe_load(HOLDOUT_FILE.read_text(encoding="utf-8"))
    return {item["id"]: " ".join(item["question"].split()) for item in items}


def ledger_rows() -> list[tuple[str, str, int | None, int | None]]:
    questions = holdout_questions()
    return [(item, questions[item], a, c) for item, a, c in _LEDGER_PASSES]


# --- The grouped benchmark strip ----------------------------------------------------------------
# A baseline benchmark is 25 dev items run once and 15 holdout items run 3 times: 70 runs.

BENCHMARK_TOTAL = 70
BENCHMARK_START = 41


def benchmark_rows(done: int) -> list[tuple[str, str, int | None, int | None]]:
    """Holdout rows of a running baseline benchmark: items fill in as their runs finish."""
    finished_items = (done - 25) // 3 if done > 25 else 0
    rows: list[tuple[str, str, int | None, int | None]] = []
    for index, (item, question) in enumerate(holdout_questions().items()):
        passes = (index * 7) % 4 if index < finished_items else None
        rows.append((item, question, passes, None))
    return rows
