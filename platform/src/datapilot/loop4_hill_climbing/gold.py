"""The gold check of a live run: a run that answered a benchmark question (the spine question in
the agent-loop and verification-loop demos) is compared with that item's gold SQL on both
warehouses, and the result is written as a grader_result run event with grader "gold".

The check runs after the answer, outside the verification loop: it is the instructor's view of the
truth, never a grader the analyst can see or retry against. It is written once per run.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import psycopg

from datapilot.contracts import AnswerEnvelope, BenchmarkItem, RunEventKind
from datapilot.loop3_events import lifecycle
from datapilot.loop4_hill_climbing.evaluator import ExecutionEvaluator

GOLD_GRADER = "gold"
UNCHECKED_RUNS = """
SELECT r.run_id, r.question, r.answer
FROM ops.runs r
WHERE r.session_id = (SELECT session_id FROM ops.live_sessions WHERE ended_at IS NULL)
  AND r.question = ANY(%(questions)s)
  AND r.status IN ('answered', 'posted', 'awaiting_approval', 'escalated')
  AND r.answer -> 'envelope' ->> 'final_sql' IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM ops.run_events e
      WHERE e.run_id = r.run_id AND e.kind = 'grader_result' AND e.payload ->> 'grader' = 'gold')
ORDER BY r.created_at
"""


def _first_row(evaluator: ExecutionEvaluator, sql: str) -> str | None:
    try:
        rows = evaluator.runner.run(sql, "warehouse", max_rows=1).rows
    except Exception as error:  # the agent's SQL may not run on its own; say so
        return f"query failed: {type(error).__name__}"
    if not rows:
        return None
    row = rows[0]
    return str(row[0]) if len(row) == 1 else ", ".join(str(v) for v in row)


def gold_payload(
    item: BenchmarkItem, envelope: AnswerEnvelope, evaluator: ExecutionEvaluator
) -> dict[str, Any]:
    result = evaluator.evaluate(item, envelope)
    assert item.gold_sql is not None
    each = evaluator.match_each(item, envelope.final_sql or "") if envelope.final_sql else {}
    reason = "; ".join(f"{w}: {why}" for w, (_, why) in each.items()) if each else result.reason
    return {
        "grader": GOLD_GRADER,
        "item_id": item.id,
        "passed": result.passed,
        "severity": "info",
        "reason": reason,
        "warehouses": {w: ok for w, (ok, _) in each.items()},
        "trap_labels": result.trap_labels,
        "agent_value": _first_row(evaluator, envelope.final_sql or ""),
        "gold_value": _first_row(evaluator, item.gold_sql),
        "sql": envelope.final_sql,
    }


def check_new_runs(
    conn: psycopg.Connection[Any], items: Sequence[BenchmarkItem], evaluator: ExecutionEvaluator
) -> list[str]:
    """Gold-check every run of the open session that answered a benchmark question and has no gold
    check yet; returns the run ids checked."""
    by_question = {i.question: i for i in items if i.gold_sql}
    checked = []
    for run in conn.execute(UNCHECKED_RUNS, {"questions": list(by_question)}).fetchall():
        try:
            envelope = AnswerEnvelope.model_validate(run["answer"]["envelope"])
            payload = gold_payload(by_question[run["question"]], envelope, evaluator)
        except Exception as error:  # one run that cannot be checked never blocks the others
            payload = {
                "grader": GOLD_GRADER,
                "item_id": by_question[run["question"]].id,
                "passed": False,
                "severity": "info",
                "reason": f"the gold check could not run: {type(error).__name__}: {error}"[:300],
                "trap_labels": [],
            }
        lifecycle.record(conn, str(run["run_id"]), RunEventKind.GRADER_RESULT, payload)
        checked.append(str(run["run_id"]))
    return checked
