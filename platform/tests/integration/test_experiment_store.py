"""Experiments and gate decisions in ops, bound to the open live session (Compose Postgres)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from datapilot import db
from datapilot.contracts import ItemResult, Split
from datapilot.contracts.live import NoLiveBaseline, NoLiveSession
from datapilot.loop4_hill_climbing import store
from datapilot.loop4_hill_climbing.experiment import Confirmation, ExperimentResult
from datapilot.loop4_hill_climbing.gate import Regressions, decide

pytestmark = pytest.mark.integration


@pytest.fixture
def conn():
    with db.connect(db.Role.APP) as connection:
        yield connection
        connection.rollback()  # every test leaves ops as it found it


def _open_session(conn) -> uuid.UUID:
    conn.execute("UPDATE ops.live_sessions SET ended_at = now() WHERE ended_at IS NULL")
    session_id = uuid.uuid4()
    conn.execute(
        "INSERT INTO ops.live_sessions (session_id, started_by, timezone) "
        "VALUES (%s, 'test', 'UTC')",
        (session_id,),
    )
    for version in ("test-v1", "test-v2"):
        conn.execute(
            "INSERT INTO ops.knowledge_versions (version, yaml, created_by) "
            "VALUES (%s, '', 'test') ON CONFLICT DO NOTHING",
            (version,),
        )
    return session_id


def _experiment(session_id: uuid.UUID, version: str, holdout_pass: bool) -> ExperimentResult:
    return ExperimentResult(
        experiment_id=uuid.uuid4(),
        session_id=session_id,
        knowledge_version=version,
        splits=[Split.DEV, Split.HOLDOUT],
        results={
            "d1": ItemResult(item_id="d1", passed=True, reason="ok", run_passes=[True]),
            "h1": ItemResult(
                item_id="h1", passed=holdout_pass, reason="", run_passes=[holdout_pass] * 3
            ),
        },
        splits_by_item={"d1": Split.DEV, "h1": Split.HOLDOUT},
        started_at=datetime.now(UTC),
        wall_seconds=12.5,
    )


def test_no_open_session_raises(conn) -> None:
    conn.execute("UPDATE ops.live_sessions SET ended_at = now() WHERE ended_at IS NULL")
    with pytest.raises(NoLiveSession):
        store.open_session(conn)


def test_the_baseline_comes_from_the_open_session_only(conn) -> None:
    old = _open_session(conn)
    store.save_experiment(
        conn, _experiment(old, "test-v1", False), holdout_repeats=3, concurrency=8
    )
    _open_session(conn)  # a new session: the older experiment can never be the baseline
    with pytest.raises(NoLiveBaseline):
        store.baseline_for(conn, "test-v1")


def test_a_saved_experiment_reads_back_and_feeds_the_gate(conn) -> None:
    session_id = _open_session(conn)
    active = _experiment(session_id, "test-v1", False)
    store.save_experiment(conn, active, holdout_repeats=3, concurrency=8)
    baseline = store.baseline_for(conn, "test-v1")
    assert baseline.experiment_id == active.experiment_id and baseline.session_id == session_id
    assert baseline.results == active.results and baseline.splits_by_item == active.splits_by_item
    decision = decide(
        baseline, _experiment(session_id, "test-v2", True), Regressions(), approved_by="test"
    )
    assert decision.verdict == "promoted"
    assert store.save_decision(conn, decision) > 0


def test_confirmation_steps_are_written_live_into_the_experiment() -> None:
    with db.connect(db.Role.APP) as conn:
        session_id = _open_session(conn)
        candidate = _experiment(session_id, "test-v2", False)
        store.save_experiment(conn, candidate, holdout_repeats=3, concurrency=8)
        conn.commit()
        try:
            confirmation = Confirmation(
                "h1", Split.HOLDOUT, steps=["Apparent regression: confirming with 3 more runs"]
            )
            sink = store.OpsStepSink(conn)
            sink.step(candidate.experiment_id, confirmation)
            with db.connect(db.Role.APP) as console:  # another session sees the committed step
                row = console.execute(
                    "SELECT per_example FROM ops.experiments WHERE experiment_id = %s",
                    (candidate.experiment_id,),
                ).fetchone()
            entry = next(e for e in row["per_example"] if e["item_id"] == "h1")
            assert entry["confirmation"]["steps"] == confirmation.steps
            confirmation.reruns, confirmation.confirmed = [False, False, True], True
            confirmation.steps.append("Confirmed regression: failed 2 of 3 more runs")
            sink.step(candidate.experiment_id, confirmation)
            readback = store.baseline_for(conn, "test-v2").confirmations["h1"]
            assert readback.confirmed is True and readback.reruns == [False, False, True]
            assert [e["item_id"] for e in row["per_example"]] == ["d1", "h1"]
        finally:
            conn.execute(
                "DELETE FROM ops.experiments WHERE experiment_id = %s", (candidate.experiment_id,)
            )
            conn.execute(
                "UPDATE ops.live_sessions SET ended_at = now() WHERE session_id = %s", (session_id,)
            )
            conn.commit()
