"""The unbounded rows demo asks for the 10,000-row SELECT its guaranteed moment names. Unlimited,
the whole order_items table (about a million rows) went back to the model with the planted bug on,
and the request was refused as too long, so the token spike never showed (live, 23 October)."""

from __future__ import annotations

from datapilot.contracts import registries
from datapilot.loop3_events.api.demo import LARGE_QUERY_QUESTION


def test_the_large_query_is_the_10000_row_select_the_moment_names() -> None:
    assert "SELECT * FROM order_items LIMIT 10000" in LARGE_QUERY_QUESTION
    moment = registries.demos().by_id("agent-unbounded-rows").guaranteed_moment
    assert "10,000-row SELECT" in moment
