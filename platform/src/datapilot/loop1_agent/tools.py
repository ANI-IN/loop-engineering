"""The analyst's tools: list_tables, describe_table, run_query.

run_query never touches the database itself: it hands the SQL to the verification loop's checker
(graders, then the read-only executor) and caps what goes back to the model.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool

from datapilot.contracts import QueryResult
from datapilot.loop1_agent.catalog import CatalogSnapshot, few_distinct_values, sample_rows
from datapilot.planted import planted


@dataclass(frozen=True)
class QueryOutcome:
    """What the checker reports for one query: a result, or the grader that blocked it."""

    result: QueryResult | None
    blocked_by: str | None = None
    feedback: str | None = None


QueryRunner = Callable[[str], QueryOutcome]


def cap_rows(rows: list[tuple[Any, ...]], limit: int) -> tuple[list[tuple[Any, ...]], bool]:
    if planted("BUG_UNBOUNDED_ROWS"):
        return rows, False  # planted: every row goes back to the model
    return rows[:limit], len(rows) > limit


def format_result(result: QueryResult, row_cap: int) -> str:
    rows, truncated = cap_rows(list(result.rows), row_cap)
    rows, values_cut = cap_values(rows)
    payload: dict[str, Any] = {
        "columns": result.columns,
        "rows": [list(r) for r in rows],
        "total_row_count": result.total_row_count,
        "truncated": truncated,
    }
    notices = [f"Showing {len(rows)} of {result.total_row_count} rows."] if truncated else []
    if values_cut:
        payload["values_cut"] = values_cut
        notices.append(f"{values_cut} value(s) were cut to {VALUE_CHARACTER_CAP} characters.")
    if notices:
        payload["notice"] = " ".join([*notices, ONE_ROW_PER_ROW])
    return json.dumps(payload, default=str)


# The most characters of one value that go back to the model. The row cap counts rows, so without
# this one row holding an array of every address reached the model whole.
VALUE_CHARACTER_CAP = 2_000
ONE_ROW_PER_ROW = "Keep one row per result row: do not combine rows into one value to see more."


def cap_values(rows: list[tuple[Any, ...]]) -> tuple[list[tuple[Any, ...]], int]:
    """Cut each value longer than VALUE_CHARACTER_CAP, as text; return the rows and how many."""
    capped: list[tuple[Any, ...]] = []
    cut = 0
    for row in rows:
        values: list[Any] = []
        for value in row:
            text = value if isinstance(value, str) else None
            if text is None and isinstance(value, (list, tuple, dict)):
                text = json.dumps(value, default=str)
            if text is not None and len(text) > VALUE_CHARACTER_CAP:
                values.append(text[:VALUE_CHARACTER_CAP])
                cut += 1
            else:
                values.append(value)
        capped.append(tuple(values))
    return capped, cut


@dataclass(frozen=True)
class Warehouse:
    """The agent role's view of the allowed schema."""

    snapshot: CatalogSnapshot
    url: str

    def list_tables(self) -> str:
        lines = [
            f"{t.name} ({t.kind}): {t.comment}".rstrip(": ")
            for t in sorted(self.snapshot.tables.values(), key=lambda t: t.name)
        ]
        return "\n".join(lines) or "No tables."

    def describe_table(self, name: str) -> str:
        table = self.snapshot.table(name.split(".")[-1])
        if table is None:
            return f"No table {name}. Tables: {', '.join(sorted(self.snapshot.tables))}."
        if planted("BUG_NAMES_ONLY_SCHEMA"):
            return f"{table.name}: {', '.join(table.column_names)}"  # planted: names only
        schema = self.snapshot.schema
        columns = [
            {
                "name": c.name,
                "type": c.data_type,
                "nullable": c.nullable,
                **({"comment": c.comment} if c.comment else {}),
            }
            for c in table.columns
        ]
        payload = {
            "table": table.name,
            "kind": table.kind,
            "comment": table.comment,
            "columns": columns,
            "sample_rows": sample_rows(self.url, table, schema),
            "distinct_values": few_distinct_values(self.url, table, schema),
        }
        return json.dumps(payload, default=str)


def analyst_tools(warehouse: Warehouse, run_query: QueryRunner, *, row_cap: int) -> list[BaseTool]:
    def list_tables() -> str:
        """List the warehouse tables and views, each with a one-line description."""
        return warehouse.list_tables()

    def describe_table(name: str) -> str:
        """Describe one table: column types, nullability, comments, 3 sample rows, and the
        distinct values of columns that have only a few."""
        return warehouse.describe_table(name)

    def run_query_tool(sql: str) -> str:
        """Run one read-only SELECT. Returns columns, at most the row cap of rows, the total row
        count, and a notice when rows were cut; or the reason the query was blocked."""
        outcome = run_query(sql)
        if outcome.result is None:
            return f"Query blocked by the {outcome.blocked_by} check: {outcome.feedback}"
        return format_result(outcome.result, row_cap)

    return [
        StructuredTool.from_function(list_tables),
        StructuredTool.from_function(describe_table),
        StructuredTool.from_function(run_query_tool, name="run_query"),
    ]
