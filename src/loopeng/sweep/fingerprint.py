"""What makes two cell files the same measurement run — recorded, not inferred.

`assert_same_run` used to establish run identity by directory membership: it compared
the FRONTIER cells against the committed `measurements.json` field for field, and
`build_worker_baseline` then froze whatever `worker_*.json` happened to sit beside them.
So the guard checked six cells and froze six others, and nothing about the six it froze
was verified. A worker cell re-run at any later date — different code, different pricing
table, different gold set — in that directory passed untouched, because the cells the
guard looked at were never involved.

Worker cells are the cheap ones. Re-running one is the single most likely thing to have
happened. A function named `assert_same_run` that checks nothing about the cells it is
freezing is this repository's own subject.

The frozen values do look internally consistent — the L0 cells agree with `prefix_v1` to
within replicate noise while L3 diverges by exactly the documented defect, which is the
signature of one run. But *looking consistent* is what this project refuses to accept as
evidence, so identity is now a fact each cell carries.

WHAT IS IN IT, AND WHY EACH ONE
-------------------------------

  warehouse_seed    the data the questions were answered against
  gold_sha256       the gold set itself: item ids, questions, gold SQL, gold rows. Not
                    `gold.build.cache_key`, which hashes the INPUTS that decide the gold
                    answers rather than the answers — close, but a cache key exists to
                    decide whether to rebuild and this exists to decide whether two
                    measurements are comparable.
  prices_taken_on   every dollar in a cell is tokens times a hand-entered table; a cell
                    priced from a different table is not the same cost measurement
  code_revision     git HEAD, with `+dirty` appended when the tree is not clean. A dirty
                    tree is NOT distinguished from another dirty tree — two different
                    uncommitted states hash the same. That is a real limit and it is
                    named here rather than left for someone to discover.
  run_id            which invocation wrote the cell

RUN ID SURVIVES A RESUME, DELIBERATELY
--------------------------------------

Resume is the runner's whole point: a dropped connection costs the cell in flight, never
the cells behind it. Minting a fresh id per invocation would mean the author's own
development run — twelve cells across however many restarts the venue network forced —
could never be frozen, and a guard that refuses the workflow it is guarding is worse than
no guard.

So `resolve_run_id` adopts the id already on disk **when, and only when, every other
field agrees**. Same code, same gold, same prices, same seed: that is the same run
continuing. Anything else and the invocation keeps its own id, which is precisely the
case worth catching.
"""

import hashlib
import json
import subprocess
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from loopeng.pricing import PRICES_TAKEN_ON

# The key a cell file carries it under. Additive, exactly like the two cache token
# classes before it: a cell written before this existed simply has no such key, and
# every reader treats absence as "unverifiable" rather than as a match.
FINGERPRINT_FIELD = "run_fingerprint"

UNKNOWN_REVISION = "unknown — not a git checkout"

# Everything except `run_id`. Two cells that agree on these came out of the same
# measurement setup; the id then says whether they came out of the same invocation.
INPUT_FIELDS = ("warehouse_seed", "gold_sha256", "prices_taken_on", "code_revision")

_REPO_ROOT = Path(__file__).resolve().parents[3]

# Short enough to read off a terminal, long enough that two runs will not collide.
RUN_ID_CHARS = 12

# git may be absent, may be slow on a network filesystem, and may be pointed at a
# checkout that is not this one. None of that is worth hanging a sweep over.
_GIT_TIMEOUT_S = 5


def _git(*args: str) -> str | None:
    try:
        done = subprocess.run(["git", *args], capture_output=True, text=True,
                              cwd=_REPO_ROOT, timeout=_GIT_TIMEOUT_S, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def code_revision() -> str:
    """git HEAD, marked `+dirty` when the working tree is not clean.

    Returns a named "unknown" rather than an empty string when there is no git: a blank
    revision compares equal to another blank revision, which would make two unrelated
    non-git runs look like one.
    """
    head = _git("rev-parse", "HEAD")
    if head is None or not head.strip():
        return UNKNOWN_REVISION
    status = _git("status", "--porcelain")
    return f"{head.strip()}{'+dirty' if status and status.strip() else ''}"


def gold_digest(items) -> str:
    """A hash of the gold set: what was asked, and what counts as right.

    Sorted by item id first, so the order a set was built in cannot change the digest —
    the sweep runs items through a thread pool and they land in whatever order they land.
    """
    digest = hashlib.sha256()
    for item in sorted(items, key=lambda i: i.item_id):
        for part in (item.item_id,
                     getattr(item, "question", ""),
                     getattr(item, "gold_sql", ""),
                     json.dumps(getattr(item, "gold_rows", []), default=str,
                                sort_keys=True)):
            digest.update(str(part).encode("utf-8"))
            digest.update(b"\x00")
    return digest.hexdigest()


@dataclass(frozen=True)
class RunFingerprint:
    """Which measurement run wrote a cell. Stamped at write time, compared at freeze."""

    run_id: str
    warehouse_seed: int | None
    gold_sha256: str
    prices_taken_on: str
    code_revision: str

    @classmethod
    def for_run(cls, items, *, warehouse_seed: int | None = None) -> "RunFingerprint":
        return cls(
            run_id=uuid.uuid4().hex[:RUN_ID_CHARS],
            warehouse_seed=warehouse_seed,
            gold_sha256=gold_digest(items),
            prices_taken_on=PRICES_TAKEN_ON,
            code_revision=code_revision(),
        )

    @classmethod
    def from_dict(cls, body: dict) -> "RunFingerprint":
        return cls(**{field: body.get(field) for field in
                      ("run_id", *INPUT_FIELDS)})

    def as_dict(self) -> dict:
        return asdict(self)

    @property
    def inputs(self) -> tuple:
        return tuple(getattr(self, field) for field in INPUT_FIELDS)

    def with_run_id(self, run_id: str) -> "RunFingerprint":
        return RunFingerprint(run_id=run_id, **{f: getattr(self, f) for f in INPUT_FIELDS})


def of(cell: dict) -> dict | None:
    """A cell's fingerprint, or None when it predates them. One accessor, so no caller
    invents a default for a cell that carries nothing."""
    return cell.get(FINGERPRINT_FIELD)


def differing_fields(left: dict, right: dict) -> list[str]:
    """Which fields two fingerprints disagree on, named so an error can say what moved."""
    return [field for field in ("run_id", *INPUT_FIELDS)
            if left.get(field) != right.get(field)]


def resolve_run_id(fingerprint: RunFingerprint, directory: Path) -> RunFingerprint:
    """Adopt the run id already in this directory when the inputs match, else keep ours.

    See the module docstring: a resumed sweep IS the same run, and a fresh id per
    invocation would make a resumed development run impossible to freeze.
    """
    directory = Path(directory)
    if not directory.is_dir():
        return fingerprint
    for path in sorted(directory.glob("*.json")):
        try:
            stored = of(json.loads(path.read_text()))
        except (OSError, json.JSONDecodeError):
            continue
        if not stored:
            continue
        if RunFingerprint.from_dict(stored).inputs == fingerprint.inputs:
            return fingerprint.with_run_id(stored["run_id"])
    return fingerprint
