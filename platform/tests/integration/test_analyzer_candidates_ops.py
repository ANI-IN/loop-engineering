"""The analyzer request's candidates in ops (Compose Postgres, zero tokens): each candidate is a
row, the kept one marked chosen; a candidate's own version is retired at once, so it is never
offered for approval; the console's version read carries the choice's sentence for the kept
draft."""

from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest

from datapilot import db
from datapilot.contracts import ItemResult, KnowledgeVersion, Split
from datapilot.loop4_hill_climbing import candidates, versions
from datapilot.loop4_hill_climbing.analyzer import AnalyzerReport
from datapilot.loop4_hill_climbing.experiment import ExperimentResult
from datapilot.settings import PLATFORM

sys.path.insert(0, str(PLATFORM / "console"))

from datapilot_console import ops_reads  # noqa: E402

pytestmark = pytest.mark.integration


@pytest.fixture
def conn() -> Iterator[Any]:
    with db.connect(db.Role.APP) as connection:
        yield connection
        connection.rollback()


def _session(conn: Any) -> uuid.UUID:
    session_id = uuid.uuid4()
    conn.execute("UPDATE ops.live_sessions SET ended_at = now() WHERE ended_at IS NULL")
    conn.execute(
        "INSERT INTO ops.live_sessions (session_id, started_by, timezone) "
        "VALUES (%s, 'integration test', 'UTC')",
        (session_id,),
    )
    return session_id


def _dev(version: str, passes: dict[str, bool], session_id: uuid.UUID) -> ExperimentResult:
    return ExperimentResult(
        experiment_id=uuid.uuid4(),
        session_id=session_id,
        knowledge_version=version,
        splits=[Split.DEV],
        results={i: ItemResult(item_id=i, passed=p, reason="") for i, p in passes.items()},
        splits_by_item={i: Split.DEV for i in passes},
        started_at=datetime.now(UTC),
        wall_seconds=1.0,
    )


def test_the_candidates_and_the_choice_are_recorded(conn: Any) -> None:
    session_id = _session(conn)
    runs = []
    for index, passes in enumerate([{"d1": True, "d2": True}, {"d1": True, "d2": False}]):
        version = candidates.selection_version("ops-test-v9", index)
        report = AnalyzerReport(candidate=KnowledgeVersion(version=version))
        candidates.save_selection_draft(conn, report.candidate)
        dev = _dev(version, passes, session_id)
        runs.append(candidates.CandidateRun(candidates.label(index), version, report, dev, []))
    chosen = candidates.choose(runs)
    versions.save_draft(conn, KnowledgeVersion(version="ops-test-v9"), created_by="test")
    said = candidates.save(
        conn,
        runs,
        chosen,
        session_id=session_id,
        request_id=None,
        from_version="v1",
        saved_as="ops-test-v9",
        naive=False,
    )
    assert said == (
        "Candidate A: 2 of 2 dev, 0 regressions, 0 rules; "
        "Candidate B: 1 of 2 dev, 0 regressions, 0 rules; chosen: A"
    )
    rows = conn.execute(
        "SELECT label, chosen, dev_passes, dev_total FROM ops.analyzer_candidates "
        "WHERE session_id = %s ORDER BY label",
        (session_id,),
    ).fetchall()
    assert [(r["label"], r["chosen"], r["dev_passes"]) for r in rows] == [
        ("A", True, 2),
        ("B", False, 1),
    ]
    assert versions.status_of(conn, "ops-test-v9-candidate-a")["status"] == "retired"
    assert versions.latest_candidate(conn) == "ops-test-v9"
    found = {v["version"]: v for v in ops_reads.knowledge_versions(conn)}
    assert found["ops-test-v9"]["selection"] == said
    assert found["ops-test-v9-candidate-b"]["selection"] is None
