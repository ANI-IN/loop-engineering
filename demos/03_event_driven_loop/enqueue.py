"""Submit a question to the queue.

Thin by rule. The queue lives in src/loopeng/queue/.
"""

import argparse

from loopeng.gold.build import build_gold
from loopeng.logging import configure_logging
from loopeng.queue import store
from loopeng.settings import load_settings
from loopeng.warehouse.connect import ensure_warehouse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Put a question on the queue.")
    parser.add_argument("--question", help="Free text; defaults to a gold question.")
    parser.add_argument("--queue", default=str(store.DEFAULT_QUEUE_PATH))
    parser.add_argument("--list", action="store_true", help="Show the queue and exit.")
    args = parser.parse_args(argv)

    configure_logging()
    settings = load_settings()
    con = store.connect(args.queue)

    if args.list:
        for row in store.all_rows(con):
            print(f"  {row.id:3d}  {row.status:8s}  {row.question[:58]}")
            if row.result:
                print(f"       -> {row.result[:96]}")
        print(f"\n  {store.counts(con)}")
        return 0

    question = args.question
    if not question:
        warehouse = ensure_warehouse(settings.warehouse_path, seed=settings.warehouse_seed)
        question = build_gold(warehouse)[0].question

    row_id = store.enqueue(con, question)
    print(f"queued id={row_id}: {question}")
    print(f"queue now: {store.counts(con)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
