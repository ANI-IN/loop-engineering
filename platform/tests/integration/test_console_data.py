"""What each console page's data functions return for seeded ops rows (Compose Postgres).

Every test seeds inside one transaction and rolls it back, so ops is left as it was found. Only
runs and experiments of the open live session ever reach a view.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import console_seed as seed
import pytest

from datapilot import db
from datapilot.settings import PLATFORM

sys.path.insert(0, str(PLATFORM / "console"))

from datapilot_console import events_view, improve_view, ops_reads, run_view, views  # noqa: E402
from datapilot_console.frame import Live  # noqa: E402

pytestmark = pytest.mark.integration


@pytest.fixture
def conn() -> Iterator[Any]:
    with db.connect(db.Role.APP) as connection:
        yield connection
        connection.rollback()


def _live(conn: Any) -> Live:
    session = views.session_model(ops_reads.open_session(conn))
    return Live(conn, session, changed=True)


def test_no_session_shows_nothing_and_says_so(conn: Any) -> None:
    seed.end_sessions(conn)
    live = _live(conn)
    board = events_view.board(live, open_ledger=None)
    assert board["session_open"] is False and board["strips"] == []
    assert improve_view.build(live)["ledger"] == {"state": "no_baseline"}
    assert run_view.build(live, None, "agent-")["run"] is None


def test_the_board_shows_only_this_sessions_runs_and_one_strip_per_benchmark(conn: Any) -> None:
    old = seed.open_session(conn, started_at=seed.now() - timedelta(hours=2))
    seed.add_run(conn, old, "posted", question="An older session's run")
    session = seed.open_session(conn, started_at=seed.now() - timedelta(minutes=20))
    runs = seed.events_scene(conn, session)
    seed.add_duplicates(conn, runs["done-0"], 2)
    board = events_view.board(_live(conn), open_ledger=None)
    strips = board["strips"]
    assert "An older session's run" not in {s["question"] for s in strips}
    lanes = {}
    for strip in strips:
        lanes.setdefault(strip["lane"], []).append(strip)
    assert {s["word"] for s in lanes["running"]} == {"Running"}
    benchmarks = [s for s in strips if s["kind"] == "benchmark"]
    assert len(benchmarks) == 1
    assert benchmarks[0]["question"] == "Baseline benchmark: 27 of 70 runs done"
    assert len(lanes["blocked_killswitch"]) == 2 and len(lanes["holding"]) == 1
    holding = lanes["holding"][0]
    assert holding["review"] and holding["step"] == "412 rows of personal data"
    assert next(s for s in strips if s["run_id"] == str(runs["done-0"]))["duplicates"] == 2
    assert all(s["stamp"]["started_at_utc"].endswith("+00:00") for s in strips)
    assert board["per_lane"] == 2


def test_the_status_line_reads_control_clearance_tokens_and_planted_items(conn: Any) -> None:
    session = seed.open_session(conn)
    seed.events_scene(conn, session)
    seed.set_control(conn, kill_switch="engaged", level="report_only")
    state = ops_reads.status(conn, session)
    assert state["kill_switch"] == "engaged" and state["autonomy_level"] == "report_only"
    assert state["family_levels"]["revenue"] == "unattended"
    assert state["tokens_used"] == 412_000
    assert "BUG_NAIVE_GUARD" in state["planted_active"]


def test_the_watermark_changes_only_when_something_shown_changes(conn: Any) -> None:
    session = seed.open_session(conn)
    run_id = seed.add_run(conn, session, "queued")
    first = ops_reads.watermark(conn, session)
    assert ops_reads.watermark(conn, session) == first
    seed.set_status(conn, run_id, "running")
    assert ops_reads.watermark(conn, session) != first


def test_the_agent_page_shows_the_run_with_tool_calls_traps_and_gold(conn: Any) -> None:
    session = seed.open_session(conn)
    run_id = seed.agent_scene(conn, session)
    view = run_view.build(_live(conn), None, "agent-")
    assert view["run"]["run_id"] == str(run_id) and view["run"]["word"] == "Answered"
    assert [t["tool"] for t in view["tools"]] == ["list_tables", "describe_table", "run_query"]
    assert view["gold"]["passed"] is False
    assert [n["trap"] for n in view["sql"]["notes"]][:2] == ["Net revenue", "Fiscal year"]
    assert view["sql"]["stamp"]["run_id"] == str(run_id)
    assert view["run"]["summary"] == "7,912 tokens, $0.0040, 6.2 s"


def test_the_verify_page_shows_the_retry_cap_and_the_defense_layers(conn: Any) -> None:
    session = seed.open_session(conn)
    seed.verify_scene(conn, session, "malicious")
    defense = run_view.build(_live(conn), None, "verify-")["defense"]
    assert [s["layers"][-1]["word"] for s in defense] == ["Stopped it", "Stopped it"]
    retry_id = seed.verify_scene(conn, session, "retry")
    view = run_view.build(_live(conn), str(retry_id), "verify-")
    assert view["run"]["status"] == "escalated"
    assert view["checklist"]["attempt"] == 3 and view["checklist"]["max_attempts"] == 3
    failed = [r for r in view["checklist"]["rows"] if r["state"] == "failed"]
    assert [r["label"] for r in failed] == ["Injected failing grader"]


def test_the_improve_page_uses_only_this_sessions_baseline(conn: Any) -> None:
    old = seed.open_session(conn, started_at=seed.now() - timedelta(hours=2))
    seed.ensure_versions(conn)
    seed.add_experiment(
        conn, old, "v1", [seed.holdout_result("orders-black-friday-2025", [True] * 3)]
    )
    session = seed.open_session(conn)
    assert improve_view.build(_live(conn))["ledger"]["state"] == "no_baseline"
    seed.improve_scene(conn, session)
    view = improve_view.build(_live(conn))
    ledger = view["ledger"]
    assert ledger["state"] == "live" and ledger["candidate_version"] == "v2"
    rows = {r["item"]: r for r in ledger["rows"]}
    assert rows["average-list-price-active"]["change"] == "regression"
    assert rows["app-share-net-revenue-fiscal-2026"]["candidate"] == {"pending": True}
    assert len(ledger["rows"]) == 15
    assert "+  - id: fiscal-year" in view["diff"]
    assert view["candidate"] == {"version": "v2", "status": "draft"}


def test_one_events_page_read_is_well_under_half_a_second(conn: Any) -> None:
    session = seed.open_session(conn)
    seed.events_scene(conn, session)
    seed.improve_scene(conn, session)
    live = _live(conn)
    started = time.perf_counter()
    ops_reads.watermark(conn, session)
    ops_reads.status(conn, session)
    events_view.board(live, open_ledger=None)
    events_view.channel(live)
    assert time.perf_counter() - started < 0.25
