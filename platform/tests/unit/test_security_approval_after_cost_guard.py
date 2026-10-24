"""A query is offered for human approval only after every pre-execution grader has passed it, the
cost grader included (zero tokens, no database). Before, a personal-data query skipped the cost
grader: the approval row count ran the agent's SQL directly and held a database backend until the
statement timeout, and the approver was asked to release rows the cost grader would then block."""

from __future__ import annotations

from typing import Any

from loops_support import fixture_config, fixture_snapshot

from datapilot.loop2_verification.checker import QueryChecker


class _Executor:
    """Plans every query at a fixed cost; never runs one."""

    url = "postgresql://never-opened"

    def __init__(self, cost: float) -> None:
        self.cost = cost
        self.explained: list[str] = []
        self.ran: list[str] = []

    def explain(self, sql: str) -> dict[str, Any]:
        self.explained.append(sql)
        return {"Total Cost": self.cost, "Plan Rows": 1.0}

    def run(self, sql: str) -> Any:
        self.ran.append(sql)
        raise AssertionError("needs_approval must not execute the query")


def _checker(cost: float) -> tuple[QueryChecker, _Executor]:
    executor = _Executor(cost)
    return QueryChecker(fixture_config(), executor, fixture_snapshot()), executor  # type: ignore[arg-type]


def test_a_cheap_personal_data_query_needs_approval() -> None:
    checker, executor = _checker(cost=1.0)
    assert checker.needs_approval("SELECT email FROM customers WHERE state = 'CA'")
    assert executor.ran == []


def test_a_cartesian_personal_data_query_is_blocked_not_offered_for_approval() -> None:
    checker, executor = _checker(cost=1.0)
    assert not checker.needs_approval("SELECT a.email FROM customers a CROSS JOIN customers b")
    assert executor.ran == []


def test_a_personal_data_query_over_the_plan_limits_is_blocked_not_offered() -> None:
    checker, executor = _checker(cost=fixture_config().max_plan_cost + 1)
    assert not checker.needs_approval("SELECT email FROM customers")
    assert executor.explained == ["SELECT email FROM customers"] and executor.ran == []


def test_a_query_with_no_personal_data_is_never_planned_for_the_approval_question() -> None:
    checker, executor = _checker(cost=1.0)
    assert not checker.needs_approval("SELECT count(*) FROM orders")
    assert executor.explained == []
