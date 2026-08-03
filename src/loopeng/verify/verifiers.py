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


# The rules below check the DIRECTION of a predicate, not the presence of a column.
#
# `_has_column_predicate` used to live here and asked only "does this column appear
# somewhere inside a WHERE or JOIN?". Every one of these passed it:
#
#     WHERE o.deleted_at IS NOT NULL      the exact opposite of the rule
#     WHERE o.deleted_at IS NULL          one table, for a rule whose own complaint
#                                         says "for customers and orders independently"
#     WHERE o.status = 'cancelled'        selecting only what must be excluded
#     WHERE c.is_internal                 selecting only the test accounts
#
# So the verifier held up as the correct one, against which the regex version is
# shown to be inadequate, accepted four queries that break the rules its own
# complaint text names. Of the three failure modes the module docstring attributes
# to regexes, it fixed one, shared one, and was worse than the regex on the third.
#
# Each rule gets its own check because the rules genuinely differ: soft-delete is
# about coverage across tables, cancelled-orders is about a value, and
# internal-accounts is about a boolean's polarity. One shared helper is what made
# them look interchangeable.


#: Tables carrying `deleted_at`. The rule applies to each one present, separately.
SOFT_DELETE_TABLES = ("orders", "customers")


def _alias_map(tree: exp.Expression) -> dict[str, str]:
    """Every way a table can be named in this query, mapped to the table."""
    names: dict[str, str] = {}
    for table in tree.find_all(exp.Table):
        if not table.name:
            continue
        name = table.name.lower()
        names[name] = name
        if table.alias:
            names[table.alias.lower()] = name
    return names


def _resolve(qualifier: str, aliases: dict[str, str], sole: str | None) -> str | None:
    """Which table a column qualifier refers to.

    An unqualified column is attributed to `sole` when exactly one candidate table
    is in play, and to nothing when the query is ambiguous — an unqualified
    `deleted_at` in a two-table join guards whichever table the engine binds it to,
    and the verifier must not guess which.
    """
    if not qualifier:
        return sole
    return aliases.get(qualifier.lower())


def _is_null_guarded(tree: exp.Expression, column: str) -> set[str]:
    """Tables for which `column IS NULL` is asserted, NOT negated.

    `IS NOT NULL` parses as `Not(Is(...))`, so the parent check is what separates
    the rule from its inverse.

    Each guard is resolved in the SELECT that contains it, not against the whole
    query. Excluding deleted rows in a CTE — `WITH live_orders AS (SELECT * FROM
    orders WHERE deleted_at IS NULL)` — is a correct and unusual way to satisfy
    this rule, and it is one of the accept-side probes precisely because a
    verifier is easy to write in a way that rejects it. An unqualified column is
    attributed to the enclosing scope's single soft-delete table; where that scope
    has two, it is attributed to neither, because the verifier must not guess
    which one the engine binds it to.
    """
    guarded = set()
    for node in tree.find_all(exp.Is):
        if not isinstance(node.expression, exp.Null):
            continue
        if isinstance(node.parent, exp.Not):
            continue
        target = node.this
        if not (isinstance(target, exp.Column) and target.name.lower() == column):
            continue

        scope = node.parent_select or tree
        in_scope = [t for t in SOFT_DELETE_TABLES if t in _tables(scope)]
        resolved = _resolve(
            (target.table or "").lower(),
            _alias_map(scope),
            in_scope[0] if len(in_scope) == 1 else None,
        )
        if resolved is not None:
            guarded.add(resolved)
    return guarded


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

    aliases = _alias_map(tree)
    present = [t for t in SOFT_DELETE_TABLES if t in _tables(tree)]
    if not present:
        return None

    sole = present[0] if len(present) == 1 else None
    guarded = {
        table
        for qualifier in _is_null_guarded(tree, "deleted_at")
        if (table := _resolve(qualifier, aliases, sole)) is not None
    }
    missing = [table for table in present if table not in guarded]
    if not missing:
        return None
    return (
        "Soft-deleted rows are not excluded. Rows with deleted_at IS NOT NULL are "
        "deleted and must be excluded, for customers and orders independently. "
        f"Not excluded for: {', '.join(missing)}."
    )


def _literal(node: exp.Expression) -> str | None:
    return node.this.lower() if isinstance(node, exp.Literal) and node.is_string else None


def _excludes_cancelled(tree: exp.Expression) -> bool:
    """Is a predicate present that removes cancelled orders, rather than selecting them?"""
    for node in tree.find_all(exp.NEQ):
        if isinstance(node.this, exp.Column) and node.this.name.lower() == "status":
            if _literal(node.expression) == "cancelled" and not isinstance(node.parent, exp.Not):
                return True
    for node in tree.find_all(exp.EQ):
        # `status = 'completed'` excludes cancelled as a side effect, and that is
        # genuinely enough — the rule is that cancelled must not count.
        if isinstance(node.this, exp.Column) and node.this.name.lower() == "status":
            value = _literal(node.expression)
            if value is not None and value != "cancelled":
                return True
    for node in tree.find_all(exp.In):
        if not (isinstance(node.this, exp.Column) and node.this.name.lower() == "status"):
            continue
        values = {_literal(e) for e in node.expressions}
        negated = isinstance(node.parent, exp.Not)
        if negated and "cancelled" in values:
            return True
        if not negated and values and "cancelled" not in values:
            return True
    return False


def check_cancelled_orders(context: VerifyContext, tree: exp.Expression) -> str | None:
    if "cancelled_orders" not in context.rules:
        return None
    if _excludes_cancelled(tree):
        return None
    return "Cancelled orders are not excluded. status = 'cancelled' must not count."


def _excludes_internal(tree: exp.Expression) -> bool:
    """`NOT is_internal`, `is_internal = FALSE`, or `is_internal IS FALSE`.

    A bare `WHERE c.is_internal` selects exactly the accounts the rule exists to
    remove, and used to satisfy it.
    """
    for node in tree.find_all(exp.Not):
        target = node.this
        if isinstance(target, exp.Column) and target.name.lower() == "is_internal":
            return True
    for node in tree.find_all(exp.EQ, exp.Is):
        if not (isinstance(node.this, exp.Column) and node.this.name.lower() == "is_internal"):
            continue
        value = node.expression
        if isinstance(value, exp.Boolean) and value.this is False:
            return True
    return False


def check_internal_accounts(context: VerifyContext, tree: exp.Expression) -> str | None:
    if "internal_accounts" not in context.rules:
        return None
    if _excludes_internal(tree):
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
