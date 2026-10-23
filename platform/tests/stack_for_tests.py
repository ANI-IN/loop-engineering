"""The tests' own database: a separate Compose project (datapilot-tests) whose Postgres listens on
its own port, so integration tests and the live stack (project datapilot, ports 5432, 8000, 8501)
can never read, empty, or claim each other's rows and jobs.

The integration tests need only Postgres: their api runs in process (TestClient) and their worker
runs in process on stub models. `make test-integration` starts this Postgres, migrates and seeds
it once, then runs the suite; the conftest points every database URL here before any test runs.

platform/scripts/prepare_tests_database.py runs prepare() for make test-stack.
"""

from __future__ import annotations

import os
from collections.abc import Callable

PROJECT = "datapilot-tests"
PORT_VARIABLE = "DATAPILOT_TEST_POSTGRES_PORT"
DEFAULT_PORT = "55432"
LIVE_PORT = "5432"

_ROLES = {
    "DATABASE_URL_OWNER": ("datapilot_owner", "datapilot"),
    "DATABASE_URL_APP": ("datapilot_app", "datapilot"),
    "DATABASE_URL_AGENT": ("datapilot_agent_ro", "datapilot"),
    "DATABASE_URL_AGENT_ALT": ("datapilot_agent_ro", "warehouse_alt"),
}


def port() -> str:
    found = os.environ.get(PORT_VARIABLE, DEFAULT_PORT)
    if found == LIVE_PORT:
        raise RuntimeError(f"{PORT_VARIABLE} must not be the live stack's port {LIVE_PORT}")
    return found


def database_urls(test_port: str | None = None) -> dict[str, str]:
    chosen = test_port or port()
    return {
        name: f"postgresql://{role}:{role}@localhost:{chosen}/{database}"
        for name, (role, database) in _ROLES.items()
    }


def use_test_database() -> dict[str, str]:
    """Point this process at the tests' database (environment beats .env in the settings)."""
    urls = database_urls()
    os.environ.update(urls)
    # the seeder sets temp_file_limit as the superuser of the same server
    os.environ["DATABASE_URL_SUPERUSER"] = (
        f"postgresql://postgres:postgres@localhost:{port()}/postgres"
    )
    # No live api, worker, or console is ever reached from a test.
    os.environ["DATAPILOT_API_URL"] = "http://localhost:1"
    from datapilot.settings import DEFAULT_PACK, get_settings

    # The tests read the class pack whatever .env selects; a test that needs another pack says so.
    os.environ["DATAPILOT_PACK"] = DEFAULT_PACK

    get_settings.cache_clear()
    return urls


def needs_seed(check: Callable[[str], list[str]], warehouse: str) -> bool:
    """True when the warehouse must be seeded: it differs from expected.yaml, or its tables do not
    exist yet (a new or partly prepared tests' database). A seeded match is reused."""
    import psycopg

    try:
        return bool(check(warehouse))
    except (psycopg.errors.UndefinedTable, psycopg.errors.InvalidSchemaName):
        return True


def prepare() -> None:
    """Migrate, then seed each warehouse that is missing or does not match expected.yaml."""
    use_test_database()
    from datapilot import db
    from datapilot.loop4_hill_climbing.pack_files import load_submodule

    db.wait_until_ready()
    applied = db.migrate()
    print(f"tests' database on port {port()}: {len(applied)} migrations applied")
    seeding = load_submodule("data_generator", "seed")
    for warehouse in seeding.DATABASES:
        if needs_seed(seeding.check, warehouse):
            report = seeding.seed(warehouse)
            print(f"seeded {warehouse} in {report.seconds:.1f} s")
        else:
            print(f"{warehouse} already matches expected.yaml")
    problems = [p for warehouse in seeding.DATABASES for p in seeding.check(warehouse)]
    if problems:  # the seeded warehouses must match expected.yaml, or the tests do not start
        raise SystemExit("tests' database does not match expected.yaml: " + "; ".join(problems))


if __name__ == "__main__":
    prepare()
