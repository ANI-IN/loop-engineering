"""The ops schema migrates once and grants each role only what it needs (Compose Postgres)."""

from __future__ import annotations

import psycopg
import pytest

from datapilot import db

pytestmark = pytest.mark.integration


def test_migrations_are_idempotent() -> None:
    db.migrate()
    assert db.migrate() == []


def test_the_app_role_reads_the_control_row() -> None:
    with db.connect(db.Role.APP) as conn:
        row = conn.execute("SELECT kill_switch, autonomy_level FROM ops.control").fetchone()
    assert row == {"kill_switch": "released", "autonomy_level": "report_only"}


def test_the_agent_role_cannot_read_ops() -> None:
    with db.connect(db.Role.AGENT) as conn, pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("SELECT * FROM ops.control")


def test_the_agent_role_cannot_create_temp_tables() -> None:
    # The role logs in read-only (roles.sql); switch that seatbelt off to reach the privilege check.
    with db.connect(db.Role.AGENT, autocommit=True) as conn:
        conn.execute("SET default_transaction_read_only = off")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("CREATE TEMP TABLE scratch (a int)")


def test_a_run_event_kind_outside_the_contract_is_refused() -> None:
    with db.connect(db.Role.APP) as conn, pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("INSERT INTO ops.runs (run_id, status) VALUES (gen_random_uuid(), 'received')")
        conn.execute(
            "INSERT INTO ops.run_events (run_id, kind) "
            "SELECT run_id, 'not_a_kind' FROM ops.runs LIMIT 1"
        )


def test_only_one_knowledge_version_can_be_active() -> None:
    with db.connect(db.Role.APP) as conn, pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(
            "INSERT INTO ops.knowledge_versions (version, yaml, status, created_by) VALUES "
            "('test-a', '', 'active', 'test'), ('test-b', '', 'active', 'test')"
        )
