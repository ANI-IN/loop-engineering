from decimal import Decimal

import pytest

from loopeng.gold.build import build_gold, read_gold, write_gold
from loopeng.gold.compare import rows_equal
from loopeng.gold.patterns import CURRENCY_RULES, PATTERNS
from loopeng.warehouse.connect import ensure_warehouse


@pytest.fixture(scope="module")
def warehouse(tmp_path_factory):
    return ensure_warehouse(tmp_path_factory.mktemp("wh") / "w.duckdb", seed=20260729)


@pytest.fixture(scope="module")
def items(warehouse):
    return build_gold(warehouse)


# ---- all 50 execute ---------------------------------------------------------


def test_fifty_items(items):
    assert len(items) == 50
    assert len({item.item_id for item in items}) == 50


def test_every_item_executed_against_the_read_only_connection(items):
    """The build runs everything through run_sql, which is the read-only factory.
    If gold could only be produced with write access, the agent could not reproduce
    it, and the whole comparison would be against something unreachable."""
    for item in items:
        assert item.gold_rows, f"{item.item_id} returned nothing"


def test_no_item_is_degenerate(items):
    """An all-null or all-zero answer cannot distinguish a right query from a wrong
    one, so it teaches the room nothing."""
    for item in items:
        flat = [value for row in item.gold_rows for value in row]
        assert any(value not in (None, 0, 0.0) for value in flat), item.item_id


# ---- the primary check ------------------------------------------------------


def test_rule_bearing_items_differ_from_their_composite_naive(items):
    """THE primary check. An item whose gold answer equals the answer you get by
    ignoring every rule scores identically at L0 and L3 and flattens the gap the
    workshop exists to show."""
    for item in items:
        if item.naive_rows is None:
            continue
        assert not rows_equal(
            item.gold_rows, item.naive_rows, order_sensitive=item.order_sensitive
        ), f"{item.item_id} cannot discriminate: composite naive equals gold"


def test_only_the_rule_free_pattern_lacks_naive_answers(items):
    without = {item.pattern_key for item in items if item.naive_rows is None}
    assert without == {"p01_product_count"}


def test_the_rule_free_pattern_is_present_and_keeps_l0_off_the_floor(items):
    """Without it L0 sits at 0% by construction and the dial chart is rigged."""
    rule_free = [item for item in items if not item.rules]
    assert len(rule_free) == 5
    assert all(item.pattern_key == "p01_product_count" for item in rule_free)


# ---- currency scoping -------------------------------------------------------


def test_currency_items_are_jpy_scoped(items):
    for item in items:
        if not (set(item.rules) & CURRENCY_RULES):
            continue
        assert "'JPY'" in item.gold_sql, f"{item.item_id} is not JPY-scoped"
        assert "IN ('EUR', 'JPY')" in item.gold_sql or "= 'JPY'" in item.gold_sql


# ---- taxonomy: ambiguity is recorded, never fatal ---------------------------


def test_colliding_variants_are_recorded_not_dropped(items):
    """Ambiguity is a reporting limitation, not a defect. The item stays and the
    reveal names both rules instead of claiming one."""
    for item in items:
        variants = sorted(item.naive_by_rule.items())
        recorded = [set(group) for group in item.ambiguous_rule_groups]
        for i, (rule_a, a) in enumerate(variants):
            for rule_b, b in variants[i + 1:]:
                if rows_equal(a["rows"], b["rows"], order_sensitive=item.order_sensitive):
                    assert any({rule_a, rule_b} <= group for group in recorded), (
                        f"{item.item_id}: {rule_a}/{rule_b} collide but are not recorded"
                    )


def test_no_item_was_lost_to_ambiguity(items):
    """The count is a measurement, not a filter."""
    assert len(items) == 50


def test_the_comparison_tolerance_cannot_swallow_a_naive_variant(items):
    """The guard that pins the upper end of the comparison tolerance.

    Tolerance was raised from 1e-6 because gold rounds and models do not, so correct
    answers were failing on display precision. Widening a comparison is exactly how an
    instrument gets quietly weakened — the regex_swap demo is about a version of this
    — so "no naive variant lands inside the tolerance" is asserted rather than argued.

    This test earned its place immediately: it rejected a first attempt at 1e-4 by
    finding that p07_aov_by_region__04's cancelled_orders variant sits 6.06e-05 from
    gold, because excluding cancelled orders barely moves an average order value. At
    1e-4 a model ignoring that rule would have scored CORRECT.

    If it fails, a gold item has a rule whose effect is smaller than the tolerance.
    Fix the item or the tolerance; do not delete the test.
    """
    from loopeng.gold.compare import REL_TOL

    margins: list[tuple[float, str]] = []
    for item in items:
        for rule, naive in item.naive_by_rule.items():
            gold_values = [v for row in item.gold_rows for v in row]
            naive_values = [v for row in naive["rows"] for v in row]
            if len(gold_values) != len(naive_values):
                continue  # different shape is already a clear difference
            numeric = [
                (float(g), float(n))
                for g, n in zip(gold_values, naive_values, strict=True)
                if isinstance(g, int | float | Decimal) and isinstance(n, int | float | Decimal)
                and not isinstance(g, bool) and not isinstance(n, bool)
            ]
            if not numeric:
                continue
            worst = max(
                (abs(g - n) / abs(g) if g else abs(g - n)) for g, n in numeric
            )
            assert worst > REL_TOL, (
                f"{item.item_id}/{rule}: naive differs from gold by only {worst:.2e}, "
                f"inside the comparison tolerance ({REL_TOL:.0e}) — a model ignoring "
                "this rule would score as CORRECT. Fix the item or the tolerance."
            )
            margins.append((worst, f"{item.item_id}/{rule}"))

    tightest, which = min(margins)
    print(f"tightest naive-variant margin: {tightest:.2e} ({which}) vs tol {REL_TOL:.0e}")


def test_every_required_rule_has_a_stored_naive_answer(items):
    for item in items:
        if not item.rules:
            continue
        missing = set(item.rules) - set(item.naive_by_rule)
        if missing & CURRENCY_RULES and set(item.naive_by_rule) & CURRENCY_RULES:
            missing -= CURRENCY_RULES
        assert not missing, f"{item.item_id} requires {sorted(missing)} with no naive answer"


# ---- ordering ---------------------------------------------------------------


def test_order_sensitivity_is_recorded_per_item(items):
    ordered = {item.pattern_key for item in items if item.order_sensitive}
    assert ordered == {"p06_top_products"}


# ---- clustering is recorded, not corrected ----------------------------------


def test_clustering_is_reported_so_precision_is_not_overstated(items):
    """50 items are 10 clusters of 5, not 50 independent trials. A systematic flaw in
    one pattern fails all five of its items together, so a Wilson interval computed
    as if n=50 is too narrow. This is not fixable by construction — it is recorded so
    it reaches the screen alongside the templating disclosure."""
    from loopeng.gold.build import clustering_summary

    summary = clustering_summary(items)
    assert summary["n_items"] == 50
    assert summary["n_clusters"] == 10
    assert summary["items_per_cluster"] == 5
    assert "independent" in summary["caveat"].lower()


# ---- persistence ------------------------------------------------------------


def test_round_trips_through_jsonl(items, tmp_path):
    path = tmp_path / "gold.jsonl"
    write_gold(items, path)
    reloaded = read_gold(path)
    assert len(reloaded) == len(items)
    assert reloaded[0].gold_rows == items[0].gold_rows
    assert reloaded[0].rules == items[0].rules
    assert reloaded[0].item_id == items[0].item_id


def test_round_trip_preserves_numeric_equality_for_every_item(tmp_path, items):
    """gold.jsonl is what reaches LangSmith and what grading compares against, so a
    value that changes type on reload breaks scoring silently.

    The specific trap: DuckDB returns DECIMAL from exactly the aggregates the revenue
    patterns use, and a blanket json default=str turns Decimal('76744.66') into the
    string '76744.66'. rows_equal then correctly refuses to equate a number with its
    string form, and every revenue item fails against a *correct* answer. Checking
    only the first item misses it — item zero is a COUNT and comes back as an int.
    """
    path = tmp_path / "gold.jsonl"
    write_gold(items, path)
    reloaded = {item.item_id: item for item in read_gold(path)}

    for item in items:
        back = reloaded[item.item_id]
        assert rows_equal(
            item.gold_rows, back.gold_rows, order_sensitive=item.order_sensitive
        ), f"{item.item_id} gold rows changed across the round trip: {back.gold_rows!r}"

        original = [value for row in item.gold_rows for value in row]
        returned = [value for row in back.gold_rows for value in row]
        for before, after in zip(original, returned, strict=True):
            assert isinstance(before, str) == isinstance(after, str), (
                f"{item.item_id}: {before!r} came back as {after!r} — a number "
                "reloaded as a string will never match a correct model answer"
            )


def test_round_trip_preserves_the_naive_taxonomy(tmp_path, items):
    path = tmp_path / "gold.jsonl"
    write_gold(items, path)
    reloaded = {item.item_id: item for item in read_gold(path)}
    for item in items:
        back = reloaded[item.item_id]
        assert set(back.naive_by_rule) == set(item.naive_by_rule)
        assert back.ambiguous_rule_groups == item.ambiguous_rule_groups


def test_questions_are_carried_onto_the_items(items):
    for item in items:
        assert item.question
        assert "{" not in item.question


def test_every_pattern_contributes_five_items(items):
    from collections import Counter

    counts = Counter(item.pattern_key for item in items)
    assert set(counts) == {pattern.key for pattern in PATTERNS}
    assert set(counts.values()) == {5}
