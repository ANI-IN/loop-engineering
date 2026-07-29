"""How a model's result is judged against gold.

Three decisions here are load-bearing, and each one is a way this comparison could
silently report a correct query as wrong — which would land in the sweep as a
model failure and be indistinguishable from a real one.

**Tolerance is relative, not absolute.** "1e-6" is ambiguous and the reading
matters. Revenue sums in this warehouse run to millions; re-associating the same
addends under a different join plan moves the low bits, easily past 1e-6 in
absolute terms. An absolute tolerance would fail two correct queries against each
other. A small absolute floor is kept alongside it because relative tolerance
degenerates at zero — `rel_tol * max(|a|, |b|)` is itself zero when both are.

**NULL equals NULL.** SQL says otherwise, and that is right for SQL; result
comparison wants the opposite. Left implicit, every item where a region has no
orders fails. NULL still does not equal 0: None means "no row matched", 0 means
"matched and summed to zero", and conflating them hides a whole class of wrong
query.

**Numeric types are normalised before comparison.** DuckDB returns DECIMAL from
some aggregates and DOUBLE from others, and `Decimal('100.00') == 100.0` is False
in Python. Without normalisation a correct query fails against gold purely on the
type the planner happened to pick.

Multiset equality, not set equality: collapsing duplicates would let a query with a
stray DISTINCT pass. Order-sensitive only when the gold SQL's outermost query has
an ORDER BY, detected from the sqlglot AST — a string search for "ORDER BY" matches
a table named `orders` and matches a subquery's ordering, which the outer result
does not preserve.
"""

import math
from decimal import Decimal
from typing import Any

import sqlglot

# Relative. Widened from 1e-6 to 1e-5 on 2026-07-29, and the value is pinned between
# two measurements rather than chosen for looking round.
#
# WHY IT HAD TO MOVE. 1e-6 demands agreement to ~6 significant figures. The gold SQL
# rounds — ROUND(x, 2) for money, ROUND(x, 6) for rates — and models generally do not,
# so a correct query returning 688.0023410828026 against a gold 688.0 was scored as a
# silent error. Measured on the first Phase 1 trap: 7 of 35 apparent silent errors were
# this artefact alone, two correct queries disagreeing about display precision. The
# largest such artefact observed is 6.02e-06.
#
# WHY IT COULD NOT MOVE FURTHER. Widening a comparison is how an instrument gets
# quietly weakened, so the ceiling is measured too: the tightest naive variant in this
# gold set is p07_aov_by_region__04's cancelled_orders, which differs from gold by
# 6.06e-05 — excluding cancelled orders barely moves an average order value. At 1e-4 a
# model ignoring that rule would have scored CORRECT. The guard test in
# tests/test_gold_build.py asserts no variant falls inside the tolerance; it is what
# caught 1e-4 being wrong.
#
# So the window is [6.02e-06, 6.06e-05] and 1e-5 is the one order of magnitude inside
# it. That is narrow. If a future gold item has a rule with a smaller effect than this,
# the guard test fails and the right response is to fix the item, not the constant.
REL_TOL = 1e-5

# Absolute floor, for values at or near zero where relative tolerance is vacuous.
ABS_TOL = 1e-9

_NUMERIC = (int, float, Decimal)


def is_order_sensitive(sql: str) -> bool:
    """True when the outermost SELECT carries an ORDER BY.

    Only the outer query decides. An ORDER BY inside a subquery constrains which
    rows survive a LIMIT, but says nothing about the order of what comes back.
    """
    try:
        parsed = sqlglot.parse_one(sql, read="duckdb")
    except Exception:
        # An unparseable query cannot be ordered, and the executor will reject it
        # anyway. Failing open here would silently make comparisons stricter.
        return False
    if parsed is None:
        return False
    return parsed.args.get("order") is not None


def _is_number(value: Any) -> bool:
    # bool is a subclass of int, and True == 1. A BOOLEAN column and an INTEGER
    # column are different answers, so booleans are never treated as numbers.
    return isinstance(value, _NUMERIC) and not isinstance(value, bool)


def _sort_key(row: tuple) -> tuple:
    """Order rows so a multiset comparison can pair them up.

    Values are ranked by kind first, so a Decimal and a float never end up compared
    as strings, and a None never has to be ordered against a number. Within the
    numeric rank the exact value is used rather than a rounded one: rounding would
    introduce a discontinuity that could split two tolerance-equal values into
    different sort positions.
    """
    key = []
    for value in row:
        if value is None:
            key.append((0, 0.0, ""))
        elif isinstance(value, bool):
            key.append((1, float(value), ""))
        elif _is_number(value):
            key.append((2, float(value), ""))
        else:
            key.append((3, 0.0, str(value)))
    return tuple(key)


def _values_equal(expected: Any, actual: Any, rel_tol: float, abs_tol: float) -> bool:
    if expected is None or actual is None:
        return expected is None and actual is None
    if isinstance(expected, bool) or isinstance(actual, bool):
        return isinstance(expected, bool) and isinstance(actual, bool) and expected == actual
    if _is_number(expected) and _is_number(actual):
        return math.isclose(float(expected), float(actual), rel_tol=rel_tol, abs_tol=abs_tol)
    if _is_number(expected) or _is_number(actual):
        # One is a number and the other is not. '100' is not 100.
        return False
    return str(expected) == str(actual)


def rows_equal(
    expected: list[tuple],
    actual: list[tuple],
    *,
    order_sensitive: bool,
    rel_tol: float = REL_TOL,
    abs_tol: float = ABS_TOL,
) -> bool:
    """Multiset equality under numeric tolerance.

    When order does not matter both sides are sorted and compared pairwise. That is
    exact whenever the tolerance is small relative to the gaps between distinct
    values, which holds throughout this gold set; a fully general answer would need
    bipartite matching, and buying that generality is not worth the complexity for
    results whose values are separated by percentages rather than by float noise.
    """
    if len(expected) != len(actual):
        return False

    left, right = list(expected), list(actual)
    if not order_sensitive:
        left = sorted(left, key=_sort_key)
        right = sorted(right, key=_sort_key)

    for expected_row, actual_row in zip(left, right, strict=True):
        if len(expected_row) != len(actual_row):
            return False
        if not all(
            _values_equal(e, a, rel_tol, abs_tol)
            for e, a in zip(expected_row, actual_row, strict=True)
        ):
            return False
    return True
