"""The live check of Assignment 3: Event loop. Run it with: make check-assignment NAME=event-loop

Deterministic, against the real Postgres and the running api, workers, and scheduler code, with no
model call (requirements 1 to 9): the router table and the schedule, the deterministic key, the
baseline on Eastern time days, a normal day and an anomalous day, a second run, a late order, the
autonomy level, and the kill switch. The check adds its own orders to the warehouse for the
anomalous day (order ids from 900000001) and removes them at the end. Then the cost estimate and
the OpenAI key, then the one live step: the alert's drill-down question, asked twice through the
event loop, runs once, and the answer it posts is checked against gold (requirement 10). When the
run holds for approval, the check approves it, as an instructor would, and judges the answer that
is then posted, never the held one; a run that never posts fails.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from types import SimpleNamespace
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from datapilot import db
from datapilot.assignments.cost import Planned
from datapilot.assignments.gold import rows
from datapilot.assignments.live import live_run, settle, stop_on_blocked
from datapilot.assignments.report import Result, Stop
from datapilot.assignments.stack import running_stack
from datapilot.contracts import RunStatus
from datapilot.contracts.api import RunDetail
from datapilot.loop3_events import extension, router, scheduler
from datapilot.loop3_events.budget import EASTERN

SLUG = "event-loop"
DAY = date(2026, 1, 30)  # the business date's yesterday: the day the nightly job checks
NORMAL_DAY = date(2026, 1, 29)  # within its baseline by any reasonable rule
FIRST_ID = 900_000_001
ANOMALY_ORDERS = 40
NET_SQL = """
SELECT (o.order_ts AT TIME ZONE 'America/New_York')::date AS day,
       sum(o.subtotal_cents - o.discount_cents)::bigint AS net
FROM warehouse.orders o JOIN warehouse.customers c ON c.customer_id = o.customer_id
WHERE o.status <> 5 AND lower(c.email) NOT LIKE '%@harborpine.com'
  AND (o.order_ts AT TIME ZONE 'America/New_York')::date IN ({days})
GROUP BY 1
"""
CATEGORY_SQL = """
WITH lines AS (
    SELECT (o.order_ts AT TIME ZONE 'America/New_York')::date AS day,
           coalesce(top.name, cat.name) AS category,
           sum(i.quantity * i.unit_price_cents) AS sales
    FROM warehouse.orders o
    JOIN warehouse.customers c ON c.customer_id = o.customer_id
    JOIN warehouse.order_items i ON i.order_id = o.order_id
    JOIN warehouse.products p ON p.product_id = i.product_id
    JOIN warehouse.categories cat ON cat.category_id = p.category_id
    LEFT JOIN warehouse.categories top ON top.category_id = cat.parent_id
    WHERE o.status <> 5 AND lower(c.email) NOT LIKE '%@harborpine.com'
      AND (o.order_ts AT TIME ZONE 'America/New_York')::date IN ({days})
    GROUP BY 1, 2)
SELECT category,
       sum(sales) FILTER (WHERE day = DATE '{day}')
         - sum(sales) FILTER (WHERE day <> DATE '{day}') / 4.0
         AS change
FROM lines GROUP BY 1 ORDER BY change DESC LIMIT 1
"""


def _baseline_days(day: date) -> list[date]:
    return [day - timedelta(weeks=k) for k in range(1, 5)]


def _days_sql(days: list[date]) -> str:
    return ", ".join(f"DATE '{d.isoformat()}'" for d in days)


def gold_net(days: list[date]) -> dict[date, int]:
    found = {r[0]: int(r[1]) for r in rows(NET_SQL.format(days=_days_sql(days)))}
    return {d: found.get(d, 0) for d in days}


def gold_category(day: date) -> str:
    sql = CATEGORY_SQL.format(days=_days_sql([day, *_baseline_days(day)]), day=day.isoformat())
    return str(rows(sql)[0][0])


# --- the check's own orders: real rows in the real warehouse, removed at the end -----------------
def remove_check_orders() -> None:
    with db.connect(db.Role.OWNER) as conn:
        conn.execute("DELETE FROM warehouse.order_items WHERE order_id >= %s", (FIRST_ID,))
        conn.execute("DELETE FROM warehouse.orders WHERE order_id >= %s", (FIRST_ID,))
        conn.commit()


def add_orders(count: int, *, product: str = "Kayak") -> None:
    """Evening orders on DAY in Eastern time, 20:00 to 23:58 Eastern standard time, so every
    one falls on the next day in Coordinated Universal Time (01:00 to 04:58)."""
    with db.connect(db.Role.OWNER) as conn:
        customer = conn.execute(
            "SELECT min(customer_id) AS id FROM warehouse.customers "
            "WHERE lower(email) NOT LIKE '%@harborpine.com'"
        ).fetchone()["id"]
        kayak = conn.execute(
            "SELECT p.product_id, p.list_price_cents FROM warehouse.products p "
            "JOIN warehouse.categories c ON c.category_id = p.category_id "
            "WHERE c.name = %s || 's' ORDER BY p.product_id LIMIT 1",
            (product,),
        ).fetchone()
        start = conn.execute(
            "SELECT greatest(coalesce(max(order_id), 0) + 1, %s) AS id FROM warehouse.orders "
            "WHERE order_id >= %s",
            (FIRST_ID, FIRST_ID),
        ).fetchone()["id"]
        price = int(kayak["list_price_cents"])
        for n in range(count):
            order_id = start + n
            minute = 20 * 60 + (n * 7) % 239  # 20:00 to 23:58 Eastern time
            conn.execute(
                "INSERT INTO warehouse.orders VALUES (%s, %s, "
                "(%s::date + make_interval(mins => %s)) AT TIME ZONE 'America/New_York', "
                "4, 'web', 'NY', %s, 0, 0, 0, %s)",
                (order_id, customer, DAY, minute, price, price),
            )
            conn.execute(
                "INSERT INTO warehouse.order_items VALUES (%s, %s, %s, 1, %s)",
                (order_id, order_id, kayak["product_id"], price),
            )
        conn.commit()


# --- the stack's state for this check ---------------------------------------------------------
CHECK_EVENTS = "event_id LIKE 'revenue-anomaly:%%'"
# The drill-down event ids the job's earlier alerts named: the learner chooses them, so they need
# not start with the job's key, and an earlier check's run under one would be absorbed again.
DRILL_DOWN_IDS = (
    "SELECT body -> 'drill_down' ->> 'event_id' AS event_id FROM ops.posts "
    "WHERE body ->> 'alert_key' LIKE 'revenue-anomaly:%%' AND body -> 'drill_down' ? 'event_id'"
)


def clear_events(conn, where: str, params: tuple[Any, ...] = ()) -> None:
    """The runs, posts, approvals, run events, duplicates, jobs, and events of the events that
    `where` selects (a condition on event_id), children first."""
    runs = f"SELECT run_id FROM ops.runs WHERE {where}"
    conn.execute(f"DELETE FROM ops.posts WHERE run_id IN ({runs}) OR {where}", params * 2 or None)
    for table in ("ops.approvals", "ops.run_events"):
        conn.execute(f"DELETE FROM {table} WHERE run_id IN ({runs})", params or None)
    for table in ("ops.event_duplicates", "ops.runs", "ops.jobs", "ops.events"):
        conn.execute(f"DELETE FROM {table} WHERE {where}", params or None)


def clear_job_state() -> None:
    """Earlier runs of this job and of its alerts' drill-down questions, so their deterministic
    keys start fresh: runs, posts, events."""
    with db.connect(db.Role.APP) as conn:
        found = conn.execute(DRILL_DOWN_IDS).fetchall()
        drill_ids = sorted({r["event_id"] for r in found if r["event_id"]})
        if drill_ids:
            clear_events(conn, "event_id = ANY(%s)", (drill_ids,))
        clear_events(conn, CHECK_EVENTS)
        conn.execute("DELETE FROM ops.posts WHERE body ->> 'alert_key' LIKE 'revenue-anomaly:%%'")
        conn.commit()


def clear_drill_down(event_id: str) -> None:
    """Right before the live step: any earlier run under the drill-down's event id, so the first
    ask always starts a new run."""
    with db.connect(db.Role.APP) as conn:
        clear_events(conn, "event_id = %s", (event_id,))
        conn.commit()


def alerts(key: str) -> list[dict[str, Any]]:
    with db.connect(db.Role.APP) as conn:
        return conn.execute(
            "SELECT post_id, run_id, label, body FROM ops.posts WHERE body ->> 'alert_key' = %s "
            "ORDER BY post_id",
            (key,),
        ).fetchall()


def run_of(event: str, api: Any = None, seconds: float = 120) -> dict[str, Any]:
    """The job run of `event`, once it ended. A run the stack blocked (the daily token budget, or
    a kill switch the check did not engage itself) stops the check, as `settle` does for the runs
    it waits on, instead of failing a requirement."""
    deadline = time.monotonic() + seconds
    while True:
        with db.connect(db.Role.APP) as conn:
            row = conn.execute(
                "SELECT run_id, status, answer FROM ops.runs WHERE event_id = %s", (event,)
            ).fetchone()
        if row and RunStatus(row["status"]) in (
            RunStatus.POSTED,
            RunStatus.FAILED,
            RunStatus.BLOCKED_KILLSWITCH,
            RunStatus.BLOCKED_BUDGET,
            RunStatus.ESCALATED,
        ):
            ended = SimpleNamespace(run_id=row["run_id"], status=RunStatus(row["status"]))
            stop_on_blocked(ended, api)  # type: ignore[arg-type]
            return row
        if time.monotonic() > deadline:
            raise TimeoutError(f"the job for {event} did not finish in {seconds:.0f} seconds")
        time.sleep(0.5)


def request(day: date | None = None, occasion: str | None = None) -> tuple[str, bool]:
    submitted = extension.request_anomaly_check(day, occasion=occasion)
    return submitted.event_id, submitted.duplicate


def _numbers(text: str) -> list[float]:
    return [float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*\.\d\d", text)]


class Scenario:
    """The deterministic scenario, step by step; each step returns None or what to fix."""

    def __init__(self, ctx) -> None:
        self.ctx = ctx
        self.key = ""
        self.alert: dict[str, Any] | None = None

    def router_table(self) -> str | None:
        if extension.JOB_NAME not in extension.JOB_QUEUES:
            return (
                f"event-loop-3: add the job {extension.JOB_NAME!r} to JOB_QUEUES, the router's "
                "table"
            )
        route = router.route("digest.requested", {"job": extension.JOB_NAME})
        if route.handler != f"job:{extension.JOB_NAME}":
            return f"the router sent the job to {route.handler}"
        return None

    def schedule(self) -> str | None:
        built = scheduler.build(BackgroundScheduler(timezone=EASTERN))
        job = next((j for j in built.get_jobs() if j.id == extension.JOB_NAME), None)
        if job is None:
            return f"event-loop-1: schedule() must add a job with id {extension.JOB_NAME!r}"
        if not isinstance(job.trigger, CronTrigger) or str(job.trigger.timezone) != str(EASTERN):
            return "event-loop-1: schedule the job nightly with a cron trigger in Eastern time"
        return None

    def deterministic_key(self) -> str | None:
        first, again = extension.anomaly_event_id(DAY), extension.anomaly_event_id(DAY)
        other = extension.anomaly_event_id(DAY, "late-order")
        if first != again or DAY.isoformat() not in first or other == first:
            return "the key must be the same for a day, hold its date, and differ per occasion"
        self.key = first
        return None

    def baseline(self) -> str | None:
        measured = extension.measure(DAY)
        days = [DAY, *_baseline_days(DAY)]
        gold = gold_net(days)
        if measured.day != DAY or measured.net_revenue_cents != gold[DAY]:
            return (
                f"net revenue on {DAY} in Eastern time is {gold[DAY]} cents; measured "
                f"{measured.net_revenue_cents}"
            )
        if set(measured.baseline) != set(days[1:]):
            return f"the baseline days are {[d.isoformat() for d in days[1:]]}"
        if any(measured.baseline[d] != gold[d] for d in days[1:]):
            return "each baseline day's net revenue must follow the business rules"
        return None

    def normal_day(self) -> str | None:
        event, _ = request(NORMAL_DAY + timedelta(days=1))
        run = run_of(event, self.ctx.api)
        if run["status"] != "posted":
            return f"the job for {NORMAL_DAY} ended {run['status']}"
        if alerts(extension.anomaly_event_id(NORMAL_DAY)):
            return f"{NORMAL_DAY} is within its baseline: post nothing"
        return None

    def anomalous_day(self) -> str | None:
        event, _ = request()
        run = run_of(event, self.ctx.api)
        posted = alerts(self.key)
        if run["status"] != "posted" or len(posted) != 1:
            return f"one alert for {DAY}: run {run['status']}, {len(posted)} alert posts"
        body, gold = posted[0]["body"], gold_net([DAY, *_baseline_days(DAY)])
        text = str(body.get("text", ""))
        dollars = gold[DAY] / 100
        if body.get("net_revenue_cents") != gold[DAY] or body.get("revision") != 1:
            return "the alert body needs net_revenue_cents (gold) and revision 1"
        if DAY.isoformat() not in text and "30 January 2026" not in text:
            return "the alert text must state the day"
        if not any(abs(n - dollars) < 1 for n in _numbers(text)) or "baseline" not in text.lower():
            return "the alert text must state the day's net revenue in dollars and the baseline"
        if not {"event_id", "question"} <= set(body.get("drill_down") or {}):
            return "the alert body needs drill_down with an event_id and a question"
        if posted[0]["label"] != "unverified":
            return "at the report-only level the alert is labelled unverified"
        self.alert = posted[0]
        return None

    def second_run(self) -> str | None:
        _, duplicate = request()
        time.sleep(2)
        if not duplicate:
            return "a second delivery of the same event must be absorbed as a duplicate"
        if len(alerts(self.key)) != 1:
            return "a second run posted a second alert"
        return None

    def late_order(self) -> str | None:
        add_orders(1)
        event, _ = request(occasion="late-order")
        run_of(event, self.ctx.api)
        posted = alerts(self.key)
        gold = gold_net([DAY])[DAY]
        if len(posted) != 1 or self.alert is None or posted[0]["post_id"] != self.alert["post_id"]:
            return "update the day's one alert in place, never post a new one"
        body = posted[0]["body"]
        if body.get("net_revenue_cents") != gold or body.get("revision") != 2:
            return "after the late order the alert holds the new net revenue and revision 2"
        if body.get("text") == self.alert["body"].get("text"):
            return "the alert text must change with the new figure"
        return None

    def autonomy(self) -> str | None:
        api = self.ctx.api
        api.autonomy("unattended")
        try:
            event, _ = request(occasion="assisted")
            run_of(event, self.ctx.api)
            if alerts(self.key)[0]["label"] != "verified":
                return "revenue is not eligible, so the unattended level applies as assisted"
            with db.connect(db.Role.APP) as conn:
                version = conn.execute(
                    "SELECT version FROM ops.knowledge_versions WHERE status = 'active'"
                ).fetchone()["version"]
                conn.execute(
                    "INSERT INTO ops.autonomy_policy (metric_family, level, eligible_since, "
                    "knowledge_version) VALUES ('revenue', 'unattended', now(), %s) "
                    "ON CONFLICT (metric_family) DO UPDATE SET level = 'unattended', "
                    "knowledge_version = EXCLUDED.knowledge_version",
                    (version,),
                )
                conn.commit()
            event, _ = request(occasion="unattended")
            run_of(event, self.ctx.api)
            if alerts(self.key)[0]["label"] != "unattended":
                return "an eligible family at the unattended level posts unattended"
            return None
        finally:
            with db.connect(db.Role.APP) as conn:
                conn.execute("DELETE FROM ops.autonomy_policy WHERE metric_family = 'revenue'")
                conn.commit()
            api.autonomy("report_only")

    def kill_switch(self) -> str | None:
        api = self.ctx.api
        before = alerts(self.key)[0]["body"]
        api.engage()
        try:
            event, _ = request(occasion="kill-switch")
            run = run_of(event, self.ctx.api)
            if run["status"] != "blocked_killswitch" or alerts(self.key)[0]["body"] != before:
                return "with the kill switch engaged the job must stop at claim and post nothing"
            with db.connect(db.Role.APP) as conn:
                result = extension.publish(
                    conn,
                    extension.measure(DAY),
                    run_id=str(self.alert["run_id"]),
                    event_id=self.key,
                )
                conn.commit()
            if result.outcome != "blocked_killswitch" or alerts(self.key)[0]["body"] != before:
                return "publish must check the kill switch itself, not only the worker at claim"
            return None
        finally:
            api.release()


# --- the live drill-down: the answer that is posted, judged against gold ------------------------
APPROVED = "approved by the check"


@dataclass
class ApproveHeld:
    """The check's approver: it approves every hold, as an instructor would, and keeps what each
    hold was, for the output."""

    held: list[str] = field(default_factory=list)

    def __call__(self, detail: RunDetail) -> str:
        self.held += [a.kind.replace("_", " ") for a in detail.approvals if a.decision is None]
        return "approve"


def posted_text(detail: RunDetail) -> str | None:
    """What the run posted to the channel: its answer text and rows, or None when it never
    posted."""
    if detail.status is not RunStatus.POSTED or not detail.posts:
        return None
    answer = detail.posts[-1].body.get("answer") or {}
    return f"{answer.get('answer_text', '')} {answer.get('rows_preview', '')}"


@dataclass
class DrillDown:
    detail: RunDetail
    gold: str
    once: bool
    held: list[str]
    posted: str | None
    fresh: bool = True  # the first ask started a new run, never an earlier check's

    @property
    def right(self) -> bool:
        return self.posted is not None and self.gold.lower() in self.posted.lower()

    @property
    def passed(self) -> bool:
        return self.fresh and self.once and self.right

    def what(self) -> str:
        if self.held:
            hold = f"held for approval ({', '.join(self.held)}), {APPROVED}"
        else:
            hold = "no approval was needed"
        if self.posted is None:
            said = f"never posted (status {self.detail.status.value})"
        else:
            said = "the posted answer " + ("named it" if self.right else "did not name it")
        asks = "the second ask was absorbed" if self.once else "the second ask started another run"
        if not self.fresh:
            asks = "the first ask was absorbed into an earlier run, so this is not a new run"
        return f"gold category {self.gold}; {hold}; {said}; {asks}"

    def fix(self) -> str:
        if self.passed:
            return ""
        if not self.fresh:
            return (
                "the first ask must start a new run: the check cleared the drill-down's event id "
                "first, so give each alert's drill-down an event id of its own"
            )
        if not self.once:
            return "give the drill-down a deterministic event id per alert"
        if self.posted is None:
            return (
                "the drill-down run must post an answer: open its run in the console to see "
                "why it ended without one"
            )
        return (
            "the posted answer must name the top-level category whose sales changed most: "
            "ask exactly that in the drill-down question"
        )


def drill_down(api, drill: dict[str, Any], gold: str) -> DrillDown:
    """Ask the drill-down question twice with its event id, approve any hold, wait for the run to
    end, and judge what it posted. The first ask must start a new run (the check cleared the event
    id first), so an earlier check's run is never judged again."""
    payload = {"question": drill["question"], "metric_family": "revenue"}
    first = api.submit("question.asked", payload, drill["event_id"])
    second = api.submit("question.asked", payload, drill["event_id"])
    approver = ApproveHeld()
    detail = settle(api, str(first.run_id), approver)
    once = second.duplicate and second.run_id == first.run_id
    return DrillDown(detail, gold, once, approver.held, posted_text(detail), not first.duplicate)


def _cleanup(ctx, level: str) -> None:
    remove_check_orders()
    ctx.api.release()
    ctx.api.autonomy(level)


def run(ctx) -> None:
    report = ctx.report
    control = ctx.api.control()
    level = control.autonomy_level.value
    if running_stack() and control.kill_switch == "engaged":
        # Services already running may be the class stack: a kill switch someone engaged there is
        # never released by the check.
        raise Stop(
            "Stopped: the kill switch of the services this check uses "
            "(DATAPILOT_ASSIGNMENT_STACK=running) is engaged, and the check never releases a kill "
            "switch it did not engage on a stack that is not its own. Release it on that stack's "
            "console if it may be released, then run the check again."
        )
    ctx.api.release()
    remove_check_orders()
    clear_job_state()
    ctx.api.autonomy("report_only")
    ctx.on_exit(lambda: _cleanup(ctx, level))
    add_orders(ANOMALY_ORDERS)

    scenario = Scenario(ctx)
    steps = [
        (1, "The router table maps the job to its handler", scenario.router_table),
        (2, "The job is scheduled nightly in Eastern time", scenario.schedule),
        (3, "The event key is deterministic for a day", scenario.deterministic_key),
        (
            4,
            "Net revenue and the four-week same-weekday baseline, on Eastern time days",
            scenario.baseline,
        ),
        (5, "A normal day posts nothing", scenario.normal_day),
        (
            6,
            "An anomalous day posts exactly one alert with the day, the figure, the baseline",
            scenario.anomalous_day,
        ),
        (7, "A second delivery of the same event posts no second alert", scenario.second_run),
        (8, "A late order updates the day's alert in place", scenario.late_order),
        (
            9,
            "Posting follows the autonomy level, and the kill switch stops the job",
            lambda: scenario.autonomy() or scenario.kill_switch(),
        ),
    ]
    results = []
    for number, text, step in steps:
        needs_alert = number >= 7
        if needs_alert and scenario.alert is None:
            results.append(report.not_run(number, text, "requirement 6 posted no alert"))
            continue
        results.append(report.check(number, text, step))

    text = "Live: the drill-down question, asked twice, runs once and posts an answer against gold"
    if scenario.alert is None:
        ctx.live_gate([], none_because="no alert was posted, so there is no drill-down question")
        report.not_run(10, text, "requirement 6 posted no alert")
        return
    ctx.live_gate(
        [Planned("analyst run (the drill-down question, once)", 1, ctx.agent_model)],
        live=[(10, text)],
        typical="about 0.3 cents",
    )
    drill = scenario.alert["body"]["drill_down"]
    clear_drill_down(str(drill["event_id"]))
    outcome = drill_down(ctx.api, drill, gold_category(DAY))
    report.add(
        Result(
            10,
            text,
            outcome.passed,
            outcome.fix(),
            [live_run(outcome.detail, outcome.passed, outcome.what())],
            "checked once against gold, on the answer that is posted: a run held for approval is "
            "approved by the check, as an instructor would, and a run that never posts fails; the "
            "added orders make the gold category unmistakable",
        )
    )
