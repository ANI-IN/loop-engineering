"""The three ways a Level 2 run ends without succeeding.

Thin by rule. The scenarios live in src/loopeng/verify/failure_paths.py.
"""

import argparse

from loopeng.entrypoint import run
from loopeng.gold.build import build_gold
from loopeng.logging import configure_logging
from loopeng.settings import load_settings
from loopeng.verify.failure_paths import SCENARIOS, run_scenario
from loopeng.warehouse.connect import ensure_warehouse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Level 2 termination branches.")
    parser.add_argument("--item", help="Gold item id; defaults to a rule-heavy one.")
    args = parser.parse_args(argv)

    configure_logging()
    settings = load_settings()
    warehouse = ensure_warehouse(settings.warehouse_path, seed=settings.warehouse_seed)
    items = build_gold(warehouse)
    item = next((i for i in items if i.item_id == args.item), None) if args.item else None
    item = item or next(i for i in items if i.pattern_key == "p07_aov_by_region")

    print(f"Q: {item.question}\nrules: {', '.join(item.rules)}\n")
    failures = 0
    for scenario in SCENARIOS:
        run = run_scenario(scenario, item.question, item.rules, warehouse)
        got = str(run.termination)
        ok = got == scenario.expect
        failures += 0 if ok else 1
        print(f"--- {scenario.key} ---")
        print(f"  why       : {scenario.why}")
        print(f"  expected  : {scenario.expect}")
        print(f"  terminated: {got}   {'OK' if ok else 'MISMATCH'}")
        print(f"  attempts  : {len(run.attempts)}   rejections: {run.rejections}")
        print(f"  cost      : est. ${run.cost_usd():.5f}\n")
    print("Every branch above ends the run deliberately. A controller whose worst")
    print("branch nobody has watched fire is a controller nobody has tested.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run(main))
