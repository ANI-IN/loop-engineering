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
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import structlog

from loopeng.agent.classify import Outcome, judge
from loopeng.agent.loop import run_question
from loopeng.gold.build import json_default, spread_across_clusters
from loopeng.metric import Metric
from loopeng.pricing import prices_for
from loopeng.registry import spec_for
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

# Measured per-call token shapes, 2026-07-29. Used ONLY to project spend before
# running, never to report it — reported cost always comes from actual usage.
SHAPES = {
    ("worker", "L3"): (666, 198),
    ("worker", "L0"): (304, 151),
    ("frontier", "L3"): (1060, 247),
    ("frontier", "L0"): (571, 488),
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

    Haiku alone is enough for delivery because the headline reproduces on it: L0
    one-shot versus L0 loop, p=0.008, with zero items where one-shot was right and the
    loop wrong. The dial's full shape is there. Sonnet was ~78% of sweep cost and its
    cells were underpowered and variance-asymmetric regardless — it cannot be pinned to
    a fixed temperature, so its bars never meant the same thing as Haiku's.
    """

    name: str
    roles: tuple[str, ...]
    replicates: int
    cap_usd: float
    runs_ablation: bool
    note: str
    # Questions the frontier model may answer live, outside the cells. Delivery keeps
    # a small allowance so "Haiku declines, Sonnet takes it" happens in the room
    # rather than being cited — an escalation nobody watches run is a slide.
    escalation_allowance: int = 0

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
    roles=("worker",),
    replicates=1,
    cap_usd=0.75,
    runs_ablation=False,
    escalation_allowance=5,
    note=(
        "Haiku only, 4 cells, 1 replicate, plus a 5-question Sonnet allowance so live "
        "escalation runs in the room. Sonnet's CELLS and the noise floors are REFERENCE "
        "MEASUREMENTS and are never recomputed. The full n=12 escalation measurement and "
        "the ablation are development findings and do not appear in the session."
    ),
)

DEVELOPMENT = Profile(
    name="development",
    roles=("worker", "frontier"),
    replicates=3,
    cap_usd=8.0,
    runs_ablation=True,
    escalation_allowance=12,
    allows_limit=True,
    note="Both models, replicates on both L0 loop cells, ablation. Run once, not per delivery.",
)

SMOKE = Profile(
    name="smoke",
    roles=("worker",),
    levels=("L0",),
    replicates=1,
    cap_usd=0.05,
    runs_ablation=False,
    item_limit=8,
    allows_limit=True,
    note=(
        "Two cells (L0 one-shot, L0 loop), Haiku, 8 items, a few cents. It measures "
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
    escalation_allowance=0,
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
        model = "Haiku" if self.role == "worker" else "Sonnet"
        mode = "one-shot" if self.mode == "one_shot" else "loop"
        rep = f" (rep {self.replicate + 1})" if self.replicate else ""
        return f"{model} · {self.level} · {mode}{rep}"

    def projected_usd(self, n_items: int) -> float:
        inp, out = SHAPES[(self.role, self.level)]
        calls = CALLS_PER_ITEM[(self.mode, self.level)]
        return n_items * calls * prices_for(spec_for(self.role).model_id).cost_usd(
            input_tokens=inp, output_tokens=out
        )


def build_cells(profile: Profile = DEVELOPMENT) -> tuple[Cell, ...]:
    """The cells this profile runs.

    Replicates go on BOTH L0 loop cells when there are two models, not one: the models
    have different determinism floors — Haiku is pinned to temperature=0 and Sonnet
    cannot be — so the replicates measure two different things and neither may be
    asserted for the other. At delivery there is one model and one replicate.
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
             fingerprint: RunFingerprint | None = None) -> dict:
    """Run one cell, writing partial state as items land so progress is observable.

    `fingerprint` is stamped into the file at write time. It makes run identity a
    recorded fact rather than something `assert_same_run` has to infer from which
    directory a file happens to sit in — see `loopeng.sweep.fingerprint`.
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
            "termination": str(run.termination), "n_attempts": attempts,
            "rejections": rejections, "cost_usd": run.ledger.cost_usd(),
            "tokens": run.ledger.totals(),
        }

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        futures = [pool.submit(_one, item) for item in items]
        for future in as_completed(futures):
            rows.append(future.result())
            partial = summarise_cell(cell, rows, complete=False,
                                     seconds=time.perf_counter() - started,
                                     fingerprint=fingerprint)
            path.write_text(json.dumps(partial, indent=2, default=json_default))
            if on_progress:
                on_progress(partial)

    report = summarise_cell(cell, rows, complete=True, seconds=time.perf_counter() - started,
                            fingerprint=fingerprint)
    path.write_text(json.dumps(report, indent=2, default=json_default))
    return report


def summarise_cell(cell: Cell, rows: list[dict], *, complete: bool, seconds: float,
                   fingerprint: RunFingerprint | None = None) -> dict:
    ran = [r for r in rows if r["ran_and_returned"]]
    correct = sum(1 for r in ran if r["correct"])
    silent = len(ran) - correct
    metric = Metric.from_counts(silent, len(ran)) if ran else None
    return {
        "key": cell.key, "label": cell.label, "role": cell.role, "level": cell.level,
        "mode": cell.mode, "replicate": cell.replicate,
        "complete": complete, "seconds": round(seconds, 1),
        # How many items this cell was RUN OVER, as distinct from how many
        # produced an answer. `load_cell` refuses to resume a cell measured over a
        # different number, which is what stops one profile inheriting another's.
        "n_items": len(rows),
        "n_done": len(rows), "ran_and_returned": len(ran),
        "correct": correct, "silent_errors": silent,
        # Never blank, never zero, never a guess.
        "silent_error_rate": (
            metric.render() if metric and complete
            else (f"in progress, n={len(ran)} so far — {metric.render()}" if metric
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
