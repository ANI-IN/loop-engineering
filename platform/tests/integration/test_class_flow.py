"""The class path of Section 4 on the tests' own database (zero tokens): a version name is never
given to a second set of rules, a reset keeps what a person approved or the gate promoted and
never deletes an experiment a runner still writes to, one runner serves a database, the runner
takes requests in order, and the finale waits for a pending promotion."""

from __future__ import annotations

import threading
import uuid
from collections.abc import Iterator

import loops_paths  # noqa: F401  (before loops_support)
import pytest
from typer.testing import CliRunner

from datapilot import db, finale
from datapilot.cli import app as cli
from datapilot.contracts import KnowledgeVersion
from datapilot.contracts.live import SessionPurpose
from datapilot.loop3_events import commands, improvement, sessions
from datapilot.loop4_hill_climbing import versions
from datapilot.loop4_hill_climbing.runner import HillClimbingRunner, RunnerAlreadyServing

pytest_plugins = ["loops_fixtures"]
pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("clean_ops")]

KNOWLEDGE_TABLES = (
    "ops.promotion_decisions, ops.experiments, ops.knowledge_versions, ops.reset_archive_rows, "
    "ops.reset_archives"
)


def execute(sql: str, *params: object) -> list[dict]:
    with db.connect(db.Role.OWNER) as conn:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall() if cursor.description else []
        conn.commit()
    return rows


@pytest.fixture
def promoted_v8() -> Iterator[None]:
    """Class: v1 shipped, v8 approved by a person and promoted by the gate in this session, with
    its candidate experiment and decision; v9, a draft nobody approved."""
    execute(f"TRUNCATE {KNOWLEDGE_TABLES} CASCADE")
    session = sessions.start_session(SessionPurpose.CLASS, "test", "UTC")
    execute(
        "INSERT INTO ops.knowledge_versions (version, yaml, status, created_by, approved_by, "
        "activated_at) VALUES ('v1', 'version: v1', 'retired', 'pack', NULL, now()), "
        "('v2-overbroad', 'version: v2-overbroad', 'retired', 'pack', NULL, NULL), "
        "('v8', 'version: v8', 'active', 'analyzer team', 'instructor', now()), "
        "('v9', 'version: v9', 'draft', 'naive analyzer', NULL, NULL)"
    )
    execute(
        "INSERT INTO ops.experiments (experiment_id, knowledge_version, split, session_id, "
        "started_at) VALUES (%s, 'v1', 'all', %s, now()), (%s, 'v8', 'all', %s, now() + "
        "interval '1 second')",
        str(uuid.uuid4()),
        session.session_id,
        str(uuid.uuid4()),
        session.session_id,
    )
    execute(
        "INSERT INTO ops.promotion_decisions (candidate_version, active_version, verdict, "
        "reasons, sentence, approved_by, decided_at) VALUES ('v8', 'v1', 'promoted', '[]', "
        "'Promoted: v8', 'instructor', now() + interval '2 seconds')"
    )
    yield
    execute(f"TRUNCATE {KNOWLEDGE_TABLES} CASCADE")


def status() -> dict[str, str]:
    rows = execute("SELECT version, status FROM ops.knowledge_versions")
    return {r["version"]: r["status"] for r in rows}


def test_a_reset_keeps_the_promoted_version_and_never_frees_a_name(promoted_v8) -> None:
    report = commands.reset("hill-climbing-loop")
    assert status() == {"v1": "active", "v2-overbroad": "retired", "v8": "retired"}
    assert report.kept_versions == ["v8"] and report.removed_versions == ["v9"]
    said = "kept, retired, the versions a person approved"
    assert any(line.startswith(said) for line in report.lines())
    with db.connect(db.Role.APP) as conn:
        # v9 is gone from ops but in the reset archive: the next draft is v10, never a second v9
        assert versions.next_name(conn) == "v10"


def test_a_draft_never_takes_a_name_in_use(promoted_v8) -> None:
    with db.connect(db.Role.APP) as conn:
        with pytest.raises(versions.VersionNameTaken, match="v8"):
            versions.save_draft(conn, KnowledgeVersion(version="v8"), created_by="test")
        assert versions.get(conn, "v8").version == "v8"  # the transaction is still usable
        versions.save_draft(conn, KnowledgeVersion(version="v10"), created_by="test")
        conn.commit()
    assert status()["v10"] == "draft"


def test_a_reset_refuses_while_the_runner_runs_a_request(promoted_v8) -> None:
    request_id = uuid.uuid4()
    execute(
        "INSERT INTO ops.improvement_requests (request_id, kind, status, started_at, "
        "requested_by) VALUES (%s, 'experiment', 'running', now(), 'test')",
        str(request_id),
    )
    with db.connect(db.Role.APP, autocommit=True) as runner:
        assert improvement.hold_runner_lock(runner)
        with pytest.raises(commands.ResetRefused, match=str(request_id)[:8]):
            commands.reset("hill-climbing-loop")
        refused = CliRunner().invoke(cli, ["reset", "hill-climbing-loop"])
        assert refused.exit_code == 1 and "not reset" in refused.output
    assert status()["v8"] == "active", "nothing changed"
    # the runner stopped (its lock went with its connection): the reset closes the request
    report = commands.reset("hill-climbing-loop")
    assert report.closed_requests == [str(request_id)]
    assert execute("SELECT count(*) AS n FROM ops.improvement_requests")[0]["n"] == 0
    archived = execute(
        "SELECT row FROM ops.reset_archive_rows WHERE source_table = 'ops.improvement_requests'"
    )
    assert archived[0]["row"]["status"] == "failed"
    assert "runner stopped" in archived[0]["row"]["result"]["error"]


def test_one_runner_serves_a_database() -> None:
    runner = HillClimbingRunner(
        items=[],
        target=None,  # type: ignore[arg-type]  (serve refuses before it uses any of them)
        evaluator=None,  # type: ignore[arg-type]
        scheme=None,  # type: ignore[arg-type]
        concurrency=1,
    )
    with db.connect(db.Role.APP, autocommit=True) as other:
        assert improvement.hold_runner_lock(other)
        with db.connect(db.Role.APP, autocommit=True) as probe:
            assert improvement.runner_serving(probe)
        with pytest.raises(RunnerAlreadyServing, match="make logs NAME=hill-climbing-runner"):
            runner.serve(threading.Event())
        started = CliRunner().invoke(cli, ["hill-climbing-runner"])
        assert started.exit_code == 2 and "already serves this database" in started.output
    with db.connect(db.Role.APP, autocommit=True) as probe:
        assert not improvement.runner_serving(probe), "the lock goes with the connection"


def test_the_runner_takes_requests_in_the_order_they_were_made() -> None:
    sessions.start_session(SessionPurpose.CLASS, "test", "UTC")
    with db.connect(db.Role.APP) as conn:
        first = improvement.enqueue(conn, "analyzer", {}, requested_by="demo")
        conn.commit()  # two api calls, two transactions: two request times
        params = {"target": "candidate"}
        second = improvement.enqueue(conn, "experiment", params, requested_by="demo")
        conn.commit()
        claimed = [improvement.claim_next(conn), improvement.claim_next(conn)]
        conn.commit()
    assert [c["request_id"] for c in claimed] == [first["request_id"], second["request_id"]]


def test_the_finale_waits_for_a_pending_promotion(promoted_v8) -> None:
    execute(
        "UPDATE ops.knowledge_versions SET status = 'approved', approved_by = 'instructor', "
        "approved_at = now() WHERE version = 'v9'"
    )
    execute("UPDATE ops.control SET autonomy_level = 'unattended'")
    with db.connect(db.Role.APP) as conn:
        state = finale.read(conn, "datapilot_us")
    assert state.pending_promotion == "v9"
    with pytest.raises(commands.FinaleRefused, match="v9 is approved"):
        commands.check_finale()
    refused = CliRunner().invoke(cli, ["demo", "improve-cleared-unattended"])
    assert refused.exit_code == 1 and "not sent" in refused.output
    # the gate decided v9 on its approval: nothing is pending, and the finale may go
    execute(
        "INSERT INTO ops.promotion_decisions (candidate_version, active_version, verdict, "
        "reasons, sentence, approved_by, decided_at) VALUES ('v9', 'v8', 'promoted', '[]', "
        "'Promoted: v9', 'instructor', now() + interval '3 seconds')"
    )
    commands.check_finale()


def test_an_approval_of_an_earlier_session_or_one_the_gate_blocked_holds_nothing(
    promoted_v8,
) -> None:
    """Review round 2: an approved version the runner could not decide in the open session (its
    approval came in an earlier one, or the gate blocked it and it stayed approved) held Send
    webhook question and the autonomy control in every later session."""
    execute(
        "UPDATE ops.knowledge_versions SET status = 'approved', approved_by = 'instructor', "
        "approved_at = now() - interval '1 day' WHERE version = 'v9'"
    )
    with db.connect(db.Role.APP) as conn:
        assert finale.read(conn, "datapilot_us").pending_promotion is None
    execute("UPDATE ops.knowledge_versions SET approved_at = now() WHERE version = 'v9'")
    with db.connect(db.Role.APP) as conn:
        assert finale.read(conn, "datapilot_us").pending_promotion == "v9"
        versions.retire_blocked(conn, "v9")  # what the gate does when it blocks v9
        conn.commit()
        assert finale.read(conn, "datapilot_us").pending_promotion is None
    assert status()["v9"] == "retired" and status()["v8"] == "active"


def test_the_finale_waits_while_the_runner_runs_the_clearance_re_runs(promoted_v8) -> None:
    execute("UPDATE ops.control SET autonomy_level = 'unattended'")
    with db.connect(db.Role.APP, autocommit=True) as runner:
        runner.execute("SELECT pg_advisory_lock(%s)", (finale.CLEARING_LOCK,))
        with db.connect(db.Role.APP) as conn:
            assert finale.read(conn, "datapilot_us").clearing == "v8"
        with pytest.raises(commands.FinaleRefused, match="clearance re-runs are still running"):
            commands.check_finale()
    with db.connect(db.Role.APP) as conn:
        assert finale.read(conn, "datapilot_us").clearing is None, "the lock went with it"
    commands.check_finale()


def test_the_finale_is_due_once_the_gate_promoted_in_this_session(promoted_v8) -> None:
    # Review round 2 (R2B-03): the webhook button sends the finale after a promotion of this
    # session even when no family cleared under it; a reset (v1 active again) ends that.
    with db.connect(db.Role.APP) as conn:
        state = finale.read(conn, "datapilot_us")
    assert state.promoted == "v8" and state.finale_due
    commands.reset("hill-climbing-loop")
    with db.connect(db.Role.APP) as conn:
        state = finale.read(conn, "datapilot_us")
    assert state.promoted is None and not state.finale_due


def test_the_finale_needs_the_unattended_level_and_a_released_kill_switch(promoted_v8) -> None:
    with pytest.raises(commands.FinaleRefused, match="report-only level"):
        commands.check_finale()
    execute("UPDATE ops.control SET kill_switch = 'engaged'")
    with pytest.raises(commands.FinaleRefused, match="kill switch is engaged"):
        commands.check_finale()
