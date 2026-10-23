"""The build-wide spend ledger: costs from the pack prices, totals by activity, the stop line."""

from __future__ import annotations

from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from datapilot.config import pack_config
from datapilot.observability import spend


def test_cost_uses_the_pack_price_table() -> None:
    price = pack_config()["prices"]["gpt-6-luna"]
    usage = spend.Usage(input_tokens=1_000_000, cached_input_tokens=0, output_tokens=1_000_000)
    assert spend.cost_usd("gpt-6-luna", usage) == pytest.approx(price["input"] + price["output"])


def test_cached_input_is_priced_separately() -> None:
    price = pack_config()["prices"]["gpt-6-luna"]
    usage = spend.Usage(input_tokens=1_000_000, cached_input_tokens=1_000_000, output_tokens=0)
    assert spend.cost_usd("gpt-6-luna", usage) == pytest.approx(price["cached_input"])


def test_an_unpriced_model_is_refused() -> None:
    with pytest.raises(KeyError):
        spend.cost_usd("unknown-model", spend.Usage(1, 0, 1))


def test_totals_by_activity(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.sqlite"
    usage = spend.Usage(input_tokens=10_000, cached_input_tokens=0, output_tokens=2_000)
    one = spend.record(
        component="analyst", model="gpt-6-luna", usage=usage, activity="a", path=ledger
    )
    spend.record(component="reviewer", model="gpt-6-luna", usage=usage, activity="b", path=ledger)
    spend.record(component="analyst", model="gpt-6-luna", usage=usage, activity="a", path=ledger)
    assert spend.total_usd(ledger) == pytest.approx(3 * one)
    assert [(a, n) for a, n, _ in spend.by_activity(ledger)] == [("a", 2), ("b", 1)]


def test_live_work_stops_at_the_stop_line(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DATAPILOT_BUILD_BUDGET", "1")
    ledger = tmp_path / "ledger.sqlite"
    stop = pack_config()["build_budget"]["stop_usd"]
    price = pack_config()["prices"]["gpt-6-luna"]["output"]
    tokens = int(stop / price * 1_000_000) + 1
    spend.record(
        component="analyst",
        model="gpt-6-luna",
        usage=spend.Usage(0, 0, tokens),
        activity="calibration",
        path=ledger,
    )
    with pytest.raises(spend.BudgetStop, match="stop line"):
        spend.check_budget(ledger, activity="calibration")


def test_usage_is_read_from_the_message_metadata() -> None:
    message = AIMessage(
        content="",
        usage_metadata={
            "input_tokens": 1200,
            "output_tokens": 300,
            "total_tokens": 1500,
            "input_token_details": {"cache_read": 200},
        },
    )
    assert spend.usage_from_message(message) == spend.Usage(1200, 200, 300)


def test_the_budget_lines_are_ordered() -> None:
    budget = pack_config()["build_budget"]
    assert budget["warn_usd"] < budget["stop_usd"] <= budget["total_usd"]


# Cache writes, priced as OpenAI bills them (the model page and the prompt caching guide).
def test_cache_writes_are_priced_at_their_own_rates() -> None:
    """OpenAI's own worked example: 12,000 input tokens, 4,000 read from the cache, 3,000 written
    for 30 minutes and 4,000 for 12 hours, so 1,000 plain input tokens."""
    price = pack_config()["prices"]["gpt-6-luna"]
    usage = spend.Usage(12_000, 4_000, 0, cache_write_tokens=3_000, cache_write_12h_tokens=4_000)
    expected = (
        1_000 * price["input"]
        + 4_000 * price["cached_input"]
        + 3_000 * price["cache_write_30m"]
        + 4_000 * price["cache_write_12h"]
    ) / 1_000_000
    assert spend.cost_usd("gpt-6-luna", usage) == pytest.approx(expected)


def test_the_price_table_has_the_published_cache_write_rates() -> None:
    price = pack_config()["prices"]["gpt-6-luna"]
    assert price["cache_write_30m"] == pytest.approx(1.25 * price["input"])
    assert price["cache_write_12h"] == pytest.approx(2.5 * price["input"])


def test_a_cache_write_costs_a_quarter_more_than_plain_input() -> None:
    plain = spend.cost_usd("gpt-6-luna", spend.Usage(1_000_000, 0, 0))
    written = spend.Usage(1_000_000, 0, 0, cache_write_tokens=1_000_000)
    assert spend.cost_usd("gpt-6-luna", written) == pytest.approx(plain * 1.25)


def test_cache_writes_are_read_from_the_message_metadata() -> None:
    message = AIMessage(
        content="",
        usage_metadata={
            "input_tokens": 1200,
            "output_tokens": 300,
            "total_tokens": 1500,
            "input_token_details": {"cache_read": 200, "cache_creation": 700},
        },
    )
    assert spend.usage_from_message(message) == spend.Usage(1200, 200, 300, cache_write_tokens=700)


def test_the_api_usage_object_is_split_by_lifetime() -> None:
    usage = {
        "input_tokens": 12_000,
        "output_tokens": 50,
        "input_tokens_details": {
            "cached_tokens": 4_000,
            "cache_write_tokens": 7_000,
            "cache_write_tokens_details": {"ttl_30m_tokens": 3_000, "ttl_12h_tokens": 4_000},
        },
    }
    assert spend.usage_from_api(usage) == spend.Usage(12_000, 4_000, 50, 3_000, 4_000)


def test_last_nights_usage_prices_to_the_usage_page() -> None:
    """The night of 2026-10-22: the ledger's and the traces' token totals, priced with cache
    writes, come to 1.78 dollars, the figure OpenAI's usage page shows (docs/costs.md)."""
    night = spend.Usage(20_904_864, 12_809_184, 1_491_337, cache_write_tokens=3_981_990)
    assert round(spend.cost_usd("gpt-6-luna", night), 2) == 1.78
    without_writes = spend.Usage(20_904_864, 12_809_184, 1_491_337)
    assert round(spend.cost_usd("gpt-6-luna", without_writes), 4) == 1.6833  # what was recorded


def test_older_ledgers_gain_the_new_columns_and_keep_their_rows(tmp_path: Path) -> None:
    import sqlite3

    path = tmp_path / "ledger.sqlite"
    with sqlite3.connect(path) as conn:  # a ledger written before the new columns
        conn.execute(spend._SCHEMA)
        conn.execute(
            "INSERT INTO spend_ledger (ts, activity, component, model, input_tokens, "
            "cached_input_tokens, output_tokens, cost_usd, run_id) "
            "VALUES ('2026-10-22T21:00:00+00:00', 'calibration', 'analyst', 'gpt-6-luna', "
            "100, 0, 10, 0.5, NULL)"
        )
    assert spend.total_usd(path) == pytest.approx(0.5)
    spend.total_usd(path)  # a second connection finds the columns already there
    with sqlite3.connect(path) as conn:
        row = conn.execute(
            "SELECT input_tokens, cache_write_tokens, cache_write_12h_tokens, estimated, error "
            "FROM spend_ledger"
        ).fetchone()
    assert row == (100, 0, 0, 0, None)
