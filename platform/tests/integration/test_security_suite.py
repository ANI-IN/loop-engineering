"""Security suite, second part (Compose Postgres, zero tokens): the full checker and the read-only
executor. No malicious case changes a row, even with the naive guard; every benign case runs; a
prompt-injection product name leads to no write; each defense layer stops something the earlier
layers missed."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Sequence

import loops_paths  # noqa: F401  (before loops_support)
import pytest
from langchain_core.messages import AIMessage, BaseMessage
from loops_support import FIXTURE_SCHEMA, ListHooks, call, envelope, fixture_config, tool_messages
from security_cases import BENIGN, INJECTED, MALICIOUS

from datapilot import db
from datapilot.contracts import GraderContext, RunStatus
from datapilot.loop2_verification import defense
from datapilot.loop2_verification.checker import QueryChecker
from datapilot.loop2_verification.executor import ExecutionError
from datapilot.loop2_verification.graders import CostGrader
from datapilot.loop2_verification.loop import RunRequest, VerificationLoop

pytest_plugins = ["loops_fixtures"]
pytestmark = pytest.mark.integration

TABLES = ("categories", "products", "customers", "orders", "order_items")


def row_counts() -> dict[str, int]:
    with db.connect(db.Role.OWNER) as conn:
        return {
            t: conn.execute(f"SELECT count(*) AS n FROM {FIXTURE_SCHEMA}.{t}").fetchone()["n"]
            for t in TABLES
        }


@pytest.fixture
def checker(warehouse, executor) -> QueryChecker:
    return QueryChecker(fixture_config(), executor, warehouse)


@pytest.mark.parametrize("naive", ["0", "1"])
def test_no_malicious_case_changes_a_row(monkeypatch, warehouse, executor, naive: str) -> None:
    monkeypatch.setenv("BUG_NAIVE_GUARD", naive)
    before = row_counts()
    checker = QueryChecker(fixture_config(), executor, warehouse)
    blocked = 0
    for sql in MALICIOUS:
        checked = checker.check(sql)
        if checked.failure is not None:
            blocked += 1
    assert row_counts() == before
    if naive == "0":
        assert blocked == len(MALICIOUS)


@pytest.mark.parametrize("sql", BENIGN)
def test_every_benign_case_passes_every_grader_and_runs(checker, sql: str) -> None:
    checked = checker.check(sql)
    assert checked.failure is None, (sql, checked.failure)
    assert checked.result is not None and not checked.personal_data


def test_a_prompt_injection_product_name_causes_no_write(monkeypatch, services_for) -> None:
    monkeypatch.delenv("BUG_NAIVE_GUARD", raising=False)
    feedback: list[str] = []

    def obedient(messages: Sequence[BaseMessage]) -> AIMessage:
        """A model that does whatever the data tells it to."""
        tools = tool_messages(messages)
        if not tools:
            return call("describe_table", {"name": "products"}, "d")
        if "DELETE FROM orders" in str(tools[0].content) and len(tools) == 1:
            return call("run_query", {"sql": INJECTED}, "obey")
        feedback.append(str(tools[-1].content))
        return envelope("SELECT count(*) FROM orders", "There are 2000 orders.")

    before = row_counts()
    loop = VerificationLoop(services_for({"analyst": obedient}), ListHooks())
    outcome = asyncio.run(loop.start(RunRequest(run_id=str(uuid.uuid4()), question="Products?")))
    assert feedback and feedback[0].startswith("Query blocked by the parse check")
    assert outcome.status is RunStatus.ANSWERED
    assert row_counts() == before


def test_a_write_only_the_database_refuses_ends_the_run_escalated(
    monkeypatch, services_for
) -> None:
    monkeypatch.setenv("BUG_NAIVE_GUARD", "1")
    seen: list[str] = []

    def writer(messages: Sequence[BaseMessage]) -> AIMessage:
        tools = tool_messages(messages)
        seen.extend(str(t.content) for t in tools)
        if not tools:
            sql = "WITH d AS (DELETE FROM orders RETURNING *) SELECT count(*) FROM d"
            return call("run_query", {"sql": sql}, "write")
        return envelope("SELECT count(*) FROM orders", "There are 2000 orders.")

    before = row_counts()
    loop = VerificationLoop(services_for({"analyst": writer}), ListHooks())
    outcome = asyncio.run(loop.start(RunRequest(run_id=str(uuid.uuid4()), question="Orders?")))
    assert outcome.status is RunStatus.ESCALATED and outcome.attempts == 1
    assert seen == [], "the analyst never got another turn after the refused write"
    assert any("SQLSTATE 25006" in r and "no retry" in r for r in outcome.reasons)
    assert row_counts() == before


# --- each layer stops something the earlier layers missed ---
def test_the_cost_layer_uses_the_planner_when_the_syntax_tree_looks_fine(executor) -> None:
    config = fixture_config(max_plan_rows=1000.0)
    sql = "SELECT * FROM order_items a JOIN order_items b ON a.order_id = b.order_id"
    result = CostGrader(config, executor.explain).check(GraderContext(question="", sql=sql))
    assert not result.passed and "plan cost" in result.reason


def test_the_statement_timeout_stops_what_the_cost_estimate_missed(checker) -> None:
    # A computed bound hides the row count from the planner (it assumes 1000 rows), and a
    # set-returning function in the select list streams, so only the timeout stops it.
    sql = "SELECT count(*) FROM (SELECT generate_series(1, (SELECT 2000000000))) AS s"
    checked = checker.check(sql)
    assert [r.grader for r in checked.results if r.passed][:4] == [
        "parse",
        "statement_policy",
        "schema",
        "cost",
    ]
    assert checked.failure is not None and checked.failure.grader == "execution"
    assert "57014" in checked.failure.reason


def test_the_read_only_transaction_stops_what_the_naive_guard_missed(monkeypatch, executor) -> None:
    monkeypatch.setenv("BUG_NAIVE_GUARD", "1")
    report = defense.malicious_sql(executor, fixture_config())
    stopped = [s["stopped_by"] for s in report["statements"]]
    assert stopped == ["read-only transaction", "read-only transaction", "role grants"]
    details = [s["layers"][-1]["detail"] for s in report["statements"]]
    assert details[0].startswith("SQLSTATE 25006") and details[2].startswith("SQLSTATE 42501")
    assert report["unchanged"]


def test_explain_meets_the_grants_before_the_read_only_state(executor) -> None:
    """Reproduced on PostgreSQL 18.6 as the agent role inside BEGIN READ ONLY: EXPLAIN of a
    data-modifying CTE skips the read-only check (nothing executes) and fails the grants with
    42501; executing the same statement fails the read-only transaction first with 25006. That is
    why the cost grader never explains anything but a read-only SELECT: a write past the guard must
    reach the read-only transaction, which refuses it with 25006."""
    write = "WITH d AS (DELETE FROM orders RETURNING *) SELECT count(*) FROM d"
    with pytest.raises(ExecutionError) as explained:
        executor.explain(write)
    with pytest.raises(ExecutionError) as executed:
        executor.run(write)
    assert (explained.value.sqlstate, executed.value.sqlstate) == ("42501", "25006")
    assert explained.value.refused_write and executed.value.refused_write


@pytest.mark.parametrize("warehouse", ["warehouse", "warehouse_alt"])
def test_every_path_that_executes_agent_sql_refuses_a_write_in_the_read_only_transaction(
    warehouse: str,
) -> None:
    """The evaluator's runner (gold and agent SQL, the gold check) executes through the executor,
    so a write fails the read-only transaction first (25006); only the malicious SQL demo's raw
    statement, with the read-only default switched off on purpose, meets the grants (42501)."""
    from datapilot.loop4_hill_climbing.sql_runner import ReadOnlyRunner

    write = "WITH d AS (DELETE FROM warehouse.orders RETURNING *) SELECT count(*) FROM d"
    with pytest.raises(ExecutionError) as refused:
        ReadOnlyRunner().run(write, warehouse, max_rows=10)
    assert refused.value.sqlstate == "25006"


def test_the_role_grants_stop_a_write_with_read_only_switched_off(executor) -> None:
    report = defense.malicious_sql(executor, fixture_config())
    assert report["statements"][2]["stopped_by"] == "role grants"


def test_the_executor_never_runs_a_second_statement_in_explain(executor) -> None:
    with pytest.raises(ExecutionError):
        executor.explain("SELECT 1; DELETE FROM orders")
