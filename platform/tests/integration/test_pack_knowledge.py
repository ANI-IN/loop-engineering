"""Knowledge versions belong to one pack: each pack installs its own v1, keeps its own active
version and candidates, and a reset or the console touches only the selected pack's versions; the
preflight data check reads the selected pack's table as the agent's role (tests' Postgres, zero
tokens)."""

from __future__ import annotations

import sys
from collections.abc import Iterator

import psycopg
import pytest

from datapilot import db
from datapilot.contracts import KnowledgeRule, KnowledgeVersion
from datapilot.loop1_agent.knowledge import active_knowledge
from datapilot.loop3_events import commands
from datapilot.loop4_hill_climbing import versions
from datapilot.loop4_hill_climbing.preflight import DataCheck
from datapilot.settings import PLATFORM

sys.path.insert(0, str(PLATFORM / "console"))

from datapilot_console import ops_reads  # noqa: E402

pytest_plugins = ["loops_fixtures"]
pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("clean_ops")]

KNOWLEDGE_TABLES = "ops.promotion_decisions, ops.experiments, ops.knowledge_versions"
TEMPLATE = "_template"


def execute(sql: str, *params: object) -> list[dict]:
    with db.connect(db.Role.OWNER) as conn:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall() if cursor.description else []
        conn.commit()
    return rows


def rows() -> list[tuple[str, str, str]]:
    found = execute("SELECT pack, version, status FROM ops.knowledge_versions")
    return sorted((r["pack"], r["version"], r["status"]) for r in found)  # code points, not locale


def install() -> list[str]:
    with db.connect(db.Role.APP) as conn:
        added = versions.install(conn)
        conn.commit()
    return added


def candidate(name: str, rule_id: str) -> KnowledgeVersion:
    rule = KnowledgeRule(
        id=rule_id, title=rule_id, rule_text=f"The {rule_id} rule.", applies_when="always"
    )
    return KnowledgeVersion(version=name, rules=[rule])


@pytest.fixture
def no_knowledge() -> Iterator[None]:
    execute(f"TRUNCATE {KNOWLEDGE_TABLES} CASCADE")
    yield
    execute(f"TRUNCATE {KNOWLEDGE_TABLES} CASCADE")


def test_each_pack_installs_and_activates_its_own_starting_version(
    no_knowledge, select_pack
) -> None:
    assert install() == ["v1", "v2-overbroad"]
    select_pack(TEMPLATE)
    assert install() == ["v1"], "the template's v1 is its own row, not the class pack's"
    assert rows() == [
        (TEMPLATE, "v1", "active"),
        ("datapilot_us", "v1", "active"),
        ("datapilot_us", "v2-overbroad", "retired"),
    ]


def test_the_agent_and_the_gate_use_the_selected_packs_versions(no_knowledge, select_pack) -> None:
    install()
    select_pack(TEMPLATE)
    install()
    with db.connect(db.Role.APP) as conn:
        assert versions.next_name(conn) == "v2", "the template ships only v1"
        versions.save_draft(conn, candidate("v2", "lantern-refunds"), created_by="test")
        versions.activate(conn, "v2")
        conn.commit()
    assert active_knowledge().version == "v2"
    assert [r.id for r in active_knowledge().rules] == ["lantern-refunds"]
    select_pack("datapilot_us")
    assert active_knowledge().version == "v1", "activating in one pack leaves the other alone"
    with db.connect(db.Role.APP) as conn:
        assert versions.status_of(conn, "v2") is None
        assert versions.latest_candidate(conn) is None
        assert versions.next_name(conn) == "v3", "the class pack ships v2-overbroad"


def test_a_reset_removes_only_the_selected_packs_candidates(no_knowledge, select_pack) -> None:
    install()
    with db.connect(db.Role.APP) as conn:
        versions.save_draft(conn, candidate("v3", "class-candidate"), created_by="test")
        conn.commit()
    select_pack(TEMPLATE)
    install()
    with db.connect(db.Role.APP) as conn:
        versions.save_draft(conn, candidate("v3", "template-candidate"), created_by="test")
        conn.commit()
    report = commands.reset("hill-climbing-loop")
    assert report.removed_versions == ["v3"] and report.active_version == "v1"
    assert ("datapilot_us", "v3", "draft") in rows()
    assert (TEMPLATE, "v3", "draft") not in rows()


def test_the_console_lists_only_the_selected_packs_versions(no_knowledge, select_pack) -> None:
    install()
    select_pack(TEMPLATE)
    install()
    with db.connect(db.Role.APP) as conn:
        assert [v["version"] for v in ops_reads.knowledge_versions(conn)] == ["v1"]
    select_pack("datapilot_us")
    with db.connect(db.Role.APP) as conn:
        assert {v["version"] for v in ops_reads.knowledge_versions(conn)} == {"v1", "v2-overbroad"}


def test_an_experiment_names_a_version_of_its_own_pack(no_knowledge) -> None:
    install()
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        execute(
            "INSERT INTO ops.experiments (experiment_id, pack, knowledge_version, split) "
            "VALUES (gen_random_uuid(), %s, 'v2-overbroad', 'all')",
            TEMPLATE,
        )


def test_each_pack_has_at_most_one_active_version(no_knowledge) -> None:
    with pytest.raises(psycopg.errors.UniqueViolation):
        execute(
            "INSERT INTO ops.knowledge_versions (pack, version, yaml, status, created_by) VALUES "
            "(%s, 'a', '', 'active', 'test'), (%s, 'b', '', 'active', 'test')",
            TEMPLATE,
            TEMPLATE,
        )


def test_the_data_check_reads_the_selected_packs_table_as_the_agent(select_pack) -> None:
    found = DataCheck.from_pack().check()
    assert found.ok and found.detail.endswith(" orders in warehouse.orders"), found.detail
    select_pack(TEMPLATE)  # the tests' database has no club schema loaded
    found = DataCheck.from_pack().check()
    assert not found.ok
    assert found.detail.startswith("club.payments is not readable as the agent's role")
