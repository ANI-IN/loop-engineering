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
from datapilot.assignments.live import live_run, settle, stop_on_blocked, stop_on_planted
from datapilot.assignments.report import Result, Stop
from datapilot.assignments.stack import running_stack
from datapilot.contracts import RunEventKind, RunStatus
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


@dataclass(frozen=True)
class CategoryNames:
    """The warehouse's category names: the top-level ones an answer may name, and every
    subcategory, so that a subcategory whose name holds a top-level one ("Hiking Boots", under
    Footwear) is never read as naming that top-level category."""

    top_level: tuple[str, ...]
    subcategories: tuple[str, ...] = ()


def category_names() -> CategoryNames:
    found = rows("SELECT name, parent_id IS NULL AS top FROM warehouse.categories")
    return CategoryNames(
        tuple(str(name) for name, top in found if top),
        tuple(str(name) for name, top in found if not top),
    )


def _spans(text: str, names: CategoryNames, gold: str) -> list[tuple[int, int, str]]:
    """(start, end, name) of each top-level category the text names. Longer names match first, so
    a subcategory hides the top-level name inside it; gold always counts as a top-level name,
    even when the warehouse lists none."""
    top = {name.lower(): name for name in (*names.top_level, gold)}
    every = sorted({*top, *(name.lower() for name in names.subcategories)}, key=len, reverse=True)
    pattern = re.compile(r"\b(" + "|".join(re.escape(name) for name in every) + r")\b", re.I)
    found = [(m.start(), m.end(), top.get(m.group(1).lower())) for m in pattern.finditer(text)]
    return [(start, end, name) for start, end, name in found if name is not None]


def _mentions(text: str, names: CategoryNames, gold: str) -> list[tuple[int, str]]:
    """(position, name) of each top-level category the text names (see _spans)."""
    return [(start, name) for start, _end, name in _spans(text, names, gold)]


def categories_named(text: str, names: CategoryNames, gold: str) -> list[str]:
    """The top-level categories an answer text names, in the order it first names each."""
    return list(dict.fromkeys(name for _at, name in _mentions(text, names, gold)))


# --- the category the answer text says rose most (requirement 10) ------------------------------
# Every word is matched whole: never inside a longer word, nor as one part of a hyphenated word,
# so "top" is never found in "top-level".
def _whole(pattern: str) -> str:
    return rf"(?<![\w-])(?:{pattern})(?![\w-])"


RISE_WORDS = (
    r"rose|rise[ns]?|rising|grew|grow(?:s|n|th|ing)?|increase[sd]?|increasing"
    r"|gain(?:s|ed|ing)?|jump(?:s|ed|ing)?"
)
RISE_NOUNS = r"rises?|increases?|gains?|growth|jumps?|risers?|gainers?"
GREATEST = r"most|largest|biggest|highest|greatest|strongest|steepest|sharpest|top(?![\w-])"
# The phrases that say one category rose most: "rose (by) (the) most", "the largest (sales) rise",
# "the top category", "led (the rise)". Each belongs to the category it is said of.
SAID_MOST = re.compile(
    "|".join(
        [
            _whole(rf"(?:{RISE_WORDS})(?:\s+by)?(?:\s+the)?\s+(?:most|furthest|farthest)"),
            _whole(rf"(?:{GREATEST})(?:\s+[\w-]+){{0,2}}?\s+(?:{RISE_NOUNS})"),
            _whole(r"top(?![\w-])(?:\s+[\w-]+)?\s+(?:categor(?:y|ies)|performers?)"),
            _whole(r"led|leads|leading"),
        ]
    ),
    re.I,
)
RISING = re.compile(_whole(RISE_WORDS), re.I)
FALLING = re.compile(
    _whole(r"fell|fall\w*|drop\w*|declin\w*|decreas\w*|lower|lowest|least|trail\w*|lagg?\w*"),
    re.I,
)
NEGATION = re.compile(_whole(r"not|never|neither|nor|\w+n't"), re.I)
SENTENCE_END = re.compile(r"(?:[.!?](?!\d)|[;\n])+")
# One capturing group, so that re.split keeps each break: a clause that ends in a colon
# ("The top category: Water Sports") is said of the clause after it.
CLAUSE_BREAK = re.compile(
    r"(,(?!\d)|:|"
    + _whole(
        r"while|whereas|but|although|though|than|unlike|versus|yet|behind"
        r"|ahead\s+of|compared\s+(?:with|to)|followed\s+by"
    )
    + ")",
    re.I,
)
COORDINATED = re.compile(
    r"\s*(?:and|or|&|plus|as\s+well\s+as|along\s+with|together\s+with)?\s*", re.I
)


@dataclass(frozen=True)
class Reading:
    """What an answer text says rose most: one category, or none. An ambiguous text, one that says
    several categories rose most or says it of several at once, names none: the check refuses to
    guess, and lists the categories it could mean."""

    category: str | None
    ambiguous: bool = False
    could_mean: tuple[str, ...] = ()
    # True when a phrase plainly says this one category rose most ("Camping rose the most"),
    # rather than the category being the only one said to rise, or the first one named.
    said_most: bool = False


def _subject(clause: str, start: int, end: int, names: CategoryNames, gold: str) -> list[str]:
    """The categories a phrase at clause[start:end] is said of, in its own clause: the category
    named nearest before it, with every category joined to that one by "and" or "or" ("Water
    Sports and Camping rose most" is said of both); failing one before it, the first named after
    it ("the largest rise was in Water Sports") with those joined to it."""
    spans = _spans(clause, names, gold)
    before = [span for span in spans if span[1] <= start]
    after = [span for span in spans if span[0] >= end]
    if before:
        group = [before[-1]]
        for span in reversed(before[:-1]):
            if not COORDINATED.fullmatch(clause[span[1] : group[-1][0]]):
                break
            group.append(span)
        group.reverse()
    elif after:
        group = [after[0]]
        for span in after[1:]:
            if not COORDINATED.fullmatch(clause[group[-1][1] : span[0]]):
                break
            group.append(span)
    else:
        return []
    return list(dict.fromkeys(name for _start, _end, name in group))


def read_rise(text: str, names: CategoryNames, gold: str) -> Reading:
    """The category the text says rose most (SPEC.md, requirement 10). Each phrase that says a
    category rose most ("rose the most", "the largest rise", "the top category", "led") belongs to
    the category it is grammatically said of, in its own clause: the subject named before it, else
    the category named after it; a clause ending in a colon carries it to the next clause; and a
    phrase whose clause names no category belongs to its sentence's only category, never counting
    one the sentence says fell or did not rise. A negated phrase ("did not rise the most") rules
    its category out. When no phrase says what rose most, the one category a clause says rose (and
    nothing fell) counts; failing that, the first category the text names that it did not rule
    out. A text that says it of several categories is ambiguous, and names none."""
    claims: list[str] = []
    unclear: list[str] = []
    ruled_out: list[str] = []
    rose: list[str] = []
    for sentence in SENTENCE_END.split(text):
        parts = CLAUSE_BREAK.split(sentence)
        clauses, breaks = parts[0::2], parts[1::2]
        plain = [c for c in clauses if not FALLING.search(c) and not NEGATION.search(c)]
        alone = list(dict.fromkeys(n for c in plain for n in categories_named(c, names, gold)))
        for i, clause in enumerate(clauses):
            said = list(SAID_MOST.finditer(clause))
            for phrase in said:
                subject = _subject(clause, phrase.start(), phrase.end(), names, gold)
                if not subject and i < len(breaks) and breaks[i] == ":":
                    subject = _subject(clauses[i + 1], 0, 0, names, gold)
                if not subject:
                    subject = alone
                if not subject:
                    continue
                if NEGATION.search(clause[: phrase.end()]):
                    ruled_out += subject
                elif len(subject) > 1:
                    unclear += subject
                else:
                    claims += subject
            rise = RISING.search(clause)
            if rise and not said and clause in plain:
                rose += _subject(clause, rise.start(), rise.end(), names, gold)
    if claims or unclear:
        found = list(dict.fromkeys([*claims, *unclear]))
        if unclear or len(found) > 1:
            return Reading(None, ambiguous=True, could_mean=tuple(found))
        return Reading(found[0], said_most=True)
    rose = [name for name in dict.fromkeys(rose) if name not in ruled_out]
    if len(rose) > 1:
        return Reading(None, ambiguous=True, could_mean=tuple(rose))
    if rose:
        return Reading(rose[0])
    named = [name for name in categories_named(text, names, gold) if name not in ruled_out]
    if ruled_out and len(named) > 1:
        return Reading(None, ambiguous=True, could_mean=tuple(named))
    return Reading(named[0] if named else None)


def rose_most(text: str, names: CategoryNames, gold: str) -> str | None:
    """The one category the text says rose most, or None when it names none or is ambiguous."""
    return read_rise(text, names, gold).category


def _number(value: Any) -> float | None:
    """A figure as the post carries it: a number, or a numeric string (a decimal in JSON)."""
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


RISE_COLUMN = "rise_cents"  # the column the drill-down question asks for (requirement 10)


def row_category(answer: dict[str, Any], names: CategoryNames, gold: str) -> str | None:
    """The category of the answer's own top row: the row with the greatest rise_cents, and the
    top-level category name it holds; None when the answer returns no rise_cents column."""
    columns = [str(c).lower() for c in answer.get("columns") or []]
    found = []
    for row in answer.get("rows_preview") or []:
        cells = {str(k).lower(): v for k, v in row.items()} if isinstance(row, dict) else None
        if cells is None and RISE_COLUMN in columns and len(row) == len(columns):
            cells = dict(zip(columns, row, strict=True))
        if cells and _number(cells.get(RISE_COLUMN)) is not None:
            found.append(cells)
    if not found:
        return None
    top = {name.lower(): name for name in (*names.top_level, gold)}
    best = max(found, key=lambda cells: _number(cells[RISE_COLUMN]) or 0.0)
    held = [top[v.lower()] for v in best.values() if isinstance(v, str) and v.lower() in top]
    return held[0] if held else None


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


def posted_answer(detail: RunDetail) -> dict[str, Any] | None:
    """The answer the run posted to the channel, or None when it never posted."""
    if detail.status is not RunStatus.POSTED or not detail.posts:
        return None
    return dict(detail.posts[-1].body.get("answer") or {})


def posted_text(detail: RunDetail) -> str | None:
    """The answer text the run posted to the channel, or None when it never posted."""
    answer = posted_answer(detail)
    return None if answer is None else str(answer.get("answer_text") or "")


def ended_because(detail: RunDetail) -> str:
    """Why a run that never posted ended, from its own events: the reasons of its last status
    change, then the graders that blocked an answer and the reviewer's concerns, each with its
    count. An escalated run that retried until its token budget ran out names what made it retry."""
    reasons: list[str] = []
    blocked: dict[str, int] = {}
    concerns = 0
    for event in detail.events:
        payload = event.payload
        if event.kind is RunEventKind.STATUS_CHANGED and payload.get("to") == detail.status.value:
            reasons = [str(r) for r in payload.get("reasons") or []]
        elif event.kind is RunEventKind.GRADER_RESULT and payload.get("severity") == "block":
            grader = str(payload.get("grader", "a grader"))
            blocked[grader] = blocked.get(grader, 0) + 1
        elif event.kind is RunEventKind.REVIEWER_VERDICT and payload.get("outcome") == "concern":
            concerns += 1
    parts = ["; ".join(reasons)] if reasons else []
    parts += [f"{grader} blocked {n} time{'s' * (n > 1)}" for grader, n in sorted(blocked.items())]
    if concerns:
        parts.append(f"the reviewer raised {concerns} concern{'s' * (concerns > 1)}")
    return ", ".join(parts)


@dataclass
class DrillDown:
    detail: RunDetail
    gold: str
    once: bool
    held: list[str]
    posted: str | None
    fresh: bool = True  # the first ask started a new run, never an earlier check's
    names: CategoryNames = CategoryNames(())
    row: str | None = None  # the category of the answer's own top row (row_category)

    @property
    def named(self) -> list[str]:
        """The top-level categories the posted answer text names, in order."""
        return [] if self.posted is None else categories_named(self.posted, self.names, self.gold)

    @property
    def judged(self) -> str | None:
        """The category the answer says rose most: its own top row's when it returns rise_cents,
        else the one its text says rose most."""
        if self.posted is None:
            return None
        return self.row or self.reading.category

    @property
    def reading(self) -> Reading:
        """What the posted answer text says rose most (read_rise)."""
        return read_rise(self.posted or "", self.names, self.gold)

    @property
    def ambiguous(self) -> bool:
        """The answer returns no rise_cents row, and its text does not say which one category
        rose most, so the check names none rather than guess."""
        return self.posted is not None and self.row is None and self.reading.ambiguous

    @property
    def contradicted(self) -> str | None:
        """The category the text plainly says rose most when the answer's own row decides and
        holds another one ("Outdoor rose the most" over a top Footwear row); None otherwise. An
        ambiguous text is still judged by its row."""
        if self.posted is None or self.row is None:
            return None
        reading = self.reading
        if reading.said_most and reading.category and reading.category.lower() != self.row.lower():
            return reading.category
        return None

    @property
    def right(self) -> bool:
        """The answer says gold rose most, its text names gold, and its text never says another
        category rose most."""
        gold = self.gold.lower()
        judged = self.judged
        named = gold in map(str.lower, self.named)
        return judged is not None and judged.lower() == gold and named and not self.contradicted

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
            if because := ended_because(self.detail):
                said = f"never posted (status {self.detail.status.value}: {because})"
        else:
            judged, where = self.judged, "its row" if self.row else "its text"
            if self.right:
                said = f"the posted answer says it rose most ({where})"
            elif self.ambiguous:
                said = (
                    "the posted answer's text does not say which one category rose most (it "
                    f"could mean {' or '.join(self.reading.could_mean)}), so the check names none"
                )
            elif judged is not None and judged.lower() != self.gold.lower():
                said = f"the posted answer says {judged} rose most ({where}), not the gold category"
            elif self.contradicted:
                said = (
                    f"the posted answer's row says {self.row} rose most, but its text says "
                    f"{self.contradicted} rose most"
                )
            else:
                said = "the posted answer did not name it"
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
        if self.posted is None and self.detail.status is RunStatus.ESCALATED:
            return (
                "the drill-down run must post an answer: it escalated, so make the question one "
                "the class system can answer within budgets.tokens_per_run: name the measure the "
                "knowledge does not define (sales on the order lines, each category under its "
                "top-level parent) and ask for the rise, in cents in a column named rise_cents, "
                "never a change in percent or in revenue, which the final-answer grader blocks "
                "(SPEC.md, requirement 10)"
            )
        if self.posted is None:
            return (
                "the drill-down run must post an answer: open its run in the console to see "
                "why it ended without one"
            )
        if self.contradicted and (self.row or "").lower() == self.gold.lower():
            return (
                "the posted answer's text must say the category of its own top row rose most, "
                "the row with the greatest rise_cents, and never another one: ask for the top "
                "category's row alone in the drill-down question"
            )
        if self.ambiguous:
            return (
                "the posted answer must name one top-level category as the one whose sales rose "
                "most, plainly, and return its row with its rise in cents in a column named "
                "rise_cents: ask for the top category's row alone in the drill-down question"
            )
        return (
            "the posted answer must say which top-level category's sales rose most, in its text "
            "and in its row's rise_cents: ask exactly that in the drill-down question"
        )


def drill_down(
    api, drill: dict[str, Any], gold: str, names: CategoryNames | None = None
) -> DrillDown:
    """Ask the drill-down question twice with its event id, approve any hold, wait for the run to
    end, and judge what it posted. The first ask must start a new run (the check cleared the event
    id first), so an earlier check's run is never judged again. A run made with a planted bug
    switched on in the stack (the missing idempotency starts a second run for the second ask)
    stops the check before the second ask, instead of failing the solution."""
    payload = {"question": drill["question"], "metric_family": "revenue"}
    first = api.submit("question.asked", payload, drill["event_id"])
    stop_on_planted(api.run(str(first.run_id)))
    second = api.submit("question.asked", payload, drill["event_id"])
    approver = ApproveHeld()
    detail = settle(api, str(first.run_id), approver)
    stop_on_planted(detail)
    once = second.duplicate and second.run_id == first.run_id
    names = category_names() if names is None else names
    answer = posted_answer(detail)
    return DrillDown(
        detail,
        gold,
        once,
        approver.held,
        posted_text(detail),
        not first.duplicate,
        names,
        None if answer is None else row_category(answer, names, gold),
    )


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
        typical="about 0.2 cents",
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
