"""The Events page's views: the run board (with grouped benchmark strips), the benchmark ledger
under it, the restart outcome, and the channel."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml

from datapilot.config import PACKS, active_pack, pack_config
from datapilot_console import ops_reads, views
from datapilot_console.frame import LIMITS, Live, display_tz


@lru_cache(maxsize=1)
def benchmark_questions() -> tuple[tuple[tuple[str, str], ...], int]:
    """(holdout item id and question, in file order; number of dev items) from the pack's
    benchmark files. Questions only: never gold SQL, never a result."""
    folder = PACKS / active_pack() / "benchmark"
    holdout = yaml.safe_load((folder / "holdout.yaml").read_text(encoding="utf-8")) or []
    dev = yaml.safe_load((folder / "dev.yaml").read_text(encoding="utf-8")) or []
    return tuple((str(i["id"]), str(i["question"]).strip()) for i in holdout), len(dev)


def total_runs(experiment: dict[str, Any]) -> int:
    holdout, dev_count = benchmark_questions()
    return views.planned_runs(
        experiment["split"], dev_count, len(holdout), int(experiment["holdout_repeats"])
    )


def board(live: Live, *, open_ledger: str | None) -> dict[str, Any]:
    if live.session is None:
        return views.board_view(
            [], per_lane=LIMITS["strips_per_lane"], session_open=False, display_tz=display_tz()
        )
    runs = ops_reads.board_runs(live.conn, live.session_id)
    found = ops_reads.experiments(live.conn, live.session_id)
    promotion = views.promotion_view(_promotion(live)) if found else None
    strips = [
        views.benchmark_strip_view(
            e,
            live.session_id,
            total=total_runs(e),
            expanded=open_ledger == str(e["experiment_id"]),
            promotion=promotion,
        )
        for e in found
    ]
    strips += [views.strip_view(r, live.session_id, int(r["duplicates"])) for r in runs]
    return views.board_view(
        strips, per_lane=LIMITS["strips_per_lane"], session_open=True, display_tz=display_tz()
    )


def ledger_for(live: Live, experiment_id: str | None) -> dict[str, Any]:
    """The holdout ledger of the benchmark whose strip is open, or the collapsed ledger."""
    if live.session is None or experiment_id is None:
        return views.collapsed_ledger_view()
    found = ops_reads.experiments(live.conn, live.session_id)
    chosen = next((e for e in found if str(e["experiment_id"]) == experiment_id), None)
    if chosen is None:
        return views.collapsed_ledger_view()
    promotion = _promotion(live)
    pair = views.promotion_pair(found, chosen, promotion)
    baseline, candidate = pair or (chosen, None)
    if pair is None and chosen["version_status"] != "active":
        active, _ = views.pick_experiments(found)
        if active is not None:
            baseline, candidate = active, chosen
    evaluation = pack_config()["evaluation"]
    holdout, _ = benchmark_questions()
    return views.ledger_view(
        list(holdout),
        baseline=baseline,
        candidate=candidate,
        session_id=live.session_id,
        display_tz=display_tz(),
        repeats=int(evaluation["holdout_repeats"]),
        pass_threshold=int(evaluation["holdout_pass_threshold"]),
        promotion=views.promotion_view(promotion) if pair else None,
    )


def _promotion(live: Live) -> dict[str, Any] | None:
    """The session's newest promotion while its version is still active (as the Improve page)."""
    found = ops_reads.last_promotion(live.conn, live.session.started_at) if live.session else None
    return views.active_promotion(found, ops_reads.knowledge_versions(live.conn)) if found else None


def restart_outcome(live: Live, holding: list[str]) -> str:
    """One sentence on what the worker restart did to the runs that were holding for approval."""
    if not holding:
        return "Worker restart requested. No run was holding for approval."
    runs = {str(r["run_id"]): r for r in ops_reads.board_runs(live.conn, live.session_id)}
    parts = []
    for run_id in holding:
        status = runs.get(run_id, {}).get("status")
        short = run_id[:8]
        if status == "awaiting_approval":
            parts.append(f"The pending approval survived: run {short} still holding.")
        elif status in {"failed", "rejected", "blocked_killswitch"}:
            parts.append(
                f"The pending approval was lost: run {short} is {status.replace('_', ' ')}."
            )
        else:
            parts.append(f"Run {short} moved on after the restart.")
    return "Worker restart requested. " + " ".join(parts)


def channel(live: Live) -> list[dict[str, str]]:
    """The newest posts of this session, each with its level and label in words."""
    if live.session is None:
        return []
    out = []
    for post in ops_reads.posts(live.conn, live.session_id):
        body = post["body"] or {}
        envelope = body.get("answer") or {}
        text = envelope.get("answer_text") or body.get("text") or ""
        level = views.AUTONOMY_WORDS.get(post.get("autonomy_level_applied") or "", "")
        heading = f"Posted at the {level}, {post['label']}" if level else f"Posted, {post['label']}"
        out.append({"heading": heading, "text": str(text)})
    return out
