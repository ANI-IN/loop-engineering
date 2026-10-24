"""Non-gating trap labels for the agent's SQL: they explain a failure, they never decide one.

Each detector reads the syntax tree and names the trap the SQL most likely fell into. A query that
does not parse gets no labels; pass or fail comes only from the execution match.
"""

from __future__ import annotations

import re

import sqlglot
from sqlglot import exp

# label -> the trap it points at (benchmark item traps)
LABELS = {
    "calendar_year_range": "fiscal_year",
    "total_cents_used": "net_revenue",
    "missing_status_filter": "cancelled_orders",
    "utc_truncation": "eastern_time",
    "missing_internal_filter": "internal_accounts",
}
_YEAR_PART = re.compile(r"^(year|yyyy|y)$", re.IGNORECASE)
_MONTH_PART = re.compile(r"^(month|mon|mm|m)$", re.IGNORECASE)
_CALENDAR_BOUND = re.compile(r"^\d{4}-(01-01|12-31)")
# A bound on 1 February or 31 January: the edges of the fiscal year itself.
_FISCAL_BOUND = re.compile(r"^\d{4}-(02-01|01-31)")
_RANGE_BOUNDS = (exp.GT, exp.GTE, exp.LT, exp.LTE, exp.Between)
# (the function node, the date part it reads, the expression it reads it from)
Part = tuple[exp.Expression, str, exp.Expression | None]


def _part(node: exp.Expression) -> tuple[str, exp.Expression | None]:
    """(the date part a function reads, the expression it reads it from)."""
    if isinstance(node, exp.Extract):
        return node.this.name, node.expression
    unit = node.args.get("unit")
    source = node.this if isinstance(node.this, exp.Expression) else None
    return (unit.name if unit is not None else ""), source


def _shifted(source: exp.Expression | None) -> bool:
    """The date is moved by an interval first, so the year read from it is a fiscal year."""
    return source is not None and any(True for _ in source.find_all(exp.Interval))


def _filters(node: exp.Expression) -> bool:
    """The node is part of a filter (WHERE or HAVING), not of what the query shows or groups by."""
    return node.find_ancestor(exp.Where, exp.Having) is not None


def _fiscal_year(tree: exp.Expression, parts: list[Part]) -> bool:
    """The query reads the fiscal year: the year of a shifted date; the year beside a month that
    is shifted or filters (a month in a monthly breakdown is no sign, review round 3); or a range
    bound on the fiscal year's own edges (1 February, 31 January), not any such date anywhere."""
    years = [source for _, part, source in parts if _YEAR_PART.match(part)]
    if any(_shifted(source) for source in years):
        return True
    months = [(node, source) for node, part, source in parts if _MONTH_PART.match(part)]
    if years and any(_shifted(source) or _filters(node) for node, source in months):
        return True
    return any(
        _FISCAL_BOUND.match(lit.this) and lit.find_ancestor(*_RANGE_BOUNDS) is not None
        for lit in tree.find_all(exp.Literal)
        if lit.is_string
    )


def _calendar_year(tree: exp.Expression) -> bool:
    """A calendar-year range: the year of the unshifted date, or a 1 January or 31 December
    bound, in a query that shows no sign of the fiscal year."""
    parts = [
        (node, *_part(node))
        for node in tree.find_all(exp.Extract, exp.Anonymous, exp.TimestampTrunc, exp.DateTrunc)
    ]
    if _fiscal_year(tree, parts):
        return False
    if any(_YEAR_PART.match(part) for _, part, _ in parts):
        return True
    if any(isinstance(n, exp.Year) for n in tree.walk()):
        return True
    return any(
        _CALENDAR_BOUND.match(lit.this) for lit in tree.find_all(exp.Literal) if lit.is_string
    )


def detect(sql: str) -> list[str]:
    """Every label whose pattern appears in `sql`, in the order of LABELS."""
    try:
        tree = sqlglot.parse_one(sql, dialect="postgres")
    except sqlglot.errors.ParseError:
        return []
    if tree is None:
        return []
    columns = {c.name.lower() for c in tree.find_all(exp.Column)}
    tables = {t.name.lower() for t in tree.find_all(exp.Table)}
    strings = [lit.this.lower() for lit in tree.find_all(exp.Literal) if lit.is_string]
    eastern = any(tree.find_all(exp.AtTimeZone)) or "america/new_york" in strings
    found = {
        "calendar_year_range": _calendar_year(tree),
        "total_cents_used": "total_cents" in columns,
        "missing_status_filter": "orders" in tables and "status" not in columns,
        "utc_truncation": "order_ts" in columns and not eastern,
        "missing_internal_filter": bool(tables & {"orders", "customers"})
        and not any("harborpine" in s for s in strings),
    }
    return [label for label in LABELS if found[label]]


def labels_for(sql: str, traps: list[str]) -> list[str]:
    """The labels that point at one of an item's traps."""
    return [label for label in detect(sql) if LABELS[label] in traps]
