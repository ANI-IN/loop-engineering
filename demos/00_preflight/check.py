"""Prove your key and your checkout before spending anything on a sweep.

Thin by rule. Every check lives in src/loopeng/preflight.py.

Numbered 00 because it runs before the loops, not because it is a loop level.
"""

import argparse

from loopeng.logging import configure_logging
from loopeng.preflight import render, run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Cheapest possible check that this checkout can spend."
    )
    parser.add_argument("--quiet", action="store_true",
                        help="Exit code only. For scripts and CI.")
    args = parser.parse_args(argv)

    configure_logging()
    result = run()
    if not args.quiet:
        print(render(result))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
