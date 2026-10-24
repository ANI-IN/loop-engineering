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
    """Review round 3 changed what stays: a data exception keeps a fixed kind of error keyed by
    its SQLSTATE, never the database's message (before, its redacted message stayed)."""
    error = ExecutionError("22P02", 'invalid input syntax for type integer: "a@b.com"')
    assert error.sqlstate == "22P02"
    assert error.message == "a text value is not valid input for its type"
    assert "a text value is not valid input for its type" in error.feedback
    assert "SQLSTATE 22P02" in error.feedback
    assert "cast" in error.feedback.lower()


# Review round 3, reviewer A: PostgreSQL 18's messages for a value it shows outside any quote, as
# bytes ("bar" is 0x62 0x61 0x72) or as character codes (98 is "b", 66 is "B", 50 is "2").
UNQUOTED = [
    ("22021", 'invalid byte sequence for encoding "UTF8": 0xf0 0x62 0x61 0x72'),
    ("22021", 'invalid byte sequence for encoding "UTF8": 0xf0 0x42 0x61 0x72'),
    ("22008", "date field value out of range: 2024-01-98"),
    ("22008", "time field value out of range: 66:00:00"),
    ("22008", "date field value out of range: 2024-01-50"),
    ("22P05", 'character with byte sequence 0x62 0x61 in encoding "UTF8" has no equivalent'),
    ("2200X", "a data exception with no kind of its own: 0x62 98"),
    ("XX000", "invalid memory alloc request size 98"),
    ("54000", "requested length too large: 98"),
]


@pytest.mark.parametrize(("sqlstate", "message"), UNQUOTED)
def test_a_value_outside_any_quote_never_reaches_the_agent_or_the_reason(
    sqlstate: str, message: str
) -> None:
    error = ExecutionError(sqlstate, message)
    result = ExecutionGrader().check(GraderContext(question="", extra={"execution_error": error}))
    for text in (error.message, str(error), error.feedback, result.reason):
        assert "0x" not in text, text
        assert not any(code in text for code in ("98", "66", "50", "2024")), text
    assert result.reason.startswith(f"SQLSTATE {sqlstate}: ")
    assert f"SQLSTATE {sqlstate}" in error.feedback


def test_a_data_exception_names_its_kind() -> None:
    assert ExecutionError("22021", "x").message == "a byte sequence is not valid in the encoding"
    assert ExecutionError("22008", "x").message == "a date or time field is out of range"
    assert ExecutionError("2200X", "x").message == (
        "a value could not be converted, or is out of range"
    )


def test_an_error_about_a_name_keeps_its_redacted_message() -> None:
    error = ExecutionError("42703", 'column "emial" does not exist')
    assert error.message == 'column "<redacted>" does not exist'


def test_a_message_with_no_quoted_part_is_unchanged() -> None:
    assert redact("division by zero") == "division by zero"
    assert redact("canceling statement due to statement timeout") == (
        "canceling statement due to statement timeout"
    )
