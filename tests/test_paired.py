"""McNemar, and the discipline of not turning a directional result into a number."""

from loopeng.paired import CLUSTERING_CAVEAT, PairedComparison, compare


def test_only_discordant_pairs_carry_information():
    """Items both arms got right, or both got wrong, say nothing about which is
    better. Two tables with wildly different agreement give the same p-value when
    their discordant counts match."""
    a = PairedComparison(both_correct=40, only_a_correct=8, only_b_correct=1, both_wrong=1)
    b = PairedComparison(both_correct=1, only_a_correct=8, only_b_correct=1, both_wrong=40)
    assert a.p_value == b.p_value
    assert a.n_discordant == b.n_discordant == 9


def test_no_discordant_pairs_gives_no_evidence_not_certainty():
    """p=1.0 would read as a measured result. There is simply no evidence."""
    comparison = PairedComparison(both_correct=25, only_a_correct=0, only_b_correct=0,
                                  both_wrong=25)
    assert comparison.p_value is None
    assert "no evidence" in comparison.render()


def test_a_lopsided_split_is_significant():
    comparison = PairedComparison(both_correct=20, only_a_correct=12, only_b_correct=1,
                                  both_wrong=5)
    assert comparison.p_value < 0.05


def test_an_even_split_is_not():
    comparison = PairedComparison(both_correct=20, only_a_correct=6, only_b_correct=5,
                                  both_wrong=5)
    assert comparison.p_value > 0.05
    assert "not distinguishable" in comparison.render()


def test_the_exact_test_matches_a_hand_computed_case():
    """b=1, c=5: two-sided exact = 2 * P(X<=1) with X~Bin(6, 0.5) = 2 * 7/64."""
    comparison = PairedComparison(both_correct=0, only_a_correct=1, only_b_correct=5,
                                  both_wrong=0)
    assert abs(comparison.p_value - 2 * (7 / 64)) < 1e-12


def test_the_verdict_is_directional_and_never_quotes_a_gap():
    """The on-screen wording is "worse; we cannot put a number on how much". A
    percentage-point difference here would be exactly the overstated precision this
    project exists to avoid."""
    comparison = PairedComparison(
        both_correct=20, only_a_correct=12, only_b_correct=1, both_wrong=5,
        label_a="L3", label_b="L0",
    )
    verdict = comparison.render()
    assert "worse" in verdict
    assert "cannot put a number on how much" in verdict
    assert "%" not in verdict


def test_the_clustering_caveat_travels_with_the_result():
    """McNemar assumes independent pairs; 10 clusters of 5 are not independent, so
    the p-value is optimistic and has to say so wherever it is reported."""
    comparison = PairedComparison(both_correct=20, only_a_correct=12, only_b_correct=1,
                                  both_wrong=5)
    payload = comparison.as_dict()
    assert payload["caveat"] == CLUSTERING_CAVEAT
    assert "are not" in CLUSTERING_CAVEAT
    assert "optimistic" in CLUSTERING_CAVEAT


def test_compare_builds_the_table_from_two_maps():
    a = {"i1": True, "i2": True, "i3": False, "i4": False}
    b = {"i1": True, "i2": False, "i3": True, "i4": False}
    comparison = compare(a, b, label_a="L3", label_b="L0")
    assert (comparison.both_correct, comparison.only_a_correct) == (1, 1)
    assert (comparison.only_b_correct, comparison.both_wrong) == (1, 1)
    assert comparison.n_pairs == 4


def test_an_item_only_one_arm_answered_is_not_a_pair():
    """Treating a missing answer as wrong would invent evidence."""
    a = {"i1": True, "i2": True}
    b = {"i1": False}
    comparison = compare(a, b)
    assert comparison.n_pairs == 1
