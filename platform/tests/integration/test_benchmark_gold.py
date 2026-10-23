"""Every gold query runs on both warehouses, returns rows, and is deterministic; every naive query
returns a different result than gold on both (trap sensitivity). Zero model calls."""

from __future__ import annotations

import pytest

from datapilot.contracts import AnswerEnvelope, AnswerStatus
from datapilot.loop4_hill_climbing.evaluator import ExecutionEvaluator, compare
from datapilot.loop4_hill_climbing.pack_files import load_benchmark
from datapilot.loop4_hill_climbing.sql_runner import WAREHOUSES, ReadOnlyRunner

pytestmark = pytest.mark.integration
ITEMS = load_benchmark()
RUNNER = ReadOnlyRunner()
TRAP_ITEMS = [i for i in ITEMS if i.naive_sql]


@pytest.mark.parametrize("warehouse", WAREHOUSES)
@pytest.mark.parametrize("item", ITEMS, ids=lambda i: i.id)
def test_gold_runs_returns_rows_and_repeats_exactly(item, warehouse: str) -> None:
    first = RUNNER.run(item.gold_sql, warehouse, max_rows=1000)
    second = RUNNER.run(item.gold_sql, warehouse, max_rows=1000)
    assert first.rows and not first.truncated
    assert all(v is not None for row in first.rows for v in row)
    assert first.rows == second.rows


@pytest.mark.parametrize("warehouse", WAREHOUSES)
@pytest.mark.parametrize("item", TRAP_ITEMS, ids=lambda i: i.id)
def test_the_naive_query_gives_a_different_answer(item, warehouse: str) -> None:
    gold = RUNNER.run(item.gold_sql, warehouse, max_rows=1000)
    naive = RUNNER.run(item.naive_sql, warehouse, max_rows=1000)
    same, _ = compare(
        naive.rows, gold.rows, tolerance=item.numeric_tolerance, order_matters=item.order_matters
    )
    assert not same


@pytest.mark.parametrize("item", ITEMS, ids=lambda i: i.id)
def test_the_evaluator_passes_gold_and_fails_naive(item) -> None:
    evaluator = ExecutionEvaluator(RUNNER)
    gold = AnswerEnvelope(status=AnswerStatus.ANSWERED, final_sql=item.gold_sql)
    assert evaluator.evaluate(item, gold).passed
    if item.naive_sql:
        naive = AnswerEnvelope(status=AnswerStatus.ANSWERED, final_sql=item.naive_sql)
        result = evaluator.evaluate(item, naive)
        assert not result.passed and result.trap_labels
