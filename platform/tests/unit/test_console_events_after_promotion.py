"""After a promotion the Events page names benchmark strips the way the Improve page does (the
promoted version active, the earlier one replaced), and an open strip's ledger pairs the
promotion's replaced and active versions."""

from __future__ import annotations

import sys
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from datapilot.contracts.live import LiveSession, SessionPurpose
from datapilot.settings import PLATFORM

CONSOLE = PLATFORM / "console"
if str(CONSOLE) not in sys.path:
    sys.path.insert(0, str(CONSOLE))

from datapilot_console import events_view, ops_reads, views  # noqa: E402
from datapilot_console.frame import Live  # noqa: E402

STARTED = datetime(2026, 10, 22, 11, 59, 9, tzinfo=UTC)
SESSION = uuid.uuid4()
PROMOTION = {
    "candidate_version": "v2",
    "active_version": "v1",
    "approved_by": "ani",
    "decided_at": STARTED + timedelta(minutes=20),
}


def _experiment(version: str, status: str, minutes: int) -> dict[str, Any]:
    started = STARTED + timedelta(minutes=minutes)
    return {
        "experiment_id": uuid.uuid4(),
        "knowledge_version": version,
        "version_status": status,
        "split": "all",
        "holdout_repeats": 3,
        "per_example": [
            {"item_id": "average-list-price-active", "split": "holdout", "run_passes": [True] * 3}
        ],
        "langsmith_url": f"https://smith.example/list?version={version}",
        "started_at": started,
        "finished_at": started + timedelta(minutes=2),
    }


VERSIONS = [
    {"version": "v1", "status": "retired", "created_at": STARTED - timedelta(days=3)},
    {"version": "v2", "status": "active", "created_at": STARTED + timedelta(minutes=5)},
]


def _live(
    monkeypatch: pytest.MonkeyPatch,
    experiments: list[dict[str, Any]],
    promotion: dict[str, Any] | None,
) -> Live:
    monkeypatch.setattr(ops_reads, "experiments", lambda conn, session: experiments)
    monkeypatch.setattr(ops_reads, "board_runs", lambda conn, session: [])
    monkeypatch.setattr(ops_reads, "knowledge_versions", lambda conn: VERSIONS)
    monkeypatch.setattr(ops_reads, "last_promotion", lambda conn, since: promotion)
    session = LiveSession(
        session_id=SESSION,
        purpose=SessionPurpose.DEVELOPMENT,
        started_at=STARTED,
        started_by="ani",
        timezone="UTC",
    )
    return Live(conn=None, session=session, changed=True)  # type: ignore[arg-type]


def test_benchmark_names_follow_the_promotion() -> None:
    promotion = views.promotion_view(PROMOTION)
    assert views.benchmark_name(_experiment("v2", "active", 10), promotion) == (
        "v2 benchmark, active"
    )
    assert views.benchmark_name(_experiment("v1", "retired", 1), promotion) == (
        "v1 benchmark, replaced"
    )
    assert views.benchmark_name(_experiment("v1", "active", 1)) == "Baseline benchmark"
    assert views.benchmark_name(_experiment("v2", "draft", 10)) == "Candidate benchmark"


def test_after_a_promotion_no_strip_calls_the_promoted_version_the_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    experiments = [_experiment("v1", "retired", 1), _experiment("v2", "active", 10)]
    board = events_view.board(_live(monkeypatch, experiments, PROMOTION), open_ledger=None)
    labels = [s["label"] for s in board["strips"] if s["kind"] == "benchmark"]
    assert labels == ["v1 benchmark, replaced", "v2 benchmark, active"]
    assert not any("Baseline" in label for label in labels)


@pytest.mark.parametrize("open_index", [0, 1])
def test_an_open_strip_pairs_the_replaced_and_the_promoted_version(
    monkeypatch: pytest.MonkeyPatch, open_index: int
) -> None:
    experiments = [_experiment("v1", "retired", 1), _experiment("v2", "active", 10)]
    chosen = str(experiments[open_index]["experiment_id"])
    ledger = events_view.ledger_for(_live(monkeypatch, experiments, PROMOTION), chosen)
    assert ledger["state"] == "live"
    assert ledger["active_label"] == "v1, replaced"
    assert ledger["candidate_label"] == "v2, active"
    assert ledger["baseline_heading"] == "Replaced, v1"
    assert ledger["candidate_heading"] == "Active, v2, promoted by ani"


def test_a_promotion_no_longer_active_changes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    experiments = [_experiment("v1", "active", 1), _experiment("v3", "draft", 10)]
    stale = {**PROMOTION, "candidate_version": "v3"}
    board = events_view.board(_live(monkeypatch, experiments, stale), open_ledger=None)
    labels = [s["label"] for s in board["strips"] if s["kind"] == "benchmark"]
    assert labels == ["Baseline benchmark", "Candidate benchmark"]


def test_the_style_tile_uses_the_gate_wording() -> None:
    tile = (CONSOLE / "design" / "style_tile.py").read_text(encoding="utf-8")
    assert "Gate: ready for human approval." in tile
