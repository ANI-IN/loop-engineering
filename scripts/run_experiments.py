"""Run the six arms on the held-out set and file each as a LangSmith experiment.

Six, not four. A, B, C and D vary the loops and the model at a fixed prompt level;
the trap varies the prompt level at a fixed loop count. They are different axes, and
the comparison view cannot infer one from the other — so the trap's two extra arms
are run explicitly and the four cells of the matrix are:

                    L0 (withheld)        L3 (given)
    agent           trap-agent-L0        A-baseline
    reference       trap-reference-L0    D-reference

**The models run first and LangSmith second.** Every arm executes to completion and
writes its results to disk before a single trace is uploaded, so a LangSmith failure
costs the view and never the measurement. That is the same rule the sweep follows and
it is the reason `results/` is the system of record.
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from loopeng.gold.build import read_gold, split_items
from loopeng.langsmith_ds import (
    create_fx_queue,
    push_prompts,
    run_experiment,
    upload_gold,
)
from loopeng.logging import configure_logging
from loopeng.settings import load_settings
from loopeng.sweep.conditions import CONDITIONS, Condition, run_item, summarise_arm
from loopeng.warehouse.connect import ensure_warehouse

OUT = Path("results/experiments")

# The trap's two extra arms: the same single-shot configuration as A and D, at L0.
# Written as (arm name, condition, level) so the level is visible at the call site
# rather than hidden in a default.
ARMS = [
    ("A-baseline", CONDITIONS["A"], "L3"),
    ("B-retry", CONDITIONS["B"], "L3"),
    ("C-verified", CONDITIONS["C"], "L3"),
    ("D-reference", CONDITIONS["D"], "L3"),
    ("trap-agent-L0", CONDITIONS["A"], "L0"),
    ("trap-reference-L0", CONDITIONS["D"], "L0"),
]


def run_arm(arm: str, condition: Condition, level: str, items, warehouse,
            concurrency: int):
    """Execute one arm to completion. Returns the rows, judgements and outputs."""

    def one(item):
        run, judgement, rejections = run_item(condition, item, warehouse, level=level)
        return item, run, judgement, rejections

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        results = list(pool.map(one, items))

    rows, judgements, costs, outputs = [], {}, {}, {}
    for item, run, judgement, rejections in results:
        cost = run.cost_usd()
        rows.append({
            "item_id": item.item_id,
            "pattern_key": item.pattern_key,
            "outcome": str(judgement.outcome),
            "termination": str(run.termination),
            "rejections": rejections,
            "cost_usd": cost,
            "sql": run.sql,
        })
        judgements[item.item_id] = judgement
        costs[item.item_id] = cost
        outputs[item.item_id] = {
            "sql": run.sql,
            "rows": run.rows,
            "error": run.error,
            "termination": str(run.termination),
        }

    return rows, judgements, costs, outputs, time.perf_counter() - started


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--limit", type=int, help="Fewer items, for a smoke run.")
    parser.add_argument("--skip-langsmith", action="store_true",
                        help="Run the arms and write results; upload nothing.")
    args = parser.parse_args(argv)

    configure_logging()
    settings = load_settings()
    warehouse = ensure_warehouse(settings.warehouse_path, seed=settings.warehouse_seed)
    held_out, _ = split_items(read_gold(Path("gold/gold.jsonl")))
    items = held_out[: args.limit] if args.limit else held_out
    OUT.mkdir(parents=True, exist_ok=True)

    print(f"held-out set: {len(items)} items, {len(ARMS)} arms\n", flush=True)

    if not args.skip_langsmith:
        # The dataset first: an experiment with nothing to reference is a project.
        result = upload_gold(items)
        print(f"dataset  : {'ok ' + str(result.value) if result.ok else result.error}",
              flush=True)
        prompts = push_prompts()
        print(f"prompts  : {'ok ' + str(prompts.value) if prompts.ok else prompts.error}",
              flush=True)

    summaries = {}
    for arm, condition, level in ARMS:
        rows, judgements, costs, outputs, seconds = run_arm(
            arm, condition, level, items, warehouse, args.concurrency
        )
        summary = summarise_arm(condition, rows)
        summary["arm"] = arm
        summary["level"] = level
        summary["seconds"] = round(seconds, 1)
        summaries[arm] = summary
        (OUT / f"{arm}.json").write_text(json.dumps(summary, indent=2, default=str))

        print(
            f"{arm:20s} acc {summary['accuracy_value']:.3f}  "
            f"silent {summary['n_silent_errors']:2d}  "
            f"visible {summary['n_visible_failures']:2d}  "
            f"abstain {summary['n_abstained']:2d}  "
            f"unearned {summary['n_unearned_correct']:2d}  "
            f"est. ${summary['cost_usd']['value']:.4f}  {seconds:.0f}s",
            flush=True,
        )

        if not args.skip_langsmith:
            filed = run_experiment(arm, judgements, costs, outputs,
                                   metadata={"level": level,
                                             "condition": condition.id,
                                             "role": condition.role})
            print(f"{'':20s} langsmith: {'filed' if filed.ok else filed.error}",
                  flush=True)

    if not args.skip_langsmith:
        queue = create_fx_queue()
        print(f"\nqueue    : {'ok ' + str(queue.value) if queue.ok else queue.error}")

    (OUT / "summary.json").write_text(json.dumps(summaries, indent=2, default=str))
    print(f"\nwrote {OUT}/*.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
