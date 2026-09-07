"""Regenerate the failure-taxonomy observation record from real cell files.

**The taxonomy is not the finding; what it has actually caught is.** `VisibleKind`
declares seven ways a failure can be visible, and a list of seven categories reads as
coverage whether or not anything has ever landed in six of them. This walks the cells
on disk and writes down which kinds real runs have produced, with the n and the date,
so "we have a category for that" and "we have seen that" stay different sentences.

Run it over any directory of sweep cells:

    uv run python scripts/observe_failures.py results/sweep [more dirs...]

It reads only what is on disk and calls no model.
"""

import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from loopeng.agent.classify import VisibleKind
from loopeng.sweep.runner import visible_kind_counts

OUT = Path("results/failure_taxonomy_observed.json")


def cells_under(directories: list[Path]) -> list[dict]:
    """Every cell file with items under these directories."""
    cells = []
    for directory in directories:
        for path in sorted(Path(directory).rglob("*.json")):
            try:
                body = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(body, dict) and isinstance(body.get("items"), list):
                cells.append(body)
    return cells


def observe(cells: list[dict]) -> dict:
    """The record. Its own coverage is part of it, not a caption somewhere else.

    `levels`, `roles` and `modes` come from the CELLS, not the rows — a row carries no
    level, so reading them from rows produced `"levels": null` on a run that very much
    had one. What the sample covers is the first thing a reader needs, because five
    kinds unobserved over one role at one level says something much weaker than five
    unobserved across the whole matrix.
    """
    rows = [row for cell in cells for row in cell["items"]]
    counts = visible_kind_counts(rows)
    outcomes = Counter(row["outcome"] for row in rows if "outcome" in row)
    return {
        "measured_on": date.today().isoformat(),
        "n_cells": len(cells),
        "n_items": len(rows),
        "n_visible_failures": sum(counts.values()),
        "covers": {
            field: sorted({cell[field] for cell in cells if field in cell})
            for field in ("role", "level", "mode")
        },
        "outcomes": dict(sorted(outcomes.items())),
        "kinds": counts,
        # Named rather than left to be inferred from the zeros. A reader scanning the
        # `kinds` map sees seven entries and five zeros; this says in words that five
        # categories have never been observed, which is the part worth arguing about.
        "never_observed": sorted(k.value for k in VisibleKind if not counts[k.value]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("directories", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--note", default="", help="What produced these cells.")
    args = parser.parse_args(argv)

    cells = cells_under(args.directories)
    if not cells:
        print(f"no cell files with items under {', '.join(map(str, args.directories))}")
        return 1

    record = observe(cells)
    # `note` and nothing else. The first version recorded the source directories, which
    # on the run that produced this file were absolute paths into a temporary
    # scratchpad — provenance that reads as precise and resolves nowhere, for anyone but
    # the machine that wrote it. What the sample covers is in `covers`, which is a fact
    # about the measurement rather than about somebody's filesystem.
    record["note"] = args.note
    record["cell_keys"] = sorted(cell["key"] for cell in cells)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    print(f"{record['n_items']} items, {record['n_visible_failures']} visible failure(s)")
    for kind, n in record["kinds"].items():
        print(f"  {kind:<20} {n}")
    print(f"\nnever observed: {', '.join(record['never_observed']) or 'none'}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
