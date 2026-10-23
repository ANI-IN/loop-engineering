"""Every path that runs agent SQL goes through loop2_verification.executor.Executor, whose _begin
opens SET TRANSACTION READ ONLY on the agent role (zero tokens, no database).

A new database connection, or a new use of the agent role, anywhere in the product fails here
until it is listed below with the reason it cannot run agent SQL outside the executor."""

from __future__ import annotations

import ast

from datapilot.settings import PLATFORM, REPO

FOLDERS = (PLATFORM / "src" / "datapilot", PLATFORM / "console", PLATFORM / "packs")
CONNECTORS = {"connect", "ConnectionPool", "AsyncConnectionPool"}

# Each direct connection, by module, with why it never runs agent SQL outside the executor.
CONNECTIONS = {
    "platform/src/datapilot/db.py": "the connection helper; the agent role is reached only below",
    "platform/src/datapilot/loop2_verification/executor.py": "the executor itself (_begin)",
    "platform/src/datapilot/loop1_agent/catalog.py": "catalog system SQL and sample rows only",
    "platform/src/datapilot/loop1_agent/knowledge.py": "the app role reading ops",
    "platform/src/datapilot/loop2_verification/defense.py": (
        "the malicious SQL demo's fixed statement with read-only switched off, to show the grants"
    ),
    "platform/src/datapilot/loop3_events/approvals.py": "the app role's checkpointer pool",
    "platform/src/datapilot/loop3_events/worker.py": "the app role's claim connection",
    "platform/console/datapilot_console/frame.py": "the console's app-role pool",
    "platform/packs/datapilot_us/data_generator/seed.py": "seeding as the owner",
}
# Each use of the agent role, by module: every one builds an Executor.
AGENT_ROLE = {
    "platform/src/datapilot/db.py",
    "platform/src/datapilot/loop3_events/api/app.py",
    "platform/src/datapilot/loop3_events/worker.py",
    "platform/src/datapilot/loop4_hill_climbing/sql_runner.py",
    "platform/src/datapilot/loop4_hill_climbing/targets.py",
    "platform/src/datapilot/loop4_hill_climbing/live_smoke.py",
}


def _modules():
    for folder in FOLDERS:
        for path in folder.rglob("*.py"):
            yield path.relative_to(REPO).as_posix(), ast.parse(path.read_text(encoding="utf-8"))


def _name(node: ast.expr) -> str:
    return node.attr if isinstance(node, ast.Attribute) else getattr(node, "id", "")


def test_every_direct_connection_is_listed_with_its_reason() -> None:
    found = {
        rel
        for rel, tree in _modules()
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and _name(node.func) in CONNECTORS
        and (_name(node.func) != "connect" or "psycopg" in ast.unparse(node.func))
    }
    assert found == set(CONNECTIONS)


def test_the_agent_role_is_used_only_to_build_executors() -> None:
    found = {
        rel
        for rel, tree in _modules()
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and node.attr in {"AGENT", "AGENT_ALT"}
        and _name(node.value) == "Role"
    }
    assert found == AGENT_ROLE


def test_the_modules_that_use_the_agent_role_build_an_executor_with_it() -> None:
    for rel, tree in _modules():
        if rel not in AGENT_ROLE or rel.endswith("db.py"):
            continue
        calls = {_name(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
        assert "Executor" in calls, rel


def test_the_evaluator_runs_gold_and_agent_sql_through_executors() -> None:
    from datapilot.loop2_verification.executor import Executor
    from datapilot.loop4_hill_climbing.evaluator import ExecutionEvaluator

    runner = ExecutionEvaluator.live().runner
    executors = runner.runner.executors  # type: ignore[attr-defined]
    assert set(executors) == {"warehouse", "warehouse_alt"}
    assert all(isinstance(e, Executor) for e in executors.values())
    assert all("datapilot_agent_ro" in e.url for e in executors.values())
