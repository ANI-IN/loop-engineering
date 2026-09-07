"""`sweep/render.py` — the selection logic behind the chart entry point.

At 0% coverage before this file existed, which is worth stating plainly: the
module holds the choice of *which cell the abstention curve is drawn from* and
*what the terminal prints after a sweep*, and it is pure, offline and free to
test. Nothing about it was hard to cover; it simply had not been.

`demos/04_hill_climbing_loop/charts.py` is a lint target — no numeric literals,
because it renders to a projector — and this module exists so that selection can
be tested without going through argparse. That argument only holds if something
actually tests it.
"""

from pathlib import Path

import pytest

from loopeng.sweep.render import (
    PREFERRED_CURVE_CELL,
    CurveCellMissing,
    abstention_panel,
    abstention_points,
    curve_cell,
    summarise,
)


def cell(key, *, complete=True, mode="loop", items=None, label=None, rate="12.0%"):
    """A cell dict as the sweep writes them.

    `reference=False` used to be a field here. Nothing has read it since the stored-cell
    path was removed, so it was a fixture teaching a shape that no longer exists — and
    the keys in these tests said `worker_*` and `frontier_*`, two role names the sweep
    stopped producing at the rename. A fixture is a claim about what real data looks
    like; one that is wrong makes every test written against it a test of nothing.
    """
    return {
        "key": key,
        "label": label or key.replace("_", " "),
        "complete": complete,
        "mode": mode,
        "items": items if items is not None else {"i1": True},
        "silent_error_rate": rate,
    }


AGENT_L3_LOOP = "agent_L3_loop_r0"
AGENT_L0_ONE_SHOT = "agent_L0_one_shot_r0"


# ---- which cell the curve is drawn from --------------------------------------


def test_no_cells_means_no_curve_cell():
    assert curve_cell([]) is None
    assert abstention_points([]) == []


def test_an_incomplete_cell_is_not_eligible():
    assert curve_cell([cell(PREFERRED_CURVE_CELL, complete=False)]) is None


def test_a_one_shot_cell_is_not_eligible():
    """A one-shot cell can never produce a `no_progress` or `hit_the_attempt_cap`
    band, so a curve from one would be missing exactly the bands it exists to show."""
    assert curve_cell([cell(AGENT_L0_ONE_SHOT, mode="one_shot")]) is None


def test_a_cell_with_no_items_is_not_eligible():
    assert curve_cell([cell(PREFERRED_CURVE_CELL, items={})]) is None


def test_the_named_cell_is_used_even_when_another_has_more_items():
    """The curve's source is a choice, not a popularity contest between cells."""
    chosen = curve_cell([
        cell(AGENT_L3_LOOP, items={f"i{n}": True for n in range(50)}),
        cell(PREFERRED_CURVE_CELL, items={"i1": True}),
    ])
    assert chosen["key"] == PREFERRED_CURVE_CELL


def test_without_the_named_cell_it_raises_rather_than_substituting():
    """This test used to assert the opposite, and asserting the defect is how the
    defect survived. It read: "the fallback exists so a smoke or frontier-only run
    still gets a curve rather than an empty panel."

    Both halves were wrong. Smoke DOES produce the named cell, and no profile in
    `runner.PROFILES` is frontier-only — the reference role never appears without the
    agent role — so the fallback insured against a case no profile can create. What it
    actually did was fire when the key went stale at the rename, drawing the curve from
    a cell nobody chose, with nothing in the output to say so.
    """
    with pytest.raises(CurveCellMissing) as refused:
        curve_cell([
            cell(AGENT_L3_LOOP, items={f"i{n}": True for n in range(50)}),
            cell("reference_L0_loop_r0", items={"i1": True}),
        ])
    message = str(refused.value)
    assert PREFERRED_CURVE_CELL in message
    assert AGENT_L3_LOOP in message, "name what IS present, or the reader cannot tell " \
                                     "a mid-flight sweep from a misconfigured one"
    assert "Refused rather than substituted" in message


def test_nothing_eligible_is_a_different_fact_from_the_named_cell_being_absent():
    """"Nothing has landed yet" is honest and common. "Cells landed and not the one
    this curve is drawn from" is a mismatch. They used to produce the same picture."""
    assert curve_cell([]) is None
    assert curve_cell([cell(AGENT_L0_ONE_SHOT, mode="one_shot")]) is None

    with pytest.raises(CurveCellMissing):
        curve_cell([cell(AGENT_L3_LOOP)])


def test_the_panel_turns_the_refusal_into_something_the_figure_can_say():
    """The boundary. The lookup still fails loudly and nothing is substituted; what
    changes is that a caller which must render SOMETHING gets the reason rather than
    an empty list, which would put "not yet measured" on a chart in the one case where
    that sentence is false."""
    points, refusal = abstention_panel([cell(AGENT_L3_LOOP)])
    assert points == []
    assert refusal is not None
    assert PREFERRED_CURVE_CELL in refusal

    points, refusal = abstention_panel([])
    assert (points, refusal) == ([], None), "nothing landed is not a refusal"


def test_the_summary_reports_the_refusal_without_losing_the_rest():
    """One missing panel must not cost the operator the counts, the cells and every
    comparison printed above it."""
    lines = summarise([cell(AGENT_L3_LOOP)], [], Path("results/sweep"), [])
    assert any("REFUSED" in line for line in lines)
    assert any(PREFERRED_CURVE_CELL in line for line in lines)
    assert any(AGENT_L3_LOOP in line for line in lines), "the cell list still printed"


# ---- what the terminal prints ------------------------------------------------


def test_an_empty_directory_says_so_rather_than_printing_nothing():
    lines = summarise([], [], Path("results/sweep"), [])
    assert any("No cells in results/sweep yet" in line for line in lines)
    assert any("not yet measured" in line for line in lines)


def test_every_cell_is_listed_with_its_rate():
    """No live/stored badge, because there is no stored case: every cell was computed
    by the run that is printing it. A column with one value forever is noise, and a
    renderer that can still SAY "REFERENCE" is one that can still show it."""
    lines = summarise(
        [cell("a", label="first one"), cell("b", label="second one")], [], Path("d"), [],
    )
    body = "\n".join(lines)
    assert "first one" in body and "second one" in body
    assert "REFERENCE" not in body


def test_the_complete_count_is_reported_separately_from_the_total():
    lines = summarise(
        [cell("a"), cell("b", complete=False)], [], Path("d"), [],
    )
    assert any("cells on disk: 2 (1 complete)" in line for line in lines)


def test_written_paths_are_echoed():
    lines = summarise([], [], Path("d"), [Path("results/charts/dial.png")])
    assert any("wrote results/charts/dial.png" in line for line in lines)


def test_an_untestable_comparison_is_still_listed_with_its_reason():
    """Nothing is summarised away. A shorter list is indistinguishable from a shorter
    finding, so a comparison that could not be tested is printed with why."""
    lines = summarise([cell("a")], [], Path("d"), [])
    assert any("comparisons: 0 testable, 0 not" in line for line in lines)


def test_the_preferred_curve_cell_is_a_key_the_sweep_can_actually_produce():
    """It read `"worker_L0_loop_r0"`, and no cell has been keyed `worker_*` since the
    roles were renamed to agent/reference.

    So the preference never matched, every run fell through to "whichever cell has the
    most items", and the curve was drawn from a cell nobody chose — no error, no empty
    panel, just a different measurement rendered confidently.

    Asserted against the keys `build_cells` produces rather than against the literal,
    because a test that restates the string would have passed the whole time it was
    wrong.
    """
    from loopeng.sweep.render import PREFERRED_CURVE_CELL
    from loopeng.sweep.runner import DEV, build_cells

    assert PREFERRED_CURVE_CELL in {cell.key for cell in build_cells(DEV)}


def test_the_oversight_view_reads_the_same_selector_not_a_second_copy_of_the_key():
    """OVERSIGHT held `CELL_KEY = "worker_L0_loop_r0"` — the same dead key the curve
    had, in the same shape, one module over — and looked it up as
    `cells.get(CELL_KEY, {}).get("items", [])`.

    Here the `.get` default turned the miss into `[]`, which the view renders as "not
    measured yet — run the sweep first". So OVERSIGHT told anyone who opened it to go
    and run the sweep they had just run. Not a wrong number: a wrong instruction.

    Two panels drawing from "the same cell" through two hardcoded copies of its key is
    not one source. Asserted by reading the module rather than by launching gradio: the
    property is that the key is not defined twice.
    """
    import loopeng.views.oversight as oversight

    assert not hasattr(oversight, "CELL_KEY"), (
        "the view names its own cell again; it must ask sweep.render"
    )
    assert oversight.curve_cell is curve_cell
