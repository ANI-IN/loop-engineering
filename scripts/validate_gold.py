"""Run every gold query against a freshly seeded warehouse and check it still matches.

**A gold set that has silently drifted from the schema poisons every number
downstream, and nothing else in the build would notice.** The items are committed as
JSON so a cloner does not have to rebuild them to see what they are; the moment they
are committed, they can disagree with the code that produced them. A column rename, a
generator change, a widened parameter space, an edited rule — any of those moves the
answers, and the stored file keeps the old ones with every test green.

So this rebuilds the warehouse from the seed, executes each stored `gold_sql`, and
compares the result to the stored `gold_rows` using the same comparison the grader
uses. It is offline, needs no credential, costs nothing, and runs in CI.

It checks the SPLIT too. Which items are held out decides which items every headline
number is computed over, so a split that changed without the file changing would move
the headline without moving anything a reader could see.
"""

import argparse
import sys
import tempfile
from pathlib import Path

from loopeng.gold.build import (
    GOLD_PATH,
    build_gold,
    read_gold,
    split_items,
)
from loopeng.gold.compare import rows_equal
from loopeng.settings import Settings
from loopeng.warehouse.connect import ensure_warehouse, run_sql


def validate(path: Path, seed: int) -> list[str]:
    """Every way the stored set can disagree with the code, as a list of problems."""
    problems: list[str] = []
    stored = read_gold(path)
    if not stored:
        return [f"{path} holds no items"]

    with tempfile.TemporaryDirectory() as tmp:
        warehouse = ensure_warehouse(Path(tmp) / "validate.duckdb", seed=seed)

        # 1. Does each stored answer still come back from the warehouse?
        for item in stored:
            try:
                rows = [list(row) for row in run_sql(item.gold_sql, warehouse)]
            except Exception as exc:  # noqa: BLE001 - the verdict IS the exception
                problems.append(f"{item.item_id}: gold SQL no longer runs — {exc}")
                continue
            if not rows_equal(rows, item.gold_rows,
                              order_sensitive=item.order_sensitive):
                problems.append(
                    f"{item.item_id}: gold answer drifted. Stored {item.gold_rows!r}, "
                    f"the warehouse now returns {rows!r}"
                )

        # 2. Is the stored set the set the patterns currently generate?
        rebuilt = {item.item_id for item in build_gold(warehouse, cache_path=None)}
        stored_ids = {item.item_id for item in stored}
        if rebuilt - stored_ids:
            problems.append(
                f"the patterns generate {len(rebuilt - stored_ids)} item(s) missing "
                f"from {path}: {sorted(rebuilt - stored_ids)[:5]}"
            )
        if stored_ids - rebuilt:
            problems.append(
                f"{path} holds {len(stored_ids - rebuilt)} item(s) the patterns no "
                f"longer generate: {sorted(stored_ids - rebuilt)[:5]}"
            )

    # 3. Does the split still hold? It decides what every headline is computed over.
    held_out, development = split_items(stored)
    if not held_out:
        problems.append("the split produced no held-out items")
    overlap = {i.item_id for i in held_out} & {i.item_id for i in development}
    if overlap:
        problems.append(f"items on both sides of the split: {sorted(overlap)[:5]}")
    if len(held_out) + len(development) != len(stored):
        problems.append(
            f"the split loses items: {len(held_out)} + {len(development)} != "
            f"{len(stored)}"
        )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--path", default=str(GOLD_PATH),
                        help="The committed gold set to validate.")
    parser.add_argument("--seed", type=int,
                        default=Settings.model_fields["warehouse_seed"].default,
                        help="Warehouse seed. Changing it changes every gold answer.")
    args = parser.parse_args(argv)

    path = Path(args.path)
    if not path.is_file():
        print(f"FAIL {path} does not exist. Run scripts/build_gold.py to write it.")
        return 1

    problems = validate(path, args.seed)
    if problems:
        print(f"FAIL {len(problems)} problem(s) in {path}:")
        for problem in problems:
            print(f"  - {problem}")
        print(
            "\nThe gold set and the code that produces it have diverged. Rebuild it "
            "with scripts/build_gold.py, read the diff, and only then commit it — a "
            "regenerated answer key nobody looked at is how a wrong number becomes "
            "the reference."
        )
        return 1

    stored = read_gold(path)
    held_out, development = split_items(stored)
    print(
        f"OK {len(stored)} gold items in {path} still match a freshly seeded "
        f"warehouse (seed {args.seed})."
    )
    print(f"   split: {len(held_out)} held out, {len(development)} development")
    return 0


if __name__ == "__main__":
    sys.exit(main())
