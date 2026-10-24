"""A database error never carries a data value to the agent, a grader's reason, a run event, or a
trace (zero tokens, no database). Review round 2: `WHERE email::int = 1` passes the personal-data
grader by design (the column only filters), and PostgreSQL's error quoted the email it could not
convert; the executor sent that line back to the model as feedback and into the grader's reason."""

from __future__ import annotations

import pytest

from datapilot.contracts import GraderContext
from datapilot.loop2_verification.executor import ExecutionError, redact
from datapilot.loop2_verification.graders import ExecutionGrader

# What PostgreSQL 18 says for each, with the value it quotes.
MESSAGES = [
    ("22P02", 'invalid input syntax for type integer: "barbararobinson57@proton.me"'),
    ("22007", 'invalid input syntax for type date: "Barbara"'),
    ("22P02", 'invalid input syntax for type integer: "(275) 555-0100"'),
    ("22003", 'value "5550100275" is out of range for type integer'),
    ("22007", 'invalid value "Barb" for "YYYY"'),
    ("22P02", 'malformed array literal: "barbararobinson57@proton.me"'),
    ("42P01", 'relation "barbararobinson57@proton.me" does not exist'),
    ("22023", 'time zone "Robinson" not recognized'),
    ("22P02", 'invalid input syntax for type integer: "a "quoted" Robinson"'),
    ("22P02", 'invalid input syntax for type integer: "Robinson'),
]
VALUES = ("barbararobinson57", "proton.me", "Barbara", "Barb", "555", "Robinson", "@")


@pytest.mark.parametrize(("sqlstate", "message"), MESSAGES)
def test_no_quoted_value_reaches_the_agent_or_the_reason(sqlstate: str, message: str) -> None:
    error = ExecutionError(sqlstate, message)
    result = ExecutionGrader().check(GraderContext(question="", extra={"execution_error": error}))
    for text in (error.message, str(error), error.feedback, result.reason):
        assert not any(value in text for value in VALUES), text
    assert result.reason.startswith(f"SQLSTATE {sqlstate}: ")


def test_the_kind_of_error_and_its_sqlstate_stay() -> None:
    error = ExecutionError("22P02", 'invalid input syntax for type integer: "a@b.com"')
    assert error.sqlstate == "22P02"
    assert error.message == 'invalid input syntax for type integer: "<redacted>"'
    assert "invalid input syntax for type integer" in error.feedback
    assert "cast" in error.feedback.lower()


def test_a_message_with_no_quoted_part_is_unchanged() -> None:
    assert redact("division by zero") == "division by zero"
    assert redact("canceling statement due to statement timeout") == (
        "canceling statement due to statement timeout"
    )
