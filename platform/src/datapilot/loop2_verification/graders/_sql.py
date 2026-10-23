"""Small sqlglot helpers shared by the graders. Parsing only: graders never regenerate SQL to run
it (regenerated SQL can differ from the original, so the executor always runs the original text)."""

from __future__ import annotations

import logging

import sqlglot
from sqlglot import exp

from datapilot.contracts import GraderResult, Severity

DIALECT = "postgres"
# sqlglot logs a warning when it falls back to an opaque Command; the parse grader reports it.
logging.getLogger("sqlglot").setLevel(logging.ERROR)


def parse_all(sql: str) -> list[exp.Expression]:
    """Every statement in the text; raises sqlglot.errors.ParseError on invalid SQL."""
    return [s for s in sqlglot.parse(sql, dialect=DIALECT) if s is not None]


def parse_single(sql: str) -> exp.Expression | None:
    """The one statement, or None when the text is not exactly one parseable statement."""
    try:
        statements = parse_all(sql)
    except sqlglot.errors.ParseError:
        return None
    return statements[0] if len(statements) == 1 else None


def cte_names(tree: exp.Expression) -> set[str]:
    return {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}


def base_tables(tree: exp.Expression) -> list[exp.Table]:
    """Table references that name a relation (not a CTE, not a function such as generate_series)."""
    ctes = cte_names(tree)
    return [
        t
        for t in tree.find_all(exp.Table)
        if isinstance(t.this, exp.Identifier) and not (not t.db and t.name.lower() in ctes)
    ]


def function_name(node: exp.Func) -> str:
    name = node.name if isinstance(node, exp.Anonymous) else node.sql_name()
    return name.lower()


def passed(grader: str, reason: str, severity: Severity = Severity.INFO) -> GraderResult:
    return GraderResult(grader=grader, passed=True, reason=reason, severity=severity)


def blocked(grader: str, reason: str, feedback: str) -> GraderResult:
    return GraderResult(
        grader=grader,
        passed=False,
        reason=reason,
        severity=Severity.BLOCK,
        feedback_for_agent=feedback,
    )
