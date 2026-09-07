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
import time
from dataclasses import dataclass
from pathlib import Path

import structlog

from loopeng.agent.classify import (
    BAND_CORRECT,
    BAND_SILENT,
    BAND_UNEARNED,
    Outcome,
    band_counts,
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

# Per-model pools. The measured ceiling is 10,000 requests/minute per model
# (results/gate0.json); this is far below it and exists to be predictable.
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
    """What a sweep run is FOR. Delivery and development are not the same sweep.

    The delivery profile is what runs in front of a room, and its cost is a hard
    constraint rather than a target. The development profile is what was run once to
    establish the findings; re-running it per delivery would spend an order of
    magnitude more to re-measure things that are properties of the setup, not results.

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


DELIVERY = Profile(
    name="delivery",
    roles=("agent",),
    replicates=1,
    cap_usd=0.75,
    runs_ablation=False,
    note=(
        "The agent role only, 4 cells, 1 replicate. Superseded by the profile set the "
        "conditions use; kept until that lands so no entry point loses its profile."
    ),
)

DEVELOPMENT = Profile(
    name="development",
    roles=("agent", "reference"),
    replicates=3,
    # Raised from 8.00, and the reason is the model policy rather than a change of
    # appetite. The reference role is now a frontier model at $10/$50 per million
    # against the $2/$10 this cap was sized for, and it writes MORE at L0 than at L3
    # — so the same twelve cells project est. $9.38 where they used to project under
    # eight. A cap that the profile's own projection cannot clear is not a budget,
    # it is a profile that refuses to start.
    #
    # PROVISIONAL. This whole profile set is replaced by smoke/session/dev, whose
    # sizes come from measured throughput rather than from what fitted before.
    cap_usd=12.0,
    runs_ablation=True,
    allows_limit=True,
    note="Both models, replicates on both L0 loop cells, ablation. Run once, not per delivery.",
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
        "smallest live path used to be `delivery` at 4 cells x 50 items, so a first-time "
        "cloner had no way to spend two cents finding out whether their key worked."
    ),
)

EXHIBIT = Profile(
    name="exhibit",
    roles=(),
    replicates=0,
    cap_usd=0.0,
    runs_ablation=False,
    note=(
        "A frozen exhibit. Makes ZERO model calls: every figure is a stored measurement "
        "rendered with its date, and the paths that would spend are disabled rather "
        "than hidden. cap_usd is 0.0 so any attempt to run a cell refuses immediately."
    ),
)

PROFILES = {p.name: p for p in (SMOKE, DELIVERY, DEVELOPMENT, EXHIBIT)}


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

    def projected_usd(self, n_items: int) -> float:
        inp, out = SHAPES[(self.role, self.level)]
        calls = CALLS_PER_ITEM[(self.mode, self.level)]
        return n_items * calls * prices_for(spec_for(self.role).model_id).cost_usd(
            input_tokens=inp, output_tokens=out
        )


def build_cells(profile: Profile = DEVELOPMENT) -> tuple[Cell, ...]:
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
    """--fresh was requested and completed cells are already on disk.

    This exists because two correct requirements collide. Cell files must be present on
    the venue machine, because they are the insurance that stages 0, the Phase 2 probes
    and stage 4 still run if the model API is unreachable. And they must be ABSENT when
    the live sweep starts, or it resumes and completes instantly, rendering finished
    numbers to a room that was just told nothing is precomputed.

    A checklist line is not enforcement — that is the defect this whole project is
    about. So the live command carries --fresh and this refuses.

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
    """Raise unless the directory holds no completed cells."""
    stale = completed_cells(directory)
    if stale:
        raise StaleCellsPresent(
            f"{len(stale)} completed cell(s) already in {directory}: "
            f"{', '.join(stale[:4])}{'…' if len(stale) > 4 else ''}.\n"
            "--fresh means the sweep must build in front of the room, and it would "
            "resume from these instead, finishing instantly with numbers that look "
            "computed and were not.\n"
            "These files are also the outage insurance for stages 0, 2-probes and 4, "
            "so this refuses rather than deleting them. Move or remove them yourself:\n"
            f"    rm -rf {directory}"
        )


def cell_path(cell: Cell, directory: Path = SWEEP_DIR) -> Path:
    return Path(directory) / f"{cell.key}.json"


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
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = cell_path(cell, directory)
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
        """Write the cell to disk on every completion, deadline or no deadline.

        This is what makes the stop clean rather than lossy: the file on disk is
        already correct for the items that have landed, so stopping is a matter of
        not starting more.
        """
        rows.append(row)
        partial = summarise_cell(cell, rows, complete=False,
                                 seconds=time.perf_counter() - started,
                                 fingerprint=fingerprint)
        path.write_text(json.dumps(partial, indent=2, default=json_default))
        if on_progress:
            on_progress(partial)

    bounded = run_bounded(items, _one, concurrency=concurrency, deadline=deadline,
                          on_result=_landed)

    # `complete` means EVERY REQUESTED ITEM RAN, which a deadline-stopped cell did not.
    # It stays False so `load_cell` will not resume one as if it were whole and
    # `completed_cells` does not count it — a partial cell must not be able to satisfy
    # a later full run by sitting in the directory.
    report = summarise_cell(cell, rows, complete=not bounded.stopped_early,
                            seconds=time.perf_counter() - started,
                            fingerprint=fingerprint,
                            stopped_early=bounded.stopped_early,
                            n_requested=bounded.requested)
    path.write_text(json.dumps(report, indent=2, default=json_default))
    return report


def _partial_rate(metric: Metric, n_ran: int, stopped_early: bool) -> str:
    """How an incomplete cell describes its own rate.

    "in progress, n=NN so far" is a promise that the number will move. It is true of a
    cell mid-flight and false of a cell the deadline ended, and the two used to render
    identically — so a stopped cell invited a room to keep waiting on a figure that was
    already final.
    """
    if stopped_early:
        return f"stopped at the deadline, final at n={n_ran} — {metric.render()}"
    return f"in progress, n={n_ran} so far — {metric.render()}"


def summarise_cell(cell: Cell, rows: list[dict], *, complete: bool, seconds: float,
                   fingerprint: RunFingerprint | None = None,
                   stopped_early: bool = False,
                   n_requested: int | None = None) -> dict:
    """One cell as a dict. **Three states, not two.**

    `complete` was a boolean and the renderers read `not complete` as "in progress,
    more is coming". A deadline-stopped cell is neither: it is finished, at a smaller
    n, and will not grow. Rendering it as in-progress would tell a room watching the
    charts to wait for a number that is never going to arrive.

        complete=True                    ran every item it was asked for
        complete=False, stopped_early    the clock ended it; this n is final
        complete=False                   still running; the n is still moving
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
        # Never blank, never zero, never a guess.
        "silent_error_rate": (
            metric.render() if metric and complete
            else (_partial_rate(metric, len(ran), stopped_early) if metric
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
