"""The Improve page's view: the holdout ledger of this session's baseline and candidate, the
gate's verdict, the knowledge diff, and the link to the trace list filtered by knowledge version.
There is no experiment-comparison view: the ledger, scored locally, is the source of truth."""

from __future__ import annotations

from typing import Any

from datapilot.config import pack_config
from datapilot_console import ops_reads, views
from datapilot_console.events_view import benchmark_questions
from datapilot_console.frame import Live, display_tz


def build(live: Live) -> dict[str, Any]:
    if live.session is None:
        return {
            "ledger": views.no_baseline_view(),
            "gate": None,
            "diff": "",
            "candidate": None,
            "has_baseline": False,
            "promotion": None,
            "selection": None,
        }
    found = ops_reads.experiments(live.conn, live.session_id)
    versions = ops_reads.knowledge_versions(live.conn)
    active = next((v for v in versions if v["status"] == "active"), None)
    promotion = views.active_promotion(
        ops_reads.last_promotion(live.conn, live.session.started_at), versions
    )
    baseline, candidate = views.pick_experiments(found, promotion)
    pair = views.is_promotion_pair(candidate, promotion)
    # After a promotion, only a version written since it is a candidate.
    since = promotion["decided_at"] if promotion else live.session.started_at
    proposed = _proposed(versions, None if pair else candidate, since)
    gate = None
    if candidate is not None:
        gate = ops_reads.gate_decision(
            live.conn, str(candidate["knowledge_version"]), live.session.started_at
        )
    if baseline is None:
        ledger = views.no_baseline_view()
    else:
        evaluation = pack_config()["evaluation"]
        holdout, _ = benchmark_questions()
        ledger = views.ledger_view(
            list(holdout),
            baseline=baseline,
            candidate=candidate,
            session_id=live.session_id,
            display_tz=display_tz(),
            repeats=int(evaluation["holdout_repeats"]),
            pass_threshold=int(evaluation["holdout_pass_threshold"]),
            promotion=views.promotion_view(promotion) if pair else None,
        )
    return {
        "ledger": ledger,
        "gate": views.gate_view(gate["verdict"], gate["sentence"]) if gate else None,
        "diff": views.knowledge_diff(active, proposed),
        "candidate": {"version": proposed["version"], "status": proposed["status"]}
        if proposed
        else None,
        "has_baseline": baseline is not None,
        "promotion": views.promotion_view(promotion),
        # the analyzer request's choice among its candidates, by their dev results only
        "selection": proposed.get("selection") if proposed else None,
    }


def _proposed(
    versions: list[dict[str, Any]], candidate: dict[str, Any] | None, since: Any
) -> dict[str, Any] | None:
    """The candidate version: the one the candidate experiment ran, else the newest draft or
    approved version written since `since`, the session's start or its last promotion (by the
    analyzer team)."""
    if candidate is not None:
        named = str(candidate["knowledge_version"])
        return next((v for v in versions if v["version"] == named), None)
    fresh = [
        v for v in versions if v["status"] in {"draft", "approved"} and v["created_at"] >= since
    ]
    return fresh[-1] if fresh else None
