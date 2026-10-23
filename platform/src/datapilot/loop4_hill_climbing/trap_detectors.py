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
_CALENDAR_BOUND = re.compile(r"^\d{4}-(01-01|12-31)")


def _calendar_year(tree: exp.Expression) -> bool:
    for node in tree.find_all(exp.Extract):
        if _YEAR_PART.match(node.this.name):
            return True
    for node in tree.find_all(exp.Anonymous, exp.TimestampTrunc, exp.DateTrunc):
        unit = node.args.get("unit")
        if unit is not None and _YEAR_PART.match(unit.name):
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
