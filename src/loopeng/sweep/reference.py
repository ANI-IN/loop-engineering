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

TWO FILES, AND WHY
------------------

`measurements.json` holds the frontier cells and is what `assets/*.png` is rendered
from. `worker_baseline.json` holds the Haiku cells from the SAME development run.

They are separate files rather than one, for a reason that is not cosmetic: the README
images are rendered from `measurements.json` and from nothing else, so adding cells to
it changes three committed PNGs. The author's images and their numbers are keepers, and
a baseline should not be able to redraw them.

Both are loaded together by `load_reference()`, so a chart sees one reference set.

WHY THE WORKER BASELINE EXISTS AT ALL
------------------------------------

`delivery` and `smoke` measure `worker_*` cells. Until this file existed, the only
committed reference was `frontier_*` — so a cloner who ran delivery and asked for the
reference got four solid worker bars beside six hatched frontier bars: ten unrelated
bars, nothing paired, and no difference computable. The comparison the repo is built
around was structurally impossible for anyone but the author.

WHY IT KEEPS PER-ITEM DETAIL, WHEN THE FRONTIER CELLS DO NOT
-----------------------------------------------------------

`build_reference` strips `items` because SQL and rows are development-only bulk. But
McNemar's input is `{item_id: was_correct}`, and stripping it made a paired comparison
against the baseline impossible — the sweep could show you two bars and could not tell
you whether they differed. So the baseline keeps `paired`: item ids and a boolean,
nothing else. It is the minimum McNemar needs and none of the bulk.

PROVENANCE
----------

The worker cells are frozen from the same sweep directory as the frontier cells, and
that is checked rather than asserted: `assert_same_run()` refuses to freeze worker cells
from a directory whose frontier cells do not match the committed `measurements.json`
field for field.

That check exists because the obvious wrong source is committed and inviting.
`results/prefix_v1/sweep/worker_*.json` are PRE-FIX measurements, taken before the
p07/p08 wording was corrected, and they differ by up to 19 percentage points on the
worker L3 cells — a gap that is entirely the defect `results/prefix_v1/README.md`
documents. Freezing those beside post-fix frontier cells would hand every cloner a
baseline whose difference from their own run is mostly an artefact of a bug we already
fixed.
"""

import json
import re
from pathlib import Path

from loopeng.paired import PAIRED_ARM_COUNT
from loopeng.sweep.runner import SWEEP_DIR

# Metric.render() bakes "computed HH:MM today" into its string. On a stored
# measurement that sentence is false, and it is false in the exact way this module
# exists to prevent — it makes a cited number look like a computed one. Rewritten at
# freeze time so no downstream renderer has to remember.
_COMPUTED_TODAY = re.compile(r"computed \d{1,2}:\d{2} today")

REFERENCE_PATH = Path("results/reference/measurements.json")
WORKER_BASELINE_PATH = Path("results/reference/worker_baseline.json")

# Every file a chart's reference set is drawn from. Both, always: a chart that loaded
# one of them would silently be missing half the baseline.
REFERENCE_PATHS = (REFERENCE_PATH, WORKER_BASELINE_PATH)

MEASURED_ON = "2026-07-29"

# How a live run and the stored baseline are allowed to appear together.
#
# This used to be a single boolean — drop any reference cell that was also computed
# live — and the reasoning behind it was sound for a DEVELOPMENT sweep re-measuring its
# own frontier cells: plotting the same cell solid and hatched looks like two
# measurements disagreeing rather than one shown twice.
#
# It also made the cloner's comparison impossible. The moment you measure
# worker_L0_loop_r0 on your own key, the stored worker_L0_loop_r0 vanished from the
# chart, so your run could never be shown beside the baseline. `compare` is the mode
# that was missing, and it is the default for anyone rendering their own run.
MODE_HIDE = "hide"        # live cells only
MODE_FILL = "fill"        # reference only where no live cell exists (the old behaviour)
MODE_COMPARE = "compare"  # both, so the difference between them can be computed
REFERENCE_MODES = (MODE_HIDE, MODE_FILL, MODE_COMPARE)

# ---------------------------------------------------------------------------
# The determinism floors: how far a model's L0 loop cell moved across replicates of the
# same 50 items. DERIVED from the committed replicate files, not typed.
#
# They were typed — `spread_pp: 3.3` and `18.8` — and both values are exactly what the
# committed data yields, so nothing measured changes here. What changes is that the
# numbers now cannot drift away from their evidence: an edit to the replicate files moves
# these, and an edit to these is impossible without moving the files.
#
# The source is results/prefix_v1/sweep/. That is the PRE-FIX measurement set, and it is
# the right source for exactly this: the floors are a fact about run-to-run variance in
# two models, which the p07/p08 wording defect does not touch. It is also where these
# figures came from originally — the post-fix run yields a different spread (2.5pp and
# 12.8pp), so deriving them from `results/sweep` would silently replace the author's
# numbers with new ones. Freezing evidence to the run it came from is the point.
# ---------------------------------------------------------------------------
FLOOR_SOURCE = Path("results/prefix_v1/sweep")

# A rate is a proportion; a spread is quoted in percentage points.
PERCENTAGE_POINTS = 100

_PINNED = {
    "claude-haiku-4-5": (
        "worker",
        True,
        "temperature=0 pinned; spread across replicates of the L0 loop cell",
    ),
    "claude-sonnet-5": (
        "frontier",
        False,
        "cannot be pinned — Sonnet 5 rejects non-default sampling with a 400 — so "
        "this floor cannot be removed, and its bars never meant the same thing as "
        "Haiku's",
    ),
}


def noise_floors(source: Path = FLOOR_SOURCE) -> dict:
    """Replicate spread per model, computed from the cell files that measured it.

    Returns an empty dict for a model with fewer than two replicates on disk rather than
    reporting a spread of zero: one replicate cannot measure run-to-run variance, and a
    zero would read as "this model is deterministic".
    """
    source = Path(source)
    floors = {}
    for model, (role, pinned, note) in _PINNED.items():
        rates = [
            json.loads(path.read_text())["rate_value"]
            for path in sorted(source.glob(f"{role}_L0_loop_r*.json"))
            if json.loads(path.read_text()).get("complete")
        ]
        if len(rates) < PAIRED_ARM_COUNT:
            continue
        floors[model] = {
            "spread_pp": round((max(rates) - min(rates)) * PERCENTAGE_POINTS, 1),
            "pinned": pinned,
            "n_replicates": len(rates),
            "note": note,
            "derived_from": f"{source}/{role}_L0_loop_r*.json",
        }
    return floors


NOISE_FLOORS = noise_floors()


class NotTheSameRun(RuntimeError):
    """A directory's frontier cells do not match the committed reference.

    Raised rather than warned. Freezing a worker baseline from a different run than the
    frontier reference produces a baseline whose difference from a cloner's own run is
    partly an artefact of whatever changed between the two runs — and nothing on the
    resulting chart would say so.
    """


def as_measured(text: str, measured_on: str = MEASURED_ON) -> str:
    """Rewrite a stored `Metric.render()` string so it stops claiming it was just computed.

    Public because more than one thing cites a stored figure. The pre-registration reads
    the determinism floor out of its own cited file, and that file's rendered rate carries
    "computed HH:MM today" — false, in exactly the way this module exists to prevent.
    """
    return _COMPUTED_TODAY.sub(f"measured {measured_on}", text)


def _freeze(cell: dict, *, keep_paired: bool) -> dict:
    cell = dict(cell)
    cell["reference"] = True
    cell["measured_on"] = MEASURED_ON
    cell["silent_error_rate"] = as_measured(cell["silent_error_rate"])
    items = cell.pop("items", None)  # SQL and rows are development-only bulk
    if keep_paired and items:
        # McNemar's whole input, and nothing else. See the module docstring.
        cell["paired"] = {
            row["item_id"]: bool(row["correct"])
            for row in items
            if row["ran_and_returned"]
        }
    return cell


def build_reference(sweep_dir: Path = SWEEP_DIR) -> dict:
    """Freeze the frontier cells and the floors from a development sweep."""
    sweep_dir = Path(sweep_dir)
    cells = []
    for path in sorted(sweep_dir.glob("frontier_*.json")):
        cell = json.loads(path.read_text())
        if not cell.get("complete"):
            continue
        cells.append(_freeze(cell, keep_paired=False))
    return {
        "measured_on": MEASURED_ON,
        "noise_floors": NOISE_FLOORS,
        "cells": cells,
        "how": (
            "Measured once under the development profile. Cited at delivery, never "
            "recomputed — recomputing would cost about ten times the delivery budget."
        ),
    }


# Fields compared to decide whether two cell files came out of the same run. Counts and
# rates, not timings: `seconds` varies with the machine and a laptop under load would
# make a legitimate freeze look like a different run.
_RUN_IDENTITY_FIELDS = (
    "rate_value", "rate_ci_low", "rate_ci_high", "rate_n",
    "correct", "silent_errors", "ran_and_returned", "n_done",
)


def assert_same_run(sweep_dir: Path = SWEEP_DIR,
                    reference_path: Path = REFERENCE_PATH) -> list[str]:
    """Refuse unless this directory's frontier cells ARE the committed reference.

    Returns the frontier keys it matched, so a caller can report what it checked
    against rather than claiming a check it cannot show.
    """
    sweep_dir, reference_path = Path(sweep_dir), Path(reference_path)
    committed = {c["key"]: c for c in json.loads(reference_path.read_text())["cells"]}
    matched = []
    for key, stored in sorted(committed.items()):
        path = sweep_dir / f"{key}.json"
        if not path.is_file():
            raise NotTheSameRun(
                f"{path} is missing, so this directory cannot be shown to be the run "
                f"{reference_path} was frozen from. Freeze from the directory that "
                f"produced the committed frontier cells, or not at all."
            )
        live = json.loads(path.read_text())
        differing = [f for f in _RUN_IDENTITY_FIELDS if live.get(f) != stored.get(f)]
        if differing:
            raise NotTheSameRun(
                f"{path} disagrees with the committed {key} on "
                f"{', '.join(differing)}. This is a DIFFERENT measurement run.\n"
                f"Freezing a worker baseline from it would produce a baseline whose "
                f"difference from a cloner's own run is partly an artefact of whatever "
                f"changed between the two runs, with nothing on the chart to say so.\n"
                f"results/prefix_v1/sweep/ is the committed example of exactly this: "
                f"pre-fix measurements, up to 19pp apart on the worker L3 cells."
            )
        matched.append(key)
    return matched


def build_worker_baseline(sweep_dir: Path = SWEEP_DIR) -> dict:
    """Freeze the Haiku cells, from the same run the frontier reference came from.

    Provenance is checked, not asserted — see `assert_same_run`.
    """
    sweep_dir = Path(sweep_dir)
    verified_against = assert_same_run(sweep_dir)

    cells = []
    for path in sorted(sweep_dir.glob("worker_*.json")):
        cell = json.loads(path.read_text())
        if not cell.get("complete"):
            continue
        cells.append(_freeze(cell, keep_paired=True))
    return {
        "measured_on": MEASURED_ON,
        "cells": cells,
        "provenance": {
            "same_run_as": str(REFERENCE_PATH),
            "verified_by_matching": verified_against,
            "not_from": "results/prefix_v1/sweep/ — PRE-FIX, up to 19pp apart",
        },
        "how": (
            "The Haiku half of the development run whose frontier cells are in "
            "measurements.json. Frozen so a cloner running `delivery` or `smoke` has a "
            "stored counterpart for every cell they compute, and so the difference "
            "between the two can be tested rather than eyeballed. Each cell keeps "
            "`paired` — {item_id: was_correct} over items that ran — because that is "
            "McNemar's input and stripping it made a paired comparison impossible."
        ),
    }


def save_reference(payload: dict, path: Path = REFERENCE_PATH) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))
    return path


def load_reference(*paths: Path, mode: str = MODE_FILL, live_keys=()) -> list[dict]:
    """Reference cells, each already flagged so charts cannot render them as live.

    `mode` decides how they sit beside a live run — see MODE_* above. `live_keys` is
    the set of cell keys computed in this run; it is only consulted by `fill`.
    """
    if mode not in REFERENCE_MODES:
        raise ValueError(f"unknown reference mode {mode!r}; expected one of {REFERENCE_MODES}")
    if mode == MODE_HIDE:
        return []

    cells: list[dict] = []
    for path in paths or REFERENCE_PATHS:
        path = Path(path)
        if not path.is_file():
            continue
        cells.extend(json.loads(path.read_text())["cells"])

    if mode == MODE_FILL:
        live = set(live_keys)
        return [cell for cell in cells if cell["key"] not in live]
    return cells


def paired_map(cell: dict) -> dict[str, bool]:
    """`{item_id: was_correct}` for a cell, live or stored. McNemar's input.

    A live cell carries full `items`; a stored one carries the compact `paired` map. One
    accessor for both, so no caller has to know which kind it is holding — and an empty
    map for a cell that has neither, which `paired.compare` handles by pairing nothing
    rather than by inventing evidence.
    """
    if "paired" in cell:
        return {str(k): bool(v) for k, v in cell["paired"].items()}
    return {
        row["item_id"]: bool(row["correct"])
        for row in cell.get("items", ())
        if row.get("ran_and_returned")
    }
