"""Runs the cells, prints the pre-registration first, and stops itself before the cap.

The pre-registration goes on screen BEFORE the first cell, because a hypothesis stated
after the numbers are in is not a hypothesis. It names what this sweep can detect, what
it cannot, and what it already knows it cannot — with the measurement that says so.
"""

import json
from pathlib import Path

import structlog

from loopeng.sweep.runner import (
    DEVELOPMENT,
    HEADROOM,
    SWEEP_DIR,
    Profile,
    SweepAborted,
    build_cells,
    load_cell,
    project_remaining,
    require_fresh,
    run_cell,
)

log = structlog.get_logger(__name__)

GRID_CAP_USD = 8.0


def detectable_effect(n: int, baseline: float = 0.5) -> float:
    """Smallest difference in proportion detectable at this n, computed not stated.

    Normal approximation, two-sided alpha=0.05, power 0.80, unpaired worst case. It is
    an approximation and is labelled as one, but the point stands whichever exact form
    is used: at n=50 the sweep can only see large effects.
    """
    z_alpha, z_beta = 1.959963984540054, 0.8416212335729143
    return (z_alpha + z_beta) * (2 * baseline * (1 - baseline) / n) ** 0.5


def pre_registration(n_items: int) -> str:
    mde = detectable_effect(n_items)
    return f"""
{'=' * 78}
PRE-REGISTRATION — stated before the first cell runs
{'=' * 78}

HEADLINE (what this sweep is for)
  L0 one-shot vs L0 loop, WITHIN each model.
  Within-model, so the temperature asymmetry below does not touch it.

NAMED SECONDARY
  Haiku + loop vs Sonnet one-shot, at each completeness level.
  Cross-model: underpowered AND carries the variance asymmetry. See below.

EXPLICITLY UNDERPOWERED
  Haiku vs Sonnet at L0. Reported, not concluded from.

NOT DETECTABLE AT ANY AFFORDABLE n — AND ALREADY MEASURED
  The L3 delta between one-shot and loop. Measured 2026-07-29 before this sweep:
  29/42 correct one-shot against 26/44 looped, McNemar exact p=0.219. Six discordant
  pairs, every one of them on an item where the loop never intervened — so that
  disagreement was the model's own run-to-run variance, not the loop.
  This sweep is not expected to resolve it and will not claim to.

DETECTABLE EFFECT SIZE AT n={n_items}
  ~{mde * 100:.0f} percentage points (two-sided alpha=0.05, power 0.80, normal
  approximation, worst case at p=0.5). Differences smaller than that are not
  measurable here, whatever the bars look like.
  The items are 10 clusters of 5, so the true figure is WORSE than this.

THE TEMPERATURE ASYMMETRY — applies to every cross-model comparison
  Haiku is pinned to temperature=0. Sonnet 5 rejects non-default sampling parameters
  with a 400, so it cannot be pinned.
  Haiku's error bars carry SAMPLING noise only.
  Sonnet's carry SAMPLING noise PLUS run-to-run variance.
  The bars are therefore NOT comparable across models. Within-model they are.
  Measured justification: at default temperature, two runs of the same items disagreed
  on 6 of 37 that took an identical path — a 16.2% floor (results/noise_floor_*.json).

REPLICATES
  3 on BOTH L0 loop cells. They measure two different determinism floors, and neither
  model's floor may be asserted for the other. Reported separately.
{'=' * 78}
"""


def run_sweep(items, warehouse: Path, *, profile: Profile = DEVELOPMENT,
              cap_usd: float | None = None, directory: Path = SWEEP_DIR,
              verifier=None, on_cell=None, quiet: bool = False,
              fresh: bool = False) -> dict:
    directory = Path(directory)
    if fresh:
        # Checked before anything else, including the pre-registration: refusing after
        # printing a hypothesis to the room reads as a crash rather than a guard.
        require_fresh(directory)
    cells = build_cells(profile)
    cap_usd = profile.cap_usd if cap_usd is None else cap_usd
    projected = project_remaining(cells, len(items))
    if not quiet:
        print(pre_registration(len(items)), flush=True)
        print(f"PROFILE: {profile.name} — {len(cells)} cells, "
              f"{len(profile.roles)} model(s), {profile.replicates} replicate(s)")
        print(f"  {profile.note}")
        print(f"  projected est. ${projected:.4f} against a ${cap_usd:.2f} cap\n", flush=True)

    spent = 0.0
    completed, skipped = [], []
    for index, cell in enumerate(cells):
        cached = load_cell(cell, directory)
        if cached:
            spent += cached["cost_usd"]["value"]
            completed.append(cached)
            skipped.append(cell.key)
            if not quiet:
                print(f"[{index + 1}/{len(cells)}] {cell.label} — resumed from disk", flush=True)
            continue

        # PROJECTED, not actual: what is already spent plus what every remaining cell
        # is projected to cost. Checked before the cell starts, so a breach is refused
        # rather than discovered.
        remaining = project_remaining(cells[index:], len(items))
        projected_total = spent + remaining
        if projected_total > cap_usd:
            raise SweepAborted(
                f"aborting BEFORE '{cell.label}'. Spent est. ${spent:.4f}; remaining "
                f"{len(cells) - index} cells project est. ${remaining:.4f} "
                f"(x{HEADROOM} headroom); projected total est. ${projected_total:.4f} "
                f"exceeds the est. ${cap_usd:.2f} cap. Last completed cell: "
                f"{completed[-1]['label'] if completed else 'none'}."
            )

        if not quiet:
            print(f"[{index + 1}/{len(cells)}] {cell.label} — running "
                  f"(spent est. ${spent:.4f}, projected total est. "
                  f"${projected_total:.4f} of ${cap_usd:.2f})", flush=True)
        kwargs = {"verifier": verifier} if verifier is not None else {}
        report = run_cell(cell, items, warehouse, directory=directory, **kwargs)
        spent += report["cost_usd"]["value"]
        completed.append(report)
        if on_cell:
            on_cell(report)
        if not quiet:
            print(f"      {report['silent_error_rate']}  "
                  f"est. ${report['cost_usd']['value']:.4f}  {report['seconds']}s", flush=True)

    return {
        "profile": profile.name, "n_cells": len(cells),
        "n_resumed": len(skipped), "resumed": skipped,
        "projected_usd": round(projected, 6),
        "spend_usd": {"value": round(spent, 6), "source": "estimated"},
        "cap_usd": cap_usd, "cells": completed,
    }


def load_all(directory: Path = SWEEP_DIR) -> list[dict]:
    """Every cell file on disk, complete or not. Charts read this."""
    directory = Path(directory)
    if not directory.is_dir():
        return []
    return [json.loads(p.read_text()) for p in sorted(directory.glob("*.json"))]
