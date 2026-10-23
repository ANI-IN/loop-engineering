"""The Improve page shows the analyzer request's choice among its candidates beside the knowledge
diff of the version it kept, and nothing for a version the analyzer did not choose that way."""

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

from datapilot_console import improve_view, ops_reads  # noqa: E402
from datapilot_console.frame import Live  # noqa: E402

STARTED = datetime(2026, 10, 23, 9, 0, tzinfo=UTC)
CHOICE = (
    "Candidate A: 14 of 25 dev, 0 regressions, 7 rules; "
    "Candidate B: 12 of 25 dev, 1 regression, 8 rules; chosen: A"
)


def _build(monkeypatch: pytest.MonkeyPatch, draft: dict[str, Any]) -> dict[str, Any]:
    active = {
        "version": "v1",
        "yaml": "version: v1\n",
        "status": "active",
        "created_at": STARTED - timedelta(days=1),
        "approved_by": None,
    }
    monkeypatch.setattr(ops_reads, "experiments", lambda conn, session: [])
    monkeypatch.setattr(ops_reads, "knowledge_versions", lambda conn: [active, draft])
    monkeypatch.setattr(ops_reads, "gate_decision", lambda conn, version, since: None)
    monkeypatch.setattr(ops_reads, "last_promotion", lambda conn, since: None)
    session = LiveSession(
        session_id=uuid.uuid4(),
        purpose=SessionPurpose.DEVELOPMENT,
        started_at=STARTED,
        started_by="ani",
        timezone="UTC",
    )
    return improve_view.build(Live(conn=None, session=session, changed=True))  # type: ignore[arg-type]


def _draft(**extra: Any) -> dict[str, Any]:
    return {
        "version": "v2",
        "yaml": "version: v2\n",
        "status": "draft",
        "created_at": STARTED + timedelta(minutes=5),
        "approved_by": None,
        **extra,
    }


def test_the_kept_candidate_shows_the_choice(monkeypatch: pytest.MonkeyPatch) -> None:
    view = _build(monkeypatch, _draft(selection=CHOICE))
    assert view["candidate"] == {"version": "v2", "status": "draft"}
    assert view["selection"] == CHOICE


def test_a_version_without_a_choice_shows_none(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _build(monkeypatch, _draft())["selection"] is None


def test_the_versions_read_carries_the_chosen_candidates_sentence() -> None:
    assert "ops.analyzer_candidates" in ops_reads.VERSIONS and "c.chosen" in ops_reads.VERSIONS
