"""Check that the slide outline matches the owner's final deck.

Usage: python platform/scripts/check_outline.py [--root PATH] [--deck PATH]

The outline is generated from the final deck (platform/scripts/outline_from_deck.py; DECISIONS.md,
28 October 2026), never from slides/source, which is superseded. Where the deck is present (the
verification gate, on the owner's machine), the check generates the outline again from a
temporary copy of the deck and requires a byte-for-byte match with slides/outline.md, printing the
first lines that differ. Where it is absent (a public checkout, continuous integration), it checks
that the outline is whole: the deck's fingerprint is recorded in its header, and it holds exactly
as many slides as that fingerprint says, numbered 1 to N. Writes no tracked file. Exits 1 on any
problem, else 0.
"""

from __future__ import annotations

import argparse
import difflib
import importlib.util
import re
import sys
from pathlib import Path

REPO = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
OUTLINE = "slides/outline.md"
DIFF_LINES = 20
SLIDE = re.compile(r"^## Slide (\d+)(?::|$)", re.M)


def _generator():
    spec = importlib.util.spec_from_file_location(
        "outline_from_deck", Path(__file__).with_name("outline_from_deck.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GENERATOR = _generator()


def whole_problems(committed: str) -> list[str]:
    """The outline on its own: its recorded fingerprint and its slides numbered 1 to N."""
    found = GENERATOR.recorded_fingerprint(committed)
    if found is None:
        return [f"{OUTLINE} records no deck fingerprint: run make outline on the final deck"]
    count, _digest = found
    numbers = [int(n) for n in SLIDE.findall(committed)]
    if numbers != list(range(1, count + 1)):
        return [
            f"{OUTLINE} records {count} slides but holds {len(numbers)} slide sections "
            f"(numbered {numbers[:3]}...): run make outline on the final deck"
        ]
    return []


def match_problems(built: str, committed: str) -> list[str]:
    if built == committed:
        return []
    diff = list(
        difflib.unified_diff(
            committed.splitlines(),
            built.splitlines(),
            f"{OUTLINE} (committed)",
            f"{OUTLINE} (from the deck)",
            lineterm="",
            n=1,
        )
    )
    shown = "\n".join(diff[:DIFF_LINES])
    more = f"\n... {len(diff) - DIFF_LINES} more diff lines" if len(diff) > DIFF_LINES else ""
    return [
        f"{OUTLINE} does not match the final deck: run make outline and commit it\n{shown}{more}"
    ]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO, help="the tree to check")
    parser.add_argument(
        "--deck", help="the final deck (read only), else found as `make outline` finds it"
    )
    args = parser.parse_args(argv)
    path = args.root.resolve() / OUTLINE
    if not path.is_file():
        print(f"x {OUTLINE} is missing: run make outline and commit it")
        print("outline check: 1 problems")
        return 1
    committed = path.read_bytes().decode("utf-8")
    problems = whole_problems(committed)
    deck = GENERATOR.find_deck(args.deck)
    if deck is None:
        print(f"the final deck is not here: {OUTLINE} checked on its own")
    else:
        print(f"compared with {deck.name}")
        problems += match_problems(GENERATOR.outline(deck), committed)
    for problem in problems:
        print(f"x {problem}")
    print(f"outline check: {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
