"""Serve any of the five views. One entry point so nothing is served two ways.

AGENT · TRAP · VERIFY · DIAL · OVERSIGHT. The event-driven loop is deliberately not a
view — see demos/03_event_driven_loop/README.md.
"""

import argparse

from loopeng.gold.build import build_gold
from loopeng.logging import configure_logging
from loopeng.queue import store
from loopeng.settings import load_settings
from loopeng.views.agent import build_agent_app
from loopeng.views.chrome import launch
from loopeng.views.dial import build_dial_app
from loopeng.views.exhibit import build_exhibit_app
from loopeng.views.oversight import build_oversight_app
from loopeng.views.trap import build_trap_app
from loopeng.views.verify import build_verify_app
from loopeng.warehouse.connect import ensure_warehouse

VIEWS = ("agent", "trap", "verify", "dial", "oversight", "exhibit")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve one of the five views.")
    parser.add_argument("--view", required=True, choices=VIEWS)
    parser.add_argument("--port", type=int)
    parser.add_argument("--share", action="store_true")
    parser.add_argument("--queue", default=str(store.DEFAULT_QUEUE_PATH))
    parser.add_argument("--sweep-dir", default="results/sweep")
    parser.add_argument("--share-url", help="Shown with a QR in the AGENT view.")
    args = parser.parse_args(argv)

    configure_logging()
    settings = load_settings()
    warehouse = ensure_warehouse(settings.warehouse_path, seed=settings.warehouse_seed)
    items = build_gold(warehouse) if args.view in ("trap", "verify", "exhibit") else []

    app = {
        "agent": lambda: build_agent_app(warehouse, args.queue, share_url=args.share_url),
        "trap": lambda: build_trap_app(items, warehouse),
        "verify": lambda: build_verify_app(items, warehouse),
        "dial": lambda: build_dial_app(args.sweep_dir),
        "oversight": lambda: build_oversight_app(args.sweep_dir),
        # The frozen exhibit, served locally. Makes zero model calls, so this is the
        # one to point a browser at when you want the app readable without spending.
        "exhibit": lambda: build_exhibit_app(args.sweep_dir, items, warehouse),
    }[args.view]()

    launch(app, share=args.share, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
