"""Assignment 1's requirement 6 on the tests' own Postgres, zero tokens: the lookup reads only as
the read-only agent role. The two lookups that passed it in the session 6 review, round 2, now
fail it: one kept an owner connection it opened during the earlier requirements, one built the
owner's Compose address from POSTGRES_PORT. A lookup through warehouse.url still passes."""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import psycopg
import pytest

from datapilot import db, tests_database_guard
from datapilot.assignments import assignment
from datapilot.assignments.runner import load_check
from datapilot.settings import COMPOSE_ROLES, get_settings

pytestmark = [pytest.mark.integration, pytest.mark.security]

agent_loop = load_check(assignment("agent-loop").check_file)
BACKPACKS = "SELECT name FROM warehouse.products WHERE name ILIKE %s ORDER BY name LIMIT 5"


@pytest.fixture
def closed_port_allowed() -> Iterator[None]:
    """The check's closed address is refused under pytest as any address but the tests' is."""
    start = len(tests_database_guard.refused)
    yield
    closed = f":{agent_loop.CLOSED_PORT}/"  # the check's closed port, on any host
    kept = [a for a in tests_database_guard.refused[start:] if closed not in a]
    tests_database_guard.refused[start:] = kept


def _found(conn: psycopg.Connection[Any], wording: str) -> SimpleNamespace:
    names = [row[0] for row in conn.execute(BACKPACKS, (f"%{wording}%",)).fetchall()]
    return SimpleNamespace(candidates=names)


def test_an_owner_connection_kept_from_the_earlier_requirements_fails(monkeypatch) -> None:
    kept: dict[str, psycopg.Connection[Any]] = {}

    def lookup(warehouse: Any, kind: str, wording: str) -> SimpleNamespace:
        if "conn" not in kept:  # opened on the first call, during requirements 1 to 5
            kept["conn"] = psycopg.connect(db.url_for(db.Role.OWNER))
        return _found(kept["conn"], wording)

    monkeypatch.setattr(agent_loop.extension, "lookup_values", lookup)
    try:
        lookup(None, "product", "trail runner")  # an earlier requirement's call
        problem = agent_loop._read_only_role()
    finally:
        kept["conn"].close()
    assert problem is not None and "it read as datapilot_owner" in problem


@pytest.mark.usefixtures("closed_port_allowed")
def test_an_owner_address_built_from_the_port_fails(monkeypatch) -> None:
    # As on the check's own stack, POSTGRES_PORT names the stack's Postgres (here the tests'),
    # while the class stack stays on its own port (the guard reads POSTGRES_PORT as the class's).
    monkeypatch.setattr(tests_database_guard, "class_port", lambda: tests_database_guard.CLASS_PORT)
    monkeypatch.setenv("POSTGRES_PORT", tests_database_guard.tests_port())
    get_settings.cache_clear()
    role, database = COMPOSE_ROLES["database_url_owner"]

    def lookup(warehouse: Any, kind: str, wording: str) -> SimpleNamespace:
        port = get_settings().postgres_port
        with psycopg.connect(f"postgresql://{role}:{role}@localhost:{port}/{database}") as conn:
            return _found(conn, wording)

    monkeypatch.setattr(agent_loop.extension, "lookup_values", lookup)
    assert lookup(None, "product", "backpack").candidates  # it reads, outside the check
    problem = agent_loop._read_only_role()
    assert problem is not None and "could not connect" in problem


def test_a_lookup_through_the_agent_roles_address_passes(monkeypatch) -> None:
    def lookup(warehouse: Any, kind: str, wording: str) -> SimpleNamespace:
        with psycopg.connect(warehouse.url) as conn:
            return _found(conn, wording)

    monkeypatch.setattr(agent_loop.extension, "lookup_values", lookup)
    assert agent_loop._read_only_role() is None
