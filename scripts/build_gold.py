"""Write the gold set to JSON. Offline, free, and deterministic given the seed.

Committed rather than rebuilt on every clone because the items ARE the contract: a
reader should be able to open the file and see the questions and the answers without
running anything. `scripts/validate_gold.py` is what stops that convenience becoming
an answer key nobody re-derived — it re-executes every query against a fresh warehouse
and refuses a mismatch, in CI, on every push.
"""

import argparse
import sys
import tempfile
from pathlib import Path

from loopeng.gold.build import (
    GOLD_PATH,
    build_gold,
    clustering_summary,
    split_items,
    write_gold,
)
from loopeng.settings import Settings
from loopeng.warehouse.connect import ensure_warehouse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--path", default=str(GOLD_PATH))
    parser.add_argument("--seed", type=int,
                        default=Settings.model_fields["warehouse_seed"].default)
    args = parser.parse_args(argv)

    with tempfile.TemporaryDirectory() as tmp:
        warehouse = ensure_warehouse(Path(tmp) / "build.duckdb", seed=args.seed)
        items = build_gold(warehouse, cache_path=None)

    write_gold(items, Path(args.path))
    held_out, development = split_items(items)
    shape = clustering_summary(items)
    print(f"wrote {len(items)} items to {args.path} (seed {args.seed})")
    print(f"  {shape['n_clusters']} clusters, {shape['items_per_cluster']} per cluster")
    print(f"  split: {len(held_out)} held out, {len(development)} development")
    return 0


if __name__ == "__main__":
    sys.exit(main())
