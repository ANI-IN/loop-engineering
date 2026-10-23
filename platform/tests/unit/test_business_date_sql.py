"""Agent SQL is business logic: it never reads the database clock, and the analyst answers with its
assumptions instead of asking (zero tokens)."""

from __future__ import annotations

import pytest
from loops_support import FIXTURE_SCHEMA

from datapilot.contracts import GraderContext
from datapilot.loop1_agent import prompts
from datapilot.loop2_verification.graders import StatementPolicyGrader

CLOCK = [
    "SELECT count(*) FROM orders WHERE order_ts >= now() - interval '1 day'",
    "SELECT count(*) FROM orders WHERE order_ts::date = CURRENT_DATE - 1",
    "SELECT date_trunc('day', CURRENT_TIMESTAMP)",
    "SELECT LOCALTIMESTAMP",
    "SELECT CURRENT_TIME",
    "SELECT LOCALTIME",
    "SELECT clock_timestamp()",
    "SELECT statement_timestamp()",
    "SELECT transaction_timestamp()",
    "SELECT timeofday()",
    "SELECT count(*) FROM orders WHERE order_ts::date = 'yesterday'::date",
    "SELECT 'today'::timestamp",
    "SELECT CAST('now' AS timestamptz)",
]


@pytest.mark.parametrize("sql", CLOCK)
def test_sql_that_reads_the_clock_is_stopped_with_the_business_date(sql: str) -> None:
    result = StatementPolicyGrader(FIXTURE_SCHEMA).check(GraderContext(question="", sql=sql))
    assert not result.passed and "clock" in result.reason
    assert result.feedback_for_agent and "31 January 2026" in result.feedback_for_agent


def test_dates_written_as_literals_are_fine() -> None:
    sql = (
        "SELECT count(*) FROM orders WHERE (order_ts AT TIME ZONE 'America/New_York') "
        ">= DATE '2026-01-30' AND (order_ts AT TIME ZONE 'America/New_York') < DATE '2026-01-31'"
    )
    assert StatementPolicyGrader(FIXTURE_SCHEMA).check(GraderContext(question="", sql=sql)).passed


def test_the_analyst_answers_with_its_assumptions_instead_of_asking() -> None:
    text = prompts.ANALYST
    assert "assumptions" in text and "Do not ask" in text
    assert "needs_clarification" in text and "nothing in the schema" in text
    assert "database clock" in text and "literal" in text


def test_the_prompt_states_no_business_rule() -> None:
    lowered = prompts.ANALYST.lower()
    for rule in ("fiscal", "cancel", "status = 5", "harborpine", "subtotal", "new_york", "eastern"):
        assert rule not in lowered, rule
