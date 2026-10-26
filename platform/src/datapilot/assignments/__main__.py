"""python -m datapilot.assignments check|apply|verify|reset (the make targets call the first three).

`reset <slug>` is the recovery for the check's own stack: it clears the section's run state,
releases the kill switch, and sets the daily token count back to zero on the check's Compose
project, never on the class stack (`make reset` is the class stack's).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from datapilot.assignments import VARIANTS
from datapilot.assignments.report import STOPPED, Stop
from datapilot.names import SECTIONS_BY_SLUG

YES = {"1", "yes", "true"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m datapilot.assignments")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="run one assignment's live check")
    check.add_argument("slug", choices=sorted(SECTIONS_BY_SLUG))
    check.add_argument("--tree", type=Path, help="a copy to check, such as one apply made")
    apply = commands.add_parser("apply", help="a scratch copy with one solution applied")
    apply.add_argument("slug", choices=sorted(SECTIONS_BY_SLUG))
    apply.add_argument("variant", choices=[*VARIANTS, "starter"])
    apply.add_argument(
        "--force", action="store_true", help="replace the copy if it exists (FORCE=1 on make)"
    )
    verify = commands.add_parser("verify", help="the build's verification passes, with captures")
    verify.add_argument("--only", nargs="*", choices=sorted(SECTIONS_BY_SLUG))
    verify.add_argument("--variant", action="append", choices=["starter", *VARIANTS])
    verify.add_argument("--once", action="store_true", help="each solution a single time")
    reset = commands.add_parser("reset", help="reset the check's own stack, never the class stack")
    reset.add_argument("slug", choices=sorted(SECTIONS_BY_SLUG))
    args = parser.parse_args(argv)

    try:
        return _run(args)
    except Stop as stop:
        print(str(stop))
        return STOPPED


def _run(args: argparse.Namespace) -> int:
    if args.command == "check":
        from datapilot.assignments.runner import PACKAGE_TREE, check_in_tree

        return check_in_tree(args.slug, args.tree or PACKAGE_TREE)
    if args.command == "apply":
        from datapilot.assignments.solutions import apply as apply_solution

        force = args.force or os.environ.get("FORCE", "").strip().lower() in YES
        dest = apply_solution(args.slug, args.variant, force=force)
        print(f"{args.variant} applied in {dest}")
        print(f"Check it: make check-assignment NAME={args.slug} TREE={dest}")
        return 0
    if args.command == "reset":
        from datapilot.assignments.cost import activity
        from datapilot.assignments.stack import reset_check_stack

        for line in reset_check_stack(args.slug, activity()):
            print(line)
        return 0
    from datapilot.assignments.solutions import verify as verify_all

    return verify_all(args.only, args.variant, args.once)


if __name__ == "__main__":
    sys.exit(main())
