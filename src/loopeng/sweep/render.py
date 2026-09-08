"""What the chart entry point needs, so the entry point stays thin.

`demos/04_hill_climbing_loop/charts.py` is a lint target: no numeric literals, because
it is the file that renders to a projector. Keeping the selection logic here means the
demo wires arguments and prints, which is the rule for every demo in this repo, and it
means the selection is testable without going through argparse.
"""

from pathlib import Path

from loopeng.registry import spec_for
from loopeng.sweep.diff import all_comparisons, partition
from loopeng.sweep.runner import Cell
from loopeng.triage.abstain import curve

# Which cell the abstention curve is computed over.
#
# The curve needs per-item telemetry from a cell where the loop actually had something
# to do: a one-shot cell can never produce a `no_progress` or `hit_the_attempt_cap`
# band, so a curve drawn from one would be missing exactly the bands it exists to show.
#
# **BUILT, not typed.** This read `"worker_L0_loop_r0"` and no cell has been keyed
# `worker_*` since the roles were renamed to agent/reference. Constructing it through
# `Cell` ties it to the key format, and `spec_for` makes the role a lookup that RAISES
# on an unknown name rather than a literal that quietly stops matching.
PREFERRED_CURVE_CELL = Cell(spec_for("agent").role, "L0", "loop").key


class CurveCellMissing(LookupError):
    """Eligible loop cells are on disk and none of them is the one asked for.

    Raised instead of picking another, which is what this function used to do. The
    combination was the worst of the four stale-configuration strings this build
    found — not because the damage was largest but because there was NO SIGNAL:

        return next(
            (cell for cell in candidates if cell["key"] == PREFERRED_CURVE_CELL),
            max(candidates, key=lambda cell: len(cell["items"])),   # <- the defect
        )

    A wrong label is visibly wrong to anyone who knows the model. A selector naming a
    role that no longer exists fell through to "whichever cell has the most items", so
    the abstention curve was drawn from a different cell than intended and nothing
    about the output said so. Same shape as `band_of` defaulting instead of raising: a
    lookup that degrades gracefully where it should fail loudly produces a plausible
    wrong answer.

    Fixing the key does not fix this. The fallback is the defect and it stays until it
    is removed — a test that the key is producible catches today's bug and not the next
    one.

    The comment justifying the fallback said it existed "so a smoke or frontier-only run
    still gets a curve rather than an empty panel". Smoke DOES produce this cell, and no
    profile in `runner.PROFILES` is frontier-only — the reference role never appears
    without the agent role. So it was insurance against a case no profile can create,
    and the one case it did fire on was the one where it was wrong.
    """


def curve_cell(cells) -> dict | None:
    """The completed loop cell the abstention curve is drawn from.

    None when NOTHING is eligible — no completed loop cell with per-item telemetry has
    landed yet. That is a real state early in a sweep, and the caller renders "not yet
    measured" for it.

    Raises `CurveCellMissing` when eligible cells exist and the preferred one is not
    among them. Those are different facts and they used to produce the same picture:
    "nothing to draw yet" is honest, "here is a curve from some other cell" is not.
    """
    candidates = [
        cell for cell in cells
        if cell.get("complete")
        and cell.get("mode") == "loop" and cell.get("items")
    ]
    if not candidates:
        return None
    for cell in candidates:
        if cell["key"] == PREFERRED_CURVE_CELL:
            return cell
    raise CurveCellMissing(
        f"the abstention curve is drawn from {PREFERRED_CURVE_CELL!r} and no such cell "
        f"is on disk. Eligible loop cells present: "
        f"{', '.join(sorted(c['key'] for c in candidates))}.\n"
        f"Refused rather than substituted: drawing the curve from another cell would "
        f"render a different measurement with nothing on the figure to say so."
    )


def abstention_points(cells) -> list[dict]:
    """The coverage/precision curve, or an empty list when no cell can produce one.

    Propagates `CurveCellMissing`. A caller that wants to keep rendering past it should
    use `abstention_panel`, which turns the refusal into something the figure can say —
    swallowing it here would put the empty-list "not yet measured" back on a chart in
    the one case where that sentence is false.
    """
    cell = curve_cell(cells)
    return curve(cell["items"]) if cell else []


def abstention_panel(cells) -> tuple[list[dict], str | None]:
    """The curve, and the reason there isn't one, for a caller that must render either.

    The boundary where a raised `CurveCellMissing` becomes a sentence on the figure
    instead of a traceback. That is not the graceful degradation being removed: the
    lookup still fails loudly, nothing is substituted, and the refusal is carried onto
    the image — where the old fallback carried nothing at all.

    Caught here rather than in `write_charts` so the decision is visible at the call
    site. A missing curve must not take the other six charts down with it, and it must
    not quietly become "not yet measured" either.
    """
    try:
        return abstention_points(cells), None
    except CurveCellMissing as missing:
        return [], str(missing)


def arm_panels(directory=None) -> dict:
    """`arms` and `trap_cells` for `write_charts`, or empty when nothing has run.

    The three headline charts accepted these from the day they were written and no
    caller ever passed them, so `outcome_shift`, `trap_matrix` and `cost_per_correct`
    rendered *not yet measured* on every run — including the runs whose headline they
    are. See `sweep.experiments`.

    Empty rather than raising on a fresh checkout: a cloner who has not run the
    experiments should get the charts that DO have data plus three honest "not yet
    measured" panels, which is exactly what those panels are for. The refusal is
    narrower and lives in `experiments.trap_cells`: a PARTIAL set of arms raises,
    because a matrix drawn from three of four cells is a different picture with no way
    to tell.
    """
    from loopeng.sweep import experiments

    arms = experiments.load_arms(directory or experiments.EXPERIMENTS_DIR)
    if not experiments.available(arms):
        return {"arms": (), "trap_cells": ()}
    return {
        "arms": experiments.outcome_shift_arms(arms),
        "trap_cells": experiments.trap_cells(arms),
    }


def comparisons_for(cells):
    return all_comparisons(cells)


def summarise(cells, comparisons, directory, written: list[Path]) -> list[str]:
    """What the terminal prints. Counts, then every cell, then every comparison.

    Nothing is summarised away: a comparison that could not be tested is listed with
    its reason, because a shorter list is indistinguishable from a shorter finding.
    """
    lines = []
    if not cells:
        lines.append(f"No cells in {directory} yet. Charts render as 'not yet measured'.")
    done = len([cell for cell in cells if cell["complete"]])
    lines.append(f"cells on disk: {len(cells)} ({done} complete)")
    for path in written:
        lines.append(f"  wrote {path}")

    for cell in sorted(cells, key=lambda c: c["label"]):
        # No badge. Every cell was computed by the run that is printing it, so a
        # column distinguishing live from stored would have one value forever — and
        # a renderer that can still SAY "REFERENCE" is a renderer that can still show
        # one, which is the capability the removal was for.
        lines.append(f"  {cell['label']:34s} {cell['silent_error_rate']}")

    testable, untestable = partition(comparisons)
    lines.append(f"comparisons: {len(testable)} testable, {len(untestable)} not")
    for comparison in testable + untestable:
        lines.append(f"  [{comparison.kind}] {comparison.label_a} -> {comparison.label_b}")
        lines.append(f"      {comparison.reading()}")
        lines.append(f"      {comparison.provenance()}")

    # Caught so one missing panel does not cost the operator the whole summary — the
    # counts, every cell and every comparison are above this line. Reported in full
    # rather than shortened: the message names which cells ARE present, which is the
    # thing that tells you whether the sweep is mid-flight or misconfigured.
    try:
        cell = curve_cell(cells)
        lines.append(
            f"abstention curve from: {cell['key']}" if cell
            else "abstention curve: not yet measured — needs a completed loop cell"
        )
    except CurveCellMissing as missing:
        lines.append("abstention curve: REFUSED — nothing was drawn")
        lines.extend(f"  {line}" for line in str(missing).splitlines())
    return lines
