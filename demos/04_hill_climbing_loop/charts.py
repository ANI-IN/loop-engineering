"""Render the DIAL and COST charts from whatever cells exist on disk.

Thin by rule, and NUMERIC LITERALS ARE BANNED IN THIS FILE — enforced by
tools/lint_no_numbers.py. Every number that reaches the room comes from a Metric
carried in a cell file, never from something typed here. A typed number is
indistinguishable from a measured one once it is on a projector.

Safe to run while the sweep is still going: cells still running render as in-progress.
"""

import argparse

from loopeng.logging import configure_logging
from loopeng.sweep.charts import write_charts
from loopeng.sweep.orchestrator import load_all
from loopeng.sweep.reference import load_reference
from loopeng.sweep.runner import SWEEP_DIR


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render the DIAL and COST charts.")
    parser.add_argument("--dir", default=str(SWEEP_DIR), help="Where cell files live.")
    parser.add_argument("--out", default="results/charts", help="Where SVGs are written.")
    parser.add_argument("--with-reference", action="store_true",
                        help="Include stored frontier cells, drawn as REFERENCE.")
    args = parser.parse_args(argv)

    configure_logging()
    cells = load_all(args.dir)
    if args.with_reference:
        # A live measurement always wins over a stored one, so the same cell is never
        # plotted twice.
        cells = cells + load_reference(exclude_keys={cell["key"] for cell in cells})
    if not cells:
        print(f"No cells in {args.dir} yet. Charts render as 'not yet measured'.")

    written = write_charts(cells, args.out)
    done = len([cell for cell in cells if cell["complete"]])
    print(f"cells on disk: {len(cells)} ({done} complete)")
    for path in written:
        print(f"  wrote {path}")
    for cell in sorted(cells, key=lambda c: c["label"]):
        print(f"  {cell['label']:34s} {cell['silent_error_rate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
