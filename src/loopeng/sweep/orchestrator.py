"""Runs the cells, prints the pre-registration first, and stops itself before the cap.

The pre-registration goes on screen BEFORE the first cell, because a hypothesis stated
after the numbers are in is not a hypothesis. It names what this sweep can detect, what
it cannot, and what it already knows it cannot — with the measurement that says so.
"""

import json
from dataclasses import replace
from pathlib import Path

import structlog

from loopeng.registry import spec_for
from loopeng.sweep.deadline import Deadline
from loopeng.sweep.fingerprint import RunFingerprint, resolve_run_id
from loopeng.sweep.runner import (
    CONCURRENCY_PER_MODEL,
    DEV,
    HEADROOM,
    SWEEP_DIR,
    Profile,
    SweepAborted,
    apply_item_limit,
    build_cells,
    load_cell,
    project_remaining,
    require_fresh,
    run_cell,
)

log = structlog.get_logger(__name__)

GRID_CAP_USD = 8.0

# How often a deadline-bounded sweep prints where it is, in items.
#
# Every item would be 480 lines for a full development sweep and the useful ones would
# be lost in it; only at cell boundaries would be too coarse, because a cell is the
# unit that overruns. The other trigger is not periodic at all: the line ALSO prints
# the moment the projection crosses from on-track to WILL OVERRUN, because that is the
# instant the operator has a decision to make and waiting for the next multiple to tell
# them would be withholding it.
STATUS_EVERY_ITEMS = 20

# The file this pre-registration cites, by name, before the first cell runs.
#
# It used to cite `results/noise_floor_*.json`, and no such file existed in the repo —
# the artifact was on the author's machine and `.gitignore` dropped it. A citation
# printed as provenance that resolves to nothing is the same defect class as the lint
# rule that pointed at a moved path and scanned nothing: it looks like evidence and is
# not checkable. The file is committed now, and a test asserts every repo-relative path
# named in this module exists on disk.
NOISE_FLOOR_PATH = Path("results/noise_floor_seeded.json")
NOISE_FLOOR_CITATION = str(NOISE_FLOOR_PATH)


def _noise_floor_reading(role: str = "agent") -> str:
    """The floor, read out of the cited file rather than restated beside it.

    A number typed next to its own citation is the failure this whole section is warning
    the room about. If the file is absent the line says so instead of quoting a figure
    nothing on disk supports.

    The UPPER BOUND is what gets quoted, not the point estimate. The measurement saw no
    verdict flips in eight items, and "0%" would be a claim the data cannot support —
    the honest reading of zero-in-eight is that the rate is somewhere below the Wilson
    bound, which is wide enough to matter.
    """
    if not NOISE_FLOOR_PATH.is_file():
        return (
            f"NOT ON DISK — {NOISE_FLOOR_PATH} is missing, so this justification cannot "
            f"be shown. The claim above stands or falls on that file."
        )
    body = json.loads(NOISE_FLOOR_PATH.read_text())
    model_id = spec_for(role).model_id
    entry = body["models"].get(model_id)
    if entry is None:
        return (
            f"NOT MEASURED — {NOISE_FLOOR_PATH} carries no reading for {model_id}, "
            f"which is the model this run uses. The floor below is unknown."
        )
    return (
        f"{entry['verdict_flips']} of {entry['n_items']} items changed verdict across "
        f"{entry['n_runs']} runs, so the flip rate is at most "
        f"{entry['verdict_flip_ci95'][1] * 100:.0f}% (Wilson 95%, measured "
        f"{body['measured_on']}). Its SQL TEXT differed on "
        f"{entry['sql_text_differs']} of {entry['n_items']} — the wording moves freely "
        f"while the answer holds, so no comparison here may key on query identity."
    )


def detectable_effect(n: int, baseline: float = 0.5) -> float:
    """Smallest difference in proportion detectable at this n, computed not stated.

    Normal approximation, two-sided alpha=0.05, power 0.80, unpaired worst case. It is
    an approximation and is labelled as one, but the point stands whichever exact form
    is used: at this n the sweep can only see large effects.
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
  RULES WITHHELD vs RULES GIVEN, within each model.
  The same model, the same items, the same loop — the only thing that changes is
  whether the business rules are in the prompt. Within-model, so nothing about the
  models' relative capability enters it.

  This is the primary result, and it was chosen before the cells ran because a
  pilot on a subset already showed it to be the largest effect this design
  produces. Naming it afterwards would be choosing the winner and calling it a
  hypothesis.

NAMED SECONDARY
  Cheap-plus-loops vs frontier-bare, on the held-out items.
  Underpowered by construction — see below — and reported with its discordant-pair
  count so the basis of the claim is visible rather than implied.

  It is PRE-COMMITTED to one of three readings, written down in docs/ before the
  data landed: reached, approached-but-short, or no-gap-to-close. A null here is a
  finding and will be shown as one. No subgroup will be gone looking for.

EXPLICITLY UNDERPOWERED
  Anything that turns on a handful of discordant pairs. Exact McNemar needs six
  discordant pairs all in one direction to clear alpha=0.05, and nine if one pair
  runs the other way. Reported, not concluded from.

DETECTABLE EFFECT SIZE AT n={n_items}
  ~{mde * 100:.0f} percentage points (two-sided alpha=0.05, power 0.80, normal
  approximation, worst case at p=0.5). Differences smaller than that are not
  measurable here, whatever the bars look like.
  The items are clustered by pattern, so the true figure is WORSE than this.

THE SAMPLING FLOOR — applies to every comparison
  Neither scoring model can be pinned to a fixed temperature: both reject a
  non-default sampling parameter with a 400. `seed` is pinned instead, which the
  vendor documents as best-effort rather than a guarantee, so a residual remains
  and it is measured rather than assumed away.
  Measured justification: {NOISE_FLOOR_CITATION}
  {_noise_floor_reading()}

REPLICATES
  Reported separately per model. Two models' determinism floors are two different
  measurements and neither may be asserted for the other.
{'=' * 78}
"""


def run_sweep(items, warehouse: Path, *, profile: Profile = DEV,
              cap_usd: float | None = None, directory: Path = SWEEP_DIR,
              verifier=None, on_cell=None, quiet: bool = False,
              resume: bool = False, item_limit: int | None = None,
              concurrency: int = CONCURRENCY_PER_MODEL,
              warehouse_seed: int | None = None,
              deadline_seconds: float | None = None,
              deadline: Deadline | None = None) -> dict:
    """Run the profile's cells, resuming what is on disk, within a cap and a clock.

    TWO LIMITS, AND THEY FAIL DIFFERENTLY, ON PURPOSE.

    The spend cap RAISES. Breaching it is a mistake — money is spent that was not
    authorised — so the sweep refuses to start the cell that would do it and the
    operator has to decide.

    The deadline RETURNS. Running out of time is not a mistake; it is the expected
    outcome of a fixed session slot, and the sweep's job at that point is to hand back
    whatever it honestly measured. Raising would make a designed ending look like a
    crash in front of a room, and — worse — would push the partial result into an
    exception path where it is easy to drop.

    TWO PARAMETERS FOR THE CLOCK, AND THE FOOTGUN THAT MADE IT TWO.

    `deadline_seconds` is the override — a plain number or None, which is exactly what
    an entry point has after argparse. `deadline` takes a constructed `Deadline` and
    exists so tests can inject a clock instead of sleeping.

    There was one parameter, and it was a live footgun with no guard.
    `deadline=None` and `Deadline(seconds=None)` are DIFFERENT ANSWERS — the first means
    "the caller did not specify, use the profile's", the second means "no clock at all"
    — and they are one keystroke apart. An entry point that wrote
    `Deadline(seconds=args.deadline)` unconditionally would discard the profile's budget
    on every run without the flag, which is every session run, with no error and no
    warning: the wall-clock protection simply absent.

    So the entry point no longer constructs a `Deadline`. It passes the number it has,
    and cannot express "no clock" by accident.
    """
    if deadline is not None and deadline_seconds is not None:
        raise ValueError(
            "pass deadline_seconds (a number, the override) or deadline (a constructed "
            "clock, for tests) — not both. Two clocks is a question about which one "
            "wins, and the answer should never be decided here."
        )
    directory = Path(directory)
    if not resume:
        # BY DEFAULT, and checked before anything else — including the pre-registration.
        # Refusing after printing a hypothesis to the room reads as a crash rather than
        # as a guard. See `StaleCellsPresent` for why the default is this way round.
        require_fresh(directory)
    # The profile's own item cap, and the refusal when --limit is not permitted here.
    # Applied in the runner so no caller can report a trimmed run as a full profile.
    items = apply_item_limit(items, profile, item_limit)
    cells = build_cells(profile)
    cap_usd = profile.cap_usd if cap_usd is None else cap_usd
    projected = project_remaining(cells, len(items))
    if not quiet:
        print(pre_registration(len(items)), flush=True)
        print(f"PROFILE: {profile.name} — {len(cells)} cells, "
              f"{len(profile.roles)} model(s), {profile.replicates} replicate(s)")
        print(f"  {profile.note}")
        print(f"  projected est. ${projected:.4f} against a ${cap_usd:.2f} cap\n", flush=True)

    # One fingerprint for the invocation, stamped into every cell it writes. Resolved
    # against what is already on disk so a RESUMED sweep keeps the id it is resuming —
    # resume is this runner's whole point, and a fresh id per invocation would make the
    # development run impossible to freeze. See loopeng.sweep.fingerprint.
    fingerprint = resolve_run_id(
        RunFingerprint.for_run(items, warehouse_seed=warehouse_seed), directory
    )

    # The projection is only meaningful once `concurrency` items have landed — see
    # `Deadline.warmup`. Carried on a copy rather than set on the caller's object: a
    # function that mutates an argument to configure itself makes the caller's next use
    # of it depend on whether this ran.
    # The profile's clock unless the caller brought one. `--deadline` overrides for a
    # rehearsal on a shorter budget; typing nothing gets the slot the profile declares,
    # which is the whole reason it lives on the profile — see `Profile.deadline_seconds`.
    if deadline is None:
        # The override if the caller gave one, otherwise the profile's own budget. A
        # profile that declares no clock yields `Deadline(seconds=None)`, which never
        # expires — see `Profile.deadline_seconds` for why `dev` is that way.
        seconds = (deadline_seconds if deadline_seconds is not None
                   else profile.deadline_seconds)
        deadline = Deadline(seconds=seconds)
    deadline = replace(deadline, warmup=concurrency)
    if not quiet and deadline.seconds is not None:
        print(f"DEADLINE: {deadline.seconds:.0f}s. Cells are started only while there "
              f"is time left; the one in flight stops between items and keeps what it "
              f"measured.\n", flush=True)

    spent = 0.0
    completed, skipped = [], []
    not_run: list[str] = []
    stopped_at_deadline = False
    interrupted = False
    # Sweep-wide, not per cell: the operator's question is whether the SWEEP finishes,
    # and a cell that is on track inside a sweep that is not would answer the wrong one.
    # Mutable and shared rather than closed over per cell: `items_total` shrinks when a
    # cell resumes, and a per-iteration closure would capture the loop variable — which
    # ruff flags, correctly, as the shape where a callback reads a value that has moved
    # on since it was written.
    clock = {"total": len(items) * len(cells), "done": 0, "at": 0, "overrun": None}

    def _progress(_partial) -> None:
        """One item landed anywhere in the sweep. Print only when it changes a decision."""
        clock["done"] += 1
        if quiet or deadline.seconds is None:
            return
        done, total = clock["done"], clock["total"]
        overrun = deadline.will_overrun(done, total)
        if overrun != clock["overrun"] or done - clock["at"] >= STATUS_EVERY_ITEMS:
            clock.update(at=done, overrun=overrun)
            print(f"      {deadline.status(done, total)}", flush=True)

    for index, cell in enumerate(cells):
        # Checked before the cell starts, like the cap, and for the same reason: a
        # limit enforced after the fact is a limit that has already been breached.
        if deadline.expired():
            stopped_at_deadline = True
            not_run = [c.key for c in cells[index:]]
            if not quiet:
                print(f"\nDEADLINE REACHED after {deadline.elapsed:.0f}s — not "
                      f"starting '{cell.label}'. {len(not_run)} cell(s) will not run: "
                      f"{', '.join(not_run)}", flush=True)
            break

        # `expect_items` is what stops one profile resuming another's cells. See
        # `load_cell`: the key encodes neither profile nor item count, and every
        # profile defaults to the same directory.
        cached = load_cell(cell, directory, expect_items=len(items))
        if cached:
            spent += cached["cost_usd"]["value"]
            completed.append(cached)
            skipped.append(cell.key)
            # A resumed cell cost no time, so it must not count toward the rate the
            # projection extrapolates from. Removed from the denominator rather than
            # added to the numerator: counting it as instantly-done work would make
            # the sweep look faster than it is and hide a real overrun.
            clock["total"] -= len(items)
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
        report = run_cell(cell, items, warehouse, directory=directory,
                          concurrency=concurrency, fingerprint=fingerprint,
                          deadline=deadline, on_progress=_progress, **kwargs)
        # Before the branches below, so an interrupted cell's spend is counted like
        # every other cell's. It used to reach here through an exception and be
        # skipped — see `run_cell`.
        spent += report["cost_usd"]["value"]
        completed.append(report)
        if on_cell:
            on_cell(report)
        if not quiet:
            print(f"      {report['silent_error_rate']}  "
                  f"est. ${report['cost_usd']['value']:.4f}  {report['seconds']}s", flush=True)
        if report["interrupted"]:
            # Ctrl-C is an operator decision, like the deadline and unlike the spend
            # cap, so the sweep RETURNS what it has rather than raising past it — a
            # partial result reached through an exception is a partial result somebody
            # drops.
            interrupted = True
            not_run = [c.key for c in cells[index + 1:]]
            if not quiet:
                print(f"\nINTERRUPTED after {deadline.elapsed:.0f}s during "
                      f"'{cell.label}': {report['n_items']} of "
                      f"{report['n_requested']} items measured and written. "
                      f"{len(not_run)} later cell(s) will not run.", flush=True)
            break
        if report["stopped_early"]:
            # The cell itself was cut. Every later cell is unreachable by definition —
            # the clock that stopped this one has not restarted.
            stopped_at_deadline = True
            not_run = [c.key for c in cells[index + 1:]]
            if not quiet:
                print("\n" + mid_cell_message(cell.label, report, not_run), flush=True)
            break

    return {
        "profile": profile.name, "n_cells": len(cells),
        "n_resumed": len(skipped), "resumed": skipped,
        "projected_usd": round(projected, 6),
        "spend_usd": {"value": round(spent, 6), "source": "estimated"},
        "cap_usd": cap_usd, "concurrency": concurrency,
        # The clock, reported like the money: what was allowed, what was used, and what
        # did not happen as a result. `cells_not_run` is named rather than counted so
        # the gap between `n_cells` and `len(cells)` never has to be inferred.
        "deadline_seconds": deadline.seconds,
        "elapsed_seconds": round(deadline.elapsed, 1),
        "stopped_at_deadline": stopped_at_deadline,
        "interrupted": interrupted,
        "cells_not_run": not_run,
        "run_fingerprint": fingerprint.as_dict(), "cells": completed,
    }


def mid_cell_message(label: str, report: dict, not_run: list[str]) -> str:
    """What the operator reads at the moment a cell is cut short.

    A function so it can be asserted on without a live sweep. The first version ended
    "0 later cell(s) will not run" whenever the stop landed in the final cell — a zero
    rendered as a statement about something that did not happen, which is the one
    sentence shape this project spends its whole time removing.
    """
    tail = (f" {len(not_run)} later cell(s) will not run."
            if not_run else " It was the last cell.")
    return (f"DEADLINE REACHED mid-cell: {label!r} measured {report['n_items']} of "
            f"{report['n_requested']} items and stopped.{tail}")


def describe_outcome(report: dict) -> str:
    """How a finished sweep describes itself, deadline or no deadline.

    Here rather than in the entry point because the demo files are thin by rule and
    lint-checked for it — and the rule earned its keep on this very change: the first
    version of this text went into `demos/.../sweep.py` and pushed it past the budget.
    A block that decides what a partial measurement is allowed to claim is not argument
    wiring.
    """
    lines = []
    if report.get("interrupted"):
        lines.append(f"INTERRUPTED after {report['elapsed_seconds']:.0f}s.")
        lines.append("  Every item that finished is on disk, including the ones that "
                     "were in flight when you pressed Ctrl-C.")
        finished = [c for c in report["cells"] if c["complete"]]
        partial = [c for c in report["cells"] if c.get("interrupted")]
        for cell in partial:
            lines.append(f"  partial   : {cell['label']} — {cell['n_items']} of "
                         f"{cell['n_requested']} items")
        if report["cells_not_run"]:
            lines.append(f"  not run   : {', '.join(report['cells_not_run'])}")
        # Only when there is something to resume FROM. "Re-run with --resume" said to
        # an operator whose interrupt landed in the first cell is advice that does
        # nothing, and advice that does nothing is how a flag gets a reputation.
        lines.append(
            f"  {len(finished)} cell(s) completed; --resume continues from those."
            if finished else
            "  No cell completed, so there is nothing to resume from — re-running "
            "starts from the beginning."
        )
    elif report["stopped_at_deadline"]:
        lines.append(
            f"STOPPED AT THE DEADLINE after {report['elapsed_seconds']:.0f}s of "
            f"{report['deadline_seconds']:.0f}s."
        )
        # "measured: 2 of 2 cells" was the first version, and on a run whose second
        # cell was cut at 5 of 8 items it was the most misleading line on the screen:
        # 2-of-2 is what a COMPLETE sweep says. A cell that ran and a cell that
        # finished are different things, so they are counted separately and only the
        # categories that happened are listed.
        partial = [cell for cell in report["cells"] if cell.get("stopped_early")]
        counts = [(len(report["cells"]) - len(partial), "complete"),
                  (len(partial), "partial"),
                  (len(report["cells_not_run"]), "never started")]
        lines.append("  cells    : " + ", ".join(f"{n} {name}" for n, name in counts if n)
                     + f" (of {report['n_cells']})")
        if report["cells_not_run"]:
            lines.append(f"  not run  : {', '.join(report['cells_not_run'])}")
        for cell in partial:
            lines.append(f"  partial  : {cell['label']} — {cell['n_items']} of "
                         f"{cell['n_requested']} items")
        lines.append("  The charts render from what landed and carry the reduced n. "
                     "Nothing was estimated for the items that never ran.")
    else:
        lines.append(f"complete: {report['profile']} profile, {report['n_cells']} cells "
                     f"({report['n_resumed']} resumed from disk)")
    lines.append(f"spend: est. ${report['spend_usd']['value']:.4f} "
                 f"of ${report['cap_usd']:.2f}")
    return "\n".join(lines)


def load_all(directory: Path = SWEEP_DIR) -> list[dict]:
    """Every cell on disk, complete or not. Charts read this.

    A summary that cannot be parsed is REBUILT from its row log rather than skipped,
    and the rebuilt cell is stamped `recovered_from_log` so nothing downstream mistakes
    it for one that was written normally. Skipping it silently would be the failure
    this whole directory exists to prevent: a chart short one cell, with nothing on it
    saying which.

    If there is no log either, the exception propagates. That is corruption, not an
    interrupted write, and a chart drawn over an unreadable directory is worse than a
    traceback naming the file.
    """
    directory = Path(directory)
    if not directory.is_dir():
        return []
    cells = []
    for path in sorted(directory.glob("*.json")):
        try:
            cells.append(json.loads(path.read_text()))
            continue
        except json.JSONDecodeError:
            recovered = _rebuild_from_log(path)
            if recovered is None:
                raise
            cells.append(recovered)
    return cells


def _rebuild_from_log(summary_path: Path) -> dict | None:
    """Re-derive a cell from its append-only rows, or None if there are none."""
    from loopeng.sweep.runner import Cell, read_rows, summarise_cell

    log = summary_path.with_suffix(".jsonl")
    rows, dropped = read_rows(log)
    if not rows:
        return None
    cell = Cell.from_key(summary_path.stem)
    rebuilt = summarise_cell(cell, rows, complete=False, seconds=0.0, interrupted=True,
                             n_requested=len(rows) + dropped)
    rebuilt["recovered_from_log"] = {"rows": len(rows), "dropped_partial_lines": dropped}
    return rebuilt
