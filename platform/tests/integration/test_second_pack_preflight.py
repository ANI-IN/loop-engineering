"""A second pack passes preflight through configuration alone: the template pack (Lantern Coffee
Club) loaded into two scratch databases on the tests' own Postgres, DATAPILOT_PACK and the agent's
database addresses pointed at them, then preflight's service, data, and canary stages.

The canary's model is a stub (zero tokens) that answers each easy question with its gold query and
each trap question with its naive one, which is what preflight expects of the starting knowledge.
Every query the executor runs, and every file opened, is recorded: nothing of Harbor & Pine (its
pack folder, its warehouse schema, its tables) may be read.
"""

from __future__ import annotations

import builtins
import io
import os
import re
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from datapilot import config, db
from datapilot.contracts import AnswerEnvelope, AnswerStatus
from datapilot.contracts.live import SessionPurpose
from datapilot.loop2_verification.executor import Executor
from datapilot.loop3_events import sessions
from datapilot.loop4_hill_climbing import preflight as checks
from datapilot.loop4_hill_climbing import versions
from datapilot.loop4_hill_climbing.evaluator import ExecutionEvaluator
from datapilot.loop4_hill_climbing.pack_files import load_benchmark
from datapilot.settings import PLATFORM, get_settings

pytest_plugins = ["loops_fixtures"]
pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("clean_ops")]

TEMPLATE = "_template"
CLUB_SQL = PLATFORM / "packs" / TEMPLATE / "data" / "club.sql"
KNOWLEDGE_TABLES = "ops.promotion_decisions, ops.experiments, ops.knowledge_versions"
# What Harbor & Pine is made of outside the code: its pack folder and its warehouse schema files.
CLASS_FILES = (PLATFORM / "packs" / "datapilot_us", PLATFORM / "ops" / "sql")
CLASS_TABLES = re.compile(r"\bwarehouse\.|\b(orders|order_items|customers|products|categories)\b")


def superuser(dbname: str = "postgres") -> psycopg.Connection[Any]:
    """The tests' Postgres superuser (stack_for_tests.py), on one database."""
    url = make_conninfo(os.environ["DATABASE_URL_SUPERUSER"], dbname=dbname)
    return psycopg.connect(url, autocommit=True)


def load_club(dbname: str, variant: int) -> None:
    """club.sql is written for psql (-v variant=N); the same text runs here with the variable
    filled in, so the rows are exactly the ones a learner loads."""
    text = CLUB_SQL.read_text(encoding="utf-8")
    text = "\n".join(line for line in text.splitlines() if not line.startswith("\\"))
    with superuser(dbname) as conn:
        conn.execute(text.replace(":variant", str(variant)))


@pytest.fixture
def club_databases(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, str]]:
    """Two scratch databases, one per template variant, dropped afterwards."""
    suffix = uuid.uuid4().hex[:8]
    names = {"warehouse": f"club_first_{suffix}", "warehouse_alt": f"club_second_{suffix}"}
    with superuser() as conn:
        for name in names.values():
            conn.execute(
                sql.SQL("CREATE DATABASE {} OWNER datapilot_owner").format(sql.Identifier(name))
            )
    try:
        for variant, name in enumerate(names.values(), start=1):
            load_club(name, variant)
        agent = get_settings().database_url_agent
        monkeypatch.setenv("DATABASE_URL_AGENT", make_conninfo(agent, dbname=names["warehouse"]))
        monkeypatch.setenv(
            "DATABASE_URL_AGENT_ALT", make_conninfo(agent, dbname=names["warehouse_alt"])
        )
        get_settings.cache_clear()
        yield names
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
        with superuser() as conn:
            for name in names.values():
                conn.execute(
                    sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name))
                )


@pytest.fixture
def no_knowledge() -> Iterator[None]:
    with db.connect(db.Role.OWNER) as conn:
        conn.execute(f"TRUNCATE {KNOWLEDGE_TABLES} CASCADE")
        conn.commit()
    yield
    with db.connect(db.Role.OWNER) as conn:
        conn.execute(f"TRUNCATE {KNOWLEDGE_TABLES} CASCADE")
        conn.commit()


@pytest.fixture
def executed(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """(database, SQL) of every query the executor runs."""
    found: list[tuple[str, str]] = []
    run = Executor.run

    def recording(self: Executor, text: str) -> Any:
        found.append((conninfo_to_dict(self.url)["dbname"], text))
        return run(self, text)

    monkeypatch.setattr(Executor, "run", recording)
    return found


@pytest.fixture
def opened(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[Path]]:
    """Every file opened by path while the test runs, with the pack configuration cache emptied
    first so the class pack's pack.yaml would have to be opened to be read."""
    found: list[Path] = []
    original = builtins.open

    def recording(file: Any, *args: Any, **kwargs: Any) -> Any:
        if isinstance(file, str | Path):
            found.append(Path(file).resolve())
        return original(file, *args, **kwargs)

    config._load.cache_clear()
    monkeypatch.setattr(builtins, "open", recording)
    monkeypatch.setattr(io, "open", recording)
    yield found
    config._load.cache_clear()


def stub_canary_model() -> tuple[Any, list[str]]:
    """Gold SQL for an easy question, naive SQL for a trap question, as the starting knowledge is
    calibrated to behave. Returns the target and the questions it was asked."""
    by_question = {item.question: item for item in load_benchmark()}
    asked: list[str] = []

    def target(question: str, knowledge_version: str) -> AnswerEnvelope:
        asked.append(question)
        item = by_question[question]
        chosen = item.naive_sql if item.traps else item.gold_sql
        return AnswerEnvelope(status=AnswerStatus.ANSWERED, final_sql=chosen, answer_text="stub")

    return target, asked


def every_page_answers() -> httpx.Client:
    """The api and console of a stack are not part of this test; they answer 200."""
    return httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200)))


def install() -> list[str]:
    with db.connect(db.Role.APP) as conn:
        added = versions.install(conn)
        conn.commit()
    return added


def test_the_template_pack_passes_preflight_on_its_own_databases(
    club_databases, no_knowledge, select_pack, executed, opened
) -> None:
    select_pack(TEMPLATE)
    settings = get_settings()
    target, asked = stub_canary_model()
    ids = checks.canary_ids()

    def canary() -> list[checks.CanaryRun]:
        evaluator = ExecutionEvaluator.live()
        return checks.run_canary(target, evaluator, load_benchmark(), ids)

    try:
        report = checks.preflight(
            SessionPurpose.DEVELOPMENT,
            settings,
            canary=canary,
            start_session=sessions.start_session,
            services=lambda: checks.service_checks(settings, client=every_page_answers()),
            key=lambda: checks.Check("openai key", True, "stub-model"),
            install=install,
        )
    finally:  # the session this test started never stays open for the next test
        with db.connect(db.Role.APP) as conn:
            conn.execute("UPDATE ops.live_sessions SET ended_at = now() WHERE ended_at IS NULL")
            conn.commit()

    assert report.stopped is None, [c.line() for c in report.checks] + [
        f"{r.item_id}: {r.reason}" for r in report.canary
    ]
    assert report.session is not None
    by_name = {c.name: c for c in report.checks}
    assert by_name["pack"].detail == TEMPLATE
    assert re.fullmatch(r"[\d,]+ payments in club\.payments", by_name["data"].detail)

    # The data check counted the template's table, on the template's database, as the agent.
    data_query = checks.DataCheck.from_pack().query()
    assert data_query == 'SELECT count(*) AS n FROM "club"."payments"'
    assert (club_databases["warehouse"], data_query) in executed

    # The canary asked the template's questions, and each behaved as calibrated.
    by_id = {item.id: item for item in load_benchmark()}
    assert ids == {
        "easy": ["plan-count", "members-north", "members-joined-2024"],
        "traps": ["net-revenue-march-2025", "charges-june-2025"],
    }
    assert sorted(asked) == sorted(by_id[i].question for i in ids["easy"] + ids["traps"])
    assert {r.item_id for r in report.canary} == set(ids["easy"] + ids["traps"])
    assert all(r.as_expected for r in report.canary)

    # The knowledge versions belong to the template alone.
    with db.connect(db.Role.OWNER) as conn:
        found = conn.execute("SELECT pack, version, status FROM ops.knowledge_versions").fetchall()
    assert [(r["pack"], r["version"], r["status"]) for r in found] == [(TEMPLATE, "v1", "active")]

    # Nothing of Harbor & Pine was read: no query outside the scratch databases or naming a class
    # table, and no file of the class pack or the warehouse schema opened.
    assert {database for database, _ in executed} == set(club_databases.values())
    assert [text for _, text in executed if CLASS_TABLES.search(text)] == []
    class_files = [p for p in opened if any(p.is_relative_to(f) for f in CLASS_FILES)]
    assert class_files == []
    assert (PLATFORM / "packs" / TEMPLATE / "pack.yaml").resolve() in opened, "the spy works"


def test_the_scratch_databases_hold_no_harbor_and_pine_schema(club_databases) -> None:
    for name in club_databases.values():
        with superuser(name) as conn:
            schemas = {r[0] for r in conn.execute("SELECT nspname FROM pg_namespace")}
        assert "club" in schemas and "warehouse" not in schemas
