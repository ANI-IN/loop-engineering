import re

import sqlglot

from loopeng.gold.patterns import CURRENCY_RULES, PATTERNS
from loopeng.warehouse.schema import load_semantic_model

# Words that would hand the model an L3 rule inside an L0 prompt. If a pattern
# cannot be phrased without one of these, the pattern is wrong, not the list.
RULE_LEAK_PATTERN = re.compile(
    r"cancell?ed|deleted|soft.delete|internal|test.account|exclud|convert|"
    r"currency|minor.unit|fan.out|duplicat|distinct",
    re.IGNORECASE,
)


def _by_key(key):
    return next(p for p in PATTERNS if p.key == key)


def _rendered_questions():
    for pattern in PATTERNS:
        for params in pattern.params:
            yield pattern.key, pattern.question.format(**params)


# ---- the leak test: the biggest risk in these tasks -------------------------


def test_questions_do_not_leak_the_rules():
    """THE test for these tasks. The build derives questions from SQL, and the
    natural phrasing of pattern 5 is "net revenue in March, excluding cancelled
    orders and internal test accounts, converted to USD". That hands the model every
    L3 rule inside the L0 prompt: the two levels stop differing, both score the same,
    and the dial chart measures nothing while looking exactly as it should.

    Questions are phrased the way a business user asks. The rules live in
    semantic_model.yaml and are rendered at L3 only.
    """
    for key, question in _rendered_questions():
        leak = RULE_LEAK_PATTERN.search(question)
        assert not leak, (
            f"{key} leaks the rule word {leak.group(0)!r} into an L0 prompt: {question}"
        )


def test_the_leak_pattern_catches_the_phrasing_it_exists_to_catch():
    """A ban list that matches nothing would pass the test above silently."""
    tempting = (
        "What was net revenue in March, excluding cancelled orders?",
        "Total revenue converted to USD",
        "Orders from customers that are not internal test accounts",
        "Count distinct orders after the fan-out",
        "Revenue ignoring soft-deleted rows",
        "Sum in minor units by currency",
    )
    for phrasing in tempting:
        assert RULE_LEAK_PATTERN.search(phrasing), f"ban list misses: {phrasing}"


def test_questions_render_without_leftover_placeholders():
    for key, question in _rendered_questions():
        assert "{" not in question and "}" not in question, key


def test_questions_are_unique():
    """Two items with the same question text would be the same item twice."""
    questions = [question for _, question in _rendered_questions()]
    assert len(set(questions)) == len(questions)


# ---- structure --------------------------------------------------------------


def test_ten_patterns_exist():
    assert len(PATTERNS) == 10
    assert len({pattern.key for pattern in PATTERNS}) == 10


def test_every_pattern_has_five_parameterisations():
    for pattern in PATTERNS:
        assert len(pattern.params) == 5, f"{pattern.key} has {len(pattern.params)}"


def test_fifty_items_in_total():
    assert sum(len(pattern.params) for pattern in PATTERNS) == 50


def test_all_sql_parses_for_every_parameterisation():
    for pattern in PATTERNS:
        for params in pattern.params:
            sqlglot.parse_one(pattern.gold_sql.format(**params), read="duckdb")
            if pattern.naive_sql is not None:
                sqlglot.parse_one(pattern.naive_sql.format(**params), read="duckdb")
            for naive_sql in pattern.naive_sql_by_rule.values():
                sqlglot.parse_one(naive_sql.format(**params), read="duckdb")


# ---- the L0 floor -----------------------------------------------------------


def test_pattern_one_requires_no_rules():
    """Without a rule-free pattern L0 sits at 0% by construction and the dial chart
    is rigged rather than measured. This is the floor, and it is load-bearing."""
    p1 = _by_key("p01_product_count")
    assert p1.rules == ()
    assert p1.naive_sql is None
    assert p1.naive_sql_by_rule == {}


def test_exactly_one_pattern_is_rule_free():
    rule_free = [pattern.key for pattern in PATTERNS if not pattern.rules]
    assert rule_free == ["p01_product_count"]


def test_every_other_pattern_declares_rules_and_a_composite_naive():
    for pattern in PATTERNS:
        if pattern.key == "p01_product_count":
            continue
        assert pattern.rules, f"{pattern.key} declares no rules"
        assert pattern.naive_sql is not None, f"{pattern.key} has no composite naive"


# ---- currency scoping -------------------------------------------------------


def test_currency_items_are_jpy_scoped():
    """Ignoring the currency rule moves gross revenue +49.25% at JPY grain and exactly
    0.00% at USD grain. A USD-scoped currency item has a naive answer bit-identical to
    gold and cannot discriminate at all; a whole-warehouse one moves only -2.33%,
    weaker than every other rule. Measured 2026-07-29."""
    for pattern in PATTERNS:
        if not (set(pattern.rules) & CURRENCY_RULES):
            continue
        for params in pattern.params:
            sql = pattern.gold_sql.format(**params)
            assert "'JPY'" in sql, f"{pattern.key} requires a currency rule but is not JPY-scoped"
            # The scope clause must admit only JPY, or JPY and EUR — never USD.
            assert "IN ('EUR', 'JPY')" in sql or "= 'JPY'" in sql, (
                f"{pattern.key} must be scoped to JPY or JPY+EUR"
            )


def test_currency_rules_travel_together():
    """multi_currency and minor_units are one SQL change — the declared factor versus
    a naive /100 — so a pattern needing one needs the other."""
    for pattern in PATTERNS:
        overlap = set(pattern.rules) & CURRENCY_RULES
        assert overlap in ({}, set(), CURRENCY_RULES), (
            f"{pattern.key} declares {sorted(overlap)} but not the pair"
        )


def test_the_currency_pair_shares_one_naive_variant():
    for pattern in PATTERNS:
        covered = set(pattern.naive_sql_by_rule) & CURRENCY_RULES
        assert len(covered) <= 1, f"{pattern.key} stores two variants for one SQL change"


# ---- declared equals enforced -----------------------------------------------


def test_declared_rules_all_exist_in_the_semantic_model():
    """A pattern claiming a rule the YAML does not define is the
    declared-versus-enforced defect in miniature."""
    known = set(load_semantic_model()["rules"])
    for pattern in PATTERNS:
        assert set(pattern.rules) <= known, f"{pattern.key} names an unknown rule"
        assert set(pattern.naive_sql_by_rule) <= known, f"{pattern.key} names an unknown rule"


def test_every_required_rule_has_a_naive_variant():
    for pattern in PATTERNS:
        missing = set(pattern.rules) - set(pattern.naive_sql_by_rule)
        if missing & CURRENCY_RULES and set(pattern.naive_sql_by_rule) & CURRENCY_RULES:
            missing -= CURRENCY_RULES
        assert not missing, f"{pattern.key} requires {sorted(missing)} with no naive variant"


def test_naive_variants_differ_from_gold_sql_textually():
    """A variant identical to the gold SQL would silently pass the discrimination
    check by comparing gold against itself."""
    for pattern in PATTERNS:
        for params in pattern.params:
            gold = pattern.gold_sql.format(**params)
            for rule, naive_sql in pattern.naive_sql_by_rule.items():
                assert naive_sql.format(**params) != gold, (
                    f"{pattern.key}/{rule} naive SQL is identical to gold"
                )


def test_only_pattern_six_is_order_sensitive():
    from loopeng.gold.compare import is_order_sensitive

    ordered = {
        pattern.key
        for pattern in PATTERNS
        if is_order_sensitive(pattern.gold_sql.format(**pattern.params[0]))
    }
    assert ordered == {"p06_top_products"}
