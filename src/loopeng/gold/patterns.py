"""The ten gold SQL patterns, graded by how many business rules each requires.

SQL is written first and the question derived from what it returns — never a
question written and its SQL guessed.

**Questions are phrased the way a business user asks, and that is load-bearing.**
The tempting phrasing for pattern 5 is "net revenue in March, excluding cancelled
orders and internal test accounts, converted to USD". That hands the model every L3
rule inside the L0 prompt: both levels then score the same, the gap closes, and the
dial chart measures nothing while looking exactly as it should. The rules live in
semantic_model.yaml and are rendered at L3 only. A test bans the vocabulary.

Each pattern carries a *composite* naive query — every rule ignored, which is what
the discrimination check compares against — and one variant per rule, ignoring that
rule alone. The variants feed the error taxonomy, which can then name the rule that
was dropped rather than reporting only total failure.

All three forms are generated from a single builder per pattern rather than written
out by hand. Thirty-odd near-identical queries maintained separately is a place for
a silent divergence to live: a filter dropped from gold but left in a variant would
make an item look discriminating when it is comparing two spellings of the same
query. Here the gold SQL and every variant come from one expression, so they cannot
drift apart.

Items requiring the currency rules are scoped to JPY and EUR. Measured 2026-07-29:
ignoring currency moves gross revenue +49.25% at JPY grain, -7.18% at JPY+EUR, and
exactly 0.00% at USD grain — a USD-scoped currency item cannot discriminate at all.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from loopeng.warehouse.schema import CATEGORIES, MONTHS, REGIONS

# Folds the FX rate and the minor-unit scale into one factor. Declared in
# semantic_model.yaml, so at L0 the model does not know it is needed.
USD_FACTOR_SQL = (
    "CASE {alias}currency WHEN 'USD' THEN 0.01 WHEN 'EUR' THEN 0.0108 "
    "WHEN 'JPY' THEN 0.0067 END"
)

# The naive form of both currency rules: treat everything as two-decimal, skip
# conversion entirely. This is the single wrong answer the taxonomy recognises.
NAIVE_FACTOR_SQL = "0.01"

# One SQL change, so one naive variant, and the JPY-scoping rule applies to either.
CURRENCY_RULES = frozenset({"multi_currency", "minor_units"})

# Scope for every currency-bearing item. EUR is included so the multi-currency rule
# is exercised as mixing and not only as JPY's zero decimal places.
CURRENCY_SCOPE = "o.currency IN ('EUR', 'JPY')"

_MONTH_NAMES = {
    "2025-01-01": "January 2025",
    "2025-02-01": "February 2025",
    "2025-03-01": "March 2025",
    "2025-04-01": "April 2025",
    "2025-05-01": "May 2025",
}


@dataclass(frozen=True)
class Pattern:
    key: str
    question: str
    gold_sql: str
    # Every rule ignored at once. The primary discrimination check compares against
    # this; an item matching it is regenerated. None for the rule-free pattern.
    naive_sql: str | None = None
    # Rule -> that rule alone ignored. Feeds the taxonomy; collisions cost nothing.
    naive_sql_by_rule: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    params: tuple[dict[str, object], ...] = ()
    rules: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Shared SQL fragments, each switchable by which rules are being ignored.
# ---------------------------------------------------------------------------


def _filters(ignored: frozenset[str]) -> list[str]:
    """The three filter rules, as predicates that vanish when the rule is ignored."""
    parts = []
    if "soft_delete" not in ignored:
        # The rule applies to customers and orders independently.
        parts.append("o.deleted_at IS NULL")
        parts.append("c.deleted_at IS NULL")
    if "cancelled_orders" not in ignored:
        parts.append("o.status <> 'cancelled'")
    if "internal_accounts" not in ignored:
        parts.append("NOT c.is_internal")
    return parts


def _customer_filters(ignored: frozenset[str]) -> list[str]:
    """The customers-only form, for patterns that never join orders."""
    parts = []
    if "soft_delete" not in ignored:
        parts.append("deleted_at IS NULL")
    if "internal_accounts" not in ignored:
        parts.append("NOT is_internal")
    return parts


def _factor(ignored: frozenset[str], alias: str = "o.") -> str:
    if ignored & CURRENCY_RULES:
        return NAIVE_FACTOR_SQL
    return USD_FACTOR_SQL.format(alias=alias)


def _where(*clauses: Iterable[str] | str) -> str:
    parts: list[str] = []
    for clause in clauses:
        if isinstance(clause, str):
            parts.append(clause)
        else:
            parts.extend(clause)
    return " AND ".join(parts)


def _build(key, question, sql_for, rules, params) -> Pattern:
    """Generate gold, composite naive and per-rule variants from one builder."""
    rules = tuple(rules)
    gold = sql_for(frozenset())
    naive = sql_for(frozenset(rules)) if rules else None

    by_rule: dict[str, str] = {}
    seen_currency = False
    for rule in rules:
        if rule in CURRENCY_RULES:
            # One SQL change: emit a single variant under the first name seen.
            if seen_currency:
                continue
            seen_currency = True
            by_rule[rule] = sql_for(CURRENCY_RULES)
        else:
            by_rule[rule] = sql_for(frozenset({rule}))

    return Pattern(
        key=key,
        question=question,
        gold_sql=gold,
        naive_sql=naive,
        naive_sql_by_rule=MappingProxyType(by_rule),
        params=tuple(params),
        rules=rules,
    )


_CATEGORY_PARAMS = tuple({"category": c} for c in CATEGORIES)
_REGION_PARAMS = tuple({"region": r} for r in REGIONS)
_MONTH_PARAMS = tuple({"month": m, "month_name": _MONTH_NAMES[m]} for m in MONTHS)

_ORDER_JOIN = "FROM orders o JOIN customers c ON c.customer_id = o.customer_id"


# ---------------------------------------------------------------------------
# Pattern 1 — no rules. The L0 floor.
# ---------------------------------------------------------------------------

_p01 = Pattern(
    key="p01_product_count",
    # No rules at all, on purpose: if every item needed the L3 rules, L0 would sit
    # at 0% by construction and the dial chart would be rigged rather than measured.
    question="How many products do we sell in the {category} range?",
    gold_sql="SELECT COUNT(*) FROM products WHERE category = '{category}'",
    naive_sql=None,
    naive_sql_by_rule=MappingProxyType({}),
    params=_CATEGORY_PARAMS,
    rules=(),
)


# ---------------------------------------------------------------------------
# Pattern 2 — orders in a month. Soft delete only.
# ---------------------------------------------------------------------------


def _p02_sql(ignored: frozenset[str]) -> str:
    return (
        f"SELECT COUNT(*) {_ORDER_JOIN} WHERE "
        + _where("date_trunc('month', o.placed_at) = DATE '{month}'", _filters(ignored))
    )


_p02 = _build(
    key="p02_orders_in_month",
    question="How many orders were placed in {month_name}?",
    sql_for=_p02_sql,
    rules=("soft_delete",),
    params=_MONTH_PARAMS,
)


# ---------------------------------------------------------------------------
# Pattern 3 — customers in a region. Soft delete plus internal accounts.
# These two are both "exclude some customers", so this is the pattern most
# likely to produce colliding naive variants. It is kept either way.
# ---------------------------------------------------------------------------


def _p03_sql(ignored: frozenset[str]) -> str:
    return "SELECT COUNT(*) FROM customers WHERE " + _where(
        "region = '{region}'", _customer_filters(ignored)
    )


_p03 = _build(
    key="p03_customers_in_region",
    question="How many customers do we have in {region}?",
    sql_for=_p03_sql,
    rules=("soft_delete", "internal_accounts"),
    params=_REGION_PARAMS,
)


# ---------------------------------------------------------------------------
# Pattern 4 — gross revenue. First pattern carrying the currency rules, so the
# first scoped to JPY+EUR.
# ---------------------------------------------------------------------------


def _p04_sql(ignored: frozenset[str]) -> str:
    return (
        f"SELECT ROUND(SUM(o.amount_minor * {_factor(ignored)}), 2) {_ORDER_JOIN} WHERE "
        + _where(
            "date_trunc('month', o.placed_at) = DATE '{month}'",
            CURRENCY_SCOPE,
            _filters(ignored),
        )
    )


_p04 = _build(
    key="p04_gross_revenue",
    question="What was gross revenue in {month_name} from our euro and yen orders, in US dollars?",
    sql_for=_p04_sql,
    rules=("soft_delete", "cancelled_orders", "internal_accounts", "multi_currency", "minor_units"),
    params=_MONTH_PARAMS,
)


# ---------------------------------------------------------------------------
# Pattern 5 — net revenue. Adds refunds, aggregated per order first because
# orders to refunds is also one-to-many.
# ---------------------------------------------------------------------------


def _p05_sql(ignored: frozenset[str]) -> str:
    if "refunds_net" in ignored:
        amount = "o.amount_minor"
        join = ""
    else:
        amount = "(o.amount_minor - COALESCE(r.refunded, 0))"
        join = " LEFT JOIN (SELECT order_id, SUM(amount_minor) AS refunded FROM refunds " \
               "GROUP BY order_id) r ON r.order_id = o.order_id"
    return (
        f"SELECT ROUND(SUM({amount} * {_factor(ignored)}), 2) {_ORDER_JOIN}{join} WHERE "
        + _where(
            "date_trunc('month', o.placed_at) = DATE '{month}'",
            CURRENCY_SCOPE,
            _filters(ignored),
        )
    )


_p05 = _build(
    key="p05_net_revenue",
    question="What was net revenue in {month_name} from our euro and yen orders, in US dollars?",
    sql_for=_p05_sql,
    rules=(
        "soft_delete",
        "cancelled_orders",
        "internal_accounts",
        "multi_currency",
        "minor_units",
        "refunds_net",
    ),
    params=_MONTH_PARAMS,
)


# ---------------------------------------------------------------------------
# Pattern 6 — top products by units. The only order-sensitive pattern, and the
# one that requires line-grain aggregation done correctly.
# ---------------------------------------------------------------------------


def _p06_sql(ignored: frozenset[str]) -> str:
    return (
        "SELECT p.product_id, SUM(i.qty) AS units "
        "FROM order_items i "
        "JOIN orders o ON o.order_id = i.order_id "
        "JOIN customers c ON c.customer_id = o.customer_id "
        "JOIN products p ON p.product_id = i.product_id WHERE "
        + _where("p.category = '{category}'", _filters(ignored))
        + " GROUP BY p.product_id ORDER BY units DESC, p.product_id LIMIT 5"
    )


_p06 = _build(
    key="p06_top_products",
    question="Which five {category} products sold the most units?",
    sql_for=_p06_sql,
    rules=("soft_delete", "cancelled_orders", "internal_accounts"),
    params=_CATEGORY_PARAMS,
)


# ---------------------------------------------------------------------------
# Pattern 7 — average order value. The fan-out trap: averaging order-level money
# after joining order_items weights each order by its line count.
# ---------------------------------------------------------------------------


def _p07_sql(ignored: frozenset[str]) -> str:
    join = (
        " JOIN order_items i ON i.order_id = o.order_id"
        if "fan_out" in ignored
        else ""
    )
    return (
        f"SELECT ROUND(AVG(o.amount_minor * {_factor(ignored)}), 2) {_ORDER_JOIN}{join} WHERE "
        + _where("c.region = '{region}'", CURRENCY_SCOPE, _filters(ignored))
    )


_p07 = _build(
    key="p07_aov_by_region",
    # "before refunds" names the MEASURE. It does not name the rule: nothing here
    # says how to exclude anything, only which quantity is being asked for. Triage
    # measured what the ambiguity cost — 100% of L3 failures on this pattern netted
    # refunds against 30% at L0, because the L3 prompt renders the refunds rule and
    # the model then nets on a question that never asked.
    question=(
        "What was the average order value in {region} for euro and yen orders, "
        "before refunds, in US dollars?"
    ),
    sql_for=_p07_sql,
    rules=(
        "soft_delete",
        "cancelled_orders",
        "internal_accounts",
        "multi_currency",
        "minor_units",
        "fan_out",
    ),
    params=_REGION_PARAMS,
)


# ---------------------------------------------------------------------------
# Pattern 8 — revenue by category. Category lives on products, so the money must
# come from the line grain. Taking it from orders instead double-counts.
# ---------------------------------------------------------------------------


def _p08_sql(ignored: frozenset[str]) -> str:
    amount = "o.amount_minor" if "fan_out" in ignored else "i.qty * i.unit_price_minor"
    return (
        f"SELECT ROUND(SUM({amount} * {_factor(ignored)}), 2) "
        "FROM order_items i "
        "JOIN orders o ON o.order_id = i.order_id "
        "JOIN customers c ON c.customer_id = o.customer_id "
        "JOIN products p ON p.product_id = i.product_id WHERE "
        + _where("p.category = '{category}'", CURRENCY_SCOPE, _filters(ignored))
    )


_p08 = _build(
    key="p08_revenue_by_category",
    # Same fix: "gross ... before refunds" states the measure, not the rule.
    question=(
        "What was gross revenue from {category} products for euro and yen orders, "
        "before refunds, in US dollars?"
    ),
    sql_for=_p08_sql,
    rules=(
        "soft_delete",
        "cancelled_orders",
        "internal_accounts",
        "multi_currency",
        "minor_units",
        "fan_out",
    ),
    params=_CATEGORY_PARAMS,
)


# ---------------------------------------------------------------------------
# Pattern 9 — refund rate by category. An order with several lines in the same
# category is still one order; dropping the DISTINCT counts it once per line.
# ---------------------------------------------------------------------------


def _p09_sql(ignored: frozenset[str]) -> str:
    order_id = "o.order_id" if "fan_out" in ignored else "DISTINCT o.order_id"
    refunded = (
        "o.order_id" if "fan_out" in ignored else "DISTINCT o.order_id"
    )
    return (
        f"SELECT ROUND(COUNT({refunded}) FILTER ("
        "WHERE EXISTS (SELECT 1 FROM refunds rf WHERE rf.order_id = o.order_id)"
        f") * 1.0 / COUNT({order_id}), 6) "
        "FROM order_items i "
        "JOIN orders o ON o.order_id = i.order_id "
        "JOIN customers c ON c.customer_id = o.customer_id "
        "JOIN products p ON p.product_id = i.product_id WHERE "
        + _where("p.category = '{category}'", _filters(ignored))
    )


_p09 = _build(
    key="p09_refund_rate",
    question="What share of {category} orders ended up with a refund?",
    sql_for=_p09_sql,
    rules=("soft_delete", "cancelled_orders", "internal_accounts", "fan_out"),
    params=_CATEGORY_PARAMS,
)


# ---------------------------------------------------------------------------
# Pattern 10 — repeat-customer rate.
# ---------------------------------------------------------------------------


def _p10_sql(ignored: frozenset[str]) -> str:
    # Scoped to a single month, not the whole year. Measured 2026-07-29: the
    # generator places ~10 orders per customer across 2025, so an all-year repeat
    # rate pins at 1.0, 0.989, 1.0 across regions — gold and naive both round to
    # "everyone", and the item cannot discriminate for any region. That is the
    # pattern being wrong rather than one slice being thin, so it was redefined
    # once rather than reparameterised: no choice of region would have fixed it.
    # Within a month the average customer places ~0.9 orders and the rate lands
    # near 0.3, where the rules move it.
    return (
        "WITH per_customer AS (SELECT c.customer_id, COUNT(*) AS n_orders "
        f"{_ORDER_JOIN} WHERE "
        + _where("date_trunc('month', o.placed_at) = DATE '{month}'", _filters(ignored))
        + " GROUP BY c.customer_id) "
        "SELECT ROUND(COUNT(*) FILTER (WHERE n_orders > 1) * 1.0 / COUNT(*), 6) FROM per_customer"
    )


_p10 = _build(
    key="p10_repeat_customer_rate",
    question="What share of customers placed more than one order in {month_name}?",
    sql_for=_p10_sql,
    rules=("soft_delete", "cancelled_orders", "internal_accounts"),
    params=_MONTH_PARAMS,
)


PATTERNS: tuple[Pattern, ...] = (_p01, _p02, _p03, _p04, _p05, _p06, _p07, _p08, _p09, _p10)
