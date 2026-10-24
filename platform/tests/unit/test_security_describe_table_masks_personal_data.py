"""describe_table never hands personal data to the model (zero tokens, no database): the sample
rows mask the pack's personal-data columns, in the base table and the marketing view, and the
distinct values leave them out. Before, three real customers' names, emails, and phones went to
the model and the trace with no grader and no approval (review round 1, F002)."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import pytest

from datapilot.loop1_agent import catalog
from datapilot.loop1_agent.catalog import PERSONAL_SAMPLE, Column, Table, personal_columns

PERSONAL = {"email", "phone", "first_name", "last_name"}


def test_the_pack_tags_the_same_columns_in_the_table_and_the_view() -> None:
    assert personal_columns("customers") == PERSONAL
    assert personal_columns("customers_marketable") == PERSONAL
    assert personal_columns("products") == frozenset()


class _Connection:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.queries: list[str] = []

    def execute(self, query: Any) -> _Connection:
        self.queries.append(str(query))
        return self

    def fetchall(self) -> list[dict[str, Any]]:
        return self.rows


ROWS = [
    {"customer_id": 1, "first_name": "Ada", "last_name": "Lane", "email": "ada@example.com",
     "phone": "555-0101", "state": "CA"},
]  # fmt: skip


@pytest.fixture
def connection(monkeypatch: pytest.MonkeyPatch) -> _Connection:
    conn = _Connection(ROWS)

    @contextmanager
    def read_only(_url: str, **_: Any):
        yield conn

    monkeypatch.setattr(catalog, "read_only", read_only)
    return conn


def _table(name: str) -> Table:
    names = ("customer_id", "first_name", "last_name", "email", "phone", "state")
    return Table(name, "table", "", tuple(Column(n, "text", True) for n in names))


@pytest.mark.parametrize("name", ["customers", "customers_marketable"])
def test_sample_rows_mask_every_personal_value(connection, name: str) -> None:
    [row] = catalog.sample_rows("postgresql://never-opened", _table(name), "warehouse")
    assert {k for k, v in row.items() if v == PERSONAL_SAMPLE} == PERSONAL
    assert row["customer_id"] == 1 and row["state"] == "CA"


def test_distinct_values_are_never_read_for_a_personal_column(connection) -> None:
    connection.rows = [{"v": "CA"}]
    found = catalog.few_distinct_values("postgresql://never-opened", _table("customers"), "w")
    assert set(found) == {"customer_id", "state"}
    assert not any(column in q for q in connection.queries for column in PERSONAL)


def test_a_table_with_no_personal_column_is_sampled_as_it_is(connection) -> None:
    rows = catalog.sample_rows("postgresql://never-opened", _table("products"), "warehouse")
    assert rows == ROWS
