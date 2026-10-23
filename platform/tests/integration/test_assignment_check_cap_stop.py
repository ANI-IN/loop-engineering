"""A check stopped at its spend cap, against the real api and Postgres, zero tokens (the worker's
model is scripted): the cap engages the kill switch through the api, the worker blocks the check's
queued run at claim, and the wind-down releases the switch and puts back the autonomy level, so the
stack ends as a normal end leaves it and nothing is left to spend."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import loops_paths  # noqa: F401  (before loops_support)
import pytest
from fastapi.testclient import TestClient
from loops_support import query_then_answer

from datapilot.assignments import cost
from datapilot.assignments.live import Api, event_id
from datapilot.contracts import RunStatus
from datapilot.loop3_events.api.app import app
from datapilot.loop3_events.worker import Worker, WorkerSettings
from datapilot.observability import spend

pytest_plugins = ["loops_fixtures"]
pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("clean_ops")]

COUNT_SCRIPT = query_then_answer("SELECT count(*) AS orders FROM orders", "There are 2000 orders.")


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_worker(services_for) -> Callable[..., Worker]:
    def build(script: Any = COUNT_SCRIPT) -> Worker:
        services = services_for({"analyst": script})
        return Worker(
            services,
            models_for=lambda _run_id, _activity: services.models,
            settings=WorkerSettings(lease_seconds=5.0, poll_seconds=0.05),
        )

    return build


def drain(worker: Worker, limit: int = 10) -> int:
    async def go() -> int:
        done = 0
        while done < limit and await worker.run_once():
            done += 1
        return done

    return asyncio.run(go())


def test_a_check_stopped_at_its_cap_leaves_the_stack_as_a_normal_end(
    client: TestClient, make_worker, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATAPILOT_SPEND_LEDGER", str(tmp_path / "ledger.sqlite"))
    assert client.post("/control/autonomy", json={"level": "assisted", "by": "test"}).is_success
    api = Api(str(client.base_url))
    api.http = client
    api.cap = cost.Cap(usd=1.00, mark=cost.ledger_mark(), activity="assignment", headroom_usd=0)

    submitted = api.submit(
        "question.asked", {"question": "How many orders are there?"}, event_id("test", "cap")
    )
    spend.record(  # the check's spend reaches its cap before the worker claims the run
        component="analyst",
        model="gpt-6-luna",
        usage=spend.Usage(0, 0, 2_000_000),
        activity="assignment",
    )
    with pytest.raises(cost.CapReached):
        api.wait(str(submitted.run_id), seconds=5)
    assert api.control().kill_switch == "engaged"
    with pytest.raises(cost.CapReached):
        api.submit("question.asked", {"question": "Another?"}, event_id("test", "cap"))

    drain(make_worker())
    assert api.run(str(submitted.run_id)).status is RunStatus.BLOCKED_KILLSWITCH

    assert api.wind_down(seconds=10) == []
    control = api.control()
    assert control.kill_switch == "released"
    assert control.autonomy_level.value == "assisted"
    assert drain(make_worker()) == 0  # nothing of the check is left to run, or to spend
