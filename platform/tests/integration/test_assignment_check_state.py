"""The checks' own state on the real Postgres, zero tokens: Assignment 3's check clears an earlier
check's drill-down run, whatever event id the learner chose, so its live step is always a new run;
a check's stack sets its daily token count back to zero without touching another day's; and
Assignment 4's check shares a live session's baseline only while every item is as it measured it."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime
from types import SimpleNamespace

import loops_paths  # noqa: F401  (before loops_support)
import pytest
from fastapi.testclient import TestClient

from datapilot import db
from datapilot.assignments import assignment, stack
from datapilot.assignments.runner import load_check
from datapilot.contracts import BenchmarkItem, ItemResult, Split
from datapilot.loop3_events.api.app import app
from datapilot.loop3_events.budget import add_usage, eastern_day
from datapilot.loop4_hill_climbing.experiment import ExperimentResult

pytest_plugins = ["loops_fixtures"]
pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("clean_ops")]

event_loop = load_check(assignment("event-loop").check_file)
DRILL = "drill-down:2026-01-30"  # a learner's own id, not starting with the job's key
OTHER = "someone-else:question"


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def _ask(client: TestClient, event_id: str) -> str:
    body = {
        "event_id": event_id,
        "type": "question.asked",
        "source": "test",
        "payload": {"question": "Which category changed most?"},
    }
    response = client.post("/events", json=body)
    assert response.is_success, response.text
    return response.json()["run_id"]


def _count(table: str, event_id: str) -> int:
    with db.connect(db.Role.APP) as conn:
        row = conn.execute(
            f"SELECT count(*) AS n FROM {table} WHERE event_id = %s", (event_id,)
        ).fetchone()
    return int(row["n"])


def test_an_earlier_checks_drill_down_run_is_cleared(client: TestClient) -> None:
    run_id = _ask(client, DRILL)
    _ask(client, OTHER)
    with db.connect(db.Role.APP) as conn:
        conn.execute(
            "INSERT INTO ops.posts (channel, run_id, label, body) VALUES (%s, %s, %s, %s)",
            (
                "analytics",
                run_id,
                "unverified",
                json.dumps(
                    {
                        "alert_key": "revenue-anomaly:2026-01-30",
                        "drill_down": {"event_id": DRILL, "question": "Which category?"},
                    }
                ),
            ),
        )
        conn.commit()
    assert _count("ops.runs", DRILL) == 1

    event_loop.clear_job_state()

    assert _count("ops.runs", DRILL) == 0 and _count("ops.events", DRILL) == 0
    assert _count("ops.runs", OTHER) == 1, "only the job's own events and drill-downs go"
    again = client.post(
        "/events",
        json={
            "event_id": DRILL,
            "type": "question.asked",
            "source": "test",
            "payload": {"question": "Which category changed most?"},
        },
    ).json()
    assert again["duplicate"] is False, "the first ask of the next check starts a new run"


def test_clearing_one_drill_down_leaves_every_other_event(client: TestClient) -> None:
    _ask(client, DRILL)
    _ask(client, OTHER)
    event_loop.clear_drill_down(DRILL)
    assert _count("ops.runs", DRILL) == 0 and _count("ops.runs", OTHER) == 1


def test_the_daily_token_count_goes_back_to_zero_for_today_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATAPILOT_ASSIGNMENT_STACK", raising=False)
    yesterday = date(2026, 10, 22)
    with db.connect(db.Role.APP) as conn:
        add_usage(conn, 2_100_000)
        add_usage(conn, 1_234, day=yesterday)
        conn.commit()
    assert stack.reset_daily_tokens(stack.DEFAULTS["COMPOSE_PROJECT_NAME"]) == 2_100_000
    with db.connect(db.Role.APP) as conn:
        rows = {
            r["day"]: r["tokens_used"]
            for r in conn.execute("SELECT day, tokens_used FROM ops.budgets").fetchall()
        }
    assert rows[eastern_day()] == 0 and rows[yesterday] == 1_234


# --- Assignment 4: a session's baseline is shared only while its items are unchanged -----------
hill_climbing_loop = load_check(assignment("hill-climbing-loop").check_file)
VERSION = "test-fingerprint-v1"


def _item(item_id: str, split: Split, gold: str = "SELECT 1") -> BenchmarkItem:
    return BenchmarkItem(
        id=item_id,
        question=f"the question of {item_id}",
        split=split,
        category="ratios",
        difficulty=1,
        metric_family="repeat_customers",
        gold_sql=gold,
    )


class _Runner:
    """Returns a finished experiment of the items, as the class runner would; no model call."""

    scheme = SimpleNamespace(holdout_repeats=3)
    concurrency = 1

    def __init__(self, session_id: uuid.UUID) -> None:
        self.session_id = session_id

    def run(self, items, version, *, session_id):
        return ExperimentResult(
            experiment_id=uuid.uuid4(),
            session_id=session_id,
            knowledge_version=version,
            splits=[Split.DEV, Split.HOLDOUT],
            results={
                i.id: ItemResult(item_id=i.id, passed=True, reason="ok", run_passes=[True])
                for i in items
            },
            splits_by_item={i.id: i.split for i in items},
            started_at=datetime.now(UTC),
            wall_seconds=1.0,
        )


def test_a_baseline_is_shared_until_an_items_gold_sql_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = uuid.uuid4()
    with db.connect(db.Role.APP) as conn:
        conn.execute(
            "INSERT INTO ops.live_sessions (session_id, started_by, timezone) "
            "VALUES (%s, 'test', 'UTC')",
            (session_id,),
        )
        conn.execute(
            "INSERT INTO ops.knowledge_versions (version, yaml, created_by) "
            "VALUES (%s, '', 'test') ON CONFLICT DO NOTHING",
            (VERSION,),
        )
        conn.commit()
    monkeypatch.setattr(hill_climbing_loop, "active_version", lambda: VERSION)
    items = [_item("fingerprint-dev", Split.DEV), _item("fingerprint-holdout", Split.HOLDOUT)]
    assert hill_climbing_loop.session_baseline(items) == (
        None,
        "this live session has no baseline yet",
    )
    saved = hill_climbing_loop._experiment(_Runner(session_id), items, VERSION, session_id)

    shared, why = hill_climbing_loop.session_baseline(items)
    assert shared is not None and shared.experiment_id == saved.experiment_id and why == ""

    changed = [items[0], _item("fingerprint-holdout", Split.HOLDOUT, gold="SELECT 2")]
    shared, why = hill_climbing_loop.session_baseline(changed)
    assert shared is None and "fingerprint-holdout" in why and "fingerprint-dev" not in why
    moved = [items[0], _item("fingerprint-holdout", Split.DEV)]
    assert hill_climbing_loop.session_baseline(moved)[0] is None
