"""The hill-climbing wiring against the Compose Postgres: installing the shipped knowledge, an
experiment streamed into ops item by item, and the gold check run event (zero tokens)."""

from __future__ import annotations

import uuid

import pytest
from psycopg.types.json import Jsonb

from datapilot import db
from datapilot.contracts import AnswerStatus, BenchmarkItem, Category, Split
from datapilot.loop4_hill_climbing import gold, store, versions
from datapilot.loop4_hill_climbing.evaluator import ExecutionEvaluator
from datapilot.loop4_hill_climbing.experiment import ExperimentRunner
from datapilot.loop4_hill_climbing.measurement import Scheme

pytestmark = pytest.mark.integration


@pytest.fixture
def conn():
    with db.connect(db.Role.APP) as connection:
        yield connection
        connection.rollback()


def test_install_adds_the_shipped_versions_and_activates_the_starting_one(conn) -> None:
    conn.execute("UPDATE ops.knowledge_versions SET status = 'retired' WHERE status = 'active'")
    versions.install(conn)
    assert versions.active_name(conn) == "v1"
    assert versions.status_of(conn, "v2-overbroad") is not None
    assert versions.install(conn) == [], "installing twice adds nothing"


def _item(item_id: str, split: Split) -> BenchmarkItem:
    return BenchmarkItem(
        id=item_id,
        question=f"How many products are there ({item_id})?",
        gold_sql="SELECT count(*) FROM warehouse.products",
        split=split,
        category=Category.SIMPLE_AGGREGATES,
        difficulty=1,
        metric_family="products",
    )


def _session() -> uuid.UUID:
    session_id = uuid.uuid4()
    with db.connect(db.Role.APP) as c:
        c.execute("UPDATE ops.live_sessions SET ended_at = now() WHERE ended_at IS NULL")
        c.execute(
            "INSERT INTO ops.live_sessions (session_id, started_by, timezone) "
            "VALUES (%s, 'integration test', 'UTC')",
            (session_id,),
        )
        c.execute(
            "INSERT INTO ops.knowledge_versions (version, yaml, created_by) "
            "VALUES ('stream-test', 'version: stream-test', 'test') ON CONFLICT DO NOTHING"
        )
        c.commit()
    return session_id


def test_an_experiment_streams_each_item_into_ops_then_finishes() -> None:
    from datapilot.contracts import AnswerEnvelope

    session_id = _session()
    seen: list[int] = []

    def target(question: str, version: str) -> AnswerEnvelope:
        with db.connect(db.Role.APP) as c:  # what the console sees while the run goes on
            row = c.execute(
                "SELECT jsonb_array_length(per_example) AS n FROM ops.experiments "
                "WHERE session_id = %s",
                (session_id,),
            ).fetchone()
            seen.append(row["n"])
        return AnswerEnvelope(
            status=AnswerStatus.ANSWERED, final_sql="SELECT count(*) FROM warehouse.products"
        )

    items = [_item("stream-dev", Split.DEV), _item("stream-holdout", Split.HOLDOUT)]
    runner = ExperimentRunner(
        target,
        ExecutionEvaluator.live(),
        Scheme(),
        concurrency=1,
        sink=store.OpsItemSink(holdout_repeats=3, concurrency=1),
    )
    try:
        result = runner.run(items, "stream-test", session_id=session_id)
        with db.connect(db.Role.APP) as c:
            store.finish_experiment(c, result, langsmith_url=None)
            c.commit()
            read = store.baseline_for(c, "stream-test")
        assert seen[0] == 0 and max(seen) == 1, "the first item was visible before the last ran"
        assert read.passes(Split.HOLDOUT) == 1 and read.results["stream-holdout"].run_passes == [
            True,
            True,
            True,
        ]
        assert read.final_sql["stream-dev"].startswith("SELECT count(*)")
    finally:
        with db.connect(db.Role.APP) as c:
            c.execute("DELETE FROM ops.experiments WHERE session_id = %s", (session_id,))
            c.execute("DELETE FROM ops.knowledge_versions WHERE version = 'stream-test'")
            c.commit()


def test_a_run_that_answered_a_benchmark_question_gets_one_gold_check(conn) -> None:
    session_id = _session()
    question = "What was our net revenue in fiscal year 2025?"
    run_id = uuid.uuid4()
    conn.execute(
        "INSERT INTO ops.runs (run_id, question, status, session_id, answer) "
        "VALUES (%s, %s, 'posted', %s, %s)",
        (
            run_id,
            question,
            session_id,
            Jsonb(
                {
                    "envelope": {
                        "status": "answered",
                        "final_sql": "SELECT round(sum(total_cents) / 100.0, 2) "
                        "FROM warehouse.orders",
                    }
                }
            ),
        ),
    )
    from datapilot.loop4_hill_climbing.pack_files import load_benchmark

    items = load_benchmark()
    checked = gold.check_new_runs(conn, items, ExecutionEvaluator.live())
    assert checked == [str(run_id)]
    event = conn.execute(
        "SELECT payload FROM ops.run_events WHERE run_id = %s AND kind = 'grader_result'",
        (run_id,),
    ).fetchone()["payload"]
    assert event["grader"] == "gold" and event["passed"] is False
    assert "total_cents_used" in event["trap_labels"]
    assert gold.check_new_runs(conn, items, ExecutionEvaluator.live()) == []


def _holdout(item_id: str, family: str) -> BenchmarkItem:
    return _item(item_id, Split.HOLDOUT).model_copy(update={"metric_family": family})


def test_a_promotion_clears_families_on_the_confirmed_standard_and_records_the_reruns() -> None:
    """Revenue: one item fell short (1 of 3) and passed 2 of 3 more runs, so it is cleared.
    Average order value: its one item fell short twice, so it stays below the unattended level."""
    from datetime import UTC, datetime

    from datapilot.contracts import ItemResult
    from datapilot.loop4_hill_climbing.experiment import ExperimentResult
    from datapilot.loop4_hill_climbing.runner import activate

    session_id = _session()
    items = [_holdout(f"clear-r{n}", "revenue") for n in (1, 2, 3)] + [_holdout("clear-a1", "aov")]
    runs = {
        "clear-r1": [True, True, True],
        "clear-r2": [False, True, False],
        "clear-r3": [True, False, True],
        "clear-a1": [False, False, True],
    }
    scheme = Scheme()
    candidate = ExperimentResult(
        experiment_id=uuid.uuid4(),
        session_id=session_id,
        knowledge_version="stream-test",
        splits=[Split.HOLDOUT],
        results={
            i: ItemResult(
                item_id=i, passed=scheme.passes(Split.HOLDOUT, r), reason="", run_passes=r
            )
            for i, r in runs.items()
        },
        splits_by_item={i: Split.HOLDOUT for i in runs},
        started_at=datetime.now(UTC),
        wall_seconds=1.0,
    )
    with db.connect(db.Role.APP) as conn:
        previous = versions.active_name(conn)
        try:
            store.save_experiment(conn, candidate, holdout_repeats=3, concurrency=1)
            script = {"clear-r2": [True, False, True], "clear-a1": [False, True, False]}
            asked: list[tuple[str, int]] = []
            seen_by_others: list[str] = []

            def rerun(benchmark_item: BenchmarkItem, times: int) -> list[bool]:
                asked.append((benchmark_item.id, times))
                # Review round 1 (F012): the activation is committed before the re-runs, which
                # call the model, so no transaction (and no row lock) is held through them.
                assert conn.info.transaction_status.name == "IDLE"
                with db.connect(db.Role.APP) as other:
                    seen_by_others.append(versions.active_name(other))
                return script[benchmark_item.id]

            clearance = activate(
                conn, "stream-test", candidate, items=items, rerun=rerun, scheme=scheme
            )
            assert clearance.cleared == ["revenue"]
            assert sorted(asked) == [("clear-a1", 3), ("clear-r2", 3)]
            assert versions.active_name(conn) == "stream-test"
            rows = conn.execute(
                "SELECT metric_family, level FROM ops.autonomy_policy WHERE knowledge_version = %s",
                ("stream-test",),
            ).fetchall()
            assert {r["metric_family"]: r["level"] for r in rows} == {"revenue": "unattended"}
            examples = conn.execute(
                "SELECT per_example FROM ops.experiments WHERE experiment_id = %s",
                (candidate.experiment_id,),
            ).fetchone()["per_example"]
            recorded = {e["item_id"]: e.get("clearance_rerun") for e in examples}
            assert recorded["clear-r2"] == {"runs": 3, "passes": 2, "reruns": [True, False, True]}
            assert recorded["clear-a1"]["passes"] == 1 and recorded["clear-r1"] is None
            assert seen_by_others == ["stream-test", "stream-test"]
        finally:
            # The activation and the clearances are committed (they no longer roll back with the
            # test, as they did when this test pinned one transaction): undo them by hand.
            conn.rollback()
            conn.execute("DELETE FROM ops.autonomy_policy WHERE knowledge_version = 'stream-test'")
            conn.execute("DELETE FROM ops.experiments WHERE knowledge_version = 'stream-test'")
            versions.activate(conn, previous)
            conn.execute("DELETE FROM ops.knowledge_versions WHERE version = 'stream-test'")
            conn.commit()
