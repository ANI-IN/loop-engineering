"""Measurements that are properties of the setup, not results of a delivery.

Some numbers cost real money to establish and do not change between deliveries. The
determinism floors are a fact about two models plus one configuration decision. The
ablation is a development finding about which verifier carries the loop. Sonnet's cells
were measured once, at ~78% of the sweep's cost, on an axis that was underpowered and
variance-asymmetric anyway.

Re-running any of them per delivery would spend roughly ten times the delivery budget
to re-derive things already known. So they are **cited with their date**, and rendered
so that citing cannot be mistaken for computing.

The ablation deliberately has no entry here: it is a development finding and does not
appear in the session at all.
"""

import json
import re
from pathlib import Path

# Metric.render() bakes "computed HH:MM today" into its string. On a stored
# measurement that sentence is false, and it is false in the exact way this module
# exists to prevent — it makes a cited number look like a computed one. Rewritten at
# freeze time so no downstream renderer has to remember.
_COMPUTED_TODAY = re.compile(r"computed \d{1,2}:\d{2} today")

REFERENCE_PATH = Path("results/reference/measurements.json")

MEASURED_ON = "2026-07-29"

NOISE_FLOORS = {
    "claude-haiku-4-5": {
        "spread_pp": 3.3,
        "pinned": True,
        "note": "temperature=0 pinned; spread across 3 replicates of the L0 loop cell",
    },
    "claude-sonnet-5": {
        "spread_pp": 18.8,
        "pinned": False,
        "note": (
            "cannot be pinned — Sonnet 5 rejects non-default sampling with a 400 — so "
            "this floor cannot be removed, and its bars never meant the same thing as "
            "Haiku's"
        ),
    },
}


def build_reference(sweep_dir: Path = Path("results/sweep")) -> dict:
    """Freeze the frontier cells and the floors from a development sweep."""
    sweep_dir = Path(sweep_dir)
    cells = []
    for path in sorted(sweep_dir.glob("frontier_*.json")):
        cell = json.loads(path.read_text())
        if not cell.get("complete"):
            continue
        cell["reference"] = True
        cell["measured_on"] = MEASURED_ON
        cell["silent_error_rate"] = _COMPUTED_TODAY.sub(
            f"measured {MEASURED_ON}", cell["silent_error_rate"]
        )
        cell.pop("items", None)  # the per-item detail is development-only
        cells.append(cell)
    return {
        "measured_on": MEASURED_ON,
        "noise_floors": NOISE_FLOORS,
        "cells": cells,
        "how": (
            "Measured once under the development profile. Cited at delivery, never "
            "recomputed — recomputing would cost about ten times the delivery budget."
        ),
    }


def save_reference(payload: dict, path: Path = REFERENCE_PATH) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))
    return path


def load_reference(path: Path = REFERENCE_PATH, *, exclude_keys=()) -> list[dict]:
    """Reference cells, each already flagged so charts cannot render them as live.

    `exclude_keys` drops any reference cell that was also computed live in this run.
    Without it a development sweep — which computes the frontier cells itself — plots
    each of them twice, once solid and once hatched, which looks like a disagreement
    between two measurements rather than the same one shown twice. A live measurement
    always wins over a stored one.
    """
    path = Path(path)
    if not path.is_file():
        return []
    excluded = set(exclude_keys)
    return [c for c in json.loads(path.read_text())["cells"] if c["key"] not in excluded]
