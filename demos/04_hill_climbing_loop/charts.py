"""Render DIAL, COST, DELTA and ABSTENTION from whatever cells exist on disk.

Thin by rule, and NUMERIC LITERALS ARE BANNED IN THIS FILE — enforced by
tools/lint_no_numbers.py. Every number that reaches the room comes from a Metric
carried in a cell file, never from something typed here. A typed number is
indistinguishable from a measured one once it is on a projector.

`--reference=compare` is the mode a cloner wants: their own cells and the committed
baseline, side by side, with the difference between them computed. `fill` was the only
behaviour available, and it deleted the stored cell as soon as a live one existed.

**It is not the default, and that is the point.** `compare` was, for every caller — so
this command on a fresh clone rendered twelve finished bars and the pre-registered
p-value on a machine that had never made an API call. The default is `auto`: `compare`
once this run has a cell of its own, `hide` until then. See `sweep.reference.MODE_AUTO`.

Safe to run while the sweep is still going: cells still running render as in-progress.
"""

import argparse

from loopeng.entrypoint import run
from loopeng.logging import configure_logging
from loopeng.sweep.charts import write_charts
from loopeng.sweep.orchestrator import load_all
from loopeng.sweep.reference import MODE_AUTO, SELECTABLE_MODES, load_reference
from loopeng.sweep.render import abstention_points, comparisons_for, summarise
from loopeng.sweep.runner import SWEEP_DIR


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render the live charts.")
    parser.add_argument("--dir", default=str(SWEEP_DIR), help="Where cell files live.")
    parser.add_argument("--out", default="results/charts", help="Where the PNGs go.")
    parser.add_argument("--reference", default=MODE_AUTO, choices=SELECTABLE_MODES,
                        help="auto (default): compare once this run has a cell of its "
                             "own, hide until then — so a machine with no live cells "
                             "renders 'not yet measured' rather than stored bars. "
                             "hide: live cells only. fill: stored cells only where no "
                             "live one exists. compare: both, paired, with the "
                             "difference computed between them.")
    args = parser.parse_args(argv)

    configure_logging()
    live = load_all(args.dir)
    cells = live + load_reference(mode=args.reference,
                                  live_keys={cell["key"] for cell in live})
    written = write_charts(cells, args.out,
                           comparisons=comparisons_for(cells),
                           abstention_points=abstention_points(cells))
    for line in summarise(cells, comparisons_for(cells), args.dir, written):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
