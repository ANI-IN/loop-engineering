"""The 8-cell sweep: resumable, progressive, and self-aborting on PROJECTED spend.

Three properties matter more than the numbers it produces.

**It resumes from `results/`, not from LangSmith.** Gate 0 measured that LangSmith
re-runs everything on restart rather than skipping completed work, so a cell that
finished is a file on disk and nothing else is consulted. A dropped connection costs
the cell in flight, never the cells behind it.

**It aborts on projected spend, not on actual.** Checking actual spend against the cap
only discovers the breach after it happened. Before every cell the runner adds what it
has already spent to what the remaining cells are projected to cost, and refuses to
start if that total exceeds the cap. Aborting in front of a room mid-sweep is the
failure this design exists to avoid.

**Incomplete cells are never blank, never zero, and never a guess.** A cell in progress
reports "in progress, n=NN so far" with the interval over what has landed. A zero on a
chart reads as a measurement.
"""

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

import structlog

from loopeng.agent.classify import (
    BAND_CORRECT,
    BAND_SILENT,
    BAND_UNEARNED,
    BAND_VISIBLE,
    Outcome,
    VisibleKind,
    band_counts,
    band_of,
    judge,
)
from loopeng.agent.loop import run_question
from loopeng.gold.build import json_default, spread_across_clusters
from loopeng.metric import Metric
from loopeng.pricing import prices_for
from loopeng.registry import spec_for
from loopeng.sweep.deadline import Deadline, run_bounded
from loopeng.sweep.fingerprint import FINGERPRINT_FIELD, RunFingerprint
from loopeng.verify.batch import as_agent_run
from loopeng.verify.governance import verify_governed
from loopeng.verify.loop import run_verified

log = structlog.get_logger(__name__)

SWEEP_DIR = Path("results/sweep")

# Per-model pools. Far below any ceiling this project has come near; it exists to be
# predictable rather than to avoid a limit.
#
# This used to read "the measured ceiling is 10,000 requests/minute per model
# (results/gate0.json)". That file is not in the repository — it was removed with the
# rest of the stored results — so the citation resolved to nothing while still reading
# as provenance, which is the same defect the pre-registration's noise-floor citation was
# fixed for. The measurement was also taken on one account against a different vendor,
# and a cloner on a lower tier has a smaller pool than either number describes.
#
# It is now the DEFAULT rather than the only value. README §18 tells the operator to
# "lower the per-model concurrency before the sweep rather than after it starts failing",
# and doing that required editing this line — advice that can only be followed by patching
# source is advice most people will not follow. `--concurrency` on the sweep entry point
# passes through to here. It matters more now than it did: the ceilings were measured on
# one account, and a cloner on a lower tier has a smaller pool than the one this number
# was chosen against.
CONCURRENCY_PER_MODEL = 8

# Measured per-call token shapes, 2026-09-07, on the models the registry now names.
# Used ONLY to project spend before running, never to report it — reported cost
# always comes from actual usage.
#
# Input is identical across roles because the prompt is: the same rendered schema
# and rules go to both, and nothing per-role is added. Output is where they diverge,
# and the divergence is not symmetric — the reference model writes far MORE at L0
# than at L3, because with the rules withheld it reasons about what it has not been
# told. That is a measurement, and it is the reason a reference L0 cell costs more
# than a reference L3 one despite answering fewer items correctly.
SHAPES = {
    ("agent", "L3"): (552, 157),
    ("agent", "L0"): (246, 154),
    ("reference", "L3"): (552, 166),
    ("reference", "L0"): (246, 286),
}
CALLS_PER_ITEM = {("one_shot", "L3"): 1.0, ("one_shot", "L0"): 1.0,
                  ("loop", "L3"): 1.16, ("loop", "L0"): 1.9}
HEADROOM = 1.3

# Token classes carried into a cell report. The two cache fields were missing, which made
# a cell's own file unable to answer whether caching fired in it — the accounting existed
# in `usage.py` all the way to here and was then dropped at the last step. Additive: a
# cell written before this simply has no cache keys, and every reader treats absence as
# "caching did not apply" rather than as a zero.
TOKEN_FIELDS = (
    "n_calls", "input_tokens", "output_tokens", "total_tokens",
    "cache_creation_input_tokens", "cache_read_input_tokens",
)


@dataclass(frozen=True)
class Profile:
    """What a sweep run is FOR. Three of them, and they are not interchangeable.

        smoke    prove the pipeline on YOUR key, for a few cents
        session  what runs in front of a room, inside a fixed slot
        dev      run once to establish the findings, offline, no clock

    **Every ceiling this profile has is a PROPERTY OF THE PROFILE, not a flag.** The
    item count, the spend cap and now the wall-clock budget are all declared here,
    because a limit that depends on someone remembering to type it is not a limit —
    the argument `item_limit` already carried, applied to the other two.

    `exhibit` is gone. Its note read "every figure is a stored measurement rendered
    with its date", which describes a capability that was removed: there is no stored
    cell format, no loader and no flag. A profile for a system that does not exist is
    a profile that will eventually be selected.

    The findings this docstring used to quote were measured on two models this build
    no longer contains, with a p-value typed into prose. They are gone rather than
    restated: a profile note describing a system that does not exist is worse than a
    profile note that says less.
    """

    name: str
    roles: tuple[str, ...]
    replicates: int
    cap_usd: float
    runs_ablation: bool
    note: str
    # Which prompt levels this profile measures. Both, except for `smoke`, whose whole
    # job is to prove the pipeline for pennies rather than to measure the L0/L3 gap.
    levels: tuple[str, ...] = ("L0", "L3")

    # How many gold items a cell runs. None means all of them.
    #
    # Declared on the profile rather than left to a flag, because a cost ceiling that
    # depends on someone remembering to type `--limit` is not a ceiling.
    item_limit: int | None = None

    # Whether `--limit` may override the above. `demos/.../sweep.py` documented the
    # flag as "(development only)" and then applied it to every profile — a declared
    # restriction nothing enforced, in the tool that runs the sweep. Now it is a
    # property of the profile and the flag is refused where the docs said it was.
    allows_limit: bool = False

    # The wall-clock budget, in seconds. None means no clock.
    #
    # On the profile for the same reason `item_limit` is: the sweep launches inside a
    # slot that ends whether it is finished or not, and a deadline that has to be typed
    # is a deadline that will be forgotten at the venue — which is the one place it
    # matters. `--deadline` still overrides, for a rehearsal on a shorter clock.
    #
    # `dev` has none deliberately. It is run once, alone, with nothing waiting on it,
    # and a partial dev sweep is a worse outcome than a slow one.
    deadline_seconds: float | None = None


SESSION = Profile(
    name="session",
    roles=("agent",),
    replicates=1,
    cap_usd=0.75,
    runs_ablation=False,
    # THE SLOT, not a guess. The sweep launches at minute 95 of the session and the
    # next stage begins at 165 whether it has finished or not, so 70 minutes is the
    # budget it actually has. Declared here so the operator cannot start it without
    # one; `--deadline` shortens it for a rehearsal.
    #
    # Measured throughput says this is not tight: a cell of 8 items at concurrency 2
    # ran in 9.8-14.5s across three live runs, i.e. roughly 1.1-1.8 s/item at that
    # concurrency, and the session default is four times that concurrent. The deadline
    # is here to bound the tail — a rate-limited or degraded API — rather than to trim
    # an expected overrun.
    deadline_seconds=70 * 60,
    note=(
        "The agent role only: 4 cells (L0/L3 x one-shot/loop), 1 replicate, every "
        "held-out item. This is what runs in front of a room, and its cost and its "
        "clock are both hard constraints rather than targets."
    ),
)

DEV = Profile(
    name="dev",
    roles=("agent", "reference"),
    replicates=3,
    # Raised from 8.00, and the reason is the model policy rather than a change of
    # appetite. The reference role is now a frontier model at $10/$50 per million
    # against the $2/$10 this cap was sized for, and it writes MORE at L0 than at L3
    # — so the same twelve cells project est. $9.38 where they used to project under
    # eight. A cap that the profile's own projection cannot clear is not a budget,
    # it is a profile that refuses to start.
    #
    cap_usd=12.0,
    runs_ablation=True,
    allows_limit=True,
    # No clock. See `Profile.deadline_seconds`: this is run once, alone, with nothing
    # waiting on it, and a partial dev sweep is worse than a slow one.
    note=(
        "Both models, replicates on both L0 loop cells, ablation, every held-out item. "
        "Run ONCE to establish the findings — not per session. Re-running it per "
        "delivery would spend an order of magnitude more to re-measure things that are "
        "properties of the setup rather than results."
    ),
)

SMOKE = Profile(
    name="smoke",
    roles=("agent",),
    levels=("L0",),
    replicates=1,
    cap_usd=0.05,
    runs_ablation=False,
    item_limit=8,
    allows_limit=True,
    note=(
        "Two cells (L0 one-shot, L0 loop) on the agent model, 8 items, a few cents. "
        "It measures "
        "nothing worth quoting — 8 items cannot separate anything — and that is not "
        "what it is for. It proves the whole pipeline on YOUR key: real calls, cells on "
        "disk, charts rendered, and the delta computed against the stored baseline. The "
        "smallest live path used to be the session profile over every gold item, so a "
        "first-time cloner had no way to spend two cents finding out whether their key "
        "worked."
    ),
    # A cloner's first command should not be able to hang. Five minutes is far longer
    # than three measured runs of this profile took (28s, 21s and a deliberately
    # deadline-stopped 16s) and exists so a degraded or rate-limited API produces a
    # partial answer with an honest n rather than a terminal that never returns.
    deadline_seconds=5 * 60,
)

PROFILES = {p.name: p for p in (SMOKE, SESSION, DEV)}


class LimitNotAllowed(RuntimeError):
    """`--limit` was passed to a profile that does not accept it.

    The flag was documented "(development only)" and applied unconditionally, so a
    delivery run could be silently cut to a handful of items and still be reported as
    delivery. Refused rather than ignored: an operator who typed a flag should be told
    it did nothing, not left to assume it worked.
    """


def resolve_item_limit(profile: Profile, requested: int | None) -> int | None:
    """The item cap for this run. Raises when the flag is not permitted here."""
    if requested is None:
        return profile.item_limit
    if not profile.allows_limit:
        allowed = sorted(p.name for p in PROFILES.values() if p.allows_limit)
        raise LimitNotAllowed(
            f"--limit is not accepted by the '{profile.name}' profile. Profiles that "
            f"accept it: {', '.join(allowed)}.\n"
            f"A cell run over fewer items than the profile declares is not that "
            f"profile's measurement, and reporting it as one is how a number nobody "
            f"can reproduce ends up on a chart."
        )
    return requested


def apply_item_limit(items, profile: Profile, requested: int | None = None) -> list:
    """The items this profile may run, with the limit rule enforced HERE.

    Enforced in the runner rather than at the call site: the caller that forgets is the
    one that reports a five-item run as a delivery measurement, and every caller —
    demos, tests, the orchestrator — should get the same refusal.
    """
    limit = resolve_item_limit(profile, requested)
    items = list(items)
    if limit is None or limit >= len(items):
        return items
    return spread_across_clusters(items, limit)


@dataclass(frozen=True)
class Cell:
    role: str
    level: str
    mode: str
    replicate: int = 0

    @property
    def key(self) -> str:
        return f"{self.role}_{self.level}_{self.mode}_r{self.replicate}"

    @property
    def label(self) -> str:
        """What a reader sees on the axis. **The model name is DERIVED, not typed.**

        This read `"Haiku" if self.role == "agent" else "Sonnet"`, and both names were
        wrong: the roles resolve to a different vendor's models entirely now. Every
        dial and cost chart in the sweep was labelling its bars with the models from
        two registries ago, and nothing failed, because a hardcoded string cannot
        disagree with anything.

        The same defect was found and fixed on the trap grid earlier in this build.
        Finding it a second time, in a second renderer, is the argument for the rule
        rather than for the fix: a label that RESTATES configuration goes stale
        silently, and the only version that cannot is the one that reads it.
        """
        mode = "one-shot" if self.mode == "one_shot" else "loop"
        rep = f" (rep {self.replicate + 1})" if self.replicate else ""
        return f"{spec_for(self.role).model_id} · {self.level} · {mode}{rep}"

    @classmethod
    def from_key(cls, key: str) -> "Cell":
        """The inverse of `.key`. Raises on anything that is not one.

        Parsed from BOTH ENDS rather than by splitting on underscores, because `mode`
        contains one: `agent_L0_one_shot_r0` splits into five pieces, not four, and a
        naive `rsplit("_", 3)` reads the role as "agent_L0" without noticing.

        `test_every_cell_key_round_trips` runs this over every key `build_cells`
        produces for every profile, so the two halves cannot drift.
        """
        role, _, rest = key.partition("_")
        level, _, rest = rest.partition("_")
        mode, _, replicate = rest.rpartition("_")
        if not (role and level and mode and replicate.startswith("r")):
            raise ValueError(
                f"{key!r} is not a cell key; expected role_level_mode_rN"
            )
        try:
            return cls(role=role, level=level, mode=mode,
                       replicate=int(replicate[1:]))
        except ValueError as exc:
            raise ValueError(
                f"{key!r} is not a cell key; expected role_level_mode_rN"
            ) from exc

    def projected_usd(self, n_items: int) -> float:
        inp, out = SHAPES[(self.role, self.level)]
        calls = CALLS_PER_ITEM[(self.mode, self.level)]
        return n_items * calls * prices_for(spec_for(self.role).model_id).cost_usd(
            input_tokens=inp, output_tokens=out
        )


def build_cells(profile: Profile = DEV) -> tuple[Cell, ...]:
    """The cells this profile runs.

    Replicates go on BOTH L0 loop cells when there are two models, not one.

    The reason USED to be that the models had different determinism floors — one pinned
    to temperature=0 and one that could not be. Under the current model policy neither
    scoring model accepts a pinned temperature, so that asymmetry is gone and the
    replicates are no longer measuring two different KINDS of residual.

    They still go on both, for a weaker but sufficient reason: the floors are the same
    in kind and not necessarily in size, and a residual measured on one model is not a
    measurement of the other's. At delivery there is one model and one replicate.
    """
    cells = []
    for role in profile.roles:
        for level in profile.levels:
            for mode in ("one_shot", "loop"):
                reps = profile.replicates if (mode == "loop" and level == "L0") else 1
                for replicate in range(reps):
                    cells.append(Cell(role, level, mode, replicate))
    return tuple(cells)


def project_remaining(cells, n_items: int) -> float:
    return sum(cell.projected_usd(n_items) for cell in cells) * HEADROOM


class SweepAborted(RuntimeError):
    """Projected spend would breach the cap. Raised BEFORE the cell runs."""


class StaleCellsPresent(RuntimeError):
    """Completed cells are already on disk and `--resume` was not passed.

    THE DEFAULT IS INVERTED, AND THAT IS THE POINT.

    This used to fire only when the operator typed `--fresh`. So the dangerous
    behaviour was the default: run the sweep in a directory that already holds finished
    cells and it resumes, completes in about a second, and renders a full set of
    numbers to a room that was told thirty seconds earlier that nothing here is
    precomputed. Every figure on screen would be correct, and the sentence said over
    them would be false.

    Two correct requirements collide, which is why the guard exists at all. Cell files
    must be PRESENT on the venue machine — they are the insurance that stages 0, the
    Phase 2 probes and stage 4 still run if the model API is unreachable. And they must
    be ABSENT when the live sweep starts.

    A guard you have to remember to switch on is a checklist line, and a checklist line
    is not enforcement — which is the defect this entire project is about. Having it
    behind `--fresh` was that defect, in the guard against that defect. So the safe
    behaviour is what you get by typing nothing, and RESUMING is what you now have to
    ask for by name.

    It refuses rather than deleting. Silently removing the outage insurance to satisfy a
    flag would trade one failure for a worse one, and the operator is the only one who
    knows whether those files are still needed.
    """


def completed_cells(directory: Path) -> list[str]:
    """Keys of cells already finished on disk. The thing --fresh refuses to run over."""
    directory = Path(directory)
    if not directory.is_dir():
        return []
    keys = []
    for path in sorted(directory.glob("*.json")):
        try:
            body = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if body.get("complete"):
            keys.append(body.get("key", path.stem))
    return keys


def require_fresh(directory: Path) -> None:
    """Raise unless the directory holds no completed cells. Runs by DEFAULT."""
    stale = completed_cells(directory)
    if stale:
        raise StaleCellsPresent(
            f"{len(stale)} completed cell(s) already in {directory}: "
            f"{', '.join(stale[:4])}{'…' if len(stale) > 4 else ''}.\n"
            "\nStarting here would RESUME from those files: the sweep would finish in "
            "about a second and render a full set of numbers that look computed and "
            "were not. Every figure would be correct and the sentence said over them "
            "would be false.\n"
            "\nThese files are also the outage insurance for stages 0, 2-probes and 4, "
            "so this refuses rather than deleting them. Pick one:\n"
            "\n  build it live, which is the session path:\n"
            f"      rm -rf {directory}\n"
            "\n  continue an interrupted run:\n"
            "      --resume\n"
            "\n  keep both:\n"
            "      --dir <somewhere else>"
        )


def cell_path(cell: Cell, directory: Path = SWEEP_DIR) -> Path:
    return Path(directory) / f"{cell.key}.json"


def rows_path(cell: Cell, directory: Path = SWEEP_DIR) -> Path:
    """The append-only row log for a cell. One JSON object per line, in landing order.

    WHY A SECOND FILE, WHEN THE SUMMARY ALREADY HELD THE ROWS

    The summary was rewritten in full after every item: `path.write_text(json.dumps(
    whole_cell))`, sixty times for a sixty-item cell. Two problems, and the second is
    the one that matters.

    It is O(n^2) writes, which is merely wasteful. But `write_text` TRUNCATES AND THEN
    WRITES, so between those two steps the only record of the cell on disk is an empty
    file, and a crash or a Ctrl-C landing in that window leaves a truncated JSON
    document. `load_all` would then raise `JSONDecodeError` for the whole directory —
    every chart in the session, lost to an interrupt that happened to arrive during a
    write to one cell.

    An append is different in kind. Each row is one line, written and flushed at the
    end of the file; nothing that already landed is ever rewritten, so no window exists
    in which earlier items are unreadable. At worst an interrupt truncates the LAST
    line, and `read_rows` drops exactly that one and says so.

    The summary is still written, because it is what the charts read — but it is now
    derived from the log and written atomically, and it can be rebuilt if it is lost.
    """
    return Path(directory) / f"{cell.key}.jsonl"


def append_row(path: Path, row: dict) -> None:
    """Append one row and flush it. The durable record of a measured item."""
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, default=json_default) + "\n")
        handle.flush()


def read_rows(path: Path) -> tuple[list[dict], int]:
    """`(rows, dropped)` from a row log. A partial final line is DROPPED AND COUNTED.

    Counted rather than tolerated silently: a run whose last line was cut off measured
    one item it cannot account for, and the difference between "59 items" and "59 items
    plus one we lost" is exactly the kind of thing this project refuses to round off.

    Only the LAST line may be partial — an append that got part-way. A malformed line
    anywhere else is a different fault and raises, because that is corruption rather
    than an interrupted write.
    """
    if not Path(path).is_file():
        return [], 0
    lines = [line for line in Path(path).read_text(encoding="utf-8").splitlines() if line]
    rows, dropped = [], 0
    for index, line in enumerate(lines):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            if index == len(lines) - 1:
                dropped = 1
                break
            raise
    return rows, dropped


def write_json_atomic(path: Path, body: dict) -> None:
    """Write a JSON document so a reader never sees it half-written.

    Same file system, then `os.replace`, which is atomic on POSIX and on Windows for
    an existing destination. The previous version truncated the real file first, so an
    interrupt mid-write destroyed the readable copy on the way to producing the new
    one.
    """
    path = Path(path)
    temporary = path.with_name(f".{path.name}.partial")
    temporary.write_text(json.dumps(body, indent=2, default=json_default),
                         encoding="utf-8")
    os.replace(temporary, path)


def load_cell(cell: Cell, directory: Path = SWEEP_DIR,
              *, expect_items: int | None = None) -> dict | None:
    """A completed cell file for this cell, or None if it must be re-run.

    `expect_items` is how many gold items THIS run intends the cell to cover. A
    stored cell measured over a different number is not the same measurement and
    is refused.

    A cell's key is `role_level_mode_rN` and encodes neither the profile nor the
    item count, while every profile defaults to the same directory. `smoke`'s two
    cells are a strict subset of `delivery`'s, so `--profile smoke` run after a
    delivery run resumed delivery's 50-item cells, reported them as the smoke
    measurement, and made NO MODEL CALLS AT ALL — while printing
    `spend: est. $0.8642 of $0.05`, seventeen times its own cap, and exiting 0.

    That is the precise opposite of what `smoke` is for. Its whole documented
    purpose is to prove the pipeline on YOUR key for a few cents, so a first-time
    cloner following the preflight's next command got a green "complete" with
    zero calls and zero evidence their key worked. `--limit 8` against a directory
    of 50-item cells was the same defect from the other direction.

    A stored cell with no recorded `n_items` predates this field and is allowed to
    resume — the same treatment `fingerprint.of()` already gives a missing
    fingerprint, and the reason is the same: refusing them would silently
    invalidate every measurement committed before the field existed.
    """
    path = cell_path(cell, directory)
    if not path.is_file():
        return None
    body = json.loads(path.read_text())
    if not body.get("complete"):
        return None
    stored = body.get("n_items")
    if expect_items is not None and stored is not None and stored != expect_items:
        return None
    return body


def run_cell(cell: Cell, items, warehouse: Path, *, verifier=verify_governed,
             directory: Path = SWEEP_DIR, on_progress=None,
             concurrency: int = CONCURRENCY_PER_MODEL,
             fingerprint: RunFingerprint | None = None,
             deadline: Deadline | None = None) -> dict:
    """Run one cell, writing partial state as items land so progress is observable.

    `fingerprint` is stamped into the file at write time. It makes run identity a
    recorded fact rather than something `assert_same_run` has to infer from which
    directory a file happens to sit in — see `loopeng.sweep.fingerprint`.

    `deadline` stops the cell BETWEEN items rather than during one — see
    `loopeng.sweep.deadline` for why an item is never cut short and scored. A cell the
    clock stopped is written with `stopped_early`, a reduced `n_items`, and a rate
    string that says the run ended rather than that it is still going.

    **A Ctrl-C RETURNS, it does not re-raise**, and the first version got that wrong in
    a way only a live interrupt showed. Raising after writing the summary looked
    careful — the record was safe on disk — but the report never reached the caller, so
    `run_sweep` could not add the cell's spend to the run total. A real interrupt nine
    seconds into a live sweep printed `spend: est. $0.0000 of $0.05` over a cell that
    had just cost $0.0019. Money spent, reported as zero, by the project whose entire
    argument is that a zero on a report reads as a measurement.

    So an interrupt is reported the way the deadline is: a flag on the returned cell.
    The caller checks `report["interrupted"]` beside `report["stopped_early"]` and
    stops, and the accounting flows through the same path as every other cell.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = cell_path(cell, directory)
    log = rows_path(cell, directory)
    # A fresh run of this cell starts a fresh log. Appending to a previous attempt's
    # rows would double-count every item it managed before it stopped, which is the one
    # way an append-only file can lie.
    log.unlink(missing_ok=True)
    rows: list[dict] = []
    started = time.perf_counter()

    def _one(item):
        if cell.mode == "one_shot":
            run = run_question(item.question, warehouse=warehouse, role=cell.role,
                               level=cell.level, max_attempts=1, item_id=item.item_id)
            judgement = judge(run, item)
            rejections, attempts = 0, len(run.attempts)
        else:
            verified = run_verified(item.question, warehouse=warehouse, rules=item.rules,
                                    role=cell.role, level=cell.level, max_attempts=3,
                                    item_id=item.item_id, verifier=verifier)
            run = as_agent_run(verified)
            judgement = judge(run, item)
            rejections, attempts = verified.rejections, len(verified.attempts)
        return {
            "item_id": item.item_id, "pattern_key": item.pattern_key,
            # SQL and rows are stored so a cell is self-sufficient for triage.
            # Without them a failure can only be counted, not classified, and
            # classifying by cause is the whole point of triage.
            "sql": run.sql, "rows": run.rows, "error": run.error,
            "outcome": str(judgement.outcome),
            # WHICH KIND of visible failure, recorded rather than recomputed.
            #
            # `judge` has always worked this out and `run_cell` has always dropped it,
            # so the sweep — the most expensive measurement path in the project — wrote
            # cells that could be counted by outcome and not classified by cause. Both
            # cheaper paths kept it: `verify/batch.py` and `agent/trap.py` store it, and
            # `triage/failures.py` exists to sort failures by cause. The instrument was
            # built, the number was computed, and the one caller that spends the most
            # money threw it away.
            #
            # None for anything that is not a visible failure, which is most rows.
            "visible_kind": (str(judgement.visible_kind)
                             if judgement.visible_kind else None),
            "ran_and_returned": judgement.ran_and_returned,
            "correct": judgement.outcome is Outcome.CORRECT,
            # Right, and not derivable from what the model was given. Carried
            # separately because it is neither correct nor a silent error, and
            # subtracting it from either would restate a ranking as arithmetic.
            "unearned_correct": judgement.unearned,
            "termination": str(run.termination), "n_attempts": attempts,
            "rejections": rejections, "cost_usd": run.ledger.cost_usd(),
            "tokens": run.ledger.totals(),
        }

    items = list(items)

    def _landed(row: dict) -> None:
        """Record one measured item, durably, before anything else happens.

        THE APPEND COMES FIRST. It is the only write here that cannot lose earlier
        work — see `rows_path` — so an interrupt or a crash at any instant after this
        line leaves the item recorded. The summary that follows is derived and
        replaceable; the log is the measurement.
        """
        append_row(log, row)
        rows.append(row)
        partial = summarise_cell(cell, rows, complete=False,
                                 seconds=time.perf_counter() - started,
                                 fingerprint=fingerprint)
        write_json_atomic(path, partial)
        if on_progress:
            on_progress(partial)

    bounded = run_bounded(items, _one, concurrency=concurrency, deadline=deadline,
                          on_result=_landed)

    # `complete` means EVERY REQUESTED ITEM RAN, which a deadline-stopped cell did not.
    # It stays False so `load_cell` will not resume one as if it were whole and
    # `completed_cells` does not count it — a partial cell must not be able to satisfy
    # a later full run by sitting in the directory.
    report = summarise_cell(
        cell, rows,
        # An interrupted cell is no more complete than a deadline-stopped one, and for
        # the same reason: it did not run what it was asked to.
        complete=not (bounded.stopped_early or bounded.interrupted),
        seconds=time.perf_counter() - started,
        fingerprint=fingerprint,
        stopped_early=bounded.stopped_early,
        interrupted=bounded.interrupted,
        n_requested=bounded.requested,
    )
    write_json_atomic(path, report)
    return report


def visible_kind_counts(rows: list[dict]) -> dict[str, int]:
    """How many failures of each kind, over EVERY kind the enum declares.

    Enumerated, not tallied from what appeared. A dict built only from the kinds present
    reads as "these are the failures there are", and a reader cannot tell a kind that
    fired zero times from one the runner never records — which was true of all seven
    until this run, because the sweep did not store the field at all.

    A row written before `visible_kind` existed has no key, and a visible failure with
    no kind is counted under `unclassified` rather than dropped: an item that failed
    visibly and cannot say how is a real state, and silently omitting it would shrink
    the total below the band count and make the two disagree.
    """
    counts = {kind.value: 0 for kind in VisibleKind}
    counts["unclassified"] = 0
    for row in rows:
        if band_of(row["outcome"]) != BAND_VISIBLE:
            continue
        kind = row.get("visible_kind")
        counts[kind if kind in counts else "unclassified"] += 1
    return counts


def _partial_rate(metric: Metric, n_ran: int, stopped_early: bool,
                  interrupted: bool = False) -> str:
    """How an incomplete cell describes its own rate.

    "in progress, n=NN so far" is a promise that the number will move. It is true of a
    cell mid-flight and false of a cell the deadline ended, and the two used to render
    identically — so a stopped cell invited a room to keep waiting on a figure that was
    already final.
    """
    if interrupted:
        return f"interrupted, final at n={n_ran} — {metric.render()}"
    if stopped_early:
        return f"stopped at the deadline, final at n={n_ran} — {metric.render()}"
    return f"in progress, n={n_ran} so far — {metric.render()}"


def summarise_cell(cell: Cell, rows: list[dict], *, complete: bool, seconds: float,
                   fingerprint: RunFingerprint | None = None,
                   stopped_early: bool = False,
                   interrupted: bool = False,
                   n_requested: int | None = None) -> dict:
    """One cell as a dict. **Three states, not two.**

    `complete` was a boolean and the renderers read `not complete` as "in progress,
    more is coming". A deadline-stopped cell is neither: it is finished, at a smaller
    n, and will not grow. Rendering it as in-progress would tell a room watching the
    charts to wait for a number that is never going to arrive.

        complete=True                    ran every item it was asked for
        complete=False, stopped_early    the clock ended it; this n is final
        complete=False, interrupted      Ctrl-C ended it; this n is final
        complete=False                   still running; the n is still moving

    `interrupted` and `stopped_early` are both "final at a smaller n" and are kept
    apart because they are different facts about the run: one is the design working,
    the other is a person deciding. A reader looking at a short cell should be able to
    tell which without asking.
    """
    ran = [r for r in rows if r["ran_and_returned"]]
    # Counted by enumeration, never derived. `silent = len(ran) - correct` swept an
    # unearned correct into the silent-error band the moment that outcome existed —
    # a right answer counted as a wrong one, on the headline metric, silently. See
    # OUTCOME_BANDS in loopeng.agent.classify for why the mapping is total.
    bands = band_counts(r["outcome"] for r in rows)
    correct = bands[BAND_CORRECT]
    unearned = bands[BAND_UNEARNED]
    silent = bands[BAND_SILENT]
    metric = Metric.from_counts(silent, len(ran)) if ran else None
    return {
        "key": cell.key, "label": cell.label, "role": cell.role, "level": cell.level,
        "mode": cell.mode, "replicate": cell.replicate,
        "complete": complete, "seconds": round(seconds, 1),
        # Additive, like the cache token classes: a cell written before this field
        # existed has no key, and absence means "not deadline-stopped" — which is what
        # every cell measured before there was a deadline in fact was.
        "stopped_early": stopped_early,
        "interrupted": interrupted,
        # How many items were ASKED FOR, as distinct from how many ran. Equal unless
        # the clock stopped it, and the pair is what the disclosure is computed from
        # rather than remembered.
        "n_requested": len(rows) if n_requested is None else n_requested,
        # How many items this cell was RUN OVER, as distinct from how many
        # produced an answer. `load_cell` refuses to resume a cell measured over a
        # different number, which is what stops one profile inheriting another's.
        "n_items": len(rows),
        "n_done": len(rows), "ran_and_returned": len(ran),
        "correct": correct, "unearned_correct": unearned, "silent_errors": silent,
        # Every band, so a renderer never has to work one out for itself.
        "bands": bands,
        # Every visible-failure kind, counted by enumeration over the enum rather than
        # over what happened to appear. A kind with no rows is a measured zero here —
        # no failure of that kind occurred — which is different from a band that is
        # absent because nobody thought of it. See `visible_kind_counts`.
        "visible_kinds": visible_kind_counts(rows),
        # Never blank, never zero, never a guess.
        "silent_error_rate": (
            metric.render() if metric and complete
            else (_partial_rate(metric, len(ran), stopped_early, interrupted) if metric
                  else "not yet measured")
        ),
        "rate_value": metric.value if metric else None,
        "rate_ci_low": metric.ci_low if metric else None,
        "rate_ci_high": metric.ci_high if metric else None,
        "rate_n": metric.n if metric else 0,
        "cost_usd": {"value": round(sum(r["cost_usd"] for r in rows), 6),
                     "source": "estimated"},
        # `.get(k, 0)` because the two cache fields are additive: a row recorded before
        # they existed simply has none, and a missing class summed as zero is correct —
        # no cache tokens is what "caching did not apply" looks like. Every reader tells
        # that apart from a measured zero by checking whether BOTH are absent.
        "tokens": {k: sum(r["tokens"].get(k, 0) for r in rows) for k in TOKEN_FIELDS}
        if rows else {},
        "rejections": sum(r["rejections"] for r in rows),
        "termination": {t: sum(1 for r in rows if r["termination"] == t)
                        for t in {r["termination"] for r in rows}},
        "patterns_with_interventions": sorted(
            {r["pattern_key"] for r in rows if r["rejections"] > 0}
        ),
        "items": sorted(rows, key=lambda r: r["item_id"]),
        # Additive, like the two cache token classes: a cell written without one simply
        # has no key, and every reader treats absence as "unverifiable" rather than as
        # a match against a default.
        **({FINGERPRINT_FIELD: fingerprint.as_dict()} if fingerprint else {}),
    }
