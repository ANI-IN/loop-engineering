"""Start the sweep. Detached by default, resumable, self-aborting on projected spend.

Thin by rule. The runner and the orchestrator live in src/loopeng/sweep/.

**--detach is the default and that is deliberate.** A sweep that holds the terminal
cannot be started at the top of a stage while you keep talking, which is the entire
reason it exists. `--foreground` is available for tests and for watching it run.
"""

import argparse
from pathlib import Path

from loopeng.gold.build import build_gold
from loopeng.logging import configure_logging
from loopeng.settings import load_settings
from loopeng.sweep.detach import detach
from loopeng.sweep.orchestrator import run_sweep
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
                             "and the whole pipeline. delivery: Haiku only, 4 cells, "
                             "under $1. development: both models, replicates, ablation.")
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
    parser.add_argument("--fresh", action="store_true",
                        help="Refuse to start if completed cells are already on disk. "
                             "Use this for the LIVE session: without it the sweep "
                             "resumes and finishes instantly.")
    args = parser.parse_args(argv)

    if not args.foreground:
        return detach(Path(__file__), argv, args.log)

    configure_logging()
    settings = load_settings()
    warehouse = ensure_warehouse(settings.warehouse_path, seed=settings.warehouse_seed)

    try:
        report = run_sweep(build_gold(warehouse), warehouse, cap_usd=args.cap_usd,
                           profile=PROFILES[args.profile], item_limit=args.limit,
                           directory=args.dir, fresh=args.fresh,
                           concurrency=args.concurrency)
    except (StaleCellsPresent, LimitNotAllowed) as refused:
        print(f"\nREFUSING TO START\n{refused}")
        return 3
    except SweepAborted as abort:
        # Report the last completed cell and stop. Retrying into the cap is how a
        # sweep ends up half-spent with nothing to show.
        print(f"\nSWEEP ABORTED\n{abort}")
        return 2

    print(f"\ncomplete: {report['profile']} profile, {report['n_cells']} cells "
          f"({report['n_resumed']} resumed from disk)")
    print(f"spend: est. ${report['spend_usd']['value']:.4f} of ${report['cap_usd']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
