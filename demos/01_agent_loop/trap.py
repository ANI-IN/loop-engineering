"""The trap: every gold question, both models, then the reveal.

Thin by rule. The runner, the scoring and the grid all live in src/loopeng/agent/.
"""

import argparse

from loopeng.agent.trap import estimate_trap_cost, print_grid, run_trap, save_state
from loopeng.agent.ui import build_trap_app
from loopeng.gold.build import build_gold
from loopeng.logging import configure_logging
from loopeng.settings import load_settings
from loopeng.warehouse.connect import ensure_warehouse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Level 1 trap — all gold questions.")
    parser.add_argument("--headless", action="store_true", help="Run in the terminal.")
    parser.add_argument("--limit", type=int, help="Run only the first N items (development).")
    parser.add_argument("--cap-usd", type=float, default=2.0, help="Abort if projected over.")
    parser.add_argument("--share", action="store_true")
    args = parser.parse_args(argv)

    configure_logging()
    settings = load_settings()
    warehouse = ensure_warehouse(settings.warehouse_path, seed=settings.warehouse_seed)
    items = build_gold(warehouse)[: args.limit] if args.limit else build_gold(warehouse)

    projected = estimate_trap_cost(len(items))
    if projected > args.cap_usd:
        print(f"ABORT: projected est. ${projected:.2f} exceeds the ${args.cap_usd:.2f} cap.")
        return 1

    if not args.headless:
        build_trap_app(items, warehouse).launch(share=args.share)
        return 0

    print(f"running {len(items)} items x 2 arms (L3 vs L0); projected est. ${projected:.2f}")
    state = run_trap(items, warehouse)
    print_grid(state, revealed=False)
    state.reveal()
    print_grid(state, revealed=True)
    print(f"\nwrote {save_state(state, settings.results_dir / 'phase1_trap.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
