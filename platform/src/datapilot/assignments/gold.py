"""Gold answers for live checks: hand-written SQL, run live on the real warehouse every time, and
compared with the agent's SQL the way the class evaluator compares them."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from datapilot.loop4_hill_climbing.evaluator import compare, normalize_cell
from datapilot.loop4_hill_climbing.sql_runner import ReadOnlyRunner

RUNNER = ReadOnlyRunner()


def rows(sql: str, warehouse: str = "warehouse") -> list[tuple[Any, ...]]:
    return list(RUNNER.run(sql, warehouse, max_rows=10_000).rows)


def same_result(
    agent_sql: str | None,
    gold_sqls: Sequence[str],
    *,
    warehouse: str = "warehouse",
    tolerance: float = 0.01,
) -> tuple[bool, str]:
    """Whether the agent's SQL returns what any one of the gold queries returns (a question may
    accept dollars or cents, for example)."""
    if not agent_sql:
        return False, "no final SQL"
    try:
        predicted = rows(agent_sql, warehouse)
    except Exception as error:
        return False, f"the final SQL failed: {type(error).__name__}"
    reason = ""
    for gold in gold_sqls:
        expected = rows(gold, warehouse)
        same, reason = compare(predicted, expected, tolerance=tolerance, order_matters=False)
        if same or holds_gold(predicted, expected, tolerance=tolerance):
            return True, "matches gold"
    return False, reason


def holds_gold(
    predicted: Sequence[tuple[Any, ...]],
    gold: Sequence[tuple[Any, ...]],
    *,
    tolerance: float = 0.01,
) -> bool:
    """The same rows as gold, each holding gold's values, with more columns allowed: an answer
    may show the product name beside its price."""
    if len(predicted) != len(gold):
        return False
    left = sorted(
        (sorted(normalize_cell(v, tolerance) for v in row) for row in predicted), key=repr
    )
    right = sorted((sorted(normalize_cell(v, tolerance) for v in row) for row in gold), key=repr)
    for have, want in zip(left, right, strict=True):
        pool = list(have)
        for cell in want:
            if cell not in pool:
                return False
            pool.remove(cell)
    return True


WORKERS = 8  # live runs a check keeps under way at once; the spend cap's headroom counts them


def in_parallel[T](jobs: Sequence[Callable[[], T]], workers: int = WORKERS) -> list[T]:
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda job: job(), jobs))
