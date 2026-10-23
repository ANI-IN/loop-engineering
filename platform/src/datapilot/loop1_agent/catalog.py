"""The warehouse catalog as the agent role sees it: tables, columns, comments, samples.

Every query here is system SQL with identifiers from the catalog itself, run as the agent role in a
read-only transaction. The agent's own SQL never comes here; it goes through the verification
executor.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

_SNAPSHOT_SQL = """
SELECT c.relname AS table_name,
       CASE c.relkind WHEN 'v' THEN 'view' WHEN 'm' THEN 'view' ELSE 'table' END AS kind,
       obj_description(c.oid, 'pg_class') AS table_comment,
       a.attname AS column_name,
       format_type(a.atttypid, a.atttypmod) AS data_type,
       NOT a.attnotnull AS nullable,
       col_description(c.oid, a.attnum) AS column_comment
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
WHERE n.nspname = %s AND c.relkind IN ('r', 'p', 'v', 'm')
  AND has_table_privilege(c.oid, 'SELECT')
ORDER BY c.relname, a.attnum
"""
# Types whose distinct values are worth showing when there are only a few of them.
_DISCRETE_TYPES = ("smallint", "integer", "boolean", "text", "character varying", "character")


@dataclass(frozen=True)
class Column:
    name: str
    data_type: str
    nullable: bool
    comment: str = ""


@dataclass(frozen=True)
class Table:
    name: str
    kind: str
    comment: str
    columns: tuple[Column, ...]

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]


@dataclass(frozen=True)
class CatalogSnapshot:
    """What exists in the allowed schema, taken once per process (the schema grader's truth)."""

    schema: str
    tables: dict[str, Table] = field(default_factory=dict)

    def table(self, name: str) -> Table | None:
        return self.tables.get(name.lower())

    def sqlglot_schema(self) -> dict[str, dict[str, dict[str, str]]]:
        return {
            self.schema: {
                t.name: {c.name: c.data_type for c in t.columns} for t in self.tables.values()
            }
        }


@contextmanager
def read_only(url: str, *, timeout_ms: int = 5000) -> Iterator[psycopg.Connection[Any]]:
    with psycopg.connect(url, row_factory=dict_row) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        conn.execute("SELECT set_config('statement_timeout', %s, true)", (f"{timeout_ms}ms",))
        try:
            yield conn
        finally:
            conn.rollback()


def load_snapshot(url: str, schema: str) -> CatalogSnapshot:
    with read_only(url) as conn:
        rows = conn.execute(_SNAPSHOT_SQL, (schema,)).fetchall()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["table_name"], []).append(row)
    tables = {
        name: Table(
            name=name,
            kind=cols[0]["kind"],
            comment=cols[0]["table_comment"] or "",
            columns=tuple(
                Column(c["column_name"], c["data_type"], c["nullable"], c["column_comment"] or "")
                for c in cols
            ),
        )
        for name, cols in grouped.items()
    }
    return CatalogSnapshot(schema=schema, tables=tables)


def sample_rows(url: str, table: Table, schema: str, *, limit: int = 3) -> list[dict[str, Any]]:
    query = sql.SQL("SELECT * FROM {}.{} ORDER BY 1 LIMIT {}").format(
        sql.Identifier(schema), sql.Identifier(table.name), sql.Literal(limit)
    )
    with read_only(url) as conn:
        return conn.execute(query).fetchall()


def few_distinct_values(
    url: str, table: Table, schema: str, *, max_distinct: int = 10
) -> dict[str, list[Any]]:
    """Distinct values of each discrete column that has at most `max_distinct` of them."""
    found: dict[str, list[Any]] = {}
    with read_only(url) as conn:
        for column in table.columns:
            if not column.data_type.startswith(_DISCRETE_TYPES):
                continue
            query = sql.SQL("SELECT {c} AS v FROM {s}.{t} GROUP BY 1 ORDER BY 1 LIMIT {n}").format(
                c=sql.Identifier(column.name),
                s=sql.Identifier(schema),
                t=sql.Identifier(table.name),
                n=sql.Literal(max_distinct + 1),
            )
            values = [r["v"] for r in conn.execute(query).fetchall()]
            if len(values) <= max_distinct:
                found[column.name] = values
    return found
