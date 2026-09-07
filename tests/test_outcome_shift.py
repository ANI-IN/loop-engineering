"""The outcome-shift chart: the session's headline visual.

It was specified as A vs C. A vs C measured as a null — condition A terminated
`success` on 60 of 60 held-out items, so retry had nothing to retry, B fired zero
retries, and C's verifiers rejected 2. Three runs of A alone scored 46, 51 and 52, so
the six-item "uplift" sits inside the arm's own spread.

That is a finding rather than a disappointment, and it is the trap seen from the other
side: verification exists to catch rule violations, and supplying the rules leaves
barely any violations to catch. So the chart is built on the arms where the bands do
separate, and these tests are about the chart's honesty rather than its subject.
"""

import pytest

from loopeng.agent.classify import BANDS
from loopeng.sweep.chart_model import (
    SHIFT_BAND_LABELS,
    SHIFT_BAND_ORDER,
    outcome_shift_rows,
)
from loopeng.sweep.charts import outcome_shift_chart


def _arm(name, **bands):
    full = dict.fromkeys(BANDS, 0)
    full.update(bands)
    return {"arm": name, "n_items": sum(full.values()), "bands": full}


def texts(figure):
    """Every string on the figure, with whitespace collapsed.

    Collapsed because the caption wrapper inserts newlines at the column width, so a
    phrase can be split mid-assertion — "measured no\nvariance" is the same content
    and a different string. These tests are about what the figure SAYS, and coupling
    them to where the wrap happens to land makes them fail on a rewording that
    changed nothing.
    """
    raw = " ".join(
        t.get_text() for t in figure.findobj(match=lambda o: hasattr(o, "get_text"))
    )
    return " ".join(raw.split())


# ---- every band is drawn, and none is derived -------------------------------


def test_every_band_has_a_position_and_a_label():
    """A chart that renders four of five bands drops a category silently, and the
    dropped one would be whichever was added last — which is how UNEARNED_CORRECT and
    SIGNALLED_MISSING_INFO would have gone missing."""
    assert set(SHIFT_BAND_ORDER) == set(BANDS)
    assert set(SHIFT_BAND_LABELS) == set(BANDS)


def test_the_band_order_puts_the_silent_band_in_the_middle():
    """Reading left to right the eye crosses the silent band on the way from "fine"
    to "declined". It is the band the session is about and it is not at an edge."""
    assert SHIFT_BAND_ORDER.index("wrong_and_silent") not in (
        0, len(SHIFT_BAND_ORDER) - 1
    )
    assert SHIFT_BAND_ORDER[0] == "correct"


def test_rows_carry_every_band_as_a_count():
    rows = outcome_shift_rows([_arm("x", correct=3, wrong_and_silent=2)])
    assert len(rows[0]["counts"]) == len(SHIFT_BAND_ORDER)
    assert sum(rows[0]["counts"]) == rows[0]["n"] == 5


def test_a_missing_band_key_counts_as_zero_not_as_absent():
    """Cell files written before a band existed simply have no key. Absent must mean
    zero here, and must not shift the other bands along by one."""
    rows = outcome_shift_rows([{"arm": "old", "n_items": 2, "bands": {"correct": 2}}])
    assert rows[0]["counts"][SHIFT_BAND_ORDER.index("correct")] == 2
    assert sum(rows[0]["counts"]) == 2


# ---- what the figure says ----------------------------------------------------


def test_the_chart_renders_the_counts_it_was_given():
    figure = outcome_shift_chart([
        _arm("agent-L0", correct=7, unearned=4, wrong_and_silent=42,
             wrong_and_caught=7),
        _arm("reference-L0", correct=9, wrong_and_silent=27, wrong_and_caught=5,
             abstained=19),
    ])
    drawn = texts(figure)
    for count in ("42", "27", "19", "7", "9"):
        assert count in drawn
    assert "n=60" in drawn


def test_the_rule_free_row_is_explained_on_the_figure():
    """A row scoring the same at both levels looks like a broken comparison until you
    know it is the floor. That belongs on the visual, not in a runbook nobody has
    open."""
    drawn = texts(outcome_shift_chart([_arm("x", correct=1)]))
    assert "L0 floor" in drawn
    assert "rigged" in drawn


def test_the_caption_names_the_abstained_band_as_not_a_failure():
    """It was scored as a crash until 2026-09-07, and a reader meeting the band for
    the first time needs to be told which way round it goes."""
    drawn = texts(outcome_shift_chart([_arm("x", abstained=1)]))
    assert "not a failure" in drawn
    assert "named the input" in drawn


def test_the_band_key_is_in_the_caption_so_the_figure_reserves_room_for_it():
    """It was drawn at a fixed figure fraction and landed on top of the caption:
    `_frame` sizes the figure from the text it is GIVEN, so text it is not given has
    nowhere reserved for it."""
    drawn = texts(outcome_shift_chart([_arm("x", correct=1)]))
    assert "Bands, left to right" in drawn
    for label in SHIFT_BAND_LABELS.values():
        assert label in drawn


def test_an_empty_arm_list_renders_not_yet_measured():
    """A chart that silently does not exist is indistinguishable from one whose
    finding is absent."""
    assert "not yet measured" in texts(outcome_shift_chart([])).lower()


def test_a_zero_band_is_not_drawn_as_a_sliver():
    """A zero-width segment with a label beside it reads as a small measurement."""
    figure = outcome_shift_chart([_arm("x", correct=10, abstained=0)])
    bars = [p for p in figure.axes[0].patches if p.get_width() > 0]
    assert len(bars) == 1


def test_labels_clear_the_projector_floor():
    """Minimum 14pt on anything read off a projector after video compression. This is
    the headline visual, so it is the one that must not need squinting at."""
    from loopeng.sweep.charts import SHIFT_LABEL_SIZE

    assert SHIFT_LABEL_SIZE >= 14


@pytest.mark.parametrize("arms", [[], [_arm("x", correct=1)]])
def test_rendering_never_raises_on_the_shapes_it_will_meet(arms):
    assert outcome_shift_chart(arms) is not None


# ---- THESIS: the trap matrix -------------------------------------------------


def _cell(model, level, correct, n=60, spread=None):
    cell = {"model": model, "level": level, "correct": correct, "n": n}
    if spread:
        cell["spread"] = spread
    return cell


def test_the_matrix_draws_all_four_cells():
    from loopeng.sweep.charts import trap_matrix_chart

    figure = trap_matrix_chart([
        _cell("luna", "L0", 7), _cell("luna", "L3", 52),
        _cell("astra", "L0", 9), _cell("astra", "L3", 60),
    ])
    drawn = texts(figure)
    for label in ("7/60", "52/60", "9/60", "60/60"):
        assert label in drawn
    assert len(figure.axes[0].patches) == 4


def test_the_matrix_says_which_error_bar_is_which():
    """Most people in a room have seen exactly one kind of error bar. A Wilson
    interval and a run-to-run spread mean different things and one is invisible to
    the other, so the figure names them rather than relying on styling."""
    drawn = texts(trap_matrix_chart_fixture())
    assert "Wilson interval" in drawn
    assert "RUN-TO-RUN spread" in drawn
    assert "invisible to the other" in drawn
    # Absent and flat mean different things, and most readers will not distinguish
    # them unless told: no bracket is "run once", a flat one is "measured no
    # variance". Only one of those is a claim.
    assert "NO bracket was run once" in drawn
    assert "measured no variance" in drawn


def test_the_matrix_refuses_a_significance_mark_on_the_row():
    """Rows are cross-model. `diff.py` refuses a p-value across that in code, and the
    caption says where the paired test actually lives."""
    drawn = texts(trap_matrix_chart_fixture())
    assert "No significance marks on the ROW" in drawn
    assert "DELTA chart" in drawn


def test_a_cell_run_once_gets_no_spread_bracket():
    """A zero-height bracket would read as "we measured no variance", which is a
    claim. A cell run once has not measured it at all."""
    from loopeng.sweep.charts import trap_matrix_chart

    one_run = trap_matrix_chart([_cell("m", "L3", 52)])
    repeated = trap_matrix_chart([_cell("m", "L3", 52, spread=(46, 52))])
    assert len(repeated.axes[0].lines) > len(one_run.axes[0].lines)


def trap_matrix_chart_fixture():
    from loopeng.sweep.charts import trap_matrix_chart

    return trap_matrix_chart([_cell("luna", "L3", 52, spread=(46, 52))])


def test_an_empty_matrix_renders_not_yet_measured():
    from loopeng.sweep.charts import trap_matrix_chart

    assert "not yet measured" in texts(trap_matrix_chart([])).lower()


# ---- COST PER CORRECT --------------------------------------------------------


def _arm_cost(label, level, per_correct):
    return {"label": label, "level": level,
            "cost_per_correct_usd": ({"value": per_correct, "source": "estimated"}
                                     if per_correct else None)}


def test_cost_per_correct_keeps_the_estimated_prefix():
    from loopeng.sweep.charts import cost_per_correct_chart

    drawn = texts(cost_per_correct_chart([_arm_cost("cheap", "L3", 0.00034)]))
    assert "est. $" in drawn
    assert "estimated" in drawn.lower()


def test_an_arm_with_nothing_correct_says_so_rather_than_drawing_a_bar():
    """Zero correct at any price is an undefined cost, not an unbounded one, and a
    bar running off a log axis would state a magnitude nobody measured."""
    from loopeng.sweep.charts import cost_per_correct_chart

    figure = cost_per_correct_chart([_arm_cost("dead", "L3", None)])
    assert "undefined" in texts(figure)
    assert not figure.axes[0].patches


def test_the_withheld_bars_are_what_make_it_an_argument():
    from loopeng.sweep.charts import cost_per_correct_chart

    drawn = texts(cost_per_correct_chart([_arm_cost("cheap", "L3", 0.0003)]))
    assert "rather than a price list" in drawn
    assert "most expensive way to be wrong" in drawn


# ---- every chart, drawn with REAL data ---------------------------------------
#
# DIAL was broken for any cell that had a value, and it survived because every test
# of it used empty or in-progress cells — which return before reaching the defect.
# A suite can be green because it never exercised the state that matters.
#
# So this draws every chart the module ships, with populated inputs, and it is
# derived from `dir(charts)` rather than listed: a chart added without a
# non-empty-input test fails here rather than joining the set silently.


def _populated_cell(key="agent_L3_loop_r0", successes=3, n=10):
    from loopeng.metric import Metric

    metric = Metric.from_counts(successes, n)
    return {
        "key": key, "label": key, "role": "agent", "level": "L3", "mode": "loop",
        "replicate": 0, "complete": True, "rate_value": metric.value,
        "rate_ci_low": metric.ci_low, "rate_ci_high": metric.ci_high, "rate_n": n,
        "silent_error_rate": metric.render(), "n_items": n, "n_done": n,
        "ran_and_returned": n, "correct": successes, "silent_errors": n - successes,
        "cost_usd": {"value": 0.0123, "source": "estimated"},
        "tokens": {"n_calls": n}, "rejections": 0, "termination": {"success": n},
        "items": [{"item_id": f"i{i}", "correct": i < successes,
                   "ran_and_returned": True} for i in range(n)],
    }


def _populated_inputs():
    """One realistic, non-empty argument set per chart builder."""
    from loopeng.sweep import diff

    cells = [_populated_cell(), _populated_cell("agent_L0_loop_r0", 7, 10)]
    for cell in cells:
        cell["level"] = cell["key"].split("_")[1]
    return {
        "dial_chart": (cells,),
        "cost_chart": (cells,),
        "delta_chart": (diff.all_comparisons(cells),),
        "abstention_chart": ([{
            "threshold": 0.5, "n_total": 10, "n_answered": 8,
            "coverage_value": 0.8, "precision_value": 0.75,
            "precision_ci_low": 0.4, "precision_ci_high": 0.94,
        }],),
        "outcome_shift_chart": ([_arm("agent-L0", correct=7, wrong_and_silent=3)],),
        "trap_matrix_chart": ([_cell("luna", "L3", 7, n=10)],),
        "cost_per_correct_chart": ([_arm_cost("cheap", "L3", 0.0004)],),
    }


def test_every_chart_is_drawn_with_populated_input():
    """The property DIAL failed: a chart tested only on empty inputs is a chart
    nobody has drawn."""
    import ast
    import pathlib

    from loopeng.sweep import charts

    source = pathlib.Path(charts.__file__).read_text(encoding="utf-8")
    builders = {node.name for node in ast.parse(source).body
                if isinstance(node, ast.FunctionDef) and node.name.endswith("_chart")}
    covered = _populated_inputs()

    assert builders == set(covered), (
        "these chart builders have no populated-input case: "
        f"{sorted(builders - set(covered))}"
    )
    for name, args in covered.items():
        assert getattr(charts, name)(*args) is not None, name


def test_no_chart_still_reads_a_stored_measurement_key():
    """The stored-measurement path was removed across 98 files. What survived it was
    a dead branch reading a key nothing sets — which raised for any cell that had
    data, on the chart this repository has had longest."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parent.parent / "src" / "loopeng"
    offenders = []
    for path in root.rglob("*.py"):
        body = path.read_text(encoding="utf-8")
        for marker in ('["reference"]', '.get("reference"', '["measured_on"]'):
            if marker in body:
                offenders.append(f"{path.relative_to(root)}: {marker}")
    assert not offenders, f"dead reads of a removed key: {offenders}"
