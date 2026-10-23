"""A write the database refuses (SQLSTATE 25006 or 42501) is a stop, not feedback (zero tokens)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from loops_support import FIXTURE_SCHEMA, fixture_config, fixture_snapshot

from datapilot.loop2_verification.checker import QueryChecker
from datapilot.loop2_verification.executor import REFUSED_WRITE_SQLSTATES, ExecutionError


@pytest.mark.parametrize(
    ("sqlstate", "refused"), [("25006", True), ("42501", True), ("57014", False)]
)
def test_only_read_only_and_permission_errors_are_refused_writes(sqlstate, refused) -> None:
    assert ExecutionError(sqlstate, "x").refused_write is refused
    assert frozenset({"25006", "42501"}) == REFUSED_WRITE_SQLSTATES


@dataclass
class _Database:
    """Stands in for the executor: the plan is cheap, and running raises the given error."""

    sqlstate: str
    url: str = "postgresql://unused"
    schema: str = FIXTURE_SCHEMA

    def explain(self, sql: str) -> dict:
        return {"Total Cost": 1.0, "Plan Rows": 1.0}

    def run(self, sql: str):
        raise ExecutionError(self.sqlstate, f"refused with {self.sqlstate}")


@pytest.mark.parametrize(
    ("sqlstate", "refused"), [("25006", True), ("42501", True), ("57014", False)]
)
def test_the_checker_marks_a_refused_write_for_the_loop(sqlstate, refused) -> None:
    database = _Database(sqlstate)
    checker = QueryChecker(fixture_config(), database, fixture_snapshot())  # type: ignore[arg-type]
    checked = checker.check("SELECT count(*) FROM orders")
    assert checked.failure is not None and checked.failure.grader == "execution"
    assert (checked.refused is not None) is refused
