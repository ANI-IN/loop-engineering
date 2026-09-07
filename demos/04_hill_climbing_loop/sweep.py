"""Start the sweep. Detached by default, resumable, self-aborting on projected spend.

Thin by rule. The runner and the orchestrator live in src/loopeng/sweep/.

**--detach is the default and that is deliberate.** A sweep that holds the terminal
cannot be started at the top of a stage while you keep talking, which is the entire
reason it exists. `--foreground` is available for tests and for watching it run.
"""

import argparse
from pathlib import Path

from loopeng.entrypoint import run
from loopeng.gold.build import build_gold
from loopeng.logging import configure_logging
from loopeng.settings import load_settings
from loopeng.sweep.deadline import Deadline
from loopeng.sweep.detach import detach
from loopeng.sweep.orchestrator import describe_outcome, run_sweep
from loopeng.sweep.runner import (
    CONCURRENCY_PER_MODEL,
    PROFILES,
    SWEEP_DIR,
    LimitNotAllowed,
    StaleCellsPresent,
    SweepAborted,
)
from loopeng.warehouse.connect import ensure_warehouse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The hill-climbing sweep.")
    # Required, with no default. A delivery run must not be able to inherit
    # development settings by omission — that is a 10x cost difference decided by a
    # flag nobody typed.
    parser.add_argument("--profile", required=True, choices=sorted(PROFILES),
                        help="smoke: 2 cells, 8 items, a few cents — proves your key "
                             "and the whole pipeline. session: the agent model only, 4 "
                             "cells, inside the slot's clock. dev: both models, "
                             "replicates, ablation — run once, not per session.")
    parser.add_argument("--cap-usd", type=float, help="Override the profile's cap.")
    parser.add_argument("--limit", type=int,
                        help="Fewer items. Accepted by the smoke and development "
                             "profiles only; refused elsewhere, because a delivery "
                             "run over 5 items is not a delivery measurement.")
    parser.add_argument("--dir", default=str(SWEEP_DIR), help="Where cell files live.")
    parser.add_argument("--foreground", action="store_true",
                        help="Block the terminal instead of detaching.")
    parser.add_argument("--concurrency", type=int, default=CONCURRENCY_PER_MODEL,
                        help="Requests in flight per model. Lower it BEFORE the sweep "
                             "on a lower-tier account; the default was chosen against "
                             "ceilings measured on one account.")
    parser.add_argument("--log", default="results/sweep_run.log")
    parser.add_argument("--deadline", type=float, metavar="SECONDS",
                        help="Override the profile's clock. Each profile declares its "
                             "own; this shortens it for a rehearsal. A cell stops "
                             "BETWEEN items and the reduced n reaches every figure. "
                             "See loopeng.sweep.deadline.")
    parser.add_argument("--resume", action="store_true",
                        help="Continue from completed cells already on disk. WITHOUT "
                             "this the sweep REFUSES to start when it finds any — "
                             "resuming in front of a room finishes in a second and "
                             "renders numbers that look computed and were not.")
    args = parser.parse_args(argv)

    # Credentials BEFORE detaching, in the process the operator is still watching —
    # see `loopeng.sweep.detach`, which records why that ordering is a constraint on
    # every caller rather than a habit of this one.
    configure_logging()
    settings = load_settings()

    if not args.foreground:
        return detach(Path(__file__), argv, args.log)

    warehouse = ensure_warehouse(settings.warehouse_path, seed=settings.warehouse_seed)

    try:
        report = run_sweep(build_gold(warehouse), warehouse, cap_usd=args.cap_usd,
                           profile=PROFILES[args.profile], item_limit=args.limit,
                           directory=args.dir, resume=args.resume,
                           concurrency=args.concurrency,
                           warehouse_seed=settings.warehouse_seed,
                           deadline=Deadline(seconds=args.deadline)
                           if args.deadline else None)
    except (StaleCellsPresent, LimitNotAllowed) as refused:
        print(f"\nREFUSING TO START\n{refused}")
        return 3
    except SweepAborted as abort:
        # Report the last completed cell and stop. Retrying into the cap is how a
        # sweep ends up half-spent with nothing to show.
        print(f"\nSWEEP ABORTED\n{abort}")
        return 2

    print()
    print(describe_outcome(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
