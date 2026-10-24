"""Test-level helpers that write ops rows the console reads: a live session, runs and their run
events, approvals, posts, experiments, knowledge versions, control, budgets, and clearance.

Only tests and the screenshot launch use these. The console itself never writes ops rows.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg

Conn = psycopg.Connection[Any]

WRONG_SQL = (
    "SELECT round(sum(o.total_cents) / 100.0, 2) AS net_revenue\n"
    "FROM warehouse.orders o\n"
    "WHERE o.order_ts >= '2025-01-01'\n"
    "  AND o.order_ts < '2026-01-01'"
)


def now() -> datetime:
    return datetime.now(UTC)


def open_session(conn: Conn, *, started_at: datetime | None = None) -> uuid.UUID:
    conn.execute("UPDATE ops.live_sessions SET ended_at = now() WHERE ended_at IS NULL")
    session_id = uuid.uuid4()
    conn.execute(
        "INSERT INTO ops.live_sessions (session_id, started_at, started_by, timezone, purpose) "
        "VALUES (%s, %s, 'test', 'UTC', 'development')",
        (session_id, started_at or now()),
    )
    return session_id


def end_sessions(conn: Conn) -> None:
    conn.execute("UPDATE ops.live_sessions SET ended_at = now() WHERE ended_at IS NULL")


def add_run(
    conn: Conn,
    session_id: uuid.UUID | None,
    status: str,
    *,
    question: str = "How many orders were placed?",
    demo_name: str | None = "events-webhook-question",
    event: bool = True,
    started_at: datetime | None = None,
    answer: dict[str, Any] | None = None,
    planted: list[str] | None = None,
    level: str | None = None,
    tokens: tuple[int, int] = (0, 0),
    trace_url: str | None = "https://smith.langchain.com/public/test-trace/r",
) -> uuid.UUID:
    run_id = uuid.uuid4()
    event_id = f"test:{run_id.hex[:12]}" if event else None
    if event_id:
        conn.execute(
            "INSERT INTO ops.events (event_id, source, type, payload) "
            "VALUES (%s, 'test', 'question.asked', '{}')",
            (event_id,),
        )
    started = started_at or now()
    conn.execute(
        "INSERT INTO ops.runs (run_id, event_id, demo_name, question, status, session_id, "
        "planted_active, autonomy_level_applied, tokens_in, tokens_out, cost_usd, langsmith_url, "
        "answer, created_at, started_at, finished_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0.004, %s, %s, %s, %s, %s)",
        (
            run_id,
            event_id,
            demo_name,
            question,
            status,
            session_id,
            PLANTED if planted is None else planted,
            level,
            tokens[0],
            tokens[1],
            trace_url,
            json.dumps(answer) if answer is not None else None,
            started,
            started,
            started + timedelta(seconds=6.2)
            if status in {"answered", "posted", "failed"}
            else None,
        ),
    )
    add_event(conn, run_id, "status_changed", {"from": None, "to": status, "by": "test"})
    return run_id


def add_event(conn: Conn, run_id: uuid.UUID, kind: str, payload: dict[str, Any]) -> None:
    conn.execute(
        "INSERT INTO ops.run_events (run_id, kind, payload) VALUES (%s, %s, %s)",
        (run_id, kind, json.dumps(payload)),
    )


def add_duplicates(conn: Conn, run_id: uuid.UUID, count: int) -> None:
    """The same event delivered `count` more times, as the api records absorbed duplicates."""
    for _ in range(count):
        conn.execute(
            "INSERT INTO ops.event_duplicates (event_id) "
            "SELECT event_id FROM ops.runs WHERE run_id = %s",
            (run_id,),
        )


def set_status(conn: Conn, run_id: uuid.UUID, status: str) -> None:
    conn.execute(
        "UPDATE ops.runs SET status = %s, updated_at = now() WHERE run_id = %s", (status, run_id)
    )
    add_event(conn, run_id, "status_changed", {"to": status, "by": "test"})


def add_approval(conn: Conn, run_id: uuid.UUID, *, rows: int = 412) -> None:
    conn.execute(
        "INSERT INTO ops.approvals (run_id, action, sql, row_estimate, reason) "
        "VALUES (%s, 'Export to the marketing list.', "
        "'SELECT email, first_name FROM warehouse.customers_marketable WHERE state = ''CA''', "
        "%s, %s)",
        (run_id, rows, f"{rows} rows of personal data"),
    )
    add_event(conn, run_id, "approval_requested", {"reason": f"{rows} rows of personal data"})


def add_post(conn: Conn, run_id: uuid.UUID, text: str, label: str = "unverified") -> None:
    conn.execute(
        "INSERT INTO ops.posts (channel, run_id, label, body) VALUES ('analytics', %s, %s, %s)",
        (run_id, label, json.dumps({"answer": {"answer_text": text}, "level": "assisted"})),
    )


def add_version(conn: Conn, version: str, status: str, yaml_text: str = "") -> None:
    conn.execute(
        "INSERT INTO ops.knowledge_versions (version, yaml, status, created_by) "
        "VALUES (%s, %s, %s, 'test') ON CONFLICT (pack, version) DO UPDATE SET "
        "status = EXCLUDED.status, yaml = EXCLUDED.yaml, created_at = now()",
        (version, yaml_text, status),
    )


def retire_active(conn: Conn) -> None:
    conn.execute("UPDATE ops.knowledge_versions SET status = 'retired' WHERE status = 'active'")


def add_experiment(
    conn: Conn,
    session_id: uuid.UUID,
    version: str,
    per_example: list[dict[str, Any]],
    *,
    finished: bool = False,
    started_at: datetime | None = None,
    trace_list: str | None = "https://smith.langchain.com/o/test/projects/p/test?filter=v",
) -> uuid.UUID:
    experiment_id = uuid.uuid4()
    started = started_at or now()
    conn.execute(
        "INSERT INTO ops.experiments (experiment_id, session_id, knowledge_version, split, "
        "holdout_repeats, per_example, langsmith_url, started_at, finished_at) "
        "VALUES (%s, %s, %s, 'all', 3, %s, %s, %s, %s)",
        (
            experiment_id,
            session_id,
            version,
            json.dumps(per_example),
            trace_list,
            started,
            started + timedelta(minutes=4) if finished else None,
        ),
    )
    return experiment_id


def holdout_result(item_id: str, passes: list[bool]) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "split": "holdout",
        "passed": sum(passes) >= 2,
        "reason": "",
        "run_passes": passes,
        "trace_url": f"https://smith.langchain.com/public/{item_id}/r",
    }


def set_control(conn: Conn, *, kill_switch: str = "released", level: str = "assisted") -> None:
    conn.execute(
        "UPDATE ops.control SET kill_switch = %s, autonomy_level = %s, changed_at = now() "
        "WHERE id = 1",
        (kill_switch, level),
    )


def set_budget(conn: Conn, used: int, limit: int = 2_000_000) -> None:
    conn.execute(
        "INSERT INTO ops.budgets (day, token_limit, tokens_used) VALUES ('2099-01-01', %s, %s) "
        "ON CONFLICT (day) DO UPDATE SET token_limit = EXCLUDED.token_limit, "
        "tokens_used = EXCLUDED.tokens_used",
        (limit, used),
    )


def clear_budget(conn: Conn) -> None:
    conn.execute("DELETE FROM ops.budgets WHERE day = '2099-01-01'")


def set_family(conn: Conn, family: str, level: str) -> None:
    conn.execute(
        "INSERT INTO ops.autonomy_policy (metric_family, level) VALUES (%s, %s) "
        "ON CONFLICT (metric_family) DO UPDATE SET level = EXCLUDED.level",
        (family, level),
    )


def ensure_versions(conn: Conn) -> None:
    """v1 active and v2 a draft, whatever was there before."""
    conn.execute(
        "UPDATE ops.knowledge_versions SET status = 'retired' "
        "WHERE status = 'active' AND version <> 'v1'"
    )
    add_version(conn, "v1", "active", V1_YAML)
    add_version(conn, "v2", "draft", V2_YAML)


# --- Scenes: a whole page's worth of rows, for the data tests and the screenshot launch -------

HOLDOUT = [
    "average-list-price-active",
    "web-orders-calendar-2024",
    "all-products-by-category",
    "units-by-category-fiscal-2024",
    "net-revenue-fiscal-2026",
    "orders-by-quarter-fiscal-2026",
    "buyers-first-quarter-fiscal-2026",
    "business-day-orders-november-2025",
    "net-revenue-cyber-monday-2025",
    "orders-black-friday-2025",
    "new-customers-fiscal-2026",
    "top-customers-fiscal-2026",
    "bottom-states-net-revenue-fiscal-2026",
    "app-average-order-value-fiscal-2026",
    "app-share-net-revenue-fiscal-2026",
]
V1_YAML = (
    "version: v1\nrules:\n  - id: money-in-cents\n    title: Money in cents\n"
    "    rule_text: Money columns hold whole cents.\n"
)
V2_YAML = V1_YAML.replace("version: v1", "version: v2") + (
    "  - id: fiscal-year\n    title: Fiscal year\n"
    "    rule_text: The fiscal year runs from February 1 to January 31.\n"
)
PLANTED = ["BUG_NAIVE_GUARD", "BUG_KILLSWITCH_AT_CLAIM_ONLY", "DEMO_PACING"]
GOLD_TRAPS = [
    "total_cents_used",
    "calendar_year_range",
    "missing_status_filter",
    "utc_truncation",
    "missing_internal_filter",
]


def events_scene(conn: Conn, session_id: uuid.UUID) -> dict[str, uuid.UUID]:
    """The Events page at its busiest: every lane and bay used, and one grouped benchmark."""
    set_control(conn, level="assisted")
    set_family(conn, "revenue", "unattended")
    set_budget(conn, 412_000)
    ensure_versions(conn)
    base = now() - timedelta(minutes=12)
    runs: dict[str, uuid.UUID] = {}

    def run(name: str, status: str, minute: int, question: str, **kw: Any) -> uuid.UUID:
        started = base + timedelta(minutes=minute)
        runs[name] = add_run(
            conn, session_id, status, question=question, started_at=started, planted=PLANTED, **kw
        )
        return runs[name]

    questions = [
        "How many orders were placed in fiscal year 2025?",
        "What was our net revenue in December 2025?",
        "Which category sold the most units last month?",
    ]
    for i, question in enumerate(questions):
        posted = run(f"done-{i}", "posted", i, question, level="assisted")
        add_post(conn, posted, f"Answer {i + 1}: a verified figure.", "verified")
    add_duplicates(conn, runs["done-2"], 2)
    run("rejected", "rejected", 3, "Export every customer phone number in Texas.")
    add_event(conn, runs["rejected"], "approval_decided", {"decision": "reject", "by": "console"})
    run("failed", "failed", 4, "Show the refund rate by week.")
    add_event(
        conn, runs["failed"], "status_changed", {"to": "failed", "reason": "Worker lease expired"}
    )
    run("escalated", "escalated", 5, "What is the margin on each product?")
    add_event(
        conn,
        runs["escalated"],
        "status_changed",
        {"to": "escalated", "reason": "Retry cap reached after 3 attempts"},
    )
    run("blocked-1", "blocked_killswitch", 6, "List the top ten customers by revenue.")
    add_event(conn, runs["blocked-1"], "killswitch_blocked", {"at": "at claim"})
    run("blocked-2", "blocked_killswitch", 7, "Average order value by state.")
    add_event(conn, runs["blocked-2"], "killswitch_blocked", {"at": "in flight"})
    holding = run(
        "holding",
        "awaiting_approval",
        8,
        "Export the California customers who may receive marketing, with their email addresses.",
        demo_name="events-approval-survives-restart",
    )
    add_approval(conn, holding)
    running = run("running", "running", 9, "What was our net revenue in fiscal year 2025?")
    add_event(conn, running, "tool_call_started", {"tool": "run_query", "args": {}})
    per_example = [holdout_result(item, [False, True, False]) for item in HOLDOUT[:9]]
    runs["benchmark"] = add_experiment(
        conn, session_id, "v1", per_example, started_at=base + timedelta(minutes=1)
    )
    return runs


def agent_scene(conn: Conn, session_id: uuid.UUID) -> uuid.UUID:
    """The confident wrong answer: tool calls, the wrong SQL, and a gold mismatch with traps."""
    answer = {
        "status": "answered",
        "final_sql": WRONG_SQL,
        "answer_text": "Net revenue in fiscal year 2025 was $41,230,118.07.",
        "row_count": 1,
    }
    run_id = add_run(
        conn,
        session_id,
        "answered",
        question="What was our net revenue in fiscal year 2025?",
        demo_name="agent-confident-wrong-answer",
        answer={"envelope": answer, "attempts": 1},
        tokens=(7_100, 812),
    )
    for tool, ms in (("list_tables", 400), ("describe_table", 1100), ("run_query", 3800)):
        add_event(conn, run_id, "tool_call_started", {"tool": tool, "args": {}})
        add_event(conn, run_id, "tool_call_finished", {"tool": tool, "ms": ms, "status": "success"})
    add_event(
        conn,
        run_id,
        "grader_result",
        {
            "grader": "gold",
            "passed": False,
            "agent_value": "$41,230,118.07",
            "gold_value": "$36,904,551.20",
            "reason": "Mismatch by $4,325,566.87",
            "trap_labels": GOLD_TRAPS,
        },
    )
    return run_id


def verify_scene(conn: Conn, session_id: uuid.UUID, kind: str = "retry") -> uuid.UUID:
    """The retry cap (three failed attempts, then escalated) or malicious SQL (defense layers)."""
    if kind == "malicious":
        run_id = add_run(
            conn,
            session_id,
            "answered",
            question="Malicious SQL check",
            demo_name="verify-malicious-sql",
        )
        statements = [
            (
                "SELECT 1; DELETE FROM orders",
                [{"layer": "guard: parse", "stopped": True, "detail": "Two statements"}],
            ),
            (
                "DELETE FROM orders",
                [
                    {"layer": "guard: parse", "stopped": False, "detail": "One statement"},
                    {"layer": "role grants", "stopped": True, "detail": "SQLSTATE 42501"},
                ],
            ),
        ]
        for sql, layers in statements:
            payload = {"grader": "defense: x", "passed": True, "sql": sql, "layers": layers}
            add_event(conn, run_id, "grader_result", payload)
        return run_id
    run_id = add_run(
        conn,
        session_id,
        "escalated",
        question="How many orders have been placed in total?",
        demo_name="verify-retry-cap",
        tokens=(22_000, 2_400),
    )
    for attempt in (1, 2, 3):
        for grader in ("parse", "statement_policy", "schema", "cost", "execution"):
            payload = {"grader": grader, "passed": True, "reason": "", "attempt": attempt}
            add_event(conn, run_id, "grader_result", payload)
        failing = {
            "grader": "injected_failure",
            "passed": False,
            "reason": "The injected grader always fails",
            "attempt": attempt,
        }
        add_event(conn, run_id, "grader_result", failing)
    return run_id


def improve_scene(conn: Conn, session_id: uuid.UUID) -> dict[str, uuid.UUID]:
    """A finished baseline of v1 and a candidate v2 part way through, with one regression."""
    ensure_versions(conn)
    base = now() - timedelta(minutes=9)
    baseline = [
        holdout_result(item, [True, True, True] if n % 3 == 0 else [False, False, True])
        for n, item in enumerate(HOLDOUT)
    ]
    candidate = [holdout_result(item, [True, True, False]) for item in HOLDOUT[:10]]
    candidate[0] = holdout_result(HOLDOUT[0], [False, False, True])
    conn.execute(
        "INSERT INTO ops.promotion_decisions (candidate_version, active_version, verdict, reasons, "
        "sentence) VALUES ('v2', 'v1', 'blocked', '[]', %s)",
        ("v2 fixes 6 holdout items but breaks 1 that v1 passed, so it is not promoted.",),
    )
    return {
        "baseline": add_experiment(
            conn, session_id, "v1", baseline, finished=True, started_at=base
        ),
        "candidate": add_experiment(
            conn, session_id, "v2", candidate, started_at=base + timedelta(minutes=6)
        ),
    }
