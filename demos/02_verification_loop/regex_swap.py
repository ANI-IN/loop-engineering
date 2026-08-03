"""The AST-to-regex swap: the score rises while the quality falls.

Thin by rule. The comparison lives in src/loopeng/verify/swap.py.
"""

import argparse
import json

from loopeng.entrypoint import run
from loopeng.gold.build import build_gold
from loopeng.logging import configure_logging
from loopeng.settings import load_settings
from loopeng.verify.swap import run_swap
from loopeng.warehouse.connect import ensure_warehouse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AST verifier vs regex verifier.")
    parser.add_argument("--limit", type=int, default=10, help="Items per arm.")
    parser.add_argument("--rule", default="fan_out",
                        help="Only items requiring this rule; fan_out is where the "
                             "two verifiers actually differ.")
    parser.add_argument("--level", default="L3", choices=("L0", "L3"))
    parser.add_argument("--max-attempts", type=int, default=3)
    args = parser.parse_args(argv)

    configure_logging()
    settings = load_settings()
    warehouse = ensure_warehouse(settings.warehouse_path, seed=settings.warehouse_seed)
    # The swap only says anything on items where the two verifiers disagree. Text
    # cannot express the fan-out trap — "orders.amount_minor aggregated AFTER joining
    # order_items" is a shape, not a word — so those items are the default.
    pool = [i for i in build_gold(warehouse) if i.rules]
    if args.rule:
        pool = [i for i in pool if args.rule in i.rules] or pool
    items = pool[: args.limit]

    report = run_swap(items, warehouse, level=args.level, max_attempts=args.max_attempts)
    for name, arm in report["arms"].items():
        print(f"\n{name.upper()} verifier")
        print(f"  accepted by the verifier : {arm['acceptance_rate']}")
        print(f"  actually correct         : {arm['correctness_rate']}")
        print(f"  rejections               : {arm['rejections']}")
        print(f"  cost                     : est. ${arm['cost_usd_estimated']:.4f}")
        surface = report["probe_surface"][name]
        print(f"  probe surface            : {surface['n_sound']}/{surface['n_rules']} sound, "
              f"{surface['n_missed_violations']} missed violations")
    print(f"\n{report['reading']}")
    (settings.results_dir / "phase2_swap.json").write_text(json.dumps(report, indent=2))
    print(f"\nwrote {settings.results_dir / 'phase2_swap.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
