"""Every registry demo is a fresh live run: triggered twice, it gives two distinct ids with strictly
newer timestamps, tagged with the open live session; a new session tags new runs with its own id.

The stub model is injected here, at test level only; the demo trigger code is the same code
`make demo NAME=` runs against the api. Zero tokens.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import datetime

import loops_paths  # noqa: F401  (before loops_support)
import pytest
from fastapi.testclient import TestClient
from loops_support import query_then_answer

from datapilot.contracts import registries
from datapilot.contracts.live import SessionPurpose
from datapilot.loop3_events import demos, sessions
from datapilot.loop3_events.api.app import app
from datapilot.loop3_events.worker import Worker, WorkerSettings

pytest_plugins = ["loops_fixtures"]
pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("clean_ops")]


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def triggered_at(client: TestClient, done: demos.Triggered) -> list[tuple[str, str, datetime]]:
    """(id, session id, created time) for each run or request a trigger made."""
    found = []
    for run_id in done.run_ids:
        run = client.get(f"/runs/{run_id}").json()
        found.append((run_id, run["session_id"], datetime.fromisoformat(run["created_at"])))
    for request_id in done.request_ids:
        rows = client.get("/improvement/requests").json()["requests"]
        row = next(r for r in rows if r["request_id"] == request_id)
        found.append((request_id, row["session_id"], datetime.fromisoformat(row["requested_at"])))
    return found


def trigger_all(client: TestClient) -> dict[str, list[tuple[str, str, datetime]]]:
    """The first run or request of each trigger, two triggers per demo. A trigger can make more
    than one (the naive analyzer demo queues the analyzer, then the candidate experiment): every
    one of them must be in the same session as the first."""
    seen: dict[str, list[tuple[str, str, datetime]]] = {}
    for demo in registries.demos().demos:
        for _ in range(2):
            done = demos.trigger(client, demo, wait_running_seconds=0)
            made = triggered_at(client, done)
            assert {m[1] for m in made} == {made[0][1]}, demo.id
            seen.setdefault(demo.id, []).append(made[0])
            client.post("/control/kill-switch", json={"action": "release"})
    return seen


def test_every_demo_twice_gives_two_fresh_runs_in_the_session(client, services_for) -> None:
    first = sessions.start_session(SessionPurpose.REHEARSAL, "test", "America/New_York")
    seen = trigger_all(client)
    assert set(seen) == {d.id for d in registries.demos().demos}
    for demo_id, (one, two) in seen.items():
        assert one[0] != two[0], demo_id
        assert two[2] > one[2], demo_id
        assert one[1] == two[1] == str(first.session_id), demo_id

    services = services_for({"analyst": query_then_answer("SELECT 1 AS one", "One.")})
    worker = Worker(
        services,
        models_for=lambda _r, _activity: services.models,
        settings=WorkerSettings(poll_seconds=0.05),
    )

    async def drain() -> None:
        while await worker.run_once():
            pass

    asyncio.run(drain())  # every run the demos made is processed live, by the stub only
    runs = client.get("/runs", params={"limit": 200}).json()["runs"]
    assert runs and all(r["status"] not in ("received", "queued", "running") for r in runs)

    second = sessions.start_session(SessionPurpose.CLASS, "test", "America/New_York")
    assert second.session_id != first.session_id
    again = trigger_all(client)
    for demo_id, (one, _two) in again.items():
        assert one[1] == str(second.session_id), demo_id
        assert one[0] not in {item[0] for item in seen[demo_id]}, demo_id
