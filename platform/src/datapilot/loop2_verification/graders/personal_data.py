"""Grader 5, personal data: queries that read personal-data columns go to human approval.

Columns come from pack.yaml (personal_data.columns), and the same columns exposed by the marketing
view count too. Stars are expanded against the catalog, so SELECT * FROM customers is caught.
Marketing exports must read the marketing view, never the base table that holds the columns.

It fails closed on the whole syntax tree. A personal column counts as read wherever it appears,
except in a predicate (WHERE, JOIN ON, GROUP BY, HAVING), whose values never come back: a select
list (the query's own or a subquery's), ORDER BY, and the FROM clause (a VALUES list, a LATERAL,
a function's arguments, a set-returning function) all count. A whole row (c, c.*, a table used as
a value) counts as every personal column of its table. A reference it cannot place counts as every
personal column of the tables the query names, and SQL held in a string (ts_stat, query_to_xml),
which hides its tables from any parser, always needs approval.
"""

from __future__ import annotations

from sqlglot import exp
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.scope import Scope, traverse_scope

from datapilot.contracts import GraderContext, GraderResult, Severity, Stage
from datapilot.loop1_agent.catalog import CatalogSnapshot
from datapilot.loop2_verification.config import VerificationConfig
from datapilot.loop2_verification.graders._sql import (
    DIALECT,
    base_tables,
    blocked,
    function_name,
    parse_single,
    passed,
)

# The clauses whose values filter, join, or group rows and never come back as a value.
PREDICATE_CLAUSES: tuple[type[exp.Expression], ...] = (exp.Where, exp.Having, exp.Group)
# Functions that run SQL held in a string (the statement policy denies them too).
SQL_IN_A_STRING = (
    "query_to_xml", "table_to_xml", "cursor_to_xml", "schema_to_xml", "database_to_xml",
    "ts_stat", "ts_rewrite", "dblink", "crosstab", "connectby",
)  # fmt: skip


def in_predicate(node: exp.Expression) -> bool:
    """True when the nearest clause holding `node` is a WHERE, JOIN ON, GROUP BY, or HAVING
    predicate: the reference filters rows, and its value is never returned. Anything else, up to
    the nearest query, returns it (a select list, ORDER BY, FROM, VALUES, a function argument)."""
    child, parent = node, node.parent
    while parent is not None:
        if isinstance(parent, PREDICATE_CLAUSES):
            return True
        if isinstance(parent, exp.Join) and child.arg_key in ("on", "using"):
            return True
        if isinstance(parent, exp.Query):
            return False
        child, parent = parent, parent.parent
    return False


def sql_in_a_string(tree: exp.Expression) -> str | None:
    """The first function of the tree that runs SQL held in a string, or None."""
    for node in tree.find_all(exp.Func):
        name = function_name(node)
        if name.startswith(SQL_IN_A_STRING):
            return name
    return None


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
        """The personal-data columns a query can return, from every reference outside a predicate
        (stars expanded); None when it cannot be resolved. A column used only to filter, join, or
        group, such as the email domain that marks internal accounts, returns no personal data."""
        tree = parse_single(sql)
        if tree is None or sql_in_a_string(tree):
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
        scopes = {id(scope.expression): scope for scope in traverse_scope(tree)}
        found: set[str] = set()
        for node in tree.find_all(exp.Column, exp.TableColumn, exp.Star):
            if isinstance(node, exp.Star) and isinstance(node.parent, exp.Column):
                continue  # c.*: read as its column
            if in_predicate(node):
                continue
            scope = _scope_of(node, scopes)
            returned = None if scope is None else self._returned(scope, node)
            if returned is None:
                return None
            found |= returned
        return sorted(found)

    def _returned(self, scope: Scope, node: exp.Expression) -> set[str] | None:
        """The personal columns one reference returns; None when it cannot say."""
        if isinstance(node, exp.Star):
            # count(*) returns no column value; any other star is one the catalog could not expand.
            return set() if isinstance(node.parent, exp.Count) else None
        table = node.table if isinstance(node, exp.Column) else ""
        whole_row = not table or isinstance(node.this, exp.Star)
        source = _source(scope, table or node.name)
        if source is None:
            if not table and _output_alias(scope, node.name):
                return set()  # ORDER BY an output column: graded where the select list names it
            return None
        if not (isinstance(source, exp.Table) and isinstance(source.this, exp.Identifier)):
            # A derived table, CTE, VALUES list, or table function: every reference inside it is
            # graded where it appears, so its output carries nothing ungraded.
            return set()
        if whole_row:  # c, c.*, or the table name used as a value: every column of the row
            return {f"{source.name}.{c}" for t, c in self.columns if t == source.name}
        return {f"{source.name}.{node.name}"} if (source.name, node.name) in self.columns else set()

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
        hidden = sql_in_a_string(tree) if tree is not None else None
        if hidden:
            return _route(f"runs SQL held in a string ({hidden}), which can read any column")
        columns = self.personal_columns_read(sql)
        if columns is None:
            touches = tables & (self.config.personal_tables | {self.config.marketing_view})
            if not touches:
                return passed(self.name, "no personal data")
            columns = [f"{t}.*" for t in sorted(touches)]
        if not columns:
            return passed(self.name, "no personal data")
        return _route(f"reads personal data ({', '.join(columns)})")


def _route(what: str) -> GraderResult:
    return GraderResult(
        grader=PersonalDataGrader.name,
        passed=True,
        reason=f"{what}; needs human approval",
        severity=Severity.ROUTE,
    )


def _scope_of(node: exp.Expression, scopes: dict[int, Scope]) -> Scope | None:
    """The innermost scope (query, VALUES list, LATERAL, or table function) holding `node`."""
    parent = node.parent
    while parent is not None:
        if id(parent) in scopes:
            return scopes[id(parent)]
        parent = parent.parent
    return None


def _source(scope: Scope | None, name: str) -> exp.Expression | Scope | None:
    """What `name` refers to from `scope`: its own sources first, then each enclosing scope's, as
    a LATERAL or correlated reference resolves; None when no scope names it."""
    while scope is not None:
        if name in scope.sources:
            source: exp.Expression | Scope = scope.sources[name]
            return source
        scope = scope.parent
    return None


def _output_alias(scope: Scope, name: str) -> bool:
    query = scope.expression
    return isinstance(query, exp.Select) and name in {s.alias_or_name for s in query.selects}
