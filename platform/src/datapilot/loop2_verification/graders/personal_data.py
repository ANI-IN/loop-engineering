"""Grader 5, personal data: queries that read personal-data columns go to human approval.

Columns come from pack.yaml (personal_data.columns), and the same columns exposed by the marketing
view count too. Stars are expanded against the catalog, so SELECT * FROM customers is caught.
Marketing exports must read the marketing view, never the base table that holds the columns.
"""

from __future__ import annotations

from sqlglot import exp
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.scope import traverse_scope

from datapilot.contracts import GraderContext, GraderResult, Severity, Stage
from datapilot.loop1_agent.catalog import CatalogSnapshot
from datapilot.loop2_verification.config import VerificationConfig
from datapilot.loop2_verification.graders._sql import (
    DIALECT,
    base_tables,
    blocked,
    parse_single,
    passed,
)


class PersonalDataGrader:
    name = "personal_data"
    stage = Stage.PRE_EXECUTION

    def __init__(self, config: VerificationConfig, snapshot: CatalogSnapshot) -> None:
        self.config = config
        self.snapshot = snapshot
        view = config.marketing_view
        self.columns = set(config.personal_columns) | {
            (view, c) for _, c in config.personal_columns
        }

    def personal_columns_read(self, sql: str) -> list[str] | None:
        """The personal-data columns a query returns in any select list (its own or a subquery's,
        stars expanded); None when it cannot be resolved. A column used only to filter, join, or
        group, such as the email domain that marks internal accounts, returns no personal data."""
        tree = parse_single(sql)
        if tree is None:
            return None
        try:
            tree = qualify(
                tree,
                schema=self.snapshot.sqlglot_schema(),
                db=self.snapshot.schema,
                dialect=DIALECT,
            )
        except Exception:
            return None
        found: set[str] = set()
        for scope in traverse_scope(tree):
            selects = scope.expression.selects if isinstance(scope.expression, exp.Select) else []
            projected = {id(c) for s in selects for c in s.find_all(exp.Column)}
            for column in scope.columns:
                if id(column) not in projected:
                    continue
                source = scope.sources.get(column.table)
                if isinstance(source, exp.Table) and (source.name, column.name) in self.columns:
                    found.add(f"{source.name}.{column.name}")
        return sorted(found)

    def check(self, context: GraderContext) -> GraderResult:
        sql = context.sql or ""
        tree = parse_single(sql)
        tables = {t.name.lower() for t in base_tables(tree)} if tree is not None else set()
        export = bool(context.extra.get("export"))
        if export and tables & self.config.personal_tables:
            view = f"{self.config.schema}.{self.config.marketing_view}"
            base = ", ".join(sorted(tables & self.config.personal_tables))
            return blocked(
                self.name,
                f"a marketing export reads the base table {base}",
                f"Marketing exports must read {view}, which holds only the people who may be "
                "contacted.",
            )
        columns = self.personal_columns_read(sql)
        if columns is None:
            touches = tables & (self.config.personal_tables | {self.config.marketing_view})
            if not touches:
                return passed(self.name, "no personal data")
            columns = [f"{t}.*" for t in sorted(touches)]
        if not columns:
            return passed(self.name, "no personal data")
        return GraderResult(
            grader=self.name,
            passed=True,
            reason=f"reads personal data ({', '.join(columns)}); needs human approval",
            severity=Severity.ROUTE,
        )
