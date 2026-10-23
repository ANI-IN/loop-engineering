"""Grader 2, statement policy: an allowlist on the syntax tree.

The root must be a SELECT or a set operation; no write or session node may appear anywhere in the
tree (a data-modifying CTE hides a DELETE under a SELECT root); no denied function; tables only in
the allowed schema. The executor still runs the original text, never SQL regenerated from the tree.
"""

from __future__ import annotations

from sqlglot import exp

from datapilot.contracts import Grader, GraderContext, GraderResult, Stage
from datapilot.loop2_verification.graders._sql import (
    base_tables,
    blocked,
    function_name,
    parse_single,
    passed,
)
from datapilot.loop2_verification.graders.parse import ParseGrader
from datapilot.planted import planted

FORBIDDEN_NODES: tuple[type[exp.Expression], ...] = (
    exp.Insert, exp.Update, exp.Delete, exp.Merge, exp.Copy, exp.Create, exp.Alter, exp.Drop,
    exp.Grant, exp.Revoke, exp.Set, exp.Command, exp.Into, exp.Lock, exp.TruncateTable,
    exp.Transaction, exp.Commit, exp.Rollback, exp.Use, exp.Pragma, exp.Analyze, exp.Comment,
    exp.Execute, exp.Kill, exp.LoadData,
)  # fmt: skip
# Exact names and prefixes: sleeping, file and large-object access, SQL hidden in strings, session
# settings, sequences, signals, locks, and catalog introspection.
DENIED_FUNCTIONS = (
    "set_config",
    "nextval",
    "setval",
    "pg_notify",
    "pg_reload_conf",
    "txid_current",
    "current_setting",
    "obj_description",
    "col_description",
    "shobj_description",
    "to_regclass",
    "format_type",
)
DENIED_PREFIXES = (
    "pg_sleep", "pg_read", "pg_ls_", "pg_stat_file", "pg_file", "pg_write", "lo_", "dblink",
    "query_to_xml", "table_to_xml", "cursor_to_xml", "schema_to_xml", "database_to_xml",
    "pg_terminate_backend", "pg_cancel_backend", "pg_advisory", "pg_try_advisory",
    "pg_create", "pg_drop", "pg_logical", "pg_replication", "pg_switch", "pg_rotate",
    "pg_promote", "pg_import", "pg_execute",
    # Catalog introspection: view definitions and comments are not the agent's to read (the
    # marketing view's definition names the internal-account rule).
    "pg_get_", "pg_describe", "pg_options_to_table", "pg_table",
)  # fmt: skip


def is_read_only_select(sql: str) -> bool:
    """The syntax-tree classification, whatever guard is planted: exactly one statement whose root
    is a SELECT or a set operation, with no write or session node anywhere in its tree."""
    tree = parse_single(sql)
    if tree is None:
        return False
    root = tree.unnest() if isinstance(tree, exp.Subquery) else tree
    if not isinstance(root, exp.Select | exp.SetOperation):
        return False
    return not any(isinstance(node, FORBIDDEN_NODES) for node in tree.walk())


def _denied(name: str) -> bool:
    return name in DENIED_FUNCTIONS or name.startswith(DENIED_PREFIXES)


class StatementPolicyGrader:
    name = "statement_policy"
    stage = Stage.PRE_EXECUTION

    def __init__(self, schema: str) -> None:
        self.schema = schema

    def check(self, context: GraderContext) -> GraderResult:
        tree = parse_single(context.sql or "")
        if tree is None:
            return blocked(self.name, "not one parseable statement", "Send one SELECT statement.")
        root = tree.unnest() if isinstance(tree, exp.Subquery) else tree
        if not isinstance(root, exp.Select | exp.SetOperation):
            kind = type(root).__name__.upper()
            return blocked(self.name, f"{kind} is not allowed", "Only SELECT queries may run.")
        for node in tree.walk():
            if isinstance(node, FORBIDDEN_NODES):
                kind = type(node).__name__.upper()
                return blocked(
                    self.name,
                    f"{kind} inside the query",
                    f"The query contains {kind}; only reads are allowed, including inside CTEs.",
                )
            if _reads_clock(node):
                return blocked(self.name, "reads the database clock", clock_feedback())
            if isinstance(node, exp.Func) and _denied(function_name(node)):
                fn = function_name(node)
                return blocked(self.name, f"function {fn} is denied", f"Do not call {fn}.")
        for table in base_tables(tree):
            if (table.db and table.db.lower() != self.schema) or table.catalog:
                where = ".".join(p for p in (table.catalog, table.db) if p)
                return blocked(
                    self.name,
                    f"table outside the {self.schema} schema: {where}.{table.name}",
                    f"Read only tables in the {self.schema} schema (list_tables shows them).",
                )
        return passed(self.name, "a read-only SELECT in the allowed schema")


class NaiveGuard:
    """The planted naive guard: a text prefix check (select, or with for CTEs)."""

    name = "statement_policy"
    stage = Stage.PRE_EXECUTION

    def check(self, context: GraderContext) -> GraderResult:
        if (context.sql or "").strip().lower().startswith(("select", "with")):
            return passed(self.name, "starts with select or with")
        return blocked(self.name, "does not start with select", "Only SELECT queries may run.")


def guard_graders(schema: str) -> list[Grader]:
    """The syntax-tree guard: parse, then the statement policy."""
    if planted("BUG_NAIVE_GUARD"):
        return [NaiveGuard()]  # planted: a startswith check replaces the syntax-tree guard
    return [ParseGrader(), StatementPolicyGrader(schema)]


# Agent SQL is business logic: "today" is the business date, never the database clock.
CLOCK_NODES: tuple[type[exp.Expression], ...] = (
    exp.CurrentDate, exp.CurrentTimestamp, exp.CurrentTime, exp.Localtimestamp, exp.Localtime,
)  # fmt: skip
CLOCK_FUNCTIONS = ("clock_timestamp", "statement_timestamp", "transaction_timestamp", "timeofday")
CLOCK_WORDS = ("now", "today", "yesterday", "tomorrow")  # PostgreSQL's special date input strings


def _reads_clock(node: exp.Expression) -> bool:
    if isinstance(node, CLOCK_NODES):
        return True
    if isinstance(node, exp.Func) and function_name(node) in CLOCK_FUNCTIONS:
        return True
    if isinstance(node, exp.Cast) and isinstance(node.this, exp.Literal) and node.this.is_string:
        return node.this.this.strip().lower() in CLOCK_WORDS
    return False


def clock_feedback() -> str:
    from datapilot import business_date

    return (
        "Do not read the database clock (the current date and time functions, now(), and the "
        "like). Today's business "
        f"date is {business_date.status_label().removeprefix('Business date: ')}: write every "
        "date as a literal resolved against it."
    )
