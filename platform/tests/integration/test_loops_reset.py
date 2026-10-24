"""`make reset NAME=hill-climbing-loop` keeps this session's baseline experiment and clears the
candidate and knowledge state; `make reset-discarding-baseline` also discards the baseline."""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import loops_paths  # noqa: F401  (before loops_support)
import psycopg
import pytest
from typer.testing import CliRunner

from datapilot import db
from datapilot.cli import app as cli
from datapilot.contracts.live import SessionPurpose
from datapilot.loop3_events import autonomy, commands, sessions

pytest_plugins = ["loops_fixtures"]
pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("clean_ops")]

KNOWLEDGE_TABLES = "ops.promotion_decisions, ops.experiments, ops.knowledge_versions"


def execute(sql: str, *params: object) -> list[dict]:
    with db.connect(db.Role.OWNER) as conn:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall() if cursor.description else []
        conn.commit()
    return rows


@pytest.fixture
def knowledge_state() -> Iterator[dict[str, str]]:
    """An older session's experiment, this session's baseline (v1), a promoted candidate with its
    experiment and gate decision, the pre-authored over-broad version, eligibility, a request."""
    execute(f"TRUNCATE {KNOWLEDGE_TABLES} CASCADE")
    older = sessions.start_session(SessionPurpose.REHEARSAL, "test", "UTC")
    execute(
        "INSERT INTO ops.knowledge_versions (version, yaml, status, created_by) VALUES "
        "('v1', 'version: v1', 'retired', 'pack'), "
        "('v2-overbroad', 'version: v2-overbroad', 'draft', 'pack'), "
        "('candidate-1', 'version: candidate-1', 'active', 'analyzer')"
    )
    ids = {name: str(uuid.uuid4()) for name in ("older", "baseline", "candidate")}
    execute(
        "INSERT INTO ops.experiments (experiment_id, knowledge_version, split, session_id, "
        "started_at) VALUES (%s, 'v1', 'all', %s, now() - interval '1 day')",
        ids["older"],
        older.session_id,
    )
    current = sessions.start_session(SessionPurpose.CLASS, "test", "UTC")
    execute(
        "INSERT INTO ops.experiments (experiment_id, knowledge_version, split, session_id, "
        "started_at) VALUES (%s, 'v1', 'all', %s, now() + interval '1 second'), "
        "(%s, 'candidate-1', 'all', %s, now() + interval '2 seconds')",
        ids["baseline"],
        current.session_id,
        ids["candidate"],
        current.session_id,
    )
    execute(
        "INSERT INTO ops.promotion_decisions (candidate_version, active_version, verdict, "
        "reasons, sentence, decided_at) VALUES ('candidate-1', 'v1', 'promoted', '[]', "
        "'promoted', now() + interval '3 seconds')"
    )
    with db.connect(db.Role.APP) as conn:
        autonomy.mark_eligible(conn, "revenue", "candidate-1")
        conn.execute(
            "INSERT INTO ops.improvement_requests (request_id, kind, requested_by) "
            "VALUES (%s, 'analyzer', 'test')",
            (uuid.uuid4(),),
        )
        conn.commit()
    yield ids
    execute(f"TRUNCATE {KNOWLEDGE_TABLES} CASCADE")


def experiments() -> set[str]:
    return {str(r["experiment_id"]) for r in execute("SELECT experiment_id FROM ops.experiments")}


def versions() -> dict[str, str]:
    rows = execute("SELECT version, status FROM ops.knowledge_versions")
    return {r["version"]: r["status"] for r in rows}


def test_reset_keeps_the_baseline_and_clears_the_candidate(knowledge_state) -> None:
    report = commands.reset("hill-climbing-loop")
    assert experiments() == {knowledge_state["older"], knowledge_state["baseline"]}
    # the promoted candidate keeps its row, retired: its name is never given to other rules
    assert versions() == {"v1": "active", "v2-overbroad": "draft", "candidate-1": "retired"}
    assert (
        report.kept_baseline and report.kept_baseline.experiment_id == knowledge_state["baseline"]
    )
    assert report.removed_versions == [] and report.kept_versions == ["candidate-1"]
    assert execute("SELECT count(*) AS n FROM ops.promotion_decisions")[0]["n"] == 0
    assert execute("SELECT count(*) AS n FROM ops.autonomy_policy")[0]["n"] == 0
    assert execute("SELECT count(*) AS n FROM ops.improvement_requests")[0]["n"] == 0
    kept = [line for line in report.lines() if line.startswith("kept this session's baseline")]
    assert kept and knowledge_state["baseline"] in kept[0] and "started 20" in kept[0]


def test_the_reset_command_prints_what_it_kept_with_its_start_time(knowledge_state) -> None:
    result = CliRunner().invoke(cli, ["reset", "hill-climbing-loop"])
    assert result.exit_code == 0, result.output
    assert f"kept this session's baseline: experiment {knowledge_state['baseline']} of v1" in (
        result.output
    )
    assert "+00:00" in result.output  # the start time, UTC ISO


def test_the_full_reset_also_discards_the_baseline(knowledge_state) -> None:
    result = CliRunner().invoke(cli, ["reset-discarding-baseline", "hill-climbing-loop"])
    assert result.exit_code == 0, result.output
    assert "discarded this session's baseline" in result.output
    assert experiments() == {knowledge_state["older"]}  # earlier sessions keep their record
    assert versions()["v1"] == "active" and versions()["candidate-1"] == "retired"


def test_only_the_hill_climbing_loop_has_a_baseline_to_discard() -> None:
    with pytest.raises(ValueError):
        commands.reset("event-loop", discard_baseline=True)


def test_a_reset_with_no_baseline_says_so() -> None:
    sessions.start_session(SessionPurpose.DEVELOPMENT, "test", "UTC")
    report = commands.reset("hill-climbing-loop")
    assert "no baseline experiment in this session to keep" in report.lines()


# --- the reset archive (decision 9 on session report 2) ---
def archived(reset_id: str) -> list[dict]:
    return execute(
        "SELECT source_table, row_key, action, row FROM ops.reset_archive_rows "
        "WHERE reset_id = %s ORDER BY archive_row_id",
        reset_id,
    )


def test_the_reset_archives_every_row_before_it_deletes_or_retires_it(knowledge_state) -> None:
    execute(
        "UPDATE ops.experiments SET per_example = %s::jsonb WHERE experiment_id = %s",
        '[{"item_id": "d1", "split": "dev", "passed": false, "run_passes": [false], '
        '"confirmation": {"split": "dev", "reruns": [false, false], "confirmed": false, '
        '"steps": ["Apparent regression: confirming with 2 more runs of each version"], '
        '"active_reruns": [false, true], "active_runs": 2}}]',
        knowledge_state["candidate"],
    )
    report = commands.reset("hill-climbing-loop")
    assert report.archived is not None
    reset_id = str(report.archived.reset_id)
    header = execute("SELECT * FROM ops.reset_archives WHERE reset_id = %s", reset_id)[0]
    current = execute("SELECT session_id FROM ops.live_sessions WHERE ended_at IS NULL")[0]
    assert header["session_id"] == current["session_id"] and header["reset_at"] is not None
    assert header["reset_by"] == "make reset NAME=hill-climbing-loop"
    rows = archived(reset_id)
    by_table: dict[tuple[str, str], list[str]] = {}
    for row in rows:
        by_table.setdefault((row["source_table"], row["action"]), []).append(row["row_key"])
    assert by_table[("ops.experiments", "deleted")] == [knowledge_state["candidate"]]
    assert len(by_table[("ops.promotion_decisions", "deleted")]) == 1
    assert by_table[("ops.autonomy_policy", "deleted")] == ["revenue"]
    assert len(by_table[("ops.improvement_requests", "deleted")]) == 1
    assert by_table[("ops.knowledge_versions", "retired")] == ["datapilot_us/candidate-1"]
    assert ("ops.knowledge_versions", "deleted") not in by_table  # promoted: kept, retired
    experiment = next(r["row"] for r in rows if r["source_table"] == "ops.experiments")
    assert experiment["per_example"][0]["confirmation"]["active_reruns"] == [False, True]
    retired = next(r["row"] for r in rows if r["action"] == "retired")
    assert retired["status"] == "active"  # the row as it was before the reset
    line = next(line for line in report.lines() if line.startswith("archived "))
    assert line.startswith(f"archived {len(rows)} rows before the reset changed them")
    assert "ops.reset_archive_rows" in line and reset_id in line
    assert "1 experiment deleted" in line


def test_the_full_reset_archives_the_baseline_too(knowledge_state) -> None:
    report = commands.reset("hill-climbing-loop", discard_baseline=True)
    assert report.archived is not None
    keys = {
        r["row_key"]
        for r in archived(str(report.archived.reset_id))
        if r["source_table"] == "ops.experiments"
    }
    assert keys == {knowledge_state["baseline"], knowledge_state["candidate"]}
    header = execute(
        "SELECT discarded_baseline, reset_by FROM ops.reset_archives WHERE reset_id = %s",
        str(report.archived.reset_id),
    )[0]
    assert header["discarded_baseline"] is True
    assert header["reset_by"] == "make reset-discarding-baseline NAME=hill-climbing-loop"


def test_the_archive_commands_read_an_archived_experiment(knowledge_state) -> None:
    reset = CliRunner().invoke(cli, ["reset", "hill-climbing-loop"])
    assert reset.exit_code == 0, reset.output
    assert "archived 5 rows" in reset.output, reset.output
    listed = CliRunner().invoke(cli, ["archive", "list"])
    assert listed.exit_code == 0, listed.output
    assert "make reset NAME=hill-climbing-loop" in listed.output
    assert f"experiment {knowledge_state['candidate']} of candidate-1" in listed.output
    shown = CliRunner().invoke(cli, ["archive", "show", knowledge_state["candidate"]])
    assert shown.exit_code == 0, shown.output
    assert f"experiment {knowledge_state['candidate']} of candidate-1" in shown.output
    assert "decision " in shown.output and "promoted" in shown.output
    missing = CliRunner().invoke(cli, ["archive", "show", str(uuid.uuid4())])
    assert missing.exit_code == 1 and "no archived experiment" in missing.output


def test_the_app_role_can_add_to_the_archive_but_never_change_it(knowledge_state) -> None:
    commands.reset("hill-climbing-loop")
    for statement in (
        "DELETE FROM ops.reset_archive_rows",
        "UPDATE ops.reset_archives SET reset_by = 'someone'",
    ):
        with db.connect(db.Role.APP) as conn, pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(statement)


def test_a_version_verified_in_rehearsal_survives_the_reset(knowledge_state) -> None:
    execute(
        "INSERT INTO ops.knowledge_versions (version, yaml, status, created_by) "
        "VALUES ('rehearsed', 'version: rehearsed', 'retired', 'analyzer')"
    )
    execute(
        "INSERT INTO ops.rehearsal_verifications (pack, version, verified_by, session_id, "
        "finale_run_id, finale_question, finale_level, cleared_families) VALUES "
        "('datapilot_us', 'rehearsed', 'test', %s, %s, 'q', 'unattended', '{revenue}')",
        str(uuid.uuid4()),
        str(uuid.uuid4()),
    )
    report = commands.reset("hill-climbing-loop")
    assert "rehearsed" in versions() and "rehearsed" not in report.removed_versions


def test_the_reset_archives_and_clears_this_sessions_analyzer_candidates(knowledge_state) -> None:
    older = execute("SELECT session_id FROM ops.live_sessions WHERE ended_at IS NOT NULL")
    current = execute("SELECT session_id FROM ops.live_sessions WHERE ended_at IS NULL")
    for session in (older[0]["session_id"], current[0]["session_id"]):
        execute(
            "INSERT INTO ops.analyzer_candidates (pack, session_id, from_version, saved_as, label, "
            "candidate_version, chosen, rules, sentence) VALUES ('datapilot_us', %s, 'v1', "
            "'candidate-1', 'A', 'candidate-1-candidate-a', true, 3, 'One candidate: 3 rules.')",
            session,
        )
    report = commands.reset("hill-climbing-loop")
    left = execute("SELECT session_id FROM ops.analyzer_candidates")
    assert [r["session_id"] for r in left] == [older[0]["session_id"]], "earlier sessions keep it"
    assert report.archived is not None
    rows = [
        r
        for r in archived(str(report.archived.reset_id))
        if r["source_table"] == "ops.analyzer_candidates"
    ]
    assert [(r["action"], r["row"]["label"]) for r in rows] == [("deleted", "A")]
    assert "1 analyzer candidate deleted" in report.archived.describe()
    assert "ops.analyzer_candidates (this session)" in report.cleared
