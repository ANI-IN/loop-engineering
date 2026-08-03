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

from loopeng.sweep.render import (
    PREFERRED_CURVE_CELL,
    abstention_points,
    curve_cell,
    summarise,
)


def cell(key, *, complete=True, reference=False, mode="loop", items=None, label=None,
         rate="12.0%"):
    return {
        "key": key,
        "label": label or key.replace("_", " "),
        "complete": complete,
        "reference": reference,
        "mode": mode,
        "items": items if items is not None else {"i1": True},
        "silent_error_rate": rate,
    }


# ---- which cell the curve is drawn from --------------------------------------


def test_no_cells_means_no_curve_cell():
    assert curve_cell([]) is None
    assert abstention_points([]) == []


def test_an_incomplete_cell_is_not_eligible():
    assert curve_cell([cell("worker_L0_loop_r0", complete=False)]) is None


def test_a_reference_cell_is_not_eligible():
    """Stored cells keep `{item_id: correct}` and nothing else. The curve needs
    terminations and rejection counts, which a baseline deliberately does not carry —
    so drawing one from a reference cell would be inventing the data."""
    assert curve_cell([cell("worker_L0_loop_r0", reference=True)]) is None


def test_a_one_shot_cell_is_not_eligible():
    """A one-shot cell can never produce a `no_progress` or `hit_the_attempt_cap`
    band, so a curve from one would be missing exactly the bands it exists to show."""
    assert curve_cell([cell("worker_L0_one_shot_r0", mode="one_shot")]) is None


def test_a_cell_with_no_items_is_not_eligible():
    assert curve_cell([cell("worker_L0_loop_r0", items={})]) is None


def test_the_preferred_cell_wins_even_when_another_has_more_items():
    """Preference order, not a hardcoded key — but the preference is real: OVERSIGHT
    draws from this cell, and the two panels must not disagree about their source."""
    chosen = curve_cell([
        cell("frontier_L3_loop_r0", items={f"i{n}": True for n in range(50)}),
        cell(PREFERRED_CURVE_CELL, items={"i1": True}),
    ])
    assert chosen["key"] == PREFERRED_CURVE_CELL


def test_without_the_preferred_cell_the_largest_eligible_one_is_used():
    """The fallback exists so a smoke or frontier-only run still gets a curve rather
    than an empty panel."""
    chosen = curve_cell([
        cell("frontier_L3_loop_r0", items={f"i{n}": True for n in range(50)}),
        cell("frontier_L0_loop_r0", items={"i1": True}),
    ])
    assert chosen["key"] == "frontier_L3_loop_r0"


# ---- what the terminal prints ------------------------------------------------


def test_an_empty_directory_says_so_rather_than_printing_nothing():
    lines = summarise([], [], Path("results/sweep"), [])
    assert any("No cells in results/sweep yet" in line for line in lines)
    assert any("not yet measured" in line for line in lines)


def test_every_cell_is_listed_with_a_live_or_reference_badge():
    lines = summarise(
        [cell("a", label="live one"), cell("b", label="stored one", reference=True)],
        [], Path("d"), [],
    )
    body = "\n".join(lines)
    assert "LIVE" in body and "REFERENCE" in body
    assert "live one" in body and "stored one" in body


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
