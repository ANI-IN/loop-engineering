"""The execution-match evaluator: an answer passes only if its SQL returns the gold result on both
warehouse and warehouse_alt.

Results are normalized before comparing: numbers on the item's tolerance grid, column names
ignored, the same column count required, rows compared as a multiset unless order matters. Trap
labels are attached for explanation only, and only to a failed result: never beside a match.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from datapilot.contracts import AnswerEnvelope, AnswerStatus, BenchmarkItem, ItemResult
from datapilot.loop4_hill_climbing.sql_runner import WAREHOUSES, ReadOnlyRunner, SqlRunner
from datapilot.loop4_hill_climbing.trap_detectors import labels_for
from datapilot.planted import planted

Cell = tuple[int, Any]  # (kind, value): kind 0 null, 1 number on the grid, 2 text


def normalize_cell(value: Any, tolerance: float) -> Cell:
    if value is None:
        return (0, None)
    if isinstance(value, bool):
        return (2, str(value).lower())
    if isinstance(value, int | float | Decimal):
        number = float(value)
        if math.isnan(number):
            return (2, "nan")
        return (1, round(number / tolerance))
    if isinstance(value, datetime) and value.tzinfo is None and value.time() == time(0):
        return (2, value.date().isoformat())
    if isinstance(value, date | datetime):
        return (2, value.isoformat())
    return (2, str(value).strip())


def normalize(rows: list[tuple[Any, ...]], tolerance: float, order_matters: bool) -> list[tuple]:
    out = [tuple(normalize_cell(v, tolerance) for v in row) for row in rows]
    return out if order_matters else sorted(out, key=repr)


def _cells_match(a: Cell, b: Cell) -> bool:
    if a[0] == b[0] == 1:
        return abs(a[1] - b[1]) <= 1  # one grid step absorbs rounding at the boundary
    return a == b


def compare(
    predicted: list[tuple[Any, ...]],
    gold: list[tuple[Any, ...]],
    *,
    tolerance: float,
    order_matters: bool,
) -> tuple[bool, str]:
    """(match, reason) for one warehouse."""
    if gold and predicted and len(predicted[0]) != len(gold[0]):
        return False, f"{len(predicted[0])} columns, expected {len(gold[0])}"
    if len(predicted) != len(gold):
        return False, f"{len(predicted)} rows, expected {len(gold)}"
    left = normalize(predicted, tolerance, order_matters)
    right = normalize(gold, tolerance, order_matters)
    for index, (p_row, g_row) in enumerate(zip(left, right, strict=True)):
        if not all(_cells_match(p, g) for p, g in zip(p_row, g_row, strict=True)):
            return False, f"row {index + 1} differs from gold"
    return True, "matches gold"


def _sql_text(sql: str) -> str:
    return " ".join(sql.lower().replace(";", " ").split())


@dataclass
class ExecutionEvaluator:
    """Implements datapilot.contracts.Evaluator. Gold SQL runs live on every evaluation."""

    runner: SqlRunner
    max_rows: int = 10_000

    @classmethod
    def live(cls) -> ExecutionEvaluator:
        return cls(runner=ReadOnlyRunner())

    def evaluate(self, item: BenchmarkItem, answer: AnswerEnvelope) -> ItemResult:
        if item.expected_status is AnswerStatus.NEEDS_CLARIFICATION:
            passed = answer.status is AnswerStatus.NEEDS_CLARIFICATION
            reason = "asked for clarification" if passed else f"status {answer.status.value}"
            return ItemResult(item_id=item.id, passed=passed, reason=reason)
        if answer.status is not AnswerStatus.ANSWERED or not answer.final_sql:
            reason = f"status {answer.status.value}, no SQL to execute"
            return ItemResult(item_id=item.id, passed=False, reason=reason)
        labels = labels_for(answer.final_sql, item.traps)
        if not item.gold_sql:
            raise ValueError(f"{item.id}: an answered item needs gold_sql")
        if planted("BUG_SQL_TEXT_EVAL"):
            # planted: compares SQL text, so a correct query written differently fails
            same = _sql_text(answer.final_sql) == _sql_text(item.gold_sql)
            reason = "SQL text matches gold" if same else "SQL text differs from gold"
            return ItemResult(
                item_id=item.id, passed=same, reason=reason, trap_labels=[] if same else labels
            )
        for warehouse in WAREHOUSES:
            passed, reason = self._match_on(item, answer.final_sql, warehouse)
            if not passed:
                return ItemResult(
                    item_id=item.id,
                    passed=False,
                    reason=f"{warehouse}: {reason}",
                    trap_labels=labels,
                )
        return ItemResult(
            item_id=item.id,
            passed=True,
            reason="matches gold on both warehouses",
        )

    def match_each(self, item: BenchmarkItem, sql: str) -> dict[str, tuple[bool, str]]:
        """(match, reason) on every warehouse, for the gold check shown in class."""
        return {warehouse: self._match_on(item, sql, warehouse) for warehouse in WAREHOUSES}

    def _match_on(self, item: BenchmarkItem, sql: str, warehouse: str) -> tuple[bool, str]:
        assert item.gold_sql is not None
        gold = self.runner.run(item.gold_sql, warehouse, max_rows=self.max_rows)
        try:
            predicted = self.runner.run(sql, warehouse, max_rows=self.max_rows)
        except Exception as error:  # the agent's SQL failed to run: a failed item, not a crash
            return False, f"query failed: {type(error).__name__}: {str(error).strip()[:200]}"
        if predicted.truncated:
            return False, f"more than {self.max_rows} rows"
        return compare(
            predicted.rows,
            gold.rows,
            tolerance=item.numeric_tolerance,
            order_matters=item.order_matters,
        )
