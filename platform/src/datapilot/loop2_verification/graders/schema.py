"""Grader 3, schema existence: every table and column exists in the catalog snapshot.

It catches what the statement policy cannot: an unqualified system catalog such as pg_shadow
(PostgreSQL searches pg_catalog first), and invented tables or columns, with feedback that names
what does exist.
"""

from __future__ import annotations

from sqlglot.errors import OptimizeError
from sqlglot.optimizer.qualify import qualify

from datapilot.contracts import GraderContext, GraderResult, Stage
from datapilot.loop1_agent.catalog import CatalogSnapshot
from datapilot.loop2_verification.graders._sql import (
    DIALECT,
    base_tables,
    blocked,
    parse_all,
    passed,
)


class SchemaGrader:
    name = "schema"
    stage = Stage.PRE_EXECUTION

    def __init__(self, snapshot: CatalogSnapshot) -> None:
        self.snapshot = snapshot

    def check(self, context: GraderContext) -> GraderResult:
        try:
            statements = parse_all(context.sql or "")
        except Exception:
            return blocked(self.name, "not parseable", "Send one SELECT statement.")
        known = sorted(self.snapshot.tables)
        for tree in statements:
            for table in base_tables(tree):
                if self.snapshot.table(table.name) is None:
                    return blocked(
                        self.name,
                        f"unknown table {table.name}",
                        f"There is no table {table.name}. Tables: {', '.join(known)}.",
                    )
            try:
                qualify(
                    tree.copy(),
                    schema=self.snapshot.sqlglot_schema(),
                    db=self.snapshot.schema,
                    dialect=DIALECT,
                    validate_qualify_columns=True,
                )
            except OptimizeError as error:
                message = str(error).split(". Line")[0]
                if "could not be resolved" in message or "Unknown column" in message:
                    return blocked(
                        self.name,
                        message,
                        f"{message}. Use describe_table to see the real column names.",
                    )
        return passed(self.name, "every table and column exists")
