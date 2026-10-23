"""The cost grader is not a security layer: it estimates only what the syntax-tree classifier calls
one read-only SELECT, never runs EXPLAIN on anything else (even with the naive guard planted), and
never runs EXPLAIN ANALYZE (zero tokens, no database)."""

from __future__ import annotations

import pytest
from loops_support import fixture_config

from datapilot.contracts import GraderContext
from datapilot.loop2_verification.graders import CostGrader

NOT_SELECTS = [
    "SELECT 1; DELETE FROM orders",
    "WITH d AS (DELETE FROM orders RETURNING *) SELECT count(*) FROM d",
    "INSERT INTO orders (order_id) VALUES (1)",
    "SELECT * INTO copied FROM orders",
    "VACUUM orders",
    "DO $$ BEGIN DELETE FROM orders; END $$",
]


class _Explain:
    def __init__(self) -> None:
        self.seen: list[str] = []

    def __call__(self, sql: str) -> dict:
        self.seen.append(sql)
        return {"Total Cost": 1.0, "Plan Rows": 1.0}


@pytest.mark.parametrize("naive", ["0", "1"])
@pytest.mark.parametrize("sql", NOT_SELECTS)
def test_a_statement_that_is_not_a_read_only_select_is_never_explained(
    monkeypatch, sql: str, naive: str
) -> None:
    monkeypatch.setenv("BUG_NAIVE_GUARD", naive)
    explain = _Explain()
    result = CostGrader(fixture_config(), explain).check(GraderContext(question="", sql=sql))
    assert explain.seen == []
    assert result.passed and result.reason.startswith("not applicable")


def test_a_read_only_select_is_estimated_once_without_analyze() -> None:
    explain = _Explain()
    sql = "SELECT count(*) FROM orders"
    result = CostGrader(fixture_config(), explain).check(GraderContext(question="", sql=sql))
    assert explain.seen == [sql] and result.passed


def test_the_executor_explains_without_analyze() -> None:
    import inspect

    from datapilot.loop2_verification.executor import Executor

    source = inspect.getsource(Executor.explain)
    assert '"EXPLAIN (FORMAT JSON) "' in source and "ANALYZE" not in source.upper().replace(
        "EXPLAIN (FORMAT JSON)", ""
    )
