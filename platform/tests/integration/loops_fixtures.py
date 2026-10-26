"""Integration fixtures for the agent, verification, and event loops (Compose Postgres, no tokens).

The fixture warehouse lives in its own schema (loops_fixture) so a seeded warehouse is never
touched; ops tables are emptied before each event-loop test.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator
from typing import Any

import loops_paths  # noqa: F401  (before loops_support)
import pytest
from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402
from loops_support import (  # noqa: E402
    FIXTURE_DDL,
    FIXTURE_SCHEMA,
    ScriptedChatModel,
    fixture_config,
)

from datapilot import db  # noqa: E402
from datapilot.config import pack_config  # noqa: E402
from datapilot.contracts import KnowledgeVersion  # noqa: E402
from datapilot.loop1_agent.analyst import AgentLimits  # noqa: E402
from datapilot.loop1_agent.catalog import CatalogSnapshot, load_snapshot  # noqa: E402
from datapilot.loop2_verification.executor import Executor  # noqa: E402
from datapilot.loop2_verification.loop import LoopServices  # noqa: E402

OPS_TABLES = (
    "ops.posts, ops.approvals, ops.run_events, ops.runs, ops.event_duplicates, ops.jobs, "
    "ops.events, ops.budgets, ops.autonomy_policy, ops.live_sessions, ops.improvement_requests"
)


@pytest.fixture(scope="session")
def warehouse() -> CatalogSnapshot:
    db.wait_until_ready()
    db.migrate()
    with db.connect(db.Role.OWNER) as conn:
        conn.execute(FIXTURE_DDL)
        conn.commit()
    return load_snapshot(db.url_for(db.Role.AGENT), FIXTURE_SCHEMA)


@pytest.fixture
def executor(warehouse: CatalogSnapshot) -> Executor:
    config = fixture_config()
    return Executor(db.url_for(db.Role.AGENT), FIXTURE_SCHEMA, config.statement_timeout_ms)


Scripts = dict[str, Callable[..., Any]]


def make_services(
    snapshot: CatalogSnapshot,
    executor: Executor,
    scripts: Scripts,
    *,
    checkpointer: Any = None,
    knowledge: KnowledgeVersion | None = None,
    scout: bool = False,
    reviewer: bool = False,
    tokens_per_run: int | None = None,
    feedback: Any = None,
) -> LoopServices:
    limits = AgentLimits.from_pack(pack_config())
    limits = AgentLimits(
        row_cap=limits.row_cap,
        model_call_limit=limits.model_call_limit,
        tool_call_limit=limits.tool_call_limit,
        tokens_per_run=tokens_per_run or limits.tokens_per_run,
        scout_enabled=scout,
        reviewer_enabled=reviewer,
    )
    models = {name: ScriptedChatModel(script=script) for name, script in scripts.items()}
    return LoopServices(
        models=lambda component: models[component],
        executor=executor,
        snapshot=snapshot,
        config=fixture_config(),
        limits=limits,
        knowledge=lambda: knowledge or KnowledgeVersion(version="v-test"),
        checkpointer=checkpointer if checkpointer is not None else InMemorySaver(),
        model_name="scripted",
        feedback=feedback,
    )


@pytest.fixture
def services_for(
    warehouse: CatalogSnapshot, executor: Executor
) -> Iterator[Callable[..., LoopServices]]:
    yield lambda scripts, **kw: make_services(warehouse, executor, scripts, **kw)


@pytest.fixture
def clean_ops() -> Iterator[None]:
    """Empty ops, then open a development session: the api refuses a run asked for over HTTP
    while no live session is open (events.require_session), as make preflight opens one live."""
    with db.connect(db.Role.OWNER) as conn:
        conn.execute(f"TRUNCATE {OPS_TABLES} RESTART IDENTITY CASCADE")
        conn.execute(
            "UPDATE ops.control SET kill_switch = 'released', autonomy_level = 'report_only', "
            "reason = NULL, worker_restart_requested_at = NULL"
        )
        conn.execute(
            "INSERT INTO ops.live_sessions (session_id, purpose, started_by, timezone) "
            "VALUES (%s, 'development', 'integration tests', 'UTC')",
            (uuid.uuid4(),),
        )
        conn.commit()
    yield


@pytest.fixture
def settings_refresh() -> Iterator[None]:
    """Clear the settings cache before and after a test that changes the environment."""
    from datapilot.settings import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
