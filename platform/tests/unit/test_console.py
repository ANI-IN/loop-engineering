"""The console without a browser or a database: demo controls by their registry labels, the api
client's calls, the view models, the trap marks, and the console's import boundary."""

from __future__ import annotations

import ast
import json
import re
import sys
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest

from datapilot import demo_questions
from datapilot.config import pack_config
from datapilot.contracts import registries
from datapilot.settings import PLATFORM

CONSOLE = PLATFORM / "console"
if str(CONSOLE) not in sys.path:
    sys.path.insert(0, str(CONSOLE))

from datapilot_console import sql_marks, views  # noqa: E402
from datapilot_console.api_client import API_DOWN, ApiClient, ApiError  # noqa: E402

SCREENS = {"Agent": "agent", "Verify": "verify", "Events": "events", "Improve": "improve"}
STARTED = datetime(2026, 10, 22, 11, 59, 9, tzinfo=UTC)
SESSION = uuid.uuid4()


# --- Every demo control exists on its page with its registry label ------------------------------


def _labels() -> list[tuple[str, str, str]]:
    out = []
    for demo in registries.demos().demos:
        page, label = (part.strip() for part in demo.trigger.console.split(">", 1))
        out.append((demo.id, page, label))
    return out


@pytest.mark.parametrize(("demo", "page", "label"), _labels())
def test_every_registry_control_is_on_its_page(demo: str, page: str, label: str) -> None:
    if page == "Status line":
        # The kill switch lives in the status line component, on every page.
        source = (CONSOLE / "datapilot_console" / "components" / "status_line.js").read_text()
        assert "'Kill switch'" in source and "Click again to stop all workers" in source
        return
    source = (CONSOLE / "screens" / f"{SCREENS[page]}.py").read_text(encoding="utf-8")
    assert f'"{label}"' in source, f"{demo}: no control labelled {label!r} on the {page} page"


# The class screen: 1280 pixels wide, less the wide layout's side padding (5rem each side), with a
# 1rem gap between columns; a 16-pixel label is at most 9 pixels a character, plus the padding.
SCREEN_PIXELS, COLUMN_GAP, CHARACTER_PIXELS, BUTTON_PADDING = 1280 - 160, 16, 9, 32


def _button_rows(source: str) -> list[tuple[list[float], list[tuple[int, str]]]]:
    """Every `name = st.columns(...)` row of a page and the literal button labels in it."""
    tree = ast.parse(source)
    rows: dict[str, tuple[list[float], list[tuple[int, str]]]] = {}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Call)
            and getattr(node.value.func, "attr", "") == "columns"
        ):
            spec = ast.literal_eval(node.value.args[0])
            weights = [1.0] * spec if isinstance(spec, int) else [float(w) for w in spec]
            rows[node.targets[0].id] = (weights, [])
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and getattr(node.func, "attr", "") == "button"
            and isinstance(node.func.value, ast.Subscript)
            and isinstance(node.func.value.value, ast.Name)
            and node.func.value.value.id in rows
            and node.args
            and isinstance(node.args[0], ast.Constant)
        ):
            index = ast.literal_eval(node.func.value.slice)
            rows[node.func.value.value.id][1].append((index, node.args[0].value))
    return list(rows.values())


def test_the_improve_page_buttons_show_their_whole_labels_at_1280_pixels() -> None:
    # Review round 2 (R2B-14): the four buttons in one row cut two labels at the class screen.
    source = (CONSOLE / "screens" / "improve.py").read_text(encoding="utf-8")
    rows = _button_rows(source)
    labels = [label for _, buttons in rows for _, label in buttons]
    assert "Run experiment on the active version" in labels
    assert "Add the over-broad rule to the active version" in labels
    for weights, buttons in rows:
        room = SCREEN_PIXELS - COLUMN_GAP * (len(weights) - 1)
        for index, label in buttons:
            column = room * weights[index] / sum(weights)
            needed = len(label) * CHARACTER_PIXELS + BUTTON_PADDING
            assert needed <= column, f"{label!r} needs {needed} pixels, its column has {column:.0f}"


def test_the_console_never_imports_loop_internals_specimens_or_tests() -> None:
    forbidden = re.compile(r"^(datapilot\.loop\d|design(\.|$)|tests|conftest|pytest|unittest)")
    found = []
    for path in CONSOLE.rglob("*.py"):
        if "design" in path.relative_to(CONSOLE).parts:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            found += [f"{path.name}: {n}" for n in names if forbidden.match(n)]
    assert found == []


def test_component_sources_never_write_markup_or_banned_styles() -> None:
    folder = CONSOLE / "datapilot_console" / "components"
    text = "\n".join(p.read_text(encoding="utf-8") for p in folder.iterdir())
    for banned in ("innerHTML", "box-shadow", "gradient", "text-transform"):
        assert banned not in text, banned
    # Limits come from pack.yaml in the data, never from constants in the JS.
    js = "\n".join(p.read_text(encoding="utf-8") for p in folder.glob("*.js"))
    assert "data.per_lane" in js and "disarm_seconds" in js


# --- The api client ------------------------------------------------------------------------------


NOW = "2026-10-22T11:59:09+00:00"
RUN = "6f1c2c1e-0000-4000-8000-000000000001"
# A valid reply per endpoint, in the shape of its datapilot.contracts.api response model.
REPLIES: dict[str, dict[str, Any]] = {
    "/events": {
        "event_id": "e",
        "run_id": RUN,
        "job_id": 1,
        "duplicate": False,
        "duplicates_ignored": 0,
        "created_at": NOW,
    },
    "/demo/": {
        "event_id": "e",
        "run_id": RUN,
        "job_id": 1,
        "duplicate": False,
        "duplicates_ignored": 0,
        "created_at": NOW,
    },
    "/approvals/": {"run_id": RUN, "decision": "approve", "kind": "tool_call", "status": "running"},
    "/control/kill-switch": {"kill_switch": "engaged"},
    "/experiments/run": {
        "request_id": RUN,
        "kind": "experiment",
        "params": {},
        "status": "queued",
        "session_id": None,
        "requested_by": "console",
        "requested_at": NOW,
    },
    "/knowledge/": {
        "version": "v2",
        "status": "approved",
        "approved_by": "console",
        "approved_at": NOW,
    },
}


def _client(calls: list[tuple[str, str, Any]], status: int = 200) -> ApiClient:
    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        calls.append((request.method, request.url.path, body))
        if status >= 400:
            return httpx.Response(status, json={"detail": "refused here"})
        path = request.url.path
        reply = next(
            v for k, v in REPLIES.items() if path == k or (k.endswith("/") and path.startswith(k))
        )
        return httpx.Response(200, json=reply)

    http = httpx.Client(base_url="http://api.test", transport=httpx.MockTransport(handle))
    return ApiClient("http://api.test", http=http)


def test_each_action_is_one_documented_api_call() -> None:
    calls: list[tuple[str, str, Any]] = []
    client = _client(calls)
    client.ask("How many orders?", "agent-simple-question")
    client.demo("large-query")
    client.decide(RUN, "approve")
    client.stop_all()
    client.run_experiment("active", plus_rule="knowledge-v2-overbroad")
    client.approve_version("v2", "Priya")
    paths = [(m, p) for m, p, _ in calls]
    assert paths == [
        ("POST", "/events"),
        ("POST", "/demo/large-query"),
        ("POST", f"/approvals/{RUN}"),
        ("POST", "/control/kill-switch"),
        ("POST", "/control/kill-switch"),
        ("POST", "/experiments/run"),
        ("POST", "/knowledge/v2/approve"),
    ]
    assert calls[0][2]["type"] == "question.asked"
    assert calls[0][2]["payload"] == {
        "question": "How many orders?",
        "demo_name": "agent-simple-question",
    }
    assert [c[2]["action"] for c in calls[3:5]] == ["arm", "engage"]
    assert calls[5][2]["plus_rule"] == "knowledge-v2-overbroad"


def test_the_naive_analyzer_button_queues_both_requests_with_the_demos_own_flag() -> None:
    """Improve > Run the naive analyzer (planted) sends what `make demo
    NAME=improve-naive-analyzer-blocked` sends: the analyzer, then the candidate experiment, each
    with the demo's flag in the planted header and the demo's name beside it."""
    seen: list[tuple[str, dict[str, str], Any]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        seen.append((request.url.path, dict(request.headers), body))
        kind = "analyzer" if request.url.path == "/analyzer/run" else "experiment"
        return httpx.Response(200, json={**REPLIES["/experiments/run"], "kind": kind})

    http = httpx.Client(base_url="http://api.test", transport=httpx.MockTransport(handle))
    client = ApiClient("http://api.test", http=http)
    sent = client.run_naive_analyzer()
    assert [path for path, _, _ in seen] == ["/analyzer/run", "/experiments/run"]
    assert seen[1][2]["target"] == "candidate"
    for _, headers, _ in seen:
        assert headers["datapilot-planted"] == "BUG_NAIVE_ANALYZER"
        assert headers["datapilot-demo"] == "improve-naive-analyzer-blocked"
    assert [request.kind for request in sent] == ["analyzer", "experiment"]
    seen.clear()
    client.run_analyzer()  # the analyzer team's button: no planted header
    assert [path for path, _, _ in seen] == ["/analyzer/run"]
    assert "datapilot-planted" not in seen[0][1]


def test_the_naive_analyzer_button_shows_only_while_demo_controls_are_allowed() -> None:
    source = (CONSOLE / "screens" / "improve.py").read_text(encoding="utf-8")
    shown = "get_settings().datapilot_allow_demo_controls and optional[1].button(\n"
    assert shown + '        "Run the naive analyzer (planted)"' in source


def test_agent_ask_labels_a_typed_question_with_the_demo_that_asks_it_or_none() -> None:
    # Review round 3 (R3B-05): Agent > Ask labelled every typed question the simple-question
    # demo. A question a Section 1 demo asks carries that demo's name; any other carries none.
    agent = demo_questions.AGENT_ASK_DEMOS
    simple = demo_questions.question_for("agent-simple-question")
    assert demo_questions.demo_asking(f"  {simple} ", agent) == "agent-simple-question"
    texas = demo_questions.question_for("agent-texas-last-quarter")
    assert demo_questions.demo_asking(texas, agent) == "agent-texas-last-quarter"
    spine = demo_questions.SPINE_QUESTION
    assert demo_questions.demo_asking(spine, agent) == "agent-confident-wrong-answer"
    assert demo_questions.demo_asking("How many customers live in Ohio?", agent) is None
    calls: list[tuple[str, str, Any]] = []
    _client(calls).ask("How many customers live in Ohio?", None)
    assert calls[0][2]["payload"] == {"question": "How many customers live in Ohio?"}
    assert calls[0][2]["event_id"].startswith("console:console:")


def test_the_client_uses_the_contract_table_and_has_no_endpoint_list_of_its_own() -> None:
    source = (CONSOLE / "datapilot_console" / "api_client.py").read_text(encoding="utf-8")
    assert "contract.endpoint(" in source and "ENDPOINTS: " not in source
    assert "class EventIn" not in source and "BaseModel" not in source


def test_every_send_is_a_fresh_event_except_the_deliberate_duplicates() -> None:
    calls: list[tuple[str, str, Any]] = []
    client = _client(calls)
    client.ask("q", "agent-simple-question")
    client.ask("q", "agent-simple-question")
    client.send_three_times("q")
    ids = [c[2]["event_id"] for c in calls]
    assert ids[0] != ids[1]
    assert len(set(ids[2:])) == 1 and ids[2] not in ids[:2]


def test_api_down_and_refusals_say_what_to_do() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    http = httpx.Client(base_url="http://api.test", transport=httpx.MockTransport(refuse))
    down = ApiClient("http://api.test", http=http)
    with pytest.raises(ApiError, match=re.escape(API_DOWN)):
        down.ask("q", "agent-simple-question")
    assert down.healthy() is False
    with pytest.raises(ApiError, match="refused here"):
        _client([], status=409).decide(RUN, "reject")


# --- View models ---------------------------------------------------------------------------------


def _state(**overrides: Any) -> dict[str, Any]:
    state = {
        "kill_switch": "released",
        "autonomy_level": "assisted",
        "family_levels": {"revenue": "unattended"},
        "tokens_used": 1_700_000,
        "token_limit": 2_000_000,
        "planted_active": ["BUG_NAIVE_GUARD", "DEMO_PACING"],
    }
    return {**state, **overrides}


def _status(**overrides: Any) -> dict[str, Any]:
    chips = {i.id: i.chip for i in registries.planted().items}
    return views.status_line_view(
        session=None,
        business_date="Business date: 31 January 2026",
        display_tz=None,
        state=_state(**overrides),
        families=list(pack_config()["autonomy"]["metric_families"]),
        tokens_cap_default=100,
        planted_chips=chips,
        pacing_seconds=2.0,
        disarm_seconds=pack_config()["console"]["kill_switch_disarm_seconds"],
        notice=None,
    )


def test_the_status_line_view_uses_words_chips_and_the_pack_limits() -> None:
    view = _status()
    assert view["autonomy"] == "assisted level" and not view["forced"]
    assert view["families"][0] == {"name": "revenue", "cleared": True}
    assert {"name": "average order value", "cleared": False} in view["families"]
    assert view["gauge"] == "near" and view["planted"] == ["Naive guard"] and view["pacing"] == 2.0
    assert view["disarm_seconds"] == pack_config()["console"]["kill_switch_disarm_seconds"]
    engaged = _status(kill_switch="engaged", autonomy_level="report_only", tokens_used=2_000_000)
    assert engaged["kill"] == "engaged" and engaged["forced"] and engaged["gauge"] == "cap"


def _run(status: str, event: dict[str, Any] | None = None, **extra: Any) -> dict[str, Any]:
    return {
        "run_id": uuid.uuid4(),
        "question": "How many orders?",
        "status": status,
        "autonomy_level_applied": extra.get("level"),
        "langsmith_url": "https://smith.example/r",
        "created_at": STARTED,
        "started_at": STARTED,
        "last_event": event,
    }


def test_strips_carry_lane_word_shape_step_and_a_utc_stamp() -> None:
    running = views.strip_view(
        _run("running", {"kind": "tool_call_started", "payload": {"tool": "run_query"}}), SESSION
    )
    assert (running["lane"], running["word"], running["edge"]) == ("running", "Running", "solid")
    assert (running["step"], running["step_code"]) == ("Calling ", "run_query")
    assert running["stamp"]["started_at_utc"] == "2026-10-22T11:59:09+00:00"
    held = views.strip_view(
        _run(
            "awaiting_approval", {"kind": "approval_requested", "payload": {"reason": "412 rows"}}
        ),
        SESSION,
        duplicates=2,
    )
    assert held["review"] and held["step"] == "412 rows" and held["duplicates"] == 2
    posted = views.strip_view(_run("posted", level="report_only"), SESSION)
    assert posted["step"] == "Posted at the report-only level"
    blocked = views.strip_view(
        _run("blocked_killswitch", {"kind": "killswitch_blocked", "payload": {"at": "in flight"}}),
        SESSION,
    )
    assert blocked["lane"] == "blocked_killswitch" and blocked["edge"] == "struck"
    assert (posted["gold"], posted["gold_text"]) == ("", "")  # no gold check yet


def _gold_event(passed: bool, agent: str, labels: list[str] | None = None) -> dict[str, Any]:
    payload = {
        "grader": "gold",
        "passed": passed,
        "agent_value": agent,
        "gold_value": "64015091.21",
        "reason": "matches gold on both warehouses" if passed else "warehouse: values differ",
        "trap_labels": labels or [],
    }
    return {"kind": "grader_result", "payload": payload}


def test_the_finale_strip_shows_its_gold_check_pass_or_fail() -> None:
    # Review round 2 (R2B-04): the class-day safeguard's trigger is a failed gold check on the
    # finale, an Events run, so its strip shows the check the runner wrote.
    passed = views.strip_view(
        {**_run("posted", level="unattended"), "gold_event": _gold_event(True, "64015091.21")},
        SESSION,
    )
    assert (passed["gold"], passed["gold_text"]) == ("pass", "Gold check passed: 64,015,091.21")
    failed = views.strip_view(
        {**_run("posted", level="unattended"), "gold_event": _gold_event(False, "72394572.08")},
        SESSION,
    )
    assert failed["gold"] == "fail"
    assert failed["gold_text"] == "Gold check failed: 72,394,572.08, gold 64,015,091.21"


def test_a_passed_gold_check_shows_no_trap_note() -> None:
    # Review round 2 (R2B-07): a gold check recorded with a label on a match draws no note.
    passed = views.gold_check([_gold_event(True, "1", ["calendar_year_range"])])
    assert passed is not None and passed["trap_labels"] == []
    failed = views.gold_check([_gold_event(False, "2", ["calendar_year_range"])])
    assert failed is not None and failed["trap_labels"] == ["calendar_year_range"]


def _experiment(version: str, status: str, per_example: list[dict[str, Any]], **kw: Any) -> dict:
    return {
        "experiment_id": uuid.uuid4(),
        "knowledge_version": version,
        "version_status": status,
        "split": "all",
        "holdout_repeats": 3,
        "per_example": per_example,
        "langsmith_url": f"https://smith.example/list?version={version}",
        "started_at": kw.get("started_at", STARTED),
        "finished_at": kw.get("finished_at"),
    }


def _item(item: str, passes: list[bool], **extra: Any) -> dict[str, Any]:
    return {"item_id": item, "split": "holdout", "run_passes": passes, **extra}


def test_a_benchmark_is_one_grouped_strip_with_its_run_count() -> None:
    total = views.planned_runs("all", dev_items=25, holdout_items=15, repeats=3)
    assert total == 70
    running = _experiment(
        "v1", "active", [_item("a", [True] * 3), {"item_id": "d", "split": "dev"}]
    )
    strip = views.benchmark_strip_view(running, SESSION, total=total, expanded=False)
    assert strip["question"] == "Baseline benchmark: 4 of 70 runs done"
    assert strip["lane"] == "running" and strip["kind"] == "benchmark"
    done = views.benchmark_strip_view(
        {**running, "finished_at": STARTED}, SESSION, total=total, expanded=True
    )
    assert done["lane"] == "done" and done["question"].endswith("70 of 70 runs done")


def test_the_ledger_marks_flips_regressions_and_the_confirmation_step() -> None:
    later = STARTED + timedelta(minutes=5)
    baseline = _experiment(
        "v1", "active", [_item("a", [False] * 3), _item("b", [True] * 3), _item("c", [True] * 3)]
    )
    candidate = _experiment(
        "v2",
        "draft",
        [
            _item("a", [True] * 3),
            _item("b", [False] * 3, confirmation={"state": "confirming", "runs": 3}),
            _item("c", [False] * 3, confirmation={"state": "confirmed", "runs": 3, "failures": 3}),
        ],
        started_at=later,
    )
    assert views.pick_experiments([baseline, candidate]) == (baseline, candidate)
    ledger = views.ledger_view(
        [("a", "A?"), ("b", "B?"), ("c", "C?"), ("d", "D?")],
        baseline=baseline,
        candidate=candidate,
        session_id=SESSION,
        display_tz=None,
        repeats=3,
        pass_threshold=2,
    )
    rows = {r["item"]: r for r in ledger["rows"]}
    assert rows["a"]["change"] == "fixed"
    assert rows["b"]["change_text"] == "Apparent regression: confirming with 3 more runs"
    assert rows["c"]["change"] == "regression" and "confirmed" in rows["c"]["change_text"]
    assert rows["d"]["active"] == {"pending": True}
    assert ledger["summary_text"].endswith("1 fixed, 1 regression.")
    assert ledger["trace_list_url"].endswith("version=v2") and ledger["list_version"] == "v2"


def test_no_baseline_in_this_session_means_no_ledger_rows() -> None:
    assert views.pick_experiments([_experiment("v2", "draft", [])]) == (None, None)
    assert views.no_baseline_view() == {"state": "no_baseline"}


def test_checklist_defense_and_gold_read_the_run_events() -> None:
    events = [
        {"kind": "grader_result", "payload": {"grader": "parse", "passed": True, "attempt": 1}},
        {
            "kind": "grader_result",
            "payload": {
                "grader": "cost",
                "passed": False,
                "attempt": 2,
                "reason": "estimated 1.2 million rows",
            },
        },
        {
            "kind": "grader_result",
            "payload": {
                "grader": "defense: x",
                "sql": "DELETE FROM orders",
                "layers": [{"layer": "guard", "stopped": True}, {"layer": "role", "stopped": True}],
            },
        },
        {
            "kind": "grader_result",
            "payload": {"grader": "gold", "passed": False, "trap_labels": ["total_cents_used"]},
        },
        {"kind": "tool_call_finished", "payload": {"tool": "run_query", "ms": 3800}},
    ]
    checklist = views.checklist(events, max_attempts=3)
    assert checklist["attempt"] == 2
    states = {r["grader"]: r["state"] for r in checklist["rows"]}
    assert states["cost"] == "failed" and states["parse"] == "not_run"
    layers = views.defense_layers(events)[0]["layers"]
    assert [layer["word"] for layer in layers] == ["Stopped it", "Not reached"]
    assert views.gold_check(events)["trap_labels"] == ["total_cents_used"]
    assert views.tool_calls(events)[0]["label"] == "run_query 3.8 s"


def test_trap_marks_point_at_real_columns_and_never_overlap() -> None:
    sql = (
        "SELECT round(sum(o.total_cents) / 100.0, 2)\n"
        "FROM warehouse.orders o\n"
        "WHERE o.order_ts >= '2025-01-01' AND o.order_ts < '2026-01-01'"
    )
    view = views.sql_view(
        sql,
        ["total_cents_used", "calendar_year_range", "missing_status_filter", "utc_truncation"],
        stamp=None,
        display_tz=None,
    )
    lines = view["lines"]
    marked = [lines[m["line"]][m["start"] : m["end"]] for m in view["marks"]]
    assert marked[:4] == ["total_cents", "'2025-01-01'", "'2026-01-01'", "warehouse.orders"]
    assert "order_ts" in marked
    assert [n["trap"] for n in view["notes"]] == [
        "Net revenue",
        "Fiscal year",
        "Cancelled orders",
        "Eastern time",
    ]
    spans = sorted((m["line"], m["start"], m["end"]) for m in view["marks"])
    assert all(a[0] != b[0] or a[2] <= b[1] for a, b in zip(spans, spans[1:], strict=False))
    assert views.sql_view(None, [], stamp=None, display_tz=None)["state"] == "waiting"
    assert sql_marks.annotate(["SELECT 1"], ["unknown_label"]) == []


# The confident wrong answer's final SQL as the analyst wrote it (run bd50f9ca, the Section 1
# capture), and the calendar-year ranges of other live runs' final SQL.
SPINE_WRONG_SQL = (
    "SELECT ROUND(SUM(subtotal_cents - discount_cents) / 100.0, 2) AS net_revenue_dollars "
    "FROM orders WHERE order_ts >= TIMESTAMPTZ '2025-01-01 00:00:00-05' "
    "AND order_ts < TIMESTAMPTZ '2026-01-01 00:00:00-05' AND status = 4"
)
CALENDAR_YEAR_SQL = {
    "timestamptz with an offset": (
        SPINE_WRONG_SQL,
        ["TIMESTAMPTZ '2025-01-01 00:00:00-05'", "TIMESTAMPTZ '2026-01-01 00:00:00-05'"],
    ),
    "timestamptz in UTC, two lines": (
        "SELECT o.customer_id, round(sum(o.subtotal_cents - o.discount_cents) / 100.0, 2)\n"
        "FROM orders o\n"
        "WHERE o.order_ts >= TIMESTAMPTZ '2025-01-01 00:00:00+00'\n"
        "  AND o.order_ts < TIMESTAMPTZ '2026-01-01 00:00:00+00'\n"
        "GROUP BY o.customer_id",
        ["TIMESTAMPTZ '2025-01-01 00:00:00+00'", "TIMESTAMPTZ '2026-01-01 00:00:00+00'"],
    ),
    "date literals in Eastern time": (
        "SELECT COUNT(*) AS order_count\n"
        "FROM warehouse.orders o\n"
        "WHERE (o.order_ts AT TIME ZONE 'America/New_York')::date >= DATE '2025-01-01'\n"
        "  AND (o.order_ts AT TIME ZONE 'America/New_York')::date < DATE '2026-01-01'",
        ["DATE '2025-01-01'", "DATE '2026-01-01'"],
    ),
    "bare date strings": (
        "SELECT count(*) FROM orders WHERE order_ts >= '2025-01-01' AND order_ts < '2026-01-01'",
        ["'2025-01-01'", "'2026-01-01'"],
    ),
    "a closed range with a cast": (
        "SELECT count(*) FROM orders\n"
        "WHERE order_ts::date BETWEEN '2025-01-01'::date AND '2025-12-31 23:59:59'::date",
        ["'2025-01-01'::date", "'2025-12-31 23:59:59'::date"],
    ),
    "the year part": (
        "SELECT sum(subtotal_cents) FROM orders WHERE EXTRACT(YEAR FROM order_ts) = 2025",
        ["EXTRACT(YEAR FROM order_ts)"],
    ),
}


@pytest.mark.parametrize("case", sorted(CALENDAR_YEAR_SQL))
def test_fiscal_year_trap_marks_the_range_the_analyst_wrote(case: str) -> None:
    from datapilot.loop4_hill_climbing import trap_detectors

    sql, expected = CALENDAR_YEAR_SQL[case]
    assert "calendar_year_range" in trap_detectors.detect(sql)  # the label the gold check gives
    view = views.sql_view(sql, ["calendar_year_range"], stamp=None, display_tz=None)
    lines = view["lines"]
    marked = [lines[m["line"]][m["start"] : m["end"]] for m in view["marks"] if m["n"] == 1]
    assert marked == expected


def test_the_spine_capture_marks_every_trap_it_names() -> None:
    labels = ["calendar_year_range", "utc_truncation", "missing_internal_filter"]
    notes = sql_marks.annotate([SPINE_WRONG_SQL], labels)
    assert [n.trap for n in notes] == ["Fiscal year", "Eastern time", "Internal accounts"]
    assert all(note.marks for note in notes)
    assert all(sql_marks.NO_MARK not in note.text for note in notes)


def test_defense_layers_wrap_a_long_statement(monkeypatch: pytest.MonkeyPatch) -> None:
    # The data-modifying CTE is the statement the demo is about: it wraps, never cut at the edge.
    from datapilot_console import widgets

    shown: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(widgets.st, "code", lambda body, **kw: shown.append((body, kw)))
    monkeypatch.setattr(widgets.st, "markdown", lambda *args, **kw: None)
    cte = "WITH d AS (DELETE FROM orders RETURNING *) SELECT count(*) FROM d"
    layer = {"word": "Stopped it", "layer": "guard", "detail": "statement_policy"}
    widgets.defense({"defense": [{"sql": cte, "layers": [layer]}]})
    assert shown == [(cte, {"language": "sql", "wrap_lines": True})]


def test_a_trap_note_never_shows_a_number_with_nothing_marked() -> None:
    # The gold check named the trap, but no fragment of this text shows it: the note says so.
    notes = sql_marks.annotate(["SELECT 1"], ["calendar_year_range", "total_cents_used"])
    assert [n.trap for n in notes] == ["Fiscal year", "Net revenue"]
    for note in notes:
        assert note.marks == []
        assert note.text.endswith(sql_marks.NO_MARK)
