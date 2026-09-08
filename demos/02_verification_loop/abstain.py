"""The intervention view: declined questions, their reasons, and the attempts behind them.

Thin by rule. Abstention scoring and the view both live in src/loopeng/triage/.
"""

import argparse

from loopeng.entrypoint import run
from loopeng.logging import configure_logging
from loopeng.sweep.orchestrator import load_all
from loopeng.sweep.render import PREFERRED_CURVE_CELL
from loopeng.triage.abstain import curve
from loopeng.views.intervention import build_intervention_app
from loopeng.views.render import render_declined


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Abstention and the intervention view.")
    # DERIVED. This defaulted to `"worker_L0_loop_r0"`, a key no sweep has produced
    # since the roles were renamed — so the demo's default could never match and it
    # printed "run the sweep first" over a directory full of cells. Same string, same
    # defect, third module: `sweep/render.py` and `views/oversight.py` both had it.
    parser.add_argument("--cell", default=PREFERRED_CURVE_CELL,
                        help="Which measured cell.")
    parser.add_argument("--dir", default="results/sweep")
    parser.add_argument("--threshold", type=float, default=1.0)
    parser.add_argument("--headless", action="store_true", help="Print instead of serving.")
    parser.add_argument("--share", action="store_true")
    args = parser.parse_args(argv)

    configure_logging()
    cells = {c["key"]: c for c in load_all(args.dir)}
    if args.cell not in cells:
        print(f"No cell {args.cell!r} in {args.dir}. Run the sweep first.")
        return 1
    runs = cells[args.cell]["items"]

    if args.headless:
        for point in curve(runs):
            print(f"  threshold {point['threshold']:.2f}  coverage {point['coverage']}  "
                  f"precision {point['precision']}")
        print()
        print(render_declined(runs, args.threshold))
        return 0

    build_intervention_app(runs).launch(share=args.share)
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
