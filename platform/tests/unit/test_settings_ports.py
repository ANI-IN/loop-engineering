"""The host commands follow the ports in .env (session 6 review, learner path): POSTGRES_PORT,
API_PORT, and CONSOLE_PORT move the containers through compose.yaml, and through the settings the
database addresses, the api address, and the console check too, unless an address is set itself.
DATABASE_URL_SUPERUSER is read from .env as well, not only from the shell."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from datapilot.loop4_hill_climbing import preflight
from datapilot.loop4_hill_climbing.pack_files import load_submodule
from datapilot.settings import Settings, get_settings

ADDRESSES = (
    "DATABASE_URL_OWNER",
    "DATABASE_URL_APP",
    "DATABASE_URL_AGENT",
    "DATABASE_URL_AGENT_ALT",
    "DATABASE_URL_SUPERUSER",
    "DATAPILOT_API_URL",
    "POSTGRES_PORT",
    "API_PORT",
    "CONSOLE_PORT",
)


@pytest.fixture
def no_addresses_in_the_shell(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The test suite points the shell at the tests' database; these tests read .env files alone.
    The settings cache is emptied on both sides: settings cached while the addresses are deleted
    hold the class stack's address, which on 25 October outlived this fixture into later tests."""
    get_settings.cache_clear()
    for name in ADDRESSES:
        monkeypatch.delenv(name, raising=False)
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


def _env(tmp_path: Path, text: str) -> Path:
    path = tmp_path / ".env"
    path.write_text(text, encoding="utf-8")
    return path


def test_the_ports_in_env_move_every_host_address(tmp_path, no_addresses_in_the_shell) -> None:
    env = _env(tmp_path, "POSTGRES_PORT=55999\nAPI_PORT=8999\nCONSOLE_PORT=8599\n")
    moved = Settings(_env_file=env)
    assert moved.database_url_owner == (
        "postgresql://datapilot_owner:datapilot_owner@localhost:55999/datapilot"
    )
    assert moved.database_url_app.endswith("@localhost:55999/datapilot")
    assert moved.database_url_agent == (
        "postgresql://datapilot_agent_ro:datapilot_agent_ro@localhost:55999/datapilot"
    )
    assert moved.database_url_agent_alt.endswith("@localhost:55999/warehouse_alt")
    assert moved.datapilot_api_url == "http://localhost:8999"
    assert preflight.settings_console_url(moved) == "http://localhost:8599/"


def test_without_ports_the_addresses_are_the_compose_defaults(
    tmp_path, no_addresses_in_the_shell
) -> None:
    plain = Settings(_env_file=_env(tmp_path, ""))
    assert plain.database_url_owner == (
        "postgresql://datapilot_owner:datapilot_owner@localhost:5432/datapilot"
    )
    assert plain.datapilot_api_url == "http://localhost:8000"
    assert preflight.settings_console_url(plain) == "http://localhost:8501/"


def test_an_address_set_on_its_own_wins_over_the_port(tmp_path, no_addresses_in_the_shell) -> None:
    own = "postgresql://me:secret@db.internal:6543/warehouse"
    env = _env(tmp_path, f"POSTGRES_PORT=55999\nDATABASE_URL_AGENT={own}\n")
    mixed = Settings(_env_file=env)
    assert mixed.database_url_agent == own
    assert mixed.database_url_owner.endswith("@localhost:55999/datapilot")


def test_the_env_example_leaves_the_addresses_to_the_ports() -> None:
    from datapilot.settings import REPO

    text = (REPO / ".env.example").read_text(encoding="utf-8")
    lines = {line.split("=", 1)[0] for line in text.splitlines() if "=" in line}
    assert {"POSTGRES_PORT", "API_PORT", "CONSOLE_PORT"} <= lines
    assert not {"DATABASE_URL_OWNER", "DATABASE_URL_APP", "DATAPILOT_API_URL"} & lines


def test_the_seeder_reads_the_superuser_address_from_env(
    tmp_path, no_addresses_in_the_shell, monkeypatch
) -> None:
    seeding = load_submodule("data_generator", "seed")
    own = "postgresql://admin:admin@db.internal:6543/postgres"
    from_file = Settings(_env_file=_env(tmp_path, f"DATABASE_URL_SUPERUSER={own}\n"))
    monkeypatch.setattr(seeding, "get_settings", lambda: from_file)
    found = seeding.superuser_url("warehouse")
    assert "user=admin" in found and "host=db.internal" in found and "dbname=datapilot" in found
