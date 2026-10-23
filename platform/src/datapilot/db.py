"""Database connections per role, and the ops schema migrations."""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from enum import StrEnum
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from datapilot.settings import PLATFORM, get_settings

MIGRATIONS = PLATFORM / "ops" / "sql" / "ops"


class Role(StrEnum):
    OWNER = "owner"  # migrations and seeding; never handed to the agent
    APP = "app"  # ops tables, the checkpointer schema
    AGENT = "agent"  # read-only, warehouse schema only
    AGENT_ALT = "agent_alt"  # the same role on warehouse_alt


def url_for(role: Role) -> str:
    s = get_settings()
    return {
        Role.OWNER: s.database_url_owner,
        Role.APP: s.database_url_app,
        Role.AGENT: s.database_url_agent,
        Role.AGENT_ALT: s.database_url_agent_alt,
    }[role]


@contextmanager
def connect(role: Role, *, autocommit: bool = False) -> Iterator[psycopg.Connection]:
    # Sessions run in UTC so every timestamp the api sends is UTC; the browser localizes it.
    with psycopg.connect(
        url_for(role), autocommit=autocommit, row_factory=dict_row, options="-c TimeZone=UTC"
    ) as conn:
        yield conn


def wait_until_ready(role: Role = Role.OWNER, *, timeout_s: float = 60.0) -> None:
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            with connect(role) as conn:
                conn.execute("SELECT 1")
            return
        except psycopg.OperationalError:
            if time.monotonic() > deadline:
                raise
            time.sleep(1.0)


def migration_files(folder: Path = MIGRATIONS) -> list[Path]:
    return sorted(folder.glob("[0-9][0-9][0-9]_*.sql"))


def migrate() -> list[str]:
    """Apply every ops migration not yet recorded in ops.schema_migrations, in order, each in its
    own transaction. Returns the names applied."""
    applied: list[str] = []
    with connect(Role.OWNER) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS ops.schema_migrations "
            "(name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
        )
        conn.commit()
        done = {r["name"] for r in conn.execute("SELECT name FROM ops.schema_migrations")}
        for path in migration_files():
            if path.name in done:
                continue
            with conn.transaction():
                conn.execute(path.read_text(encoding="utf-8"))
                conn.execute("INSERT INTO ops.schema_migrations (name) VALUES (%s)", (path.name,))
            applied.append(path.name)
    return applied
