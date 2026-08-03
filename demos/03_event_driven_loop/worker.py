"""Poll the queue, claim a question, run the Level 2 loop, write the answer back.

Thin by rule. The worker lives in src/loopeng/queue/worker.py.
"""

import argparse

from loopeng.entrypoint import run
from loopeng.logging import configure_logging
from loopeng.queue import store, worker
from loopeng.settings import load_settings
from loopeng.warehouse.connect import ensure_warehouse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The event-driven worker.")
    parser.add_argument("--queue", default=str(store.DEFAULT_QUEUE_PATH))
    parser.add_argument("--poll-seconds", type=float, default=worker.POLL_SECONDS)
    parser.add_argument("--drain", action="store_true",
                        help="Stop once the queue is empty instead of polling forever.")
    args = parser.parse_args(argv)

    configure_logging()
    settings = load_settings()
    warehouse = ensure_warehouse(settings.warehouse_path, seed=settings.warehouse_seed)
    con = store.connect(args.queue)

    print(f"worker up. polling every {args.poll_seconds}s. Ctrl-C to stop.")
    print("no backoff, no dead-lettering, no retry — a failed row stays failed.\n")
    try:
        done = worker.serve(con, warehouse, poll_seconds=args.poll_seconds,
                            max_idle_polls=1 if args.drain else None)
        print(f"\ndrained. processed {done} row(s). {store.counts(con)}")
    except KeyboardInterrupt:
        # An in-flight row stays `claimed`. That is what no retry logic looks like.
        print(f"\nstopped. {store.counts(con)}")
        print("any row left in 'claimed' was in flight — nothing will pick it up.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
