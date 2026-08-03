"""Level 2, one question: verifiers that reject a query which ran.

Thin by rule. The loop and the verifiers live in src/loopeng/verify/.
"""

import argparse

from loopeng.entrypoint import run
from loopeng.gold.build import build_gold
from loopeng.logging import configure_logging
from loopeng.settings import load_settings
from loopeng.verify.loop import run_verified
from loopeng.warehouse.connect import ensure_warehouse


def _render(run) -> str:
    lines = [f"**termination:** {run.termination} · rejections: {run.rejections}", ""]
    for step in run.attempts:
        head = "ran" if step.attempt.executed else "failed to execute"
        lines.append(f"--- attempt {step.attempt.n} ({head}) ---")
        lines.append(step.attempt.sql or "(no SQL)")
        if step.attempt.error:
            lines.append(f"database said: {step.attempt.error}")
        elif not step.verdict.ok:
            lines.append("VERIFIER REJECTED — this query ran cleanly and is still wrong:")
            lines.append(step.verdict.feedback())
        else:
            lines.append(f"accepted; returned {str(step.attempt.rows)[:120]}")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Level 2 verification loop — one question.")
    parser.add_argument("--item", help="Gold item id; defaults to a rule-heavy one.")
    parser.add_argument("--role", default="worker", choices=("worker", "frontier"))
    parser.add_argument("--level", default="L3", choices=("L0", "L3"))
    parser.add_argument("--max-attempts", type=int, default=3)
    args = parser.parse_args(argv)

    configure_logging()
    settings = load_settings()
    warehouse = ensure_warehouse(settings.warehouse_path, seed=settings.warehouse_seed)
    items = build_gold(warehouse)
    item = next((i for i in items if i.item_id == args.item), None) if args.item else None
    item = item or next(i for i in items if i.pattern_key == "p05_net_revenue")

    run = run_verified(
        item.question, warehouse=warehouse, rules=item.rules, role=args.role,
        level=args.level, max_attempts=args.max_attempts, item_id=item.item_id,
    )
    print(f"Q: {item.question}\nrules: {', '.join(item.rules)}\n")
    print(_render(run))
    print(f"cost: est. ${run.cost_usd():.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
