"""Run a whole gold set through the Level 2 loop, persisting every item.

Per-item outcomes are the point. A batch that saves only aggregates cannot be paired
with anything afterwards, which is how a comparison that should have been McNemar ends
up being two intervals eyeballed for overlap. The first Gate 2 pass made exactly that
mistake and had to be re-run.
"""

import json
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from loopeng.agent.classify import Outcome, judge
from loopeng.agent.loop import AgentRun
from loopeng.gold.build import GoldItem, json_default
from loopeng.metric import Metric
from loopeng.verify.governance import verify_governed
from loopeng.verify.loop import run_verified

CONCURRENCY = 8


def as_agent_run(verified) -> AgentRun:
    """Adapt a VerifiedRun so the Phase 1 classifier judges it unchanged."""
    return AgentRun(
        question=verified.question,
        level=verified.level,
        role=verified.role,
        model_id=verified.model_id,
        attempts=tuple(a.attempt for a in verified.attempts),
        termination=verified.termination,
        item_id=verified.item_id,
        ledger=verified.ledger,
    )


def run_level2_pass(
    items: list[GoldItem],
    warehouse: Path,
    *,
    role: str = "worker",
    level: str = "L3",
    max_attempts: int = 3,
    budget_usd: float = 0.15,
    verifier=verify_governed,
    client=None,
) -> dict:
    start = time.perf_counter()
    rows = []
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futures = {
            pool.submit(
                run_verified,
                item.question,
                warehouse=warehouse,
                rules=item.rules,
                role=role,
                level=level,
                max_attempts=max_attempts,
                budget_usd=budget_usd,
                item_id=item.item_id,
                verifier=verifier,
                client=client,
            ): item
            for item in items
        }
        for future in as_completed(futures):
            item = futures[future]
            verified = future.result()
            judgement = judge(as_agent_run(verified), item)
            rows.append(
                {
                    "item_id": item.item_id,
                    "pattern_key": item.pattern_key,
                    "role": role,
                    "level": level,
                    "termination": str(verified.termination),
                    "n_attempts": len(verified.attempts),
                    "rejections": verified.rejections,
                    "sql": verified.sql,
                    "rows": verified.rows,
                    "error": verified.error,
                    "outcome": str(judgement.outcome),
                    "visible_kind": (
                        str(judgement.visible_kind) if judgement.visible_kind else None
                    ),
                    "ran_and_returned": judgement.ran_and_returned,
                    "correct": judgement.outcome is Outcome.CORRECT,
                    "attributed_rules": list(judgement.attributed_rules),
                    "cost_usd": verified.cost_usd(),
                }
            )
            del verified

    elapsed = time.perf_counter() - start
    ran = [r for r in rows if r["ran_and_returned"]]
    correct = sum(1 for r in ran if r["correct"])
    silent = len(ran) - correct
    # Totals come from the per-item costs rather than holding every ledger in memory.
    total_cost = sum(r["cost_usd"] for r in rows)

    return {
        "role": role,
        "level": level,
        "max_attempts": max_attempts,
        "n_items": len(rows),
        "seconds": round(elapsed, 1),
        "rejections": sum(r["rejections"] for r in rows),
        "termination": dict(Counter(r["termination"] for r in rows)),
        "ran_and_returned": len(ran),
        "correct": correct,
        "silent_errors": silent,
        "silent_error_rate": (
            Metric.from_counts(silent, len(ran)).render() if ran else "not yet measured"
        ),
        "cost_usd": {"value": round(total_cost, 6), "source": "estimated"},
        "items": sorted(rows, key=lambda r: r["item_id"]),
    }


def save_pass(report: dict, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=json_default), encoding="utf-8")
    return path


def correct_by_item(report: dict) -> dict[str, bool]:
    """{item_id: was_correct} over items that ran. The input to McNemar."""
    return {r["item_id"]: r["correct"] for r in report["items"] if r["ran_and_returned"]}
