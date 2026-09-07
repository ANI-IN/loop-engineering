"""Render DIAL, COST, DELTA and ABSTENTION from whatever cells exist on disk.

Thin by rule, and NUMERIC LITERALS ARE BANNED IN THIS FILE — enforced by
tools/lint_no_numbers.py. Every number that reaches the room comes from a Metric
carried in a cell file, never from something typed here. A typed number is
indistinguishable from a measured one once it is on a projector.

**There is no `--reference` flag, and there is no stored set to fold in.** Every bar
this renders was computed by the run that is being rendered. The flag used to select
between four ways of mixing live cells with committed ones, and the whole apparatus is
gone — a render path that can still express "stored" is a render path that can still
show one, and the session's claim is that nothing on screen was precomputed.

Safe to run while the sweep is still going: cells still running render as in-progress.
"""

import argparse

from loopeng.entrypoint import run
from loopeng.logging import configure_logging
from loopeng.sweep.charts import write_charts
from loopeng.sweep.orchestrator import load_all
from loopeng.sweep.render import abstention_panel, comparisons_for, summarise
from loopeng.sweep.runner import SWEEP_DIR


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render the live charts.")
    parser.add_argument("--dir", default=str(SWEEP_DIR), help="Where cell files live.")
    parser.add_argument("--out", default="results/charts", help="Where the PNGs go.")
    args = parser.parse_args(argv)

    configure_logging()
    cells = load_all(args.dir)
    points, refusal = abstention_panel(cells)
    written = write_charts(cells, args.out,
                           comparisons=comparisons_for(cells),
                           abstention_points=points,
                           abstention_refusal=refusal)
    for line in summarise(cells, comparisons_for(cells), args.dir, written):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
