"""What the chart entry point needs, so the entry point stays thin.

`demos/04_hill_climbing_loop/charts.py` is a lint target: no numeric literals, because
it is the file that renders to a projector. Keeping the selection logic here means the
demo wires arguments and prints, which is the rule for every demo in this repo, and it
means the selection is testable without going through argparse.
"""

from pathlib import Path

from loopeng.sweep.diff import all_comparisons, partition
from loopeng.triage.abstain import curve

# Which cell the abstention curve is computed over.
#
# Preference order, not a hardcoded key: the curve needs per-item telemetry from a cell
# where the loop actually had something to do, and a one-shot cell can never produce a
# `no_progress` or `hit_the_attempt_cap` band. `worker_L0_loop_r0` is what OVERSIGHT
# uses; the fallbacks exist so a `smoke` or frontier-only run still gets a curve rather
# than an empty panel.
PREFERRED_CURVE_CELL = "worker_L0_loop_r0"


def curve_cell(cells) -> dict | None:
    """The completed live loop cell the abstention curve is drawn from, or None.

    Live only. A stored cell keeps `{item_id: correct}` and nothing else, and the curve
    needs terminations and rejection counts — recomputing it from a baseline would need
    data the baseline deliberately does not carry.
    """
    candidates = [
        cell for cell in cells
        if cell.get("complete") and not cell.get("reference")
        and cell.get("mode") == "loop" and cell.get("items")
    ]
    if not candidates:
        return None
    return next(
        (cell for cell in candidates if cell["key"] == PREFERRED_CURVE_CELL),
        max(candidates, key=lambda cell: len(cell["items"])),
    )


def abstention_points(cells) -> list[dict]:
    """The coverage/precision curve, or an empty list when no cell can produce one."""
    cell = curve_cell(cells)
    return curve(cell["items"]) if cell else []


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
        badge = "REFERENCE" if cell.get("reference") else "LIVE     "
        lines.append(f"  {badge} {cell['label']:34s} {cell['silent_error_rate']}")

    testable, untestable = partition(comparisons)
    lines.append(f"comparisons: {len(testable)} testable, {len(untestable)} not")
    for comparison in testable + untestable:
        lines.append(f"  [{comparison.kind}] {comparison.label_a} -> {comparison.label_b}")
        lines.append(f"      {comparison.reading()}")
        lines.append(f"      {comparison.provenance()}")

    cell = curve_cell(cells)
    lines.append(
        f"abstention curve from: {cell['key']}" if cell
        else "abstention curve: not yet measured — needs a completed live loop cell"
    )
    return lines
