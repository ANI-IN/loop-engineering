"""python -m datapilot.assignments check|apply|verify (the make targets call these)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from datapilot.assignments import VARIANTS
from datapilot.names import SECTIONS_BY_SLUG


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m datapilot.assignments")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="run one assignment's live check")
    check.add_argument("slug", choices=sorted(SECTIONS_BY_SLUG))
    check.add_argument("--tree", type=Path, help="a copy to check, such as one apply made")
    apply = commands.add_parser("apply", help="a scratch copy with one solution applied")
    apply.add_argument("slug", choices=sorted(SECTIONS_BY_SLUG))
    apply.add_argument("variant", choices=[*VARIANTS, "starter"])
    verify = commands.add_parser("verify", help="the build's verification passes, with captures")
    verify.add_argument("--only", nargs="*", choices=sorted(SECTIONS_BY_SLUG))
    args = parser.parse_args(argv)

    if args.command == "check":
        from datapilot.assignments.runner import PACKAGE_TREE, check_in_tree

        return check_in_tree(args.slug, args.tree or PACKAGE_TREE)
    if args.command == "apply":
        from datapilot.assignments.solutions import apply as apply_solution

        dest = apply_solution(args.slug, args.variant)
        print(f"{args.variant} applied in {dest}")
        print(f"Check it: make check-assignment NAME={args.slug} TREE={dest}")
        return 0
    from datapilot.assignments.solutions import verify as verify_all

    return verify_all(args.only)


if __name__ == "__main__":
    sys.exit(main())
