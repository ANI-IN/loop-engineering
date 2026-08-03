"""Level 1, one question. Browser by default, terminal with --question.

Thin by rule: everything below wires arguments, calls into loopeng.agent, and
renders. The loop itself lives in src/loopeng/agent/loop.py.
"""

import argparse

from loopeng.agent.loop import run_question
from loopeng.entrypoint import run
from loopeng.logging import configure_logging
from loopeng.settings import load_settings
from loopeng.views.agent import build_run_app
from loopeng.views.render import render_attempt_timeline, render_cost
from loopeng.warehouse.connect import ensure_warehouse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Level 1 agent loop — one question.")
    parser.add_argument("--question", help="Run headless in the terminal instead of the browser.")
    parser.add_argument("--role", default="worker", choices=("worker", "frontier"))
    parser.add_argument("--level", default="L3", choices=("L0", "L3"))
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--share", action="store_true", help="Expose the Gradio app publicly.")
    args = parser.parse_args(argv)

    configure_logging()
    settings = load_settings()
    # Cold start: generated if absent, so no earlier stage needs to have run.
    warehouse = ensure_warehouse(settings.warehouse_path, seed=settings.warehouse_seed)

    if args.question:
        run = run_question(
            args.question,
            warehouse=warehouse,
            role=args.role,
            level=args.level,
            max_attempts=args.max_attempts,
        )
        print(render_attempt_timeline(run))
        print(render_cost(run.ledger))
        return 0

    build_run_app(warehouse, level=args.level).launch(share=args.share)
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
