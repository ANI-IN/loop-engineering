"""Tests reach only their own database, never the live stack's (zero tokens, no database)."""

from __future__ import annotations

import pytest
import stack_for_tests

from datapilot import db


def test_every_role_points_at_the_tests_database_port() -> None:
    port = stack_for_tests.port()
    assert port != stack_for_tests.LIVE_PORT
    for role in db.Role:
        assert f"@localhost:{port}/" in db.url_for(role), role


def test_the_live_port_is_refused(monkeypatch) -> None:
    monkeypatch.setenv(stack_for_tests.PORT_VARIABLE, stack_for_tests.LIVE_PORT)
    with pytest.raises(RuntimeError, match="live stack"):
        stack_for_tests.database_urls()


def test_an_empty_tests_database_is_seeded() -> None:
    import psycopg

    def missing(warehouse: str) -> list[str]:
        raise psycopg.errors.UndefinedTable('relation "warehouse.categories" does not exist')

    assert stack_for_tests.needs_seed(missing, "warehouse")


def test_a_seeded_match_is_reused_and_a_mismatch_is_seeded_again() -> None:
    assert not stack_for_tests.needs_seed(lambda warehouse: [], "warehouse")
    assert stack_for_tests.needs_seed(lambda warehouse: ["orders: 1 rows, expected 2"], "warehouse")


def test_other_database_errors_are_not_hidden() -> None:
    import psycopg

    def down(warehouse: str) -> list[str]:
        raise psycopg.OperationalError("connection refused")

    with pytest.raises(psycopg.OperationalError):
        stack_for_tests.needs_seed(down, "warehouse")


def test_no_test_reaches_the_live_api() -> None:
    from datapilot.settings import get_settings

    assert get_settings().datapilot_api_url == "http://localhost:1"
