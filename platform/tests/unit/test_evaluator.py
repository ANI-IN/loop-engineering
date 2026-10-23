"""The evaluator: execution match on both warehouses, normalized, with non-gating trap labels."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest
from loop4_doubles import TableRunner, answered, item

from datapilot.contracts import AnswerEnvelope, AnswerStatus
from datapilot.loop4_hill_climbing.evaluator import ExecutionEvaluator, compare
from datapilot.loop4_hill_climbing.trap_detectors import detect, labels_for

GOLD = "SELECT gold"


def _both(sql: str, main: list[tuple], alt: list[tuple]) -> dict:
    return {(sql, "warehouse"): main, (sql, "warehouse_alt"): alt}


def test_numbers_match_within_the_tolerance_and_column_names_are_ignored() -> None:
    assert compare([(Decimal("100.004"),)], [(100.0,)], tolerance=0.01, order_matters=False)[0]
    assert not compare([(100.03,)], [(100.0,)], tolerance=0.01, order_matters=False)[0]


def test_rows_are_a_multiset_unless_order_matters() -> None:
    rows, flipped = [("a", 1), ("b", 2)], [("b", 2), ("a", 1)]
    assert compare(flipped, rows, tolerance=0.01, order_matters=False)[0]
    assert not compare(flipped, rows, tolerance=0.01, order_matters=True)[0]


def test_column_count_and_row_count_must_match() -> None:
    assert (
        compare([(1, 2)], [(1,)], tolerance=0.01, order_matters=False)[1] == "2 columns, expected 1"
    )
    assert not compare([(1,), (1,)], [(1,)], tolerance=0.01, order_matters=False)[0]


def test_a_midnight_timestamp_equals_its_date() -> None:
    assert compare(
        [(datetime(2024, 11, 29), 5)], [(date(2024, 11, 29), 5)], tolerance=0.01, order_matters=True
    )[0]


def test_a_match_on_both_warehouses_passes() -> None:
    runner = TableRunner({**_both(GOLD, [(10,)], [(7,)]), **_both("SELECT p", [(10,)], [(7,)])})
    result = ExecutionEvaluator(runner).evaluate(item(gold_sql=GOLD), answered("SELECT p"))
    assert result.passed and result.reason == "matches gold on both warehouses"


def test_a_match_on_one_warehouse_only_fails() -> None:
    runner = TableRunner({**_both(GOLD, [(10,)], [(7,)]), **_both("SELECT p", [(10,)], [(10,)])})
    result = ExecutionEvaluator(runner).evaluate(item(gold_sql=GOLD), answered("SELECT p"))
    assert not result.passed and result.reason.startswith("warehouse_alt:")


def test_a_query_that_fails_to_run_is_a_failed_item() -> None:
    runner = TableRunner(_both(GOLD, [(1,)], [(1,)]))
    result = ExecutionEvaluator(runner).evaluate(item(gold_sql=GOLD), answered("SELEC broken"))
    assert not result.passed and "query failed" in result.reason


def test_an_answer_without_sql_fails() -> None:
    answer = AnswerEnvelope(status=AnswerStatus.REFUSED)
    result = ExecutionEvaluator(TableRunner({})).evaluate(item(), answer)
    assert not result.passed


def test_a_clarification_item_passes_only_on_needs_clarification() -> None:
    ambiguous = item(gold_sql=None, expected_status=AnswerStatus.NEEDS_CLARIFICATION)
    evaluator = ExecutionEvaluator(TableRunner({}))
    asked = AnswerEnvelope(status=AnswerStatus.NEEDS_CLARIFICATION, clarifying_question="Which?")
    assert evaluator.evaluate(ambiguous, asked).passed
    assert not evaluator.evaluate(ambiguous, answered("SELECT 1")).passed


def test_the_sql_text_evaluator_marks_a_correct_answer_wrong(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = TableRunner({**_both(GOLD, [(10,)], [(7,)]), **_both("SELECT p", [(10,)], [(7,)])})
    evaluator = ExecutionEvaluator(runner)
    monkeypatch.setenv("BUG_SQL_TEXT_EVAL", "1")
    assert not evaluator.evaluate(item(gold_sql=GOLD), answered("SELECT p")).passed
    assert runner.calls == []
    monkeypatch.setenv("BUG_SQL_TEXT_EVAL", "0")
    assert evaluator.evaluate(item(gold_sql=GOLD), answered("SELECT p")).passed


NAIVE = "SELECT sum(total_cents) FROM warehouse.orders WHERE extract(year FROM order_ts) = 2025"
GOOD = (
    "SELECT sum(o.subtotal_cents - o.discount_cents) FROM warehouse.orders o "
    "JOIN warehouse.customers c ON c.customer_id = o.customer_id WHERE o.status <> 5 "
    "AND lower(c.email) NOT LIKE '%@harborpine.com' "
    "AND (o.order_ts AT TIME ZONE 'America/New_York') >= DATE '2024-02-01'"
)


def test_trap_detectors_label_the_naive_query() -> None:
    assert detect(NAIVE) == [
        "calendar_year_range",
        "total_cents_used",
        "missing_status_filter",
        "utc_truncation",
        "missing_internal_filter",
    ]


def test_trap_detectors_find_nothing_in_the_rule_following_query() -> None:
    assert detect(GOOD) == []


def test_labels_are_limited_to_the_item_traps_and_never_gate() -> None:
    assert labels_for(NAIVE, ["net_revenue"]) == ["total_cents_used"]
    runner = TableRunner({**_both(GOLD, [(1,)], [(1,)]), **_both(NAIVE, [(1,)], [(1,)])})
    result = ExecutionEvaluator(runner).evaluate(
        item(gold_sql=GOLD, traps=["net_revenue"]), answered(NAIVE)
    )
    assert result.passed and result.trap_labels == ["total_cents_used"]


def test_unparseable_sql_gets_no_labels() -> None:
    assert detect("SELEC 1 FROM") == []
