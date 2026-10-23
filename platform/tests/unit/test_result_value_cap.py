"""The size cap on each value of a result sent to the model. Found live in the verification of
Assignment 2: Verification loop, where one `array_agg` row of every California address reached the
analyst whole, because the row cap counts rows, and the run reached its token budget. The notice
that rows were cut must not invite gathering every row into one value either."""

from __future__ import annotations

import json

from datapilot.contracts import KnowledgeVersion, QueryResult
from datapilot.loop1_agent.tools import VALUE_CHARACTER_CAP, cap_values, format_result
from datapilot.loop2_verification.reviewer import review_request

HUGE = ["someone@example.com"] * 10_000  # an array_agg of every address, as one value


def _result(rows: list[tuple], total: int | None = None) -> QueryResult:
    return QueryResult(
        columns=["state", "emails"],
        rows=rows,
        total_row_count=len(rows) if total is None else total,
        truncated=False,
    )


def test_a_value_longer_than_the_cap_is_cut_to_the_cap() -> None:
    payload = json.loads(format_result(_result([("CA", HUGE)]), row_cap=50))
    value = payload["rows"][0][1]
    assert isinstance(value, str)
    assert len(value) <= VALUE_CHARACTER_CAP
    assert payload["values_cut"] == 1
    assert str(VALUE_CHARACTER_CAP) in payload["notice"]


def test_short_values_go_back_unchanged_and_without_a_notice() -> None:
    payload = json.loads(format_result(_result([("CA", 12), ("OR", "Portland")]), row_cap=50))
    assert payload["rows"] == [["CA", 12], ["OR", "Portland"]]
    assert "values_cut" not in payload
    assert "notice" not in payload


def test_the_whole_payload_stays_near_the_row_cap_times_the_value_cap() -> None:
    rows = [("CA", HUGE)] * 80
    text = format_result(_result(rows), row_cap=50)
    # JSON escaping can at most double a cut value's characters
    assert len(text) < 50 * (2 * VALUE_CHARACTER_CAP + 100) + 2_000
    assert len(text) < len(str(HUGE))


def test_no_notice_invites_gathering_every_row() -> None:
    rows_cut = json.loads(format_result(_result([("CA", 1)] * 60), row_cap=50))
    values_cut = json.loads(format_result(_result([("CA", HUGE)]), row_cap=50))
    for payload in (rows_cut, values_cut):
        notice = payload["notice"].lower()
        assert "every row" not in notice
        assert "aggregate" not in notice
        assert "one row per" in notice
    assert "Showing 50 of 60 rows" in rows_cut["notice"]


def test_cap_values_counts_each_cut_value() -> None:
    rows, cut = cap_values([("CA", HUGE, "x" * (VALUE_CHARACTER_CAP + 1)), ("OR", 3, "y")])
    assert cut == 2
    assert rows[1] == ("OR", 3, "y")


def test_the_reviewer_preview_caps_values_too() -> None:
    knowledge = KnowledgeVersion(version="v1", rules=[], notes="")
    result = _result([("CA", HUGE)])
    text = review_request("Export them", "SELECT 1", result, knowledge, preview_rows=50)
    assert len(text) < 2 * VALUE_CHARACTER_CAP + 5_000
