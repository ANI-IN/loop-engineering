"""The reviewer sees the business date (zero tokens). Live, it raised a concern that an answer for
"yesterday" hard-coded 30 January 2026, because nothing told it today is 31 January 2026."""

from __future__ import annotations

from datapilot.contracts import KnowledgeVersion, QueryResult
from datapilot.loop2_verification.reviewer import review_request


def test_the_review_request_states_the_business_date() -> None:
    result = QueryResult(columns=["n"], rows=[(291,)], total_row_count=1, truncated=False)
    text = review_request(
        "How many orders were placed on the previous day?",
        "SELECT 1",
        result,
        KnowledgeVersion(version="v1"),
        preview_rows=5,
    )
    assert "Saturday, 31 January 2026" in text
