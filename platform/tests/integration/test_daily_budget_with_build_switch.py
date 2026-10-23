"""The daily token budget holds with DATAPILOT_BUILD_BUDGET off (a learner's machine) and on (the
build): an exhausted day blocks a run before its claim, and a run that crosses the day's limit is
stopped. The other run limits have the same test without a database
(unit/test_build_budget_scope.py). Tests' Postgres, scripted models, zero tokens."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import loops_paths  # noqa: F401  (before loops_support)
import pytest
from fastapi.testclient import TestClient
from loops_support import query_then_answer

from datapilot import db
from datapilot.config import pack_config
from datapilot.loop1_agent.guard import StopReason
from datapilot.loop3_events import budget
from datapilot.loop3_events.api.app import app
from datapilot.loop3_events.worker import Worker, WorkerSettings, _daily_budget_stop
from datapilot.observability import spend

pytest_plugins = ["loops_fixtures"]
pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("clean_ops")]

COUNT_SQL = "SELECT count(*) AS orders FROM orders"


@pytest.fixture(params=["0", "1"], ids=["switch-off-learners", "switch-on-the-build"])
def switch(request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("DATAPILOT_SPEND_LEDGER", str(tmp_path / "ledger.sqlite"))
    monkeypatch.setenv("DATAPILOT_BUILD_BUDGET", request.param)
    return request.param


def execute(query: str, *params: Any) -> list[dict]:
    with db.connect(db.Role.OWNER) as conn:
        cursor = conn.execute(query, params)
        rows = cursor.fetchall() if cursor.description else []
        conn.commit()
    return rows


def ask(client: TestClient) -> str:
    body = {"type": "question.asked", "payload": {"question": "How many orders are there?"}}
    response = client.post("/events", json={"event_id": f"budget:{uuid.uuid4().hex}", **body})
    assert response.status_code == 200, response.text
    return response.json()["run_id"]


def drain(worker: Worker) -> None:
    async def go() -> None:
        for _ in range(5):
            if not await worker.run_once():
                return

    asyncio.run(go())


@pytest.fixture
def make_worker(services_for) -> Callable[..., Worker]:
    def build() -> Worker:
        services = services_for({"analyst": query_then_answer(COUNT_SQL, "2000 orders.")})
        return Worker(
            services,
            models_for=lambda _run_id, _activity: services.models,
            settings=WorkerSettings(lease_seconds=5.0, poll_seconds=0.05),
        )

    return build


def test_the_day_limit_is_the_pack_value_either_way(switch: str) -> None:
    assert spend.build_budget_on() is (switch == "1")
    with db.connect(db.Role.APP) as conn:
        assert not budget.exhausted(conn)
        conn.commit()
    limit = execute("SELECT token_limit FROM ops.budgets")[0]["token_limit"]
    assert limit == pack_config()["budgets"]["tokens_per_day"]


def test_an_exhausted_day_blocks_the_run_before_its_claim(switch: str, make_worker) -> None:
    execute(
        "INSERT INTO ops.budgets (day, token_limit, tokens_used) VALUES (%s, 100, 100)",
        budget.eastern_day(),
    )
    assert _daily_budget_stop() is StopReason.DAILY_BUDGET
    with TestClient(app) as client:
        run_id = ask(client)
        drain(make_worker())
        assert client.get(f"/runs/{run_id}").json()["status"] == "blocked_budget"


def test_a_run_that_crosses_the_day_limit_is_stopped(switch: str, make_worker) -> None:
    execute(
        "INSERT INTO ops.budgets (day, token_limit, tokens_used) VALUES (%s, 100, 0)",
        budget.eastern_day(),
    )
    with TestClient(app) as client:
        run_id = ask(client)  # the first model call uses 120 tokens: past the limit of 100
        drain(make_worker())
        detail = client.get(f"/runs/{run_id}").json()
    assert detail["status"] == "blocked_budget", detail["status"]
    assert execute("SELECT tokens_used FROM ops.budgets")[0]["tokens_used"] >= 100
