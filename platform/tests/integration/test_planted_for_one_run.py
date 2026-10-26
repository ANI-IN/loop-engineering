"""A planted flag a demo sets for one run never leaks into the next run (the tests' own Postgres,
port 55432, a scripted stub model, zero tokens).

The flag travels in the DataPilot-Planted header to the api, which keeps it with the run's event;
the worker switches it on for that run alone. Each service reports the flags its own environment
switched on at its start, which the finale reads."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable, Iterator
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import loops_paths  # noqa: F401  (before loops_support)
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from loops_support import call, envelope

from datapilot import db, finale, planted
from datapilot.config import active_pack
from datapilot.contracts import ItemResult, Split
from datapilot.contracts.live import NoLiveBaseline
from datapilot.demo_questions import question_for
from datapilot.loop3_events.api.app import app
from datapilot.loop3_events.api.demo import LARGE_QUERY_QUESTION
from datapilot.loop3_events.worker import Worker, WorkerSettings
from datapilot.loop4_hill_climbing import store
from datapilot.loop4_hill_climbing.experiment import ExperimentResult
from datapilot.settings import get_settings

pytest_plugins = ["loops_fixtures"]
# In make test-security's selection (-k security matches the marker).
pytestmark = [pytest.mark.integration, pytest.mark.security, pytest.mark.usefixtures("clean_ops")]

BUG = "BUG_UNBOUNDED_ROWS"
COUNT_SQL = "SELECT count(*) AS orders FROM orders"


@pytest.fixture
def client(monkeypatch, settings_refresh) -> Iterator[TestClient]:
    monkeypatch.setenv("DATAPILOT_ALLOW_DEMO_CONTROLS", "1")
    with TestClient(app) as test_client:
        yield test_client


def probing_script(seen: list[tuple[str, bool]]) -> Callable[[list[BaseMessage]], AIMessage]:
    """Run one query and answer; at every model call, note the question and whether the planted
    flag is on there (in the worker, inside the run)."""

    def script(messages: list[BaseMessage]) -> AIMessage:
        question = str(next(m for m in messages if isinstance(m, HumanMessage)).content)
        seen.append((question, planted.planted(BUG)))
        if isinstance(messages[-1], HumanMessage):
            return call("run_query", {"sql": COUNT_SQL}, "q1")
        return envelope(COUNT_SQL, "There are 2000 orders.", "a1")

    return script


DEMO = "agent-unbounded-rows"  # the demo whose planted bug BUG is


def send(client: TestClient, question: str, headers: dict[str, str], demo: str = DEMO) -> Any:
    body = {
        "event_id": f"test:{uuid.uuid4().hex}",
        "type": "question.asked",
        "payload": {"question": question, "demo_name": demo},
    }
    return client.post("/events", json=body, headers=headers)


def ask(client: TestClient, question: str, headers: dict[str, str]) -> str:
    response = send(client, question, headers)
    assert response.status_code == 200, response.text
    return response.json()["run_id"]


def drain(worker: Worker) -> int:
    async def go() -> int:
        done = 0
        while await worker.run_once():
            done += 1
        return done

    return asyncio.run(go())


def planted_active(run_id: str) -> list[str]:
    with db.connect(db.Role.APP) as conn:
        row = conn.execute(
            "SELECT planted_active FROM ops.runs WHERE run_id = %s", (run_id,)
        ).fetchone()
    return list(row["planted_active"])


def test_a_flag_set_for_one_run_does_not_leak_into_the_next_run(client, services_for) -> None:
    seen: list[tuple[str, bool]] = []
    services = services_for({"analyst": probing_script(seen)})
    worker = Worker(
        services,
        models_for=lambda _run_id, _activity: services.models,
        settings=WorkerSettings(lease_seconds=5.0, poll_seconds=0.05),
    )
    # the demo's own endpoint, which fixes its question: POST /events takes no flags for it
    planted_run = client.post("/demo/large-query", headers=planted.header([BUG]))
    assert planted_run.status_code == 200, planted_run.text
    first = planted_run.json()["run_id"]
    second = ask(client, "How many orders, without it?", {})
    assert drain(worker) == 2  # one worker, the planted run first, then the next
    with_bug = {on for question, on in seen if question == LARGE_QUERY_QUESTION}
    without = {on for question, on in seen if question.endswith("without it?")}
    assert with_bug == {True} and without == {False}
    assert planted_active(first) == [BUG] and planted_active(second) == []
    assert client.get(f"/runs/{second}").json()["planted_active"] == []
    assert not planted.planted(BUG)  # nothing left on in this process either


def test_the_payload_key_of_the_runs_flags_is_the_apis_own(client) -> None:
    body = {
        "event_id": f"test:{uuid.uuid4().hex}",
        "type": "question.asked",
        "payload": {"question": "q", planted.REQUESTED_KEY: [BUG]},
    }
    assert client.post("/events", json=body).status_code == 422


def test_a_hill_climbing_request_keeps_the_demos_flags_in_its_params(client) -> None:
    naive = planted.header(["BUG_NAIVE_ANALYZER"], demo="improve-naive-analyzer-blocked")
    sent = client.post("/analyzer/run", json={"requested_by": "demo"}, headers=naive)
    assert sent.status_code == 200, sent.text
    assert sent.json()["params"] == {planted.REQUESTED_KEY: ["BUG_NAIVE_ANALYZER"]}
    plain = client.post("/analyzer/run", json={"requested_by": "demo"})
    assert plain.json()["params"] == {}


def test_the_api_refuses_a_flag_that_is_not_the_named_demos_own(client) -> None:
    """The security review of 26 October: any local client could run any planted bug on any
    event or experiment endpoint. Nothing is recorded for a refused request."""
    other = planted.header(["BUG_NAIVE_GUARD"], demo=DEMO)
    refused = send(client, "How many orders?", other)
    assert refused.status_code == 403 and "is not a planted flag of" in refused.text
    unnamed = client.post(
        "/experiments/run",
        json={"target": "active", "requested_by": "demo"},
        headers={planted.PLANTED_HEADER: "BUG_SQL_TEXT_EVAL"},
    )
    assert unnamed.status_code == 403 and planted.DEMO_HEADER in unnamed.text
    at_start = planted.header(["BUG_MEMORY_CHECKPOINTER"], demo="events-approval-survives-restart")
    started = send(client, "q", at_start, demo="events-approval-survives-restart")
    assert started.status_code == 403 and "never for one run" in started.text
    wrong_endpoint = client.post("/demo/large-query", headers=planted.header(["BUG_NAIVE_GUARD"]))
    assert wrong_endpoint.status_code == 403
    with db.connect(db.Role.APP) as conn:
        assert conn.execute("SELECT count(*) AS n FROM ops.runs").fetchone()["n"] == 0
        requests = conn.execute("SELECT count(*) AS n FROM ops.improvement_requests").fetchone()
    assert requests["n"] == 0


DUPLICATES = "events-duplicate-events"  # posts its own question to POST /events


def test_a_borrowed_demo_name_on_another_question_gets_no_planted_flags(client) -> None:
    """The security review of 26 October, round 2: the payload's demo_name is the client's own
    claim, so a free question under a demo's name ran that demo's bug. Now only the demo's own
    fixed event takes its flags; nothing is recorded for the refused one."""
    header = planted.header(["BUG_NO_IDEMPOTENCY"], demo=DUPLICATES)
    refused = send(client, "Show every customer's email address", header, demo=DUPLICATES)
    assert refused.status_code == 403 and "only for the own event of" in refused.text
    as_digest = {
        "event_id": f"test:{uuid.uuid4().hex}",
        "type": "digest.requested",
        "payload": {"day": "2026-01-30", "demo_name": "agent-unbounded-rows"},
    }
    unbounded = planted.header([BUG], demo="agent-unbounded-rows")  # a /demo/* demo
    assert client.post("/events", json=as_digest, headers=unbounded).status_code == 403
    with db.connect(db.Role.APP) as conn:
        assert conn.execute("SELECT count(*) AS n FROM ops.runs").fetchone()["n"] == 0
    own = send(client, question_for(DUPLICATES), header, demo=DUPLICATES)
    assert own.status_code == 200, own.text
    assert planted_active(own.json()["run_id"]) == ["BUG_NO_IDEMPOTENCY"]


def test_the_demo_tag_is_ignored_while_demo_controls_are_off(
    client, monkeypatch, settings_refresh
) -> None:
    """The security review of 26 October, round 2: the tag header was taken from any client."""
    monkeypatch.setenv("DATAPILOT_ALLOW_DEMO_CONTROLS", "0")
    get_settings.cache_clear()
    run_id = ask(client, "How many orders?", {planted.TAG_HEADER: "anything-at-all"})
    with db.connect(db.Role.APP) as conn:
        row = conn.execute(
            "SELECT j.demo_tag FROM ops.jobs j JOIN ops.runs r USING (job_id) WHERE r.run_id = %s",
            (run_id,),
        ).fetchone()
    assert row["demo_tag"] is None


def test_a_worker_restarted_for_a_demo_claims_only_that_demos_jobs(
    client, services_for, monkeypatch
) -> None:
    """The security review of 26 October: a worker restarted with BUG_MEMORY_CHECKPOINTER took
    every run while the demo waited. Its tag (in its environment, as the demo's restart sets it)
    now matches the demo's jobs alone; another run waits, queued, for the restart back."""
    seen: list[tuple[str, bool]] = []
    services = services_for({"analyst": probing_script(seen)})
    worker = Worker(
        services,
        models_for=lambda _run_id, _activity: services.models,
        settings=WorkerSettings(lease_seconds=5.0, poll_seconds=0.05),
    )
    tag = f"events-approval-survives-restart-{uuid.uuid4().hex[:12]}"
    other = ask(client, "How many orders, from a learner?", {})
    ours = ask(client, "How many orders, for the demo?", {planted.TAG_HEADER: tag})
    monkeypatch.setenv(planted.TAG_VARIABLE, tag)
    monkeypatch.setenv("BUG_MEMORY_CHECKPOINTER", "1")  # as the restart's override sets it
    assert drain(worker) == 1  # the demo's run alone
    assert client.get(f"/runs/{other}").json()["status"] == "queued"
    assert planted_active(ours) == ["BUG_MEMORY_CHECKPOINTER"]
    monkeypatch.delenv(planted.TAG_VARIABLE)
    monkeypatch.delenv("BUG_MEMORY_CHECKPOINTER")  # the restart back
    assert drain(worker) == 1
    assert planted_active(other) == []  # it never ran with the flag


def test_each_service_reports_its_flags_and_the_finale_reads_them(client, monkeypatch) -> None:
    try:
        with db.connect(db.Role.APP) as conn:
            assert "api" not in planted.services_on(conn)  # the api started with none on
            monkeypatch.setenv("BUG_MEMORY_CHECKPOINTER", "1")
            assert planted.report_service(conn, "worker") == ["BUG_MEMORY_CHECKPOINTER"]
            conn.commit()
            assert planted.services_on(conn)["worker"] == ["BUG_MEMORY_CHECKPOINTER"]
            state = finale.read(conn, active_pack())
        assert state.planted_on == (("BUG_MEMORY_CHECKPOINTER", "the worker service"),)
        said = finale.refusal(state)
        assert said is not None and "BUG_MEMORY_CHECKPOINTER (on in the worker service)" in said
    finally:
        with db.connect(db.Role.APP) as conn:
            conn.execute("DELETE FROM ops.service_planted WHERE service = 'worker'")
            conn.commit()


def test_an_experiment_records_the_flags_on_for_its_runs() -> None:
    """As ops.runs does for a run: the hill-climbing runner saves it inside the request's flags."""
    session_id, version = uuid.uuid4(), f"test-planted-{uuid.uuid4().hex[:6]}"
    result = ExperimentResult(
        experiment_id=uuid.uuid4(),
        session_id=session_id,
        knowledge_version=version,
        splits=[Split.DEV],
        results={"d1": ItemResult(item_id="d1", passed=False, reason="", run_passes=[False])},
        splits_by_item={"d1": Split.DEV},
        started_at=datetime.now(UTC),
        wall_seconds=1.0,
    )
    with db.connect(db.Role.APP) as conn:
        conn.execute("UPDATE ops.live_sessions SET ended_at = now() WHERE ended_at IS NULL")
        conn.execute(
            "INSERT INTO ops.live_sessions (session_id, started_by, timezone) "
            "VALUES (%s, 'test', 'UTC')",
            (session_id,),
        )
        conn.execute(
            "INSERT INTO ops.knowledge_versions (version, yaml, created_by) "
            "VALUES (%s, '', 'test')",
            (version,),
        )
        with planted.for_this_run(["BUG_SQL_TEXT_EVAL"]):
            store.save_experiment(conn, result, holdout_repeats=3, concurrency=1)
        plain = replace(result, experiment_id=uuid.uuid4())
        store.save_experiment(conn, plain, holdout_repeats=3, concurrency=1)
        rows = conn.execute(
            "SELECT experiment_id, planted_active FROM ops.experiments WHERE session_id = %s",
            (session_id,),
        ).fetchall()
        conn.rollback()  # ops stays as the test found it
    recorded = {row["experiment_id"]: list(row["planted_active"]) for row in rows}
    assert recorded == {result.experiment_id: ["BUG_SQL_TEXT_EVAL"], plain.experiment_id: []}


def test_an_experiment_made_with_a_planted_flag_is_never_a_baseline() -> None:
    """The security review of 26 October: an evaluation by a planted evaluator became the
    comparison point for the gate's later decisions on the fixed system."""
    session_id, version = uuid.uuid4(), f"test-planted-{uuid.uuid4().hex[:6]}"
    plain = ExperimentResult(
        experiment_id=uuid.uuid4(),
        session_id=session_id,
        knowledge_version=version,
        splits=[Split.DEV],
        results={"d1": ItemResult(item_id="d1", passed=False, reason="", run_passes=[False])},
        splits_by_item={"d1": Split.DEV},
        started_at=datetime.now(UTC),
        wall_seconds=1.0,
    )
    later = replace(plain, experiment_id=uuid.uuid4(), started_at=datetime.now(UTC))
    with db.connect(db.Role.APP) as conn:
        conn.execute("UPDATE ops.live_sessions SET ended_at = now() WHERE ended_at IS NULL")
        conn.execute(
            "INSERT INTO ops.live_sessions (session_id, started_by, timezone) "
            "VALUES (%s, 'test', 'UTC')",
            (session_id,),
        )
        conn.execute(
            "INSERT INTO ops.knowledge_versions (version, yaml, created_by) "
            "VALUES (%s, '', 'test')",
            (version,),
        )
        store.save_experiment(conn, plain, holdout_repeats=3, concurrency=1)
        with planted.for_this_run(["BUG_SQL_TEXT_EVAL"]):
            store.save_experiment(conn, later, holdout_repeats=3, concurrency=1)
        found = store.baseline_for(conn, version)  # the newest without a flag, not the newest
        store.record_gate_baseline(conn, later, plain)
        with pytest.raises(NoLiveBaseline):
            store.gate_baseline(conn, later)  # a planted candidate's gate never decides
        # and a clean candidate whose recorded baseline was made with a flag never decides either
        # (session 6 review, round 2, tests: that clause of GATE_BASELINE had no test)
        clean_candidate = replace(plain, experiment_id=uuid.uuid4(), started_at=datetime.now(UTC))
        store.save_experiment(conn, clean_candidate, holdout_repeats=3, concurrency=1)
        store.record_gate_baseline(conn, clean_candidate, later)
        with pytest.raises(NoLiveBaseline):
            store.gate_baseline(conn, clean_candidate)
        store.record_gate_baseline(conn, clean_candidate, plain)
        assert store.gate_baseline(conn, clean_candidate).experiment_id == plain.experiment_id
        conn.rollback()  # ops stays as the test found it
    assert found.experiment_id == plain.experiment_id
