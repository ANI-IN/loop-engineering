"""Benchmark dates: gold and naive SQL never ask the database for today, and every relative date in
a question resolves against the business date (31 January 2026) to the literal period in its gold
SQL, inside the seeded data."""

from __future__ import annotations

import re
from datetime import date, timedelta

import pytest

from datapilot import business_date
from datapilot.loop4_hill_climbing.pack_files import load_benchmark

ITEMS = load_benchmark()
FIRST_DAY, END = date(2023, 2, 1), date(2026, 2, 1)  # the seeded data, end exclusive
SQL_TODAY = re.compile(
    r"\b(current_date|current_timestamp|current_time|localtimestamp|localtime|clock_timestamp|"
    r"statement_timestamp|transaction_timestamp|timeofday)\b|\bnow\s*\(|'(today|now|yesterday)'",
    re.I,
)
RELATIVE = re.compile(
    r"\b(today|yesterday|tomorrow|(last|this|next|previous|past|current) (\w+ )?"
    r"(day|week|month|quarter|year)s?|year to date|so far|recent(ly)?)\b",
    re.I,
)


def _fiscal_year_start(day: date) -> date:
    return date(day.year if day.month >= 2 else day.year - 1, 2, 1)


def resolve(phrase: str, today: date) -> tuple[date, date]:
    """The period a relative phrase names, as [start, end), on the fiscal calendar."""
    this_year = _fiscal_year_start(today)
    periods = {
        "this fiscal year": (this_year, this_year.replace(year=this_year.year + 1)),
        "last fiscal year": (this_year.replace(year=this_year.year - 1), this_year),
        "yesterday": (today - timedelta(days=1), today),
    }
    return periods[phrase]


# Every benchmark item whose question holds a relative date: (phrase, start, end of its period).
RELATIVE_ITEMS = {
    "average-order-value-fiscal-2025": ("last fiscal year", date(2024, 2, 1), date(2025, 2, 1)),
    "app-average-order-value-fiscal-2026": ("this fiscal year", date(2025, 2, 1), date(2026, 2, 1)),
}


def test_the_business_date_is_the_last_day_of_the_data() -> None:
    assert business_date.today() == date(2026, 1, 31) == END - timedelta(days=1)


@pytest.mark.parametrize("item", ITEMS, ids=lambda i: i.id)
def test_no_query_asks_the_database_for_today(item) -> None:
    for sql in (item.gold_sql or "", item.naive_sql or ""):
        assert SQL_TODAY.search(sql) is None


def test_every_relative_date_item_is_listed() -> None:
    found = {i.id for i in ITEMS if RELATIVE.search(i.question)}
    assert found == set(RELATIVE_ITEMS)


@pytest.mark.parametrize("item_id", sorted(RELATIVE_ITEMS))
def test_relative_dates_resolve_to_the_literal_period_in_gold(item_id: str) -> None:
    phrase, start, end = RELATIVE_ITEMS[item_id]
    item = next(i for i in ITEMS if i.id == item_id)
    assert phrase in item.question
    assert resolve(phrase, business_date.today()) == (start, end)
    assert item.gold_sql is not None
    assert f"DATE '{start.isoformat()}'" in item.gold_sql
    assert f"DATE '{end.isoformat()}'" in item.gold_sql


@pytest.mark.parametrize("item", ITEMS, ids=lambda i: i.id)
def test_every_literal_date_in_gold_lies_in_the_data(item) -> None:
    for literal in re.findall(r"DATE '(\d{4}-\d{2}-\d{2})'", item.gold_sql or ""):
        assert date(2023, 1, 1) <= date.fromisoformat(literal) <= END, literal
