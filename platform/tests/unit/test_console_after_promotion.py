"""After a promotion the Improve page shows the promoted version as the active one, with its
promotion, beside the version it replaced; "No candidate version" only when none was written
since the promotion."""

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

from datapilot_console import improve_view, ops_reads, views  # noqa: E402
from datapilot_console.frame import Live  # noqa: E402

STARTED = datetime(2026, 10, 22, 11, 59, 9, tzinfo=UTC)
SESSION = uuid.uuid4()
PROMOTED = (
    "Promoted: v2 passes 9 of 15 holdout items against 6, with no regressions, approved by ani."
)


# --- After a promotion: the promoted version is active, beside the version it replaced -------


def _experiment(version: str, status: str, started_at: datetime) -> dict[str, Any]:
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
        "started_at": started_at,
        "finished_at": started_at + timedelta(minutes=2),
    }


def _version(version: str, status: str, created_at: datetime) -> dict[str, Any]:
    return {
        "version": version,
        "yaml": f"version: {version}\n",
        "status": status,
        "created_at": created_at,
        "approved_by": "ani" if status != "draft" else None,
    }


PROMOTION = {
    "candidate_version": "v2",
    "active_version": "v1",
    "approved_by": "ani",
    "decided_at": STARTED + timedelta(minutes=20),
}


def _build(
    monkeypatch: pytest.MonkeyPatch,
    experiments: list[dict[str, Any]],
    versions: list[dict[str, Any]],
    promotion: dict[str, Any] | None,
) -> dict[str, Any]:
    gate = {"verdict": "promoted", "sentence": PROMOTED, "decided_at": PROMOTION["decided_at"]}
    monkeypatch.setattr(ops_reads, "experiments", lambda conn, session: experiments)
    monkeypatch.setattr(ops_reads, "knowledge_versions", lambda conn: versions)
    monkeypatch.setattr(ops_reads, "gate_decision", lambda conn, version, since: gate)
    monkeypatch.setattr(ops_reads, "last_promotion", lambda conn, since: promotion)
    session = LiveSession(
        session_id=SESSION,
        purpose=SessionPurpose.DEVELOPMENT,
        started_at=STARTED,
        started_by="ani",
        timezone="UTC",
    )
    return improve_view.build(Live(conn=None, session=session, changed=True))  # type: ignore[arg-type]


def _promoted_session() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    experiments = [
        _experiment("v1", "retired", STARTED + timedelta(minutes=1)),
        _experiment("v2", "active", STARTED + timedelta(minutes=10)),
    ]
    versions = [
        _version("v1", "retired", STARTED - timedelta(days=3)),
        _version("v2", "active", STARTED + timedelta(minutes=5)),
    ]
    return experiments, versions


def test_after_a_promotion_the_promoted_version_is_the_active_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    experiments, versions = _promoted_session()
    view = _build(monkeypatch, experiments, versions, PROMOTION)
    ledger = view["ledger"]
    assert ledger["state"] == "live"
    assert ledger["candidate_version"] == "v2"
    assert ledger["active_label"] == "v1, replaced"
    assert ledger["candidate_label"] == "v2, active"
    assert ledger["baseline_heading"] == "Replaced, v1"
    assert ledger["candidate_heading"] == "Active, v2, promoted by ani"
    assert "Baseline" not in ledger["baseline_heading"] + ledger["candidate_heading"]
    assert view["promotion"] == {"version": "v2", "replaced": "v1", "approved_by": "ani"}
    assert view["candidate"] is None
    text = views.no_candidate_text(view["promotion"])
    assert text.startswith("v2 is the active version, promoted from v1, approved by ani.")
    assert "since the promotion" in text


def test_a_draft_written_after_the_promotion_is_the_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    experiments, versions = _promoted_session()
    stale = _version("v2b", "draft", STARTED + timedelta(minutes=6))
    fresh = _version("v3", "draft", STARTED + timedelta(minutes=30))
    view = _build(monkeypatch, experiments, [*versions, stale], PROMOTION)
    assert view["candidate"] is None, "a draft from before the promotion is not a candidate"
    view = _build(monkeypatch, experiments, [*versions, stale, fresh], PROMOTION)
    assert view["candidate"] == {"version": "v3", "status": "draft"}


def test_without_a_promotion_the_ledger_keeps_baseline_and_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    experiments = [
        _experiment("v1", "active", STARTED + timedelta(minutes=1)),
        _experiment("v2", "draft", STARTED + timedelta(minutes=10)),
    ]
    versions = [
        _version("v1", "active", STARTED - timedelta(days=3)),
        _version("v2", "draft", STARTED + timedelta(minutes=5)),
    ]
    view = _build(monkeypatch, experiments, versions, None)
    ledger = view["ledger"]
    assert ledger["baseline_heading"] == "Baseline, v1, active"
    assert ledger["candidate_heading"] == "Candidate, v2"
    assert view["promotion"] is None
    assert view["candidate"] == {"version": "v2", "status": "draft"}
    assert views.no_candidate_text(None).startswith("No candidate version in this session yet.")


def test_the_ledger_takes_its_stamp_headings_from_the_view() -> None:
    js = (CONSOLE / "datapilot_console" / "components" / "holdout_ledger.js").read_text("utf-8")
    assert "data.baseline_heading" in js and "data.candidate_heading" in js
    assert "'Baseline, '" not in js and "'Candidate, '" not in js
