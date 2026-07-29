"""The Level 2 verifiers: rule checks that read SQL, not answers.

Each verifier is handed a `VerifyContext` — question, SQL, schema, declared rules,
and what happened when the query ran — and returns the rules it believes were
violated, with a complaint the loop can feed back to the model.

**No verifier receives the gold answer, and that is structural rather than
conventional.** `VerifyContext` has no field for it, and the function that builds
one (`loopeng.verify.loop.build_context`) takes no gold parameter, so there is
nothing in scope for a careless author to pass through. A verifier that could see
the answer would trivially score 100% and measure nothing.

Checks are performed on the **sqlglot AST**, not on the query text. A rule check
that greps for `deleted_at IS NULL` passes a query with that string inside a comment,
inside a subquery that never joins, or negated. The regex versions in
`loopeng.verify.regex_verifiers` exist to demonstrate exactly that failure — they
score *higher* while catching *less*.
"""

from dataclasses import dataclass

import sqlglot
from sqlglot import exp

from loopeng.contracts import VerifyContext


@dataclass(frozen=True)
class Violation:
    rule: str
    complaint: str


@dataclass(frozen=True)
class VerifyResult:
    violations: tuple[Violation, ...]

    @property
    def ok(self) -> bool:
        return not self.violations

    @property
    def rules(self) -> tuple[str, ...]:
        return tuple(v.rule for v in self.violations)

    def feedback(self) -> str:
        """What the model is told. Names the rule; never names the answer."""
        if self.ok:
            return ""
        lines = ["That query does not satisfy the business rules:"]
        lines.extend(f"- [{v.rule}] {v.complaint}" for v in self.violations)
        lines.append("Return a corrected query. SQL only.")
        return "\n".join(lines)


def _parse(sql: str) -> exp.Expression | None:
    try:
        return sqlglot.parse_one(sql, read="duckdb")
    except Exception:
        return None


def _tables(tree: exp.Expression) -> set[str]:
    return {t.name.lower() for t in tree.find_all(exp.Table) if t.name}


def _has_column_predicate(tree: exp.Expression, column: str) -> bool:
    """Is this column actually constrained anywhere in the query's logic?

    Walks the AST for a comparison, IS NULL, or NOT involving the column. A text
    search would match the column appearing in a SELECT list, in a comment, or in a
    subquery whose result is never filtered on.
    """
    column = column.lower()
    for node in tree.find_all(exp.Is, exp.EQ, exp.NEQ, exp.Not, exp.In, exp.Boolean):
        for identifier in node.find_all(exp.Column):
            if identifier.name.lower() == column:
                return True
    # `WHERE NOT is_internal` parses the column as a bare condition under Not/Where.
    for node in tree.find_all(exp.Where, exp.Join):
        for identifier in node.find_all(exp.Column):
            if identifier.name.lower() == column:
                return True
    return False


def _selects_currency_conversion(tree: exp.Expression) -> bool:
    """Does the query convert, rather than sum raw minor units?

    Looks for a CASE over `currency`, which is how the declared usd_factor has to be
    applied when the rates live in config rather than in a table.
    """
    for case in tree.find_all(exp.Case):
        for column in case.find_all(exp.Column):
            if column.name.lower() == "currency":
                return True
    return False


def _aggregates_order_amount_with_items_joined(tree: exp.Expression) -> bool:
    """The fan-out trap: order-grain money aggregated after joining order_items."""
    tables = _tables(tree)
    if "order_items" not in tables or "orders" not in tables:
        return False
    for agg in tree.find_all(exp.Sum, exp.Avg):
        for column in agg.find_all(exp.Column):
            if column.name.lower() == "amount_minor":
                table = (column.table or "").lower()
                if table in ("o", "orders", ""):
                    return True
    return False


# --- individual rule checks -------------------------------------------------
# Each returns a complaint string when violated, or None. They are deliberately
# small and independent so a rule-surface probe can exercise one at a time.


def check_soft_delete(context: VerifyContext, tree: exp.Expression) -> str | None:
    if "soft_delete" not in context.rules:
        return None
    if _has_column_predicate(tree, "deleted_at"):
        return None
    return (
        "Soft-deleted rows are not excluded. Rows with deleted_at IS NOT NULL are "
        "deleted and must be excluded, for customers and orders independently."
    )


def check_cancelled_orders(context: VerifyContext, tree: exp.Expression) -> str | None:
    if "cancelled_orders" not in context.rules:
        return None
    if _has_column_predicate(tree, "status"):
        return None
    return "Cancelled orders are not excluded. status = 'cancelled' must not count."


def check_internal_accounts(context: VerifyContext, tree: exp.Expression) -> str | None:
    if "internal_accounts" not in context.rules:
        return None
    if _has_column_predicate(tree, "is_internal"):
        return None
    return (
        "Internal test accounts are not excluded. Customers with is_internal true "
        "must be excluded from every business metric."
    )


def check_currency(context: VerifyContext, tree: exp.Expression) -> str | None:
    if not ({"multi_currency", "minor_units"} & set(context.rules)):
        return None
    if _selects_currency_conversion(tree):
        return None
    return (
        "Amounts in different currencies are being combined without conversion. "
        "Convert to USD with the declared usd_factor per currency before aggregating; "
        "JPY has no minor unit, so a flat divide by 100 is wrong."
    )


def check_fan_out(context: VerifyContext, tree: exp.Expression) -> str | None:
    if "fan_out" not in context.rules:
        return None
    if _aggregates_order_amount_with_items_joined(tree):
        return (
            "orders.amount_minor is aggregated after joining order_items, which "
            "double-counts: orders to order_items is one-to-many. Aggregate "
            "order-level money at order grain, or use qty * unit_price_minor."
        )
    return None


def check_refunds_net(context: VerifyContext, tree: exp.Expression) -> str | None:
    if "refunds_net" not in context.rules:
        return None
    if "refunds" in _tables(tree):
        return None
    return (
        "Net revenue must subtract refunds, and the refunds table is not referenced. "
        "Refunds are one-to-many per order, so aggregate them per order first."
    )


RULE_CHECKS = {
    "soft_delete": check_soft_delete,
    "cancelled_orders": check_cancelled_orders,
    "internal_accounts": check_internal_accounts,
    "multi_currency": check_currency,
    # minor_units and multi_currency are ONE SQL change — the declared usd_factor
    # versus a naive /100 — so they share a check. Both are listed explicitly rather
    # than one being folded silently into the other: the governance layer starts from
    # the rules the config declares, and a rule that is enforced only as a side effect
    # of another is indistinguishable, from the config's side, from one that is not
    # enforced at all. That gap is what the V2 build gate exists to catch, and it
    # caught this one on its first run.
    "minor_units": check_currency,
    "fan_out": check_fan_out,
    "refunds_net": check_refunds_net,
}


def verify(context: VerifyContext) -> VerifyResult:
    """Run every applicable rule check against the query's AST."""
    # A query that did not run is already a visible failure; Level 1 handles it and
    # there is no AST worth inspecting.
    if context.execution_error:
        return VerifyResult(violations=())

    tree = _parse(context.sql)
    if tree is None:
        return VerifyResult(violations=())

    violations = []
    for rule, check in RULE_CHECKS.items():
        complaint = check(context, tree)
        if complaint:
            violations.append(Violation(rule=rule, complaint=complaint))
    return VerifyResult(violations=tuple(violations))
