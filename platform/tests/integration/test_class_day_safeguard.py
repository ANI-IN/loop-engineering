"""The class-day safeguard (decision 2 on session report 2), on the tests' own database: a version
is marked verified in rehearsal by its correct finale run, and in class one command activates it
through the normal activation path, recorded as a safeguard activation beside the gate's records,
with only the families it cleared in rehearsal at the unattended level under it."""

from __future__ import annotations

import sys
import uuid
from collections.abc import Iterator
from typing import Any

import loops_paths  # noqa: F401  (before loops_support)
import pytest
from psycopg.types.json import Jsonb
from typer.testing import CliRunner

from datapilot import db
from datapilot.cli import app as cli
from datapilot.contracts.live import SessionPurpose
from datapilot.demo_questions import SPINE_QUESTION
from datapilot.loop3_events import autonomy, commands, sessions
from datapilot.loop4_hill_climbing import versions
from datapilot.settings import PLATFORM

sys.path.insert(0, str(PLATFORM / "console"))

from datapilot_console import ops_reads, views  # noqa: E402

pytest_plugins = ["loops_fixtures"]
pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("clean_ops")]

KNOWLEDGE_TABLES = "ops.promotion_decisions, ops.experiments, ops.knowledge_versions"
REHEARSED, CLASS_CANDIDATE = "v5", "v7"


def execute(sql: str, *params: object) -> list[dict]:
    with db.connect(db.Role.OWNER) as conn:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall() if cursor.description else []
        conn.commit()
    return rows


def finale_run(
    session_id: Any,
    *,
    version: str = REHEARSED,
    passed: bool | None = True,
    question: str = SPINE_QUESTION,
) -> str:
    """A posted finale run with its gold check (None: no gold check yet)."""
    run_id = str(uuid.uuid4())
    execute(
        "INSERT INTO ops.runs (run_id, demo_name, question, metric_family, status, "
        "autonomy_level_applied, knowledge_version, session_id) VALUES "
        "(%s, 'improve-cleared-unattended', %s, 'revenue', 'posted', 'unattended', %s, %s)",
        run_id,
        question,
        version,
        session_id,
    )
    if passed is not None:
        execute(
            "INSERT INTO ops.run_events (run_id, kind, payload) VALUES (%s, 'grader_result', %s)",
            run_id,
            Jsonb(
                {
                    "grader": "gold",
                    "passed": passed,
                    "reason": "matches gold" if passed else "row 1 differs from gold",
                    "agent_value": "64015091.21" if passed else "63986616.77",
                    "gold_value": "64015091.21",
                }
            ),
        )
    return run_id


@pytest.fixture
def rehearsal() -> Iterator[Any]:
    """A rehearsal session in which v5 was promoted and cleared revenue for the unattended level."""
    execute(f"TRUNCATE {KNOWLEDGE_TABLES} CASCADE")
    execute(
        "INSERT INTO ops.knowledge_versions (version, yaml, status, created_by) VALUES "
        "('v1', 'version: v1', 'retired', 'pack'), "
        "('v5', 'version: v5', 'active', 'analyzer team')"
    )
    session = sessions.start_session(SessionPurpose.REHEARSAL, "test", "UTC")
    with db.connect(db.Role.APP) as conn:
        autonomy.mark_eligible(conn, "revenue", REHEARSED)
        conn.commit()
    yield session
    execute(f"TRUNCATE {KNOWLEDGE_TABLES} CASCADE")


def verify(run_id: str, name: str = REHEARSED) -> versions.RehearsalVerification:
    with db.connect(db.Role.APP) as conn:
        found = versions.verify_in_rehearsal(conn, name, run_id, verified_by="lead, rehearsal")
        conn.commit()
    return found


def class_day() -> Any:
    """Class: v7 promoted by the gate, cleared for revenue and orders, gives a wrong finale."""
    session = sessions.start_session(SessionPurpose.CLASS, "test", "UTC")
    execute(
        "INSERT INTO ops.knowledge_versions (version, yaml, status, created_by) "
        "VALUES ('v7', 'version: v7', 'retired', 'analyzer team')"
    )
    with db.connect(db.Role.APP) as conn:
        versions.activate(conn, CLASS_CANDIDATE)
        conn.execute(
            "INSERT INTO ops.promotion_decisions (candidate_version, active_version, verdict, "
            "reasons, sentence, approved_by) VALUES ('v7', 'v5', 'promoted', '[]', "
            "'Promoted: v7 passes 12 of 15 holdout items', 'instructor')"
        )
        autonomy.mark_eligible(conn, "revenue", CLASS_CANDIDATE)
        autonomy.mark_eligible(conn, "orders", CLASS_CANDIDATE)
        conn.commit()
    return session


def test_a_correct_rehearsal_finale_marks_its_version_verified(rehearsal) -> None:
    run_id = finale_run(rehearsal.session_id)
    found = verify(run_id)
    assert found.version == REHEARSED and found.finale_run_id == run_id
    assert found.cleared_families == ["revenue"] and found.finale_level == "unattended"
    assert found.agent_value == found.gold_value == "64015091.21"
    stored = execute("SELECT verified_by, session_id FROM ops.rehearsal_verifications")
    assert stored == [{"verified_by": "lead, rehearsal", "session_id": rehearsal.session_id}]


@pytest.mark.parametrize(
    ("kind", "says"),
    [
        ("wrong answer", "its gold check failed"),
        ("no gold check", "it has no gold check yet"),
        ("other version", "it ran under v1, not v5"),
        ("other question", "it is not the finale question"),
    ],
)
def test_only_a_correct_finale_of_the_version_can_verify_it(rehearsal, kind, says) -> None:
    run_id = {
        "wrong answer": lambda: finale_run(rehearsal.session_id, passed=False),
        "no gold check": lambda: finale_run(rehearsal.session_id, passed=None),
        "other version": lambda: finale_run(rehearsal.session_id, version="v1"),
        "other question": lambda: finale_run(rehearsal.session_id, question="How many orders?"),
    }[kind]()
    with pytest.raises(versions.SafeguardRefused, match=says):
        verify(run_id)
    assert execute("SELECT count(*) AS n FROM ops.rehearsal_verifications")[0]["n"] == 0


def test_a_finale_outside_rehearsal_cannot_verify(rehearsal) -> None:
    development = sessions.start_session(SessionPurpose.DEVELOPMENT, "test", "UTC")
    run_id = finale_run(development.session_id)
    with pytest.raises(versions.SafeguardRefused, match="development, not a rehearsal"):
        verify(run_id)


def test_the_safeguard_activates_the_rehearsed_version_with_its_own_clearance(rehearsal) -> None:
    verify(finale_run(rehearsal.session_id))
    class_session = class_day()
    with db.connect(db.Role.APP) as conn:
        done = versions.activate_verified(conn, activated_by="instructor")
        conn.commit()
    assert (done.version, done.replaced) == (REHEARSED, CLASS_CANDIDATE)
    with db.connect(db.Role.APP) as conn:
        assert versions.active_name(conn) == REHEARSED
        policy = autonomy.OpsAutonomyPolicy.load(conn, REHEARSED)
    assert policy.eligible == frozenset({"revenue"})  # orders was cleared under v7 only
    assert "cleared in rehearsal on" in (policy.notes["revenue"] or "")
    decisions = execute(
        "SELECT candidate_version, active_version, verdict, kind, approved_by, sentence "
        "FROM ops.promotion_decisions ORDER BY decision_id"
    )
    assert decisions[0]["candidate_version"] == CLASS_CANDIDATE and decisions[0]["kind"] == "gate"
    safeguard = decisions[1]
    assert (safeguard["candidate_version"], safeguard["active_version"]) == ("v5", "v7")
    assert (safeguard["kind"], safeguard["verdict"], safeguard["approved_by"]) == (
        "safeguard",
        "promoted",
        "instructor",
    )
    assert safeguard["sentence"].startswith("Safeguard activation: v5, verified in rehearsal")
    with db.connect(db.Role.APP) as conn:
        state = ops_reads.status(conn, class_session.session_id)
        promotion = ops_reads.last_promotion(conn, class_session.started_at)
    assert state["family_levels"] == {"revenue": "unattended", "orders": "assisted"}
    assert views.safeguard_notice(state["safeguard"]).startswith(
        "Class-day safeguard: v5 is active, the version verified in rehearsal"
    )
    shown = views.promotion_view(promotion)
    assert shown is not None and shown["safeguard"] is True
    assert "activated by the class-day safeguard" in views.no_candidate_text(shown)


def test_the_safeguard_needs_a_verified_version_and_never_reactivates_one(rehearsal) -> None:
    with db.connect(db.Role.APP) as conn, pytest.raises(versions.SafeguardRefused):
        versions.activate_verified(conn, activated_by="instructor")
    verify(finale_run(rehearsal.session_id))
    with db.connect(db.Role.APP) as conn, pytest.raises(versions.SafeguardRefused, match="already"):
        versions.activate_verified(conn, activated_by="instructor")


def test_the_safeguard_commands(rehearsal) -> None:
    run_id = finale_run(rehearsal.session_id)
    refused = CliRunner().invoke(
        cli, ["safeguard", "verify", "v1", "--run", run_id, "--by", "lead"]
    )
    assert refused.exit_code == 1 and "cannot verify v1" in refused.output
    marked = CliRunner().invoke(
        cli, ["safeguard", "verify", REHEARSED, "--run", run_id, "--by", "lead"]
    )
    assert marked.exit_code == 0, marked.output
    assert "verified in rehearsal: v5" in marked.output
    class_day()
    done = CliRunner().invoke(cli, ["safeguard", "activate", "--by", "instructor"])
    assert done.exit_code == 0, done.output
    assert "Safeguard activation: v5" in done.output
    assert "make demo NAME=improve-cleared-unattended" in done.output
    status = CliRunner().invoke(cli, ["safeguard", "status"])
    assert "active knowledge version: v5 (the safeguard's)" in status.output


def test_a_class_reset_after_the_safeguard_archives_its_decision_and_keeps_the_version(
    rehearsal,
) -> None:
    verify(finale_run(rehearsal.session_id))
    class_day()
    with db.connect(db.Role.APP) as conn:
        versions.activate_verified(conn, activated_by="instructor")
        conn.commit()
    report = commands.reset("hill-climbing-loop")
    assert report.archived is not None
    kinds = [
        r["row"]["kind"]
        for r in execute(
            "SELECT row FROM ops.reset_archive_rows WHERE reset_id = %s "
            "AND source_table = 'ops.promotion_decisions'",
            str(report.archived.reset_id),
        )
    ]
    assert sorted(kinds) == ["gate", "safeguard"]
    names = {r["version"] for r in execute("SELECT version FROM ops.knowledge_versions")}
    assert REHEARSED in names
