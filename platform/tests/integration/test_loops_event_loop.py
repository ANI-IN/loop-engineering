"""The event loop end to end on the Compose Postgres, with a scripted stub model (zero tokens)."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Any

import loops_paths  # noqa: F401  (before loops_support)
import psycopg
import pytest
from fastapi.testclient import TestClient
from loops_support import call, human_messages, query_then_answer

from datapilot import db, planted
from datapilot.contracts import RunStatus
from datapilot.contracts.live import NoLiveSession, SessionPurpose
from datapilot.loop3_events import approvals, autonomy, killswitch, lifecycle, scheduler, sessions
from datapilot.loop3_events.api.app import app
from datapilot.loop3_events.worker import DbHooks, Worker, WorkerSettings
from datapilot.observability import spend
from datapilot.settings import get_settings

pytest_plugins = ["loops_fixtures"]
pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("clean_ops")]

COUNT_SQL = "SELECT count(*) AS orders FROM orders"
COUNT_SCRIPT = query_then_answer(COUNT_SQL, "There are 2000 orders.")
EMAIL_SQL = "SELECT email FROM customers_marketable WHERE state = 'CA' ORDER BY 1"
EXPORT_SCRIPT = query_then_answer(EMAIL_SQL, "Exported the California customers.")


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_worker(services_for) -> Callable[..., Worker]:
    def build(script: Any = COUNT_SCRIPT, *, lease: float = 5.0, **kw: Any) -> Worker:
        services = services_for({"analyst": script}, **kw)
        return Worker(
            services,
            models_for=lambda _run_id, _activity: services.models,
            settings=WorkerSettings(lease_seconds=lease, poll_seconds=0.05),
        )

    return build


def ask(client: TestClient, question: str = "How many orders are there?", **kw: Any) -> dict:
    event_id = kw.pop("event_id", f"test:{uuid.uuid4().hex}")
    body = {
        "event_id": event_id,
        "type": kw.pop("type", "question.asked"),
        "payload": {"question": question, **kw},
    }
    response = client.post("/events", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def run(client: TestClient, run_id: str) -> dict:
    return client.get(f"/runs/{run_id}").json()


def statuses(detail: dict) -> list[str]:
    return [e["payload"]["to"] for e in detail["events"] if e["kind"] == "status_changed"]


def sql(query: str, *params: Any) -> list[dict]:
    """Runs the query once (a write through it applies once) and returns its rows, if any."""
    with db.connect(db.Role.OWNER) as conn:
        cursor = conn.execute(query, params)
        rows = cursor.fetchall() if cursor.description else []
        conn.commit()
    return rows


def execute(query: str, *params: Any) -> None:
    with db.connect(db.Role.OWNER) as conn:
        conn.execute(query, params)
        conn.commit()


def drain(worker: Worker, limit: int = 10) -> int:
    async def go() -> int:
        done = 0
        while done < limit and await worker.run_once():
            done += 1
        return done

    return asyncio.run(go())


# --- events, duplicates, lifecycle ---
def test_a_question_moves_through_the_lifecycle_and_posts_unverified(client, make_worker) -> None:
    submitted = ask(client)
    assert drain(make_worker()) == 1
    detail = run(client, submitted["run_id"])
    assert detail["status"] == "posted"
    assert statuses(detail) == ["received", "queued", "running", "verifying", "answered", "posted"]
    assert detail["posts"][0]["label"] == "unverified"
    assert detail["autonomy_level_applied"] == "report_only"
    assert detail["tokens_in"] > 0


def test_duplicates_are_absorbed(client, make_worker, monkeypatch) -> None:
    monkeypatch.delenv("BUG_NO_IDEMPOTENCY", raising=False)
    first, *again = [ask(client, event_id="same-event") for _ in range(3)]
    assert {s["run_id"] for s in again} == {first["run_id"]}
    assert again[-1]["duplicate"] and again[-1]["duplicates_ignored"] == 2
    drain(make_worker())
    assert len(sql("SELECT * FROM ops.posts")) == 1
    assert run(client, first["run_id"])["duplicates_ignored"] == 2


def test_planted_missing_idempotency_posts_three_answers(client, make_worker, monkeypatch) -> None:
    monkeypatch.setenv("BUG_NO_IDEMPOTENCY", "1")
    runs = {ask(client, event_id="same-event")["run_id"] for _ in range(3)}
    drain(make_worker())
    assert len(runs) == 3 and len(sql("SELECT * FROM ops.posts")) == 3


def test_the_digest_id_is_deterministic(monkeypatch) -> None:
    monkeypatch.delenv("BUG_RANDOM_DIGEST_ID", raising=False)
    day = date(2026, 10, 22)
    assert scheduler.digest_event_id(day) == "digest:2026-10-22"
    first, second = scheduler.request_digest(day), scheduler.request_digest(day)
    assert second.duplicate and second.run_id == first.run_id
    jobs = scheduler.build().get_jobs()
    assert [str(j.trigger) for j in jobs] == ["cron[hour='8', minute='0']"]
    assert str(jobs[0].trigger.timezone) == "America/New_York"


def test_planted_random_digest_id_posts_two_digests(monkeypatch, make_worker) -> None:
    monkeypatch.setenv("BUG_RANDOM_DIGEST_ID", "1")
    day = date(2026, 10, 22)
    first, second = scheduler.request_digest(day), scheduler.request_digest(day)
    assert not second.duplicate and first.run_id != second.run_id
    drain(make_worker())
    assert len(sql("SELECT * FROM ops.posts")) == 2


# --- leases, crashes, the reaper ---
def test_crash_recovery_requeues_an_expired_lease(client, make_worker) -> None:
    submitted = ask(client)
    crashed = make_worker(lease=0.2)
    assert crashed._claim() is not None
    DbHooks(submitted["run_id"]).status(RunStatus.RUNNING)  # then the worker dies mid-run
    time.sleep(0.4)
    assert drain(make_worker()) == 1
    detail = run(client, submitted["run_id"])
    assert detail["status"] == "posted"
    assert statuses(detail)[:4] == ["received", "queued", "running", "queued"]
    assert sql("SELECT attempts FROM ops.jobs")[0]["attempts"] == 2  # counted at each claim


def test_a_job_whose_leases_keep_expiring_is_dead(client, make_worker) -> None:
    submitted = ask(client)
    execute("UPDATE ops.jobs SET max_attempts = 2")
    worker = make_worker(lease=0.1)
    for _ in range(2):
        assert worker._claim() is not None
        DbHooks(submitted["run_id"]).status(RunStatus.RUNNING)
        time.sleep(0.25)
        worker.reap()
    job = sql("SELECT status, attempts FROM ops.jobs")[0]
    assert job == {"status": "dead", "attempts": 2}
    assert run(client, submitted["run_id"])["status"] == "failed"


def test_a_late_worker_cannot_finish_a_job_it_lost(client, make_worker) -> None:
    ask(client)
    late = make_worker(lease=0.1)
    claimed = late._claim()
    assert claimed is not None
    time.sleep(0.2)
    late.reap()
    assert late._finish(claimed[0], None, "done") is False


def test_a_stale_attempt_can_neither_finish_nor_extend_the_newer_one(client, make_worker) -> None:
    ask(client)
    shared = WorkerSettings(worker_id="worker-reused-id", lease_seconds=0.1, poll_seconds=0.05)
    first = make_worker()
    first.settings = shared
    claimed = first._claim()
    assert claimed is not None and claimed[0].attempts == 1
    time.sleep(0.2)
    first.reap()
    second = make_worker()
    second.settings = WorkerSettings(worker_id="worker-reused-id", lease_seconds=30.0)
    again = second._claim()
    assert again is not None and again[0].attempts == 2
    # Even with the same owner id, the first attempt's heartbeat and finish touch 0 rows.
    assert first.heartbeat_once(claimed[0]) is False
    assert first._finish(claimed[0], None, "done") is False
    assert sql("SELECT status, attempts FROM ops.jobs")[0] == {"status": "running", "attempts": 2}
    assert second.heartbeat_once(again[0]) is True
    assert second._finish(again[0], None, "done") is True


def slow_script(seconds: float):
    def script(messages):
        time.sleep(seconds)
        return COUNT_SCRIPT(messages)

    return script


def observe_job_during_run(worker: Worker, observe: Callable[[], Any]) -> Any:
    async def go() -> Any:
        task = asyncio.create_task(worker.run_once())
        await asyncio.sleep(0.4)
        seen = await asyncio.to_thread(observe)
        await task
        return seen

    return asyncio.run(go())


def job_seen_from_outside() -> dict:
    with psycopg.connect(db.url_for(db.Role.APP), autocommit=True) as conn:
        conn.execute("SET lock_timeout = '100ms'")
        try:
            conn.execute("SELECT 1 FROM ops.jobs FOR UPDATE NOWAIT")
            locked = False
        except psycopg.errors.LockNotAvailable:
            locked = True
        row = conn.execute("SELECT status, lease_owner FROM ops.jobs").fetchone()
        idle = conn.execute(
            "SELECT count(*) FROM pg_stat_activity WHERE state = 'idle in transaction' "
            "AND usename = 'datapilot_app'"
        ).fetchone()[0]
    return {"locked": locked, "status": row[0], "lease_owner": row[1], "idle_in_transaction": idle}


def test_the_claim_is_a_short_transaction_with_a_visible_lease(
    client, make_worker, monkeypatch
) -> None:
    monkeypatch.delenv("BUG_LOCK_DURING_LLM", raising=False)
    ask(client)
    seen = observe_job_during_run(make_worker(slow_script(0.3)), job_seen_from_outside)
    assert seen["status"] == "running" and seen["lease_owner"] and not seen["locked"]
    assert sql("SELECT status, attempts FROM ops.jobs")[0] == {"status": "done", "attempts": 1}


def kill_the_claim_transaction() -> dict:
    """What an observer sees mid-run, then the worker's claim connection dies (a killed worker)."""
    seen = job_seen_from_outside()
    with psycopg.connect(db.url_for(db.Role.APP), autocommit=True) as conn:
        conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE state = 'idle in transaction' AND query LIKE '%%UPDATE ops.jobs%%'"
        )
    return seen


def test_planted_lock_held_during_the_model_call(client, make_worker, monkeypatch) -> None:
    monkeypatch.setenv("BUG_LOCK_DURING_LLM", "1")
    ask(client)
    seen = observe_job_during_run(make_worker(slow_script(0.3)), kill_the_claim_transaction)
    # Mid-run the lease is invisible: the row looks queued, stays locked by an idle transaction,
    # and the run's own writes wait on that lock. Killing the worker rolls the claim back, so the
    # job is queued again with no attempt counted, although the run already started.
    assert seen["locked"] and seen["status"] == "queued" and seen["idle_in_transaction"] >= 1
    job = sql("SELECT status, attempts FROM ops.jobs")[0]
    assert job == {"status": "queued", "attempts": 0}


# --- approvals and the checkpointer ---
def export(client: TestClient) -> dict:
    return ask(client, "Export California customers for marketing", type="export.requested")


async def one_job_with_checkpointer(make_worker) -> bool:
    async with approvals.checkpointer() as saver:
        return await make_worker(EXPORT_SCRIPT, checkpointer=saver).run_once()


def test_an_approval_survives_a_worker_restart(client, make_worker, monkeypatch) -> None:
    monkeypatch.delenv("BUG_MEMORY_CHECKPOINTER", raising=False)
    client.post("/control/autonomy", json={"level": "assisted"})
    submitted = export(client)
    asyncio.run(one_job_with_checkpointer(make_worker))  # this worker process then ends
    detail = run(client, submitted["run_id"])
    assert detail["status"] == "awaiting_approval"
    pending = detail["approvals"][0]
    assert pending["sql"] == EMAIL_SQL and pending["row_estimate"] == 5
    assert sql("SELECT status FROM ops.jobs")[0]["status"] == "parked"
    decided = client.post(f"/approvals/{submitted['run_id']}", json={"decision": "approve"})
    assert decided.status_code == 200
    asyncio.run(one_job_with_checkpointer(make_worker))  # a new worker process
    detail = run(client, submitted["run_id"])
    assert detail["status"] == "posted" and detail["posts"][0]["label"] == "verified"
    assert len(detail["posts"][0]["body"]["answer"]["rows_preview"]) == 5


def test_planted_in_memory_checkpointer_loses_the_approval(
    client, make_worker, monkeypatch
) -> None:
    monkeypatch.setenv("BUG_MEMORY_CHECKPOINTER", "1")
    submitted = export(client)
    asyncio.run(one_job_with_checkpointer(make_worker))
    client.post(f"/approvals/{submitted['run_id']}", json={"decision": "approve"})
    asyncio.run(one_job_with_checkpointer(make_worker))
    detail = run(client, submitted["run_id"])
    assert detail["status"] == "failed"
    assert "approval was lost" in str(detail["events"][-1]["payload"])


def test_approvals_are_approve_or_reject_only(client, make_worker) -> None:
    submitted = export(client)
    drain(make_worker(EXPORT_SCRIPT))
    run_id = submitted["run_id"]
    assert client.post(f"/approvals/{run_id}", json={"decision": "edit"}).status_code == 422
    assert (
        client.post(f"/approvals/{run_id}", json={"decision": "reject"}).json()["status"]
        == "rejected"
    )
    assert client.post(f"/approvals/{run_id}", json={"decision": "approve"}).status_code == 409


def test_an_approval_that_lands_before_the_job_is_parked_still_resumes_the_run(
    client, make_worker
) -> None:
    """Review round 1 (F067): the worker commits awaiting_approval, then parks the job in a later
    transaction. An approval in between matched no parked job, and the run stayed stuck."""
    submitted = export(client)
    worker = make_worker(EXPORT_SCRIPT)
    drain(worker)
    execute("UPDATE ops.jobs SET status = 'running', lease_owner = 'a worker still finishing'")
    client.post(f"/approvals/{submitted['run_id']}", json={"decision": "approve"})
    assert [j["status"] for j in sql("SELECT status FROM ops.jobs")] == ["queued"]
    drain(worker)
    assert run(client, submitted["run_id"])["status"] == "posted"


def test_report_only_level_never_releases_export_rows(client, make_worker) -> None:
    submitted = export(client)
    worker = make_worker(EXPORT_SCRIPT)  # one process: its in-memory checkpointer keeps the run
    drain(worker)
    client.post(f"/approvals/{submitted['run_id']}", json={"decision": "approve"})
    drain(worker)
    post = run(client, submitted["run_id"])["posts"][0]
    assert post["label"] == "unverified" and post["body"]["answer"]["rows_preview"] == []


def test_a_reviewer_concern_after_an_approval_is_fed_back_once_in_the_whole_run(
    client, services_for
) -> None:
    """Live, an export needing approvals reached about 110,000 tokens: after each approval the
    reviewer's concern sent the analyst back, its rewritten query was held again, and the resumed
    run had forgotten the concern it already fed back. Now the second concern holds the answer."""
    reviews: list[str] = []

    def analyst(messages: Any) -> Any:
        turn = len(human_messages(messages))  # each feedback is a new turn and a rewritten query
        rewritten = f"{EMAIL_SQL.removesuffix(' ORDER BY 1')} AND customer_id > {turn} ORDER BY 1"
        return query_then_answer(rewritten, "Exported the California customers.")(messages)

    def reviewer(messages: Any) -> Any:
        reviews.append("concern")
        return call("ReviewVerdict", {"outcome": "concern", "reasons": ["check the filter"]}, "v")

    services = services_for({"analyst": analyst, "reviewer": reviewer}, reviewer=True)
    worker = Worker(
        services,
        models_for=lambda _run_id, _activity: services.models,
        settings=WorkerSettings(poll_seconds=0.05),
    )
    submitted = export(client)
    run_id = submitted["run_id"]
    drain(worker)
    for _ in range(3):  # approve whatever is held, at most three times
        if run(client, run_id)["status"] != "awaiting_approval":
            break
        if sql("SELECT kind FROM ops.approvals WHERE decision IS NULL")[0]["kind"] != "tool_call":
            break
        client.post(f"/approvals/{run_id}", json={"decision": "approve"})
        drain(worker)
    kinds = [r["kind"] for r in sql("SELECT kind FROM ops.approvals ORDER BY approval_id")]
    assert kinds == ["tool_call", "tool_call", "held_answer"], kinds
    assert len(reviews) == 2, "one concern fed back, the second holds the answer"
    assert run(client, run_id)["answer"]["attempts"] == 2


# --- the spend activity travels with the job ---
def test_the_starters_spend_activity_travels_with_the_job(client, services_for) -> None:
    """Live, the worker charged every run to its own .env activity, so calibration and demo runs
    landed on the development line. The starter's activity now rides on the job, approvals too."""
    services = services_for({"analyst": EXPORT_SCRIPT})
    seen: list[tuple[str, str | None]] = []

    def models_for(run_id: str, activity: str | None) -> Any:
        seen.append((run_id, activity))
        return services.models

    worker = Worker(services, models_for=models_for, settings=WorkerSettings(poll_seconds=0.05))
    body = {
        "event_id": f"test:{uuid.uuid4().hex}",
        "type": "export.requested",
        "payload": {"question": "Export California customers for marketing"},
    }
    named = {spend.ACTIVITY_HEADER: "calibration-traps"}
    submitted = client.post("/events", json=body, headers=named).json()
    again = client.post("/events", json=body, headers={spend.ACTIVITY_HEADER: "rehearsal"})
    assert again.json()["duplicate"], "a duplicate never changes the job's activity"
    plain = ask(client)
    assert sql("SELECT event_id, spend_activity FROM ops.jobs ORDER BY job_id") == [
        {"event_id": body["event_id"], "spend_activity": "calibration-traps"},
        {"event_id": plain["event_id"], "spend_activity": None},
    ]
    drain(worker)  # the export pauses for approval; the question is answered
    client.post(f"/approvals/{submitted['run_id']}", json={"decision": "approve"})
    drain(worker)  # the approval puts the same job back, with its activity
    assert run(client, submitted["run_id"])["status"] == "posted"
    by_run = {run_id: [a for r, a in seen if r == run_id] for run_id, _ in seen}
    assert by_run[submitted["run_id"]] == ["calibration-traps", "calibration-traps"]
    assert by_run[plain["run_id"]] == [None], "no activity named: the worker's own applies"


# --- autonomy ---
@pytest.fixture
def active_version() -> Iterator[str]:
    execute(
        "INSERT INTO ops.knowledge_versions (version, yaml, status, created_by) "
        "VALUES ('loops-test', 'version: loops-test', 'active', 'test')"
    )
    yield "loops-test"
    execute("DELETE FROM ops.knowledge_versions WHERE version = 'loops-test'")


def test_unattended_posting_only_for_eligible_families(client, make_worker, active_version) -> None:
    client.post("/control/autonomy", json={"level": "unattended"})
    with db.connect(db.Role.APP) as conn:
        autonomy.mark_eligible(conn, "orders", active_version)
        autonomy.mark_eligible(conn, "revenue", "an-older-version")
        conn.commit()
    eligible = ask(client, "How many orders are there?")
    other = ask(client, "What was revenue last week?")
    drain(make_worker())
    assert run(client, eligible["run_id"])["posts"][0]["label"] == "unattended"
    assert run(client, other["run_id"])["posts"][0]["label"] == "verified"


def test_an_answer_cleared_in_rehearsal_says_so_where_it_posts(
    client, make_worker, active_version
) -> None:
    """The class-day safeguard: the family's clearance came from rehearsal, and the post says so."""
    client.post("/control/autonomy", json={"level": "unattended"})
    note = "cleared in rehearsal on 2026-11-01 (live session x); carried by the class-day safeguard"
    with db.connect(db.Role.APP) as conn:
        autonomy.mark_cleared_in_rehearsal(conn, "orders", active_version, note)
        autonomy.mark_eligible(conn, "revenue", active_version)
        conn.commit()
    carried = ask(client, "How many orders are there?")
    earned = ask(client, "What was revenue last week?")
    drain(make_worker())
    carried_post = run(client, carried["run_id"])["posts"][0]
    earned_post = run(client, earned["run_id"])["posts"][0]
    assert carried_post["label"] == "unattended" and carried_post["body"]["clearance"] == note
    assert earned_post["label"] == "unattended" and "clearance" not in earned_post["body"]


def test_three_escalations_in_a_row_demote_to_report_only(client, make_worker) -> None:
    client.post("/control/autonomy", json={"level": "assisted"})
    for _ in range(3):
        ask(client, inject_failing_grader=True)
    drain(make_worker())
    control = client.get("/control").json()
    assert control["autonomy_level"] == "report_only"
    assert control["reason"] == "consecutive_escalations"


# --- the kill switch and the budget ---
def engage(client: TestClient) -> None:
    assert client.post("/control/kill-switch", json={"action": "arm"}).status_code == 200
    assert client.post("/control/kill-switch", json={"action": "engage"}).status_code == 200


def test_the_kill_switch_must_be_armed_first(client) -> None:
    assert client.post("/control/kill-switch", json={"action": "engage"}).status_code == 409


def test_the_kill_switch_is_checked_at_claim(client, make_worker) -> None:
    submitted = ask(client)
    engage(client)
    drain(make_worker())
    detail = run(client, submitted["run_id"])
    assert detail["status"] == "blocked_killswitch"
    assert any(e["kind"] == "killswitch_blocked" for e in detail["events"])


def paced_run_with_kill(client: TestClient, worker: Worker, run_id: str) -> None:
    async def go() -> None:
        task = asyncio.create_task(worker.run_once())
        for _ in range(100):
            await asyncio.sleep(0.05)
            if run(client, run_id)["status"] == "running":
                break
        await asyncio.sleep(0.1)
        engage(client)
        await task

    asyncio.run(go())


@pytest.mark.parametrize("flag", ["0", "1"])
def test_the_kill_switch_stops_an_in_flight_paced_run(
    client, make_worker, monkeypatch, settings_refresh, flag: str
) -> None:
    monkeypatch.setenv("DEMO_PACING", "1")
    monkeypatch.setenv("DEMO_PACING_SECONDS", "0.3")
    monkeypatch.setenv("BUG_KILLSWITCH_AT_CLAIM_ONLY", flag)
    get_settings.cache_clear()
    submitted = ask(client)
    paced_run_with_kill(client, make_worker(), submitted["run_id"])
    detail = run(client, submitted["run_id"])
    assert client.get("/control").json()["autonomy_level"] == "report_only"
    if flag == "1":  # planted: the in-flight run keeps going
        assert detail["status"] == "posted"
    else:
        assert detail["status"] == "blocked_killswitch"
        assert not detail["posts"]


def test_a_worker_that_lost_its_lease_stops_the_agent_at_its_next_step(
    client, services_for
) -> None:
    """Review round 1 (F066): the heartbeat noted the lost lease, but the agent ran to the end,
    spending tokens on a result that was then thrown away."""
    from loops_support import envelope

    calls: list[int] = []

    def script(messages: Any) -> Any:
        calls.append(1)
        if len(calls) == 1:
            execute("UPDATE ops.jobs SET lease_owner = 'another worker'")  # the lease is gone
            time.sleep(0.5)  # the heartbeat, every 0.1 seconds, sees it
            return call("run_query", {"sql": COUNT_SQL}, "q")
        return envelope(COUNT_SQL, "There are 2000 orders.")

    services = services_for({"analyst": script})
    worker = Worker(
        services,
        models_for=lambda _run_id, _activity: services.models,
        settings=WorkerSettings(lease_seconds=0.3, poll_seconds=0.05),
    )
    submitted = ask(client)
    drain(worker, limit=1)
    assert calls == [1], "no model call after the lease was lost"
    assert run(client, submitted["run_id"])["posts"] == []


def test_engaging_blocks_runs_waiting_for_approval(client, make_worker) -> None:
    submitted = export(client)
    drain(make_worker(EXPORT_SCRIPT))
    engage(client)
    assert run(client, submitted["run_id"])["status"] == "blocked_killswitch"
    assert client.post("/control/autonomy", json={"level": "assisted"}).status_code == 409
    # Review round 1 (F068): the approval stayed open, so the console still offered it.
    closed = sql("SELECT decision, decided_by, decided_at FROM ops.approvals")
    assert [(a["decision"], a["decided_by"]) for a in closed] == [
        ("reject", "kill switch, engaged by console")
    ]
    assert closed[0]["decided_at"] is not None


def waiting_on_a_lock(timeout_s: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if sql("SELECT count(*) AS n FROM pg_locks WHERE NOT granted")[0]["n"]:
            return True
        time.sleep(0.05)
    return False


def test_engaging_while_a_rejection_commits_still_engages(client, make_worker) -> None:
    """Review round 3 (R3A-02): connection A rejects the held run, as POST /approvals/{run_id}
    does, and has not committed; connection B engages the switch, waits on the run's row lock, then
    read rejected and failed on rejected -> blocked_killswitch. The switch stayed armed. Now B
    leaves a run decided in the meantime alone and the switch engages."""
    submitted = export(client)
    drain(make_worker(EXPORT_SCRIPT))
    run_id = submitted["run_id"]
    assert run(client, run_id)["status"] == "awaiting_approval"
    assert client.post("/control/kill-switch", json={"action": "arm"}).status_code == 200

    def engage_on_its_own_connection() -> str:
        with db.connect(db.Role.APP) as conn:
            new = killswitch.set_state(conn, "engage", by="test: connection B")
            conn.commit()
        return new

    with db.connect(db.Role.APP) as deciding, ThreadPoolExecutor(max_workers=1) as pool:
        lifecycle.current_status(deciding, run_id, lock=True)
        approvals.decide(deciding, run_id, "reject", by="test: connection A")
        lifecycle.transition(deciding, run_id, RunStatus.REJECTED, by="test: connection A")
        engaging = pool.submit(engage_on_its_own_connection)
        assert waiting_on_a_lock(), "connection B never waited on the run's row lock"
        deciding.commit()
        assert engaging.result(timeout=10) == "engaged"
    assert client.get("/control").json()["kill_switch"] == "engaged"
    detail = run(client, run_id)
    assert detail["status"] == "rejected"
    assert not any(e["kind"] == "killswitch_blocked" for e in detail["events"])
    decided = sql("SELECT decision, decided_by FROM ops.approvals")
    assert [(a["decision"], a["decided_by"]) for a in decided] == [("reject", "test: connection A")]


def test_the_daily_budget_blocks_before_claim(client, make_worker) -> None:
    from datapilot.loop3_events.budget import eastern_day

    execute(
        "INSERT INTO ops.budgets (day, token_limit, tokens_used) VALUES (%s, 100, 100)",
        eastern_day(),
    )
    client.post("/control/autonomy", json={"level": "assisted"})
    submitted = ask(client)
    drain(make_worker())
    detail = run(client, submitted["run_id"])
    assert detail["status"] == "blocked_budget"
    assert any(e["kind"] == "budget_blocked" for e in detail["events"])
    assert client.get("/control").json()["reason"] == "budget_exhausted"


def test_the_daily_budget_stops_a_run_mid_way(client, make_worker) -> None:
    from datapilot.loop3_events.budget import eastern_day

    execute(
        "INSERT INTO ops.budgets (day, token_limit, tokens_used) VALUES (%s, 150, 0)", eastern_day()
    )
    submitted = ask(client)  # the first model call uses 120 tokens, the second would pass 150
    drain(make_worker(query_then_answer(COUNT_SQL, "There are 2000 orders.")))
    detail = run(client, submitted["run_id"])
    assert detail["status"] in ("blocked_budget", "posted")
    used = sql("SELECT tokens_used FROM ops.budgets")[0]["tokens_used"]
    assert used >= 120


# --- the verification demos as runs ---
@pytest.mark.parametrize("flag", ["0", "1"])
def test_the_malicious_sql_demo_shows_which_layer_stopped_each(
    client, make_worker, monkeypatch, flag
) -> None:
    monkeypatch.setenv("BUG_NAIVE_GUARD", flag)
    submitted = client.post("/demo/malicious-sql").json()
    drain(make_worker())
    detail = run(client, submitted["run_id"])
    assert detail["status"] == "posted"
    rows = detail["answer"]["envelope"]["rows_preview"]
    stopped_by = [stopper for _sql, stopper in rows]
    if flag == "1":
        assert stopped_by == ["read-only transaction", "read-only transaction", "role grants"]
    else:
        assert stopped_by == ["guard: parse", "guard: statement_policy", "role grants"]
    assert detail["answer"]["envelope"]["assumptions"] == ["orders unchanged: True"]


def test_the_cost_guard_demo_rejects_at_once(client, make_worker, monkeypatch) -> None:
    monkeypatch.delenv("BUG_NO_COST_GUARD", raising=False)
    submitted = client.post("/demo/cartesian-query").json()
    drain(make_worker())
    rows = run(client, submitted["run_id"])["answer"]["envelope"]["rows_preview"]
    assert rows[0][1] == "cost guard"


# --- sessions, live stamps, demo controls ---
def end_sessions() -> None:
    sql("UPDATE ops.live_sessions SET ended_at = now() WHERE ended_at IS NULL")


def test_runs_belong_to_the_open_session_and_carry_live_stamps(client) -> None:
    end_sessions()
    with pytest.raises(NoLiveSession):
        sessions.current_session()
    assert client.get("/sessions/current").status_code == 404
    first = sessions.start_session(SessionPurpose.DEVELOPMENT, "test", "America/New_York")
    inside = ask(client)
    listed = client.get("/runs").json()
    assert [r["run_id"] for r in listed["runs"]] == [inside["run_id"]]
    stamp = listed["runs"][0]["live_stamp"]
    assert listed["runs"][0]["session_id"] == str(first.session_id)
    assert stamp["run_id"] == inside["run_id"] and stamp["started_at_utc"].endswith("+00:00")
    assert listed["session"]["session_id"] == str(first.session_id)
    second = sessions.start_session(SessionPurpose.CLASS, "test", "America/New_York")
    assert sessions.current_session().session_id == second.session_id != first.session_id
    assert client.get("/runs").json()["runs"] == []
    assert len(client.get("/runs", params={"all_sessions": True}).json()["runs"]) == 1


def test_with_no_live_session_open_a_run_is_refused_before_any_model_call(client) -> None:
    """Session 6 review, learner path: a run asked for with no session open belonged to none,
    spent tokens, and never showed on the console. Now the api refuses it, and makes nothing;
    the scheduler's own digest, which no person asks for, still goes in without one."""
    end_sessions()
    body = {"event_id": f"test:{uuid.uuid4().hex}", "type": "question.asked"}
    refused = client.post("/events", json={**body, "payload": {"question": "How many orders?"}})
    assert refused.status_code == 409 and refused.json()["detail"] == sessions.NO_SESSION
    assert client.post("/demo/large-query").status_code == 409
    # before the planted header rules: an unknown flag, or another demo's, still gets the 409
    unknown = {planted.PLANTED_HEADER: "BUG_NOT_IN_THE_REGISTRY"}
    assert client.post("/demo/large-query", headers=unknown).status_code == 409
    foreign = {planted.PLANTED_HEADER: "BUG_NAIVE_GUARD"}
    assert client.post("/demo/large-query", headers=foreign).status_code == 409
    assert sql("SELECT count(*) AS n FROM ops.runs")[0]["n"] == 0
    assert sql("SELECT count(*) AS n FROM ops.jobs")[0]["n"] == 0
    digest = scheduler.request_digest(date(2026, 1, 31))
    assert not digest.duplicate and run(client, str(digest.run_id))["status"] == "queued"


def test_the_restart_control_is_off_unless_demo_controls_are_on(
    client, make_worker, monkeypatch, settings_refresh
) -> None:
    monkeypatch.setenv("DATAPILOT_ALLOW_DEMO_CONTROLS", "0")
    get_settings.cache_clear()
    assert client.post("/control/restart-worker").status_code == 403
    monkeypatch.setenv("DATAPILOT_ALLOW_DEMO_CONTROLS", "1")
    get_settings.cache_clear()
    worker = make_worker()
    assert client.post("/control/restart-worker").status_code == 200
    assert asyncio.run(worker.serve(asyncio.Event())) == "restart"


def test_experiment_and_analyzer_requests_are_enqueued_with_the_session(client) -> None:
    session = sessions.start_session(SessionPurpose.DEVELOPMENT, "test", "UTC")
    experiment = client.post("/experiments/run", json={"target": "active"}).json()
    analyzer = client.post("/analyzer/run", json={}).json()
    assert experiment["kind"] == "experiment" and analyzer["kind"] == "analyzer"
    assert experiment["session_id"] == str(session.session_id)
    rows = sql("SELECT status FROM ops.improvement_requests")
    assert [r["status"] for r in rows] == ["queued", "queued"]


def test_a_draft_knowledge_version_can_be_approved(client) -> None:
    execute(
        "INSERT INTO ops.knowledge_versions (version, yaml, created_by) "
        "VALUES ('loops-draft', 'version: loops-draft', 'test')"
    )
    try:
        approved = client.post("/knowledge/loops-draft/approve", json={"approved_by": "owner"})
        assert approved.json()["status"] == "approved"
        again = client.post("/knowledge/loops-draft/approve", json={"approved_by": "owner"})
        assert again.status_code == 409
        missing = client.post("/knowledge/no-such/approve", json={"approved_by": "owner"})
        assert missing.status_code == 404
    finally:
        execute("DELETE FROM ops.knowledge_versions WHERE version = 'loops-draft'")


def test_a_knowledge_approval_without_a_persons_name_is_refused(client) -> None:
    """Owner's decision, 27 October 2026: an empty name or "console" is refused (422) and the
    draft stays a draft."""
    execute(
        "INSERT INTO ops.knowledge_versions (version, yaml, created_by) "
        "VALUES ('loops-draft', 'version: loops-draft', 'test')"
    )
    try:
        for body in ({}, {"approved_by": ""}, {"approved_by": "console"}):
            assert client.post("/knowledge/loops-draft/approve", json=body).status_code == 422
        with db.connect(db.Role.OWNER) as conn:
            row = conn.execute(
                "SELECT status, approved_by FROM ops.knowledge_versions "
                "WHERE version = 'loops-draft'"
            ).fetchone()
        assert row is not None and row["status"] == "draft" and row["approved_by"] is None
    finally:
        execute("DELETE FROM ops.knowledge_versions WHERE version = 'loops-draft'")


def test_reset_clears_run_state_and_releases_the_kill_switch(client) -> None:
    from datapilot.loop3_events import commands

    ask(client)
    engage(client)
    commands.reset("event-loop")
    assert sql("SELECT count(*) AS n FROM ops.runs")[0]["n"] == 0
    assert client.get("/control").json()["kill_switch"] == "released"


def test_the_executor_serves_the_evaluator_interface(executor) -> None:
    from datapilot.loop2_verification.executor import WarehouseRunner

    result = WarehouseRunner({"warehouse": executor}).run(
        "SELECT order_id FROM orders", "warehouse", max_rows=10
    )
    assert len(result.rows) == 10 and result.total_row_count == 2000 and result.truncated


def test_console_settings_come_from_the_pack(client) -> None:
    settings = client.get("/console/settings").json()
    assert settings["kill_switch_disarm_seconds"] > 0 and settings["business_date"]


def test_kill_switch_state_machine() -> None:
    with db.connect(db.Role.APP) as conn:
        assert killswitch.set_state(conn, "arm", by="t") == "armed"
        assert killswitch.set_state(conn, "release", by="t") == "released"
        with pytest.raises(killswitch.KillSwitchRefused):
            killswitch.set_state(conn, "engage", by="t")
        conn.rollback()
