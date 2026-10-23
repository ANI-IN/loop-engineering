"""The Agent and Verify pages' view of one run: its status, tool calls, SQL with trap notes,
graders, defense layers, the gold check, and the reviewer, all from ops.runs and ops.run_events
of the open session."""

from __future__ import annotations

from typing import Any

from datapilot.config import pack_config
from datapilot.contracts.lifecycle import RunStatus
from datapilot_console import ops_reads, views
from datapilot_console.frame import Live, display_tz


def pick(live: Live, chosen: str | None, prefix: str) -> dict[str, Any] | None:
    """The run this page started (when it belongs to the open session), else the session's newest
    run of this page's demos. Never a run of another session."""
    if live.session is None:
        return None
    if chosen:
        run = ops_reads.run_by_id(live.conn, live.session_id, chosen)
        if run is not None:
            return run
    return ops_reads.latest_run(live.conn, live.session_id, prefix)


def build(live: Live, chosen: str | None, prefix: str) -> dict[str, Any]:
    run = pick(live, chosen, prefix)
    if run is None:
        return {"run": None, "sql": views.sql_view(None, [], stamp=None, display_tz=display_tz())}
    events = ops_reads.run_events(live.conn, run["run_id"])
    gold = views.gold_check(events)
    # ops.runs.answer holds the answer envelope under "envelope", beside the run's reasons.
    stored = run["answer"] or {}
    answer = stored.get("envelope") or {}
    status = RunStatus(run["status"])
    _, word, _ = views.STATUS_VIEW[status]
    return {
        "run": {
            "run_id": str(run["run_id"]),
            "question": run["question"] or "",
            "status": status.value,
            "word": word,
            "finished": views.is_finished(run),
            "summary": views.run_summary(run),
            "answer_text": str(answer.get("answer_text", "")),
            "row_count": answer.get("row_count"),
        },
        "sql": views.sql_view(
            answer.get("final_sql"),
            gold["trap_labels"] if gold else [],
            stamp=views.run_stamp(run, live.session_id),
            display_tz=display_tz(),
        ),
        "tools": views.tool_calls(events),
        "gold": gold,
        "checklist": views.checklist(events, int(pack_config()["limits"]["max_retries"])),
        "defense": views.defense_layers(events),
        "reviewer": views.reviewer_verdict(events),
        "tokens_cap": int(pack_config()["budgets"]["tokens_per_run"]),
        "tokens": int(run["tokens_in"] or 0) + int(run["tokens_out"] or 0),
    }
