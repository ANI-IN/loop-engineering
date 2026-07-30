"""The comparison the sweep could not make.

`loopeng.paired` implemented exact McNemar correctly from the start and was wired into
the TRAP demo and the views — and never into the sweep, even though `verify/batch.py`
already builds `{item_id: was_correct}` and cell files retain the per-item detail. So the
sweep could show two bars and could not say whether they differed.

These tests are mostly about what the module REFUSES to say, because that is where a
difference chart does damage.
"""

import pytest

from loopeng.sweep import diff
from loopeng.sweep.charts import delta_chart


def cell(key, *, role="worker", level="L0", mode="loop", replicate=0,
         correct=(), wrong=(), reference=False, complete=True, label=None):
    """A cell file, reduced to what a comparison reads off it."""
    items = [
        {"item_id": item_id, "correct": True, "ran_and_returned": True}
        for item_id in correct
    ] + [
        {"item_id": item_id, "correct": False, "ran_and_returned": True}
        for item_id in wrong
    ]
    body = {
        "key": key, "label": label or key, "role": role, "level": level,
        "mode": mode, "replicate": replicate, "complete": complete, "items": items,
    }
    if reference:
        body["reference"] = True
        body["measured_on"] = "2026-07-29"
        body["paired"] = {row["item_id"]: row["correct"] for row in items}
        del body["items"]
    return body


# ---- the threshold is derived, not picked ------------------------------------


def test_the_minimum_discordant_count_is_computed_from_alpha():
    """With n discordant pairs all one way the two-sided exact p is 2/2**n, so below
    some n no split of the data can be significant. That is a fact about the design and
    is computed rather than typed."""
    assert diff.MIN_DISCORDANT == diff.min_discordant_for_significance(diff.ALPHA)
    n = diff.MIN_DISCORDANT
    assert 2 / (2**n) < diff.ALPHA
    assert 2 / (2 ** (n - 1)) >= diff.ALPHA, "the threshold is not tight"


def test_a_tighter_alpha_demands_more_discordant_pairs():
    assert diff.min_discordant_for_significance(0.001) > diff.MIN_DISCORDANT


# ---- what it refuses to say --------------------------------------------------


def test_a_cross_model_comparison_gets_no_p_value():
    """The guardrail in pre_registration and in the DIAL caption, enforced in the code
    that draws the chart. Haiku is pinned to temperature=0 and Sonnet cannot be, so a
    significance claim across the two would be measuring the asymmetry."""
    haiku = cell("worker_L0_loop_r0", role="worker", correct=list("abcdefghij"))
    sonnet = cell("frontier_L0_one_shot_r0", role="frontier", mode="one_shot",
                  wrong=list("abcdefghij"))

    comparison = diff._build("mode", haiku, sonnet)

    assert comparison.cross_model
    assert comparison.p_value is None
    assert not comparison.distinguishable
    assert "No p-value" in comparison.reading()


def test_a_cross_model_p_value_is_refused_even_when_the_data_would_support_one():
    """The refusal must not be a side effect of thin data. Ten discordant pairs all one
    way would be significant within a model; across models it still says no."""
    haiku = cell("worker_L0_loop_r0", role="worker", correct=list("abcdefghij"))
    sonnet = cell("frontier_L0_loop_r0", role="frontier", wrong=list("abcdefghij"))

    comparison = diff._build("mode", haiku, sonnet)

    assert comparison.n_discordant >= diff.MIN_DISCORDANT
    assert comparison.paired.p_value is not None, "the underlying test DOES have a value"
    assert comparison.p_value is None, "and the Comparison refuses to report it"


def test_too_few_discordant_pairs_says_so_rather_than_showing_a_number():
    a = cell("worker_L0_one_shot_r0", mode="one_shot",
             correct=list("abcdefghij"), wrong=["x"])
    b = cell("worker_L0_loop_r0", correct=list("abcdefghij") + ["x"])

    comparison = diff._build("mode", a, b)

    assert comparison.n_discordant < diff.MIN_DISCORDANT
    assert not comparison.distinguishable
    assert "not distinguishable at this n" in comparison.reading()
    assert "property of the design" in comparison.reading()


def test_no_shared_items_is_reported_rather_than_differenced():
    a = cell("worker_L0_one_shot_r0", mode="one_shot", correct=["a", "b"])
    b = cell("worker_L0_loop_r0", correct=["y", "z"])

    comparison = diff._build("mode", a, b)

    assert comparison.n_pairs == 0
    assert comparison.delta_pp is None
    assert comparison.interval_pp is None
    assert "nothing to pair" in comparison.reading()
    assert "share no answered items" in comparison.reading()


# ---- a diagnostic must not misattribute its own cause ------------------------
#
# Six of the ten comparisons a fresh render produces are Sonnet pairs, and every one
# reported "no shared answered items between … — nothing to pair, so nothing to
# compare". That reads as a fact about the data: these two arms answered disjoint sets.
#
# It is a fact about the freeze. `build_worker_baseline` calls `_freeze(keep_paired=
# True)`; `build_reference` does not, so the stored FRONTIER cells carry no per-item
# outcomes at all and can never be paired with anything. The items overlapped fine when
# they were measured — the outcomes were discarded at freeze time.
#
# Two different facts, and only one of them is fixable. The message has to say which.


def _frozen_without_items(key, **kw):
    """A stored frontier cell as `build_reference` freezes it: no `items`, no `paired`."""
    body = cell(key, role="frontier", reference=True, correct=list("abcde"), **kw)
    body.pop("paired", None)
    return body


def test_a_pair_stripped_at_freeze_time_says_so_rather_than_blaming_the_items():
    a = _frozen_without_items("frontier_L0_one_shot_r0", mode="one_shot")
    b = _frozen_without_items("frontier_L0_loop_r0")

    reading = diff._build("mode", a, b).reading()

    assert "not retained" in reading, reading
    assert "frozen" in reading
    assert "share no answered items" not in reading, (
        "the items overlapped when they were measured; saying they did not is a claim "
        "about the data that the freeze is responsible for"
    )


def test_only_the_side_that_lost_its_items_is_named():
    """A live arm against a stripped stored one: the live side kept everything, and a
    message blaming both would send a reader looking in the wrong file."""
    live = cell("frontier_L0_loop_r0", role="frontier", correct=list("abcde"))
    stored = _frozen_without_items("frontier_L0_one_shot_r0", mode="one_shot")

    reading = diff._build("mode", stored, live).reading()

    assert "REFERENCE frontier_L0_one_shot_r0" in reading
    assert "LIVE frontier_L0_loop_r0" not in reading


def test_the_delta_chart_carries_the_real_cause_too():
    """The row on the chart is what a room reads; the terminal line is not."""
    svg = delta_chart(diff.all_comparisons([
        _frozen_without_items("frontier_L0_one_shot_r0", mode="one_shot"),
        _frozen_without_items("frontier_L0_loop_r0"),
    ]))
    assert "not retained" in svg


# ---- the delta itself --------------------------------------------------------


def test_the_delta_is_signed_and_positive_means_worse():
    """B has more silent errors than A."""
    a = cell("worker_L0_one_shot_r0", mode="one_shot", correct=list("abcdefgh"))
    b = cell("worker_L0_loop_r0", wrong=list("abcdefgh"))

    comparison = diff._build("mode", a, b)

    assert comparison.delta_pp == pytest.approx(100.0)
    assert comparison.distinguishable


def test_the_delta_is_negative_when_the_second_arm_is_better():
    a = cell("worker_L0_one_shot_r0", mode="one_shot", wrong=list("abcdefgh"))
    b = cell("worker_L0_loop_r0", correct=list("abcdefgh"))

    comparison = diff._build("mode", a, b)

    assert comparison.delta_pp == pytest.approx(-100.0)


def test_the_delta_is_paired_not_the_gap_between_the_two_bars():
    """Each bar's rate is over the items THAT cell ran, and the two cells did not run
    the same set. Subtracting the bars mixes a real difference with a difference in
    denominators; the paired delta is over the shared set only."""
    a = cell("worker_L0_one_shot_r0", mode="one_shot",
             correct=["shared1"], wrong=["shared2", "only_in_a"])
    b = cell("worker_L0_loop_r0",
             correct=["shared1", "shared2"], wrong=["only_in_b"])

    comparison = diff._build("mode", a, b)

    assert comparison.n_pairs == 2, "only the shared items are paired"
    assert comparison.delta_pp == pytest.approx(-50.0)


def test_the_interval_is_reported_with_the_delta():
    a = cell("worker_L0_one_shot_r0", mode="one_shot",
             correct=list("abcdefgh"), wrong=list("ijkl"))
    b = cell("worker_L0_loop_r0", wrong=list("abcdefgh"), correct=list("ijkl"))

    lo, hi = diff._build("mode", a, b).interval_pp

    assert lo < hi
    assert lo <= diff._build("mode", a, b).delta_pp <= hi


# ---- provenance -------------------------------------------------------------


def test_a_live_versus_stored_comparison_carries_both_dates():
    """So it cannot be read as two fresh measurements."""
    stored = cell("worker_L0_loop_r0", reference=True, correct=list("abcdefgh"))
    live = cell("worker_L0_loop_r0", wrong=list("abcdefgh"))

    [comparison] = diff.live_vs_reference([stored, live])

    assert comparison.measured_on_a == "2026-07-29"
    assert comparison.measured_on_b == diff.LIVE_STAMP
    assert "2026-07-29" in comparison.provenance()
    assert diff.LIVE_STAMP in comparison.provenance()


def test_two_live_cells_say_both_computed_this_run():
    a = cell("worker_L0_one_shot_r0", mode="one_shot", correct=["a"])
    b = cell("worker_L0_loop_r0", correct=["a"])

    assert diff._build("mode", a, b).provenance() == "both computed this run"


def test_a_live_cell_wins_its_slot_so_the_stored_twin_is_not_self_compared():
    """The mode and level families must compare live against live, not accidentally
    pick up the stored twin as one of the arms."""
    stored = cell("worker_L0_loop_r0", reference=True, correct=["a"])
    live = cell("worker_L0_loop_r0", correct=["a"])
    one_shot = cell("worker_L0_one_shot_r0", mode="one_shot", wrong=["a"])

    [comparison] = diff.mode_deltas([stored, live, one_shot])

    assert comparison.measured_on_b == diff.LIVE_STAMP


# ---- the three families -----------------------------------------------------


def test_the_mode_family_is_the_pre_registered_headline():
    cells = [
        cell("worker_L0_one_shot_r0", mode="one_shot", correct=["a"]),
        cell("worker_L0_loop_r0", wrong=["a"]),
    ]
    [comparison] = diff.mode_deltas(cells)
    assert (comparison.key_a, comparison.key_b) == (
        "worker_L0_one_shot_r0", "worker_L0_loop_r0"
    )


def test_the_level_family_compares_l0_against_l3_at_a_fixed_mode():
    cells = [
        cell("worker_L0_loop_r0", level="L0", correct=["a"]),
        cell("worker_L3_loop_r0", level="L3", wrong=["a"]),
    ]
    [comparison] = diff.level_deltas(cells)
    assert (comparison.key_a, comparison.key_b) == (
        "worker_L0_loop_r0", "worker_L3_loop_r0"
    )


def test_an_incomplete_cell_is_never_differenced():
    """A partial cell against a finished one reports a gap that is mostly the items
    that have not landed yet."""
    cells = [
        cell("worker_L0_one_shot_r0", mode="one_shot", correct=["a"]),
        cell("worker_L0_loop_r0", wrong=["a"], complete=False),
    ]
    assert diff.mode_deltas(cells) == []


def test_untestable_comparisons_are_partitioned_rather_than_dropped():
    """A chart showing fewer comparisons than the cells imply is the same failure as a
    bar rendering zero for 'not measured'."""
    pairable = [
        cell("worker_L0_one_shot_r0", mode="one_shot", correct=["a"]),
        cell("worker_L0_loop_r0", wrong=["a"]),
    ]
    unpairable = [
        cell("frontier_L0_one_shot_r0", role="frontier", mode="one_shot"),
        cell("frontier_L0_loop_r0", role="frontier"),
    ]
    testable, untestable = diff.partition(diff.all_comparisons(pairable + unpairable))

    assert [c.kind for c in testable] == ["mode"]
    # The frontier mode pair (no per-item record on either side) and the named secondary
    # against it (no record on the Sonnet side). Both listed, neither dropped.
    assert sorted(c.kind for c in untestable) == ["mode", "secondary"]


# ---- the chart --------------------------------------------------------------


def test_the_delta_chart_draws_zero_as_a_reference_line():
    """Zero is a real delta. Leaving the axis implicit would let a bar of no width read
    as an absent bar."""
    svg = delta_chart(diff.all_comparisons([
        cell("worker_L0_one_shot_r0", mode="one_shot", correct=list("abcdefgh")),
        cell("worker_L0_loop_r0", wrong=list("abcdefgh")),
    ]))
    assert "0 pp — no difference" in svg
    assert svg.startswith("<svg")


def test_the_delta_chart_never_draws_a_bar_it_cannot_test():
    svg = delta_chart(diff.all_comparisons([
        cell("worker_L0_one_shot_r0", mode="one_shot", correct=list("abcdefghij")),
        cell("worker_L0_loop_r0", correct=list("abcdefghij")),
    ]))
    assert "not distinguishable at this n" in svg


def test_the_delta_chart_reports_what_it_could_not_compare():
    """Counted and named. No silent caps."""
    svg = delta_chart(diff.all_comparisons([
        cell("frontier_L0_one_shot_r0", role="frontier", mode="one_shot"),
        cell("frontier_L0_loop_r0", role="frontier"),
    ]))
    assert "1 comparison(s) not shown" in svg
    assert "no per-item record" in svg


def test_the_delta_chart_refuses_a_cross_model_p_value_on_screen():
    svg = delta_chart(diff.all_comparisons([
        cell("worker_L0_loop_r0", role="worker", correct=list("abcdefghij")),
        cell("frontier_L0_one_shot_r0", role="frontier", mode="one_shot",
             wrong=list("abcdefghij")),
    ]))
    assert "no p-value — cross-model" in svg
    assert "cannot be pinned" in svg


def test_the_cross_model_refusal_is_reachable_at_all():
    """It was not. The mode, level and live families are within-model by construction,
    so the guard could never fire — a guardrail that exists in code and cannot trigger
    is the same defect as one that exists only in prose. The NAMED SECONDARY family
    exists to make it real."""
    comparisons = diff.all_comparisons([
        cell("worker_L0_loop_r0", role="worker", correct=list("abcdefghij")),
        cell("frontier_L0_one_shot_r0", role="frontier", mode="one_shot",
             wrong=list("abcdefghij")),
    ])
    cross = [c for c in comparisons if c.cross_model]
    assert cross, "no family produces a cross-model comparison"
    assert all(c.kind == "secondary" for c in cross)


def test_the_named_secondary_follows_the_level_rather_than_being_typed_per_level():
    comparisons = diff.named_secondary_deltas([
        cell("worker_L0_loop_r0", level="L0", correct=["a"]),
        cell("frontier_L0_one_shot_r0", role="frontier", level="L0",
             mode="one_shot", wrong=["a"]),
        cell("worker_L3_loop_r0", level="L3", correct=["a"]),
        cell("frontier_L3_one_shot_r0", role="frontier", level="L3",
             mode="one_shot", wrong=["a"]),
    ])
    assert [c.key_a for c in comparisons] == ["worker_L0_loop_r0", "worker_L3_loop_r0"]
    assert all(c.cross_model for c in comparisons)


def test_an_empty_delta_chart_says_not_yet_measured():
    svg = delta_chart([])
    assert "not yet measured" in svg
    assert "--reference=compare" in svg


# ---- a p-value is never rendered as a zero it is not -------------------------


def test_a_strongly_significant_p_renders_with_a_less_than():
    """`f"{p:.3f}"` printed p=0.000, which exact McNemar cannot return — the tail is
    2/2**n. A rounding artefact claiming precision the test does not have."""
    from loopeng.paired import PairedComparison

    assert PairedComparison.render_p(0.0000001) == "<0.001"
    assert PairedComparison.render_p(0.039) == "=0.039"


def test_the_delta_chart_never_prints_p_equals_zero():
    svg = delta_chart(diff.all_comparisons([
        cell("worker_L0_one_shot_r0", mode="one_shot", correct=list("abcdefghijklmnop")),
        cell("worker_L0_loop_r0", wrong=list("abcdefghijklmnop")),
    ]))
    assert "p=0.000" not in svg
    # `<` is XML-escaped in the rendered text, which is why the raw form is not here.
    assert "p&lt;0.001" in svg
