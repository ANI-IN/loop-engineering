"""The console's run summary shows the cost of a cheap run instead of rounding it to zero."""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta

from datapilot.settings import PLATFORM

sys.path.insert(0, str(PLATFORM / "console"))

from datapilot_console.views import run_summary  # noqa: E402


def test_a_run_costing_hundredths_of_a_cent_is_not_shown_as_zero() -> None:
    started = datetime(2026, 1, 31, 12, 0, tzinfo=UTC)
    run = {
        "tokens_in": 2672,
        "tokens_out": 57,
        "cost_usd": 0.0003,
        "started_at": started,
        "finished_at": started + timedelta(seconds=15.6),
    }
    assert run_summary(run) == "2,729 tokens, $0.0003, 15.6 s"


def test_a_run_without_timings_still_shows_tokens_and_cost() -> None:
    assert run_summary({"tokens_in": 0, "tokens_out": 0, "cost_usd": None}) == "0 tokens, $0.0000"
