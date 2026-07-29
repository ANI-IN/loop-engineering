from decimal import Decimal

from loopeng.gold.compare import ABS_TOL, REL_TOL, is_order_sensitive, rows_equal

# ---- ordering ---------------------------------------------------------------


def test_order_insensitive_by_default():
    assert rows_equal([(1,), (2,)], [(2,), (1,)], order_sensitive=False)


def test_order_matters_when_gold_says_so():
    assert not rows_equal([(1,), (2,)], [(2,), (1,)], order_sensitive=True)
    assert rows_equal([(1,), (2,)], [(1,), (2,)], order_sensitive=True)


def test_order_sensitivity_is_detected_from_the_ast():
    assert is_order_sensitive("SELECT a FROM t ORDER BY a")
    assert not is_order_sensitive("SELECT a FROM t")


def test_a_nested_order_by_does_not_make_the_result_ordered():
    """A string search for 'ORDER BY' gets this wrong. The outer query decides."""
    sql = "SELECT x FROM (SELECT a AS x FROM t ORDER BY a LIMIT 5)"
    assert not is_order_sensitive(sql)


def test_the_word_order_in_a_table_name_is_not_an_order_by():
    assert not is_order_sensitive("SELECT COUNT(*) FROM orders")


def test_unparseable_sql_is_not_order_sensitive():
    assert not is_order_sensitive("this is not sql at all ((")


# ---- shape ------------------------------------------------------------------


def test_duplicates_are_multiset_not_set():
    """Collapsing duplicates would let a wrong query with a stray DISTINCT pass."""
    assert not rows_equal([(1,), (1,)], [(1,)], order_sensitive=False)


def test_row_shape_mismatch_fails():
    assert not rows_equal([(1, 2)], [(1,)], order_sensitive=False)


def test_empty_results_are_equal_to_each_other():
    assert rows_equal([], [], order_sensitive=False)
    assert not rows_equal([], [(1,)], order_sensitive=False)


# ---- NULL is explicit, not incidental ---------------------------------------


def test_null_equals_null():
    """SQL says NULL != NULL. Result comparison wants the opposite, and leaving it
    implicit silently fails every item where a region has no orders."""
    assert rows_equal([(None,)], [(None,)], order_sensitive=False)
    assert rows_equal([(1, None)], [(1, None)], order_sensitive=False)


def test_null_is_not_zero():
    """None means "no row matched"; 0 means "matched, summed to zero". Treating them
    as equal hides an entire class of wrong query."""
    assert not rows_equal([(None,)], [(0,)], order_sensitive=False)
    assert not rows_equal([(0,)], [(None,)], order_sensitive=False)


def test_null_is_not_an_empty_string():
    assert not rows_equal([(None,)], [("",)], order_sensitive=False)


def test_nulls_sort_stably_in_a_multiset():
    assert rows_equal(
        [(None,), (1,), (None,)], [(1,), (None,), (None,)], order_sensitive=False
    )
    assert not rows_equal([(None,), (1,)], [(None,), (None,)], order_sensitive=False)


# ---- tolerance is RELATIVE --------------------------------------------------


def test_small_values_tolerate_small_drift():
    assert rows_equal([(1.0000001,)], [(1.0,)], order_sensitive=False)
    assert not rows_equal([(1.01,)], [(1.0,)], order_sensitive=False)


def test_large_sums_tolerate_float_association_drift():
    """The reason tolerance is relative rather than absolute, made concrete.

    Gross revenue over this warehouse is ~3.12e6 summed from ~3600 doubles. Worst-case
    association drift is n * eps * sum ~= 2.5e-6 — larger than 1e-6, so re-associating
    the same addends under a different join plan can move the total past an absolute
    1e-6 threshold. Two correct queries would then compare unequal and the sweep would
    record a model failure that never happened. The same drift is 1e-12 relative.
    """
    gold = 3_123_493.82
    drift = 3e-6  # above the absolute threshold, far below the relative one
    drifted = gold + drift

    # An absolute-tolerance implementation rejects this pair. That is the bug.
    assert abs(drifted - gold) > 1e-6
    # A relative one accepts it, because 3e-6 on 3.12e6 is ~1e-12 relative.
    assert abs(drifted - gold) / gold < REL_TOL
    assert rows_equal([(gold,)], [(drifted,)], order_sensitive=False)


def test_a_genuinely_wrong_large_answer_still_fails():
    """Relative tolerance must not become a licence to be wrong by a lot. The
    tightest naive variant in this gold set differs from gold by 7.18%, so the gap
    between what tolerance forgives (1e-4) and what the sweep measures is roughly
    three orders of magnitude."""
    assert not rows_equal([(3_123_493.82,)], [(3_050_869.26,)], order_sensitive=False)
    assert not rows_equal([(1_000_000.0,)], [(1_001_000.0,)], order_sensitive=False)


def test_display_precision_differences_are_not_wrong_answers():
    """The artefact that widening the tolerance exists to remove. The gold SQL rounds
    and models generally do not, so a correct query returns 688.0023410828026 where
    gold holds 688.0. Under a 1e-6 tolerance that scored as a silent error; measured
    on the first Phase 1 trap, 7 of 35 apparent silent errors were exactly this."""
    assert rows_equal([(688.0023410828026,)], [(688.0,)], order_sensitive=False)
    assert rows_equal([(0.09090909361839294,)], [(0.090909,)], order_sensitive=False)
    assert rows_equal([(642.9123163822526,)], [(642.91,)], order_sensitive=False)


def test_near_zero_needs_the_absolute_floor():
    """Relative tolerance degenerates at zero: rel_tol * max(|a|, |b|) is zero when
    both are, so nothing but exact equality would pass without an absolute floor."""
    assert rows_equal([(0.0,)], [(0.0,)], order_sensitive=False)
    assert rows_equal([(0.0,)], [(1e-12,)], order_sensitive=False)
    assert not rows_equal([(0.0,)], [(0.5,)], order_sensitive=False)


def test_the_two_tolerances_are_distinguishable_constants():
    """REL_TOL is pinned between two measurements: it must exceed the largest
    display-rounding artefact (6.02e-06) and stay below the tightest naive-variant
    margin (6.06e-05). One order of magnitude of room, so the value is not free."""
    assert REL_TOL == 1e-5
    assert 6.02e-6 < REL_TOL < 6.06e-5
    assert 0 < ABS_TOL < REL_TOL


# ---- type coercion across Decimal, float, int -------------------------------


def test_decimal_equals_float():
    """DuckDB returns DECIMAL from some aggregates and DOUBLE from others, and
    Decimal('100.00') == 100.0 is False in Python. Left unnormalised, a correct
    query fails against gold purely on the type the planner happened to pick."""
    assert rows_equal([(Decimal("100.00"),)], [(100.0,)], order_sensitive=False)
    assert rows_equal([(100.0,)], [(Decimal("100.00"),)], order_sensitive=False)


def test_decimal_equals_int():
    assert rows_equal([(Decimal("42"),)], [(42,)], order_sensitive=False)


def test_decimals_of_different_scale_are_equal():
    assert rows_equal([(Decimal("100.0"),)], [(Decimal("100.00"),)], order_sensitive=False)


def test_int_equals_float():
    assert rows_equal([(42,)], [(42.0,)], order_sensitive=False)


def test_decimal_still_fails_when_actually_different():
    assert not rows_equal([(Decimal("100.00"),)], [(101.0,)], order_sensitive=False)


def test_mixed_numeric_types_sort_together_in_a_multiset():
    """If Decimal sorted as a string and float as a number, the multiset pairing
    would be wrong and two equal results would compare unequal."""
    assert rows_equal(
        [(Decimal("2.00"),), (1.0,)],
        [(1,), (2.0,)],
        order_sensitive=False,
    )


def test_booleans_do_not_equal_their_integer_forms():
    """True == 1 in Python. A BOOLEAN column and an INTEGER column are different
    answers, and DuckDB returns bool for one and int for the other."""
    assert not rows_equal([(True,)], [(1,)], order_sensitive=False)
    assert rows_equal([(True,)], [(True,)], order_sensitive=False)
    assert not rows_equal([(True,)], [(False,)], order_sensitive=False)


def test_strings_are_compared_exactly():
    assert rows_equal([("EMEA",)], [("EMEA",)], order_sensitive=False)
    assert not rows_equal([("EMEA",)], [("emea",)], order_sensitive=False)


def test_a_number_does_not_equal_its_string_form():
    """Otherwise a query returning '100' passes against gold's 100."""
    assert not rows_equal([(100,)], [("100",)], order_sensitive=False)
