"""Seed warehouse and warehouse_alt from the generator, and check them against expected.yaml.

Order of work per database: generate the CSV files, create the tables (owner role), COPY the
files, add keys and indexes, apply the agent role's grants and settings (superuser), ANALYZE.
"""

from __future__ import annotations

import hashlib
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
import yaml
from psycopg import sql
from psycopg.conninfo import make_conninfo

from datapilot import db
from datapilot.config import pack_config
from datapilot.settings import PLATFORM, get_settings

from .generator import PROFILES, TABLES, HarborPineGenerator

SQL_DIR = PLATFORM / "ops" / "sql"
EXPECTED = Path(__file__).with_name("expected.yaml")
# Database name of each warehouse. Both have the same schema and the same agent role.
DATABASES = {"warehouse": "datapilot", "warehouse_alt": "warehouse_alt"}
PRIMARY_KEYS = {
    "categories": "category_id",
    "products": "product_id",
    "customers": "customer_id",
    "orders": "order_id",
    "order_items": "order_item_id",
}


@dataclass(frozen=True)
class SeedReport:
    warehouse: str
    counts: dict[str, int]
    content_hash: str
    seconds: float


def owner_url(warehouse: str) -> str:
    return make_conninfo(db.url_for(db.Role.OWNER), dbname=DATABASES[warehouse])


def superuser_url(warehouse: str) -> str:
    """The local Compose superuser (POSTGRES_PASSWORD in compose.yaml); role settings such as
    temp_file_limit can only be set by a superuser. DATABASE_URL_SUPERUSER, in .env or the
    environment, overrides it."""
    base = get_settings().database_url_superuser
    if not base:
        base = make_conninfo(db.url_for(db.Role.OWNER), user="postgres", password="postgres")
    return make_conninfo(base, dbname=DATABASES[warehouse])


def role_settings() -> dict[str, sql.Composable]:
    limits = pack_config()["limits"]
    return {
        "statement_timeout": sql.Literal(f"{limits['statement_timeout_ms']}ms"),
        "idle_timeout": sql.Literal(f"{limits['idle_in_transaction_timeout_ms']}ms"),
        "temp_file_limit": sql.Literal(f"{limits['temp_file_limit_kb']}kB"),
    }


def _sql(name: str) -> str:
    return (SQL_DIR / name).read_text(encoding="utf-8")


def load(warehouse: str, files: Path) -> None:
    with psycopg.connect(owner_url(warehouse)) as conn:
        conn.execute(_sql("warehouse_schema.sql"))
        with conn.cursor() as cur:
            for table in TABLES:
                copy = f"COPY warehouse.{table} FROM STDIN (FORMAT csv)"
                with (files / f"{table}.csv").open("rb") as handle, cur.copy(copy) as out:
                    while chunk := handle.read(1 << 20):
                        out.write(chunk)
        conn.execute(_sql("warehouse_indexes.sql"))
    with psycopg.connect(superuser_url(warehouse), autocommit=True) as conn:
        conn.execute(sql.SQL(_sql("roles.sql")).format(**role_settings()))
        conn.execute("ANALYZE")


def seed(warehouse: str) -> SeedReport:
    """Generate the CSV files in a temporary folder, load them, and remove them."""
    started = time.monotonic()
    profile = PROFILES[warehouse]
    with tempfile.TemporaryDirectory(prefix=f"datapilot-{warehouse}-") as folder:
        files = Path(folder)
        counts = HarborPineGenerator(profile).generate(files, seed=profile.seed)
        load(warehouse, files)
    return SeedReport(warehouse, counts, fingerprint(warehouse)[1], time.monotonic() - started)


def fingerprint(warehouse: str) -> tuple[dict[str, int], str]:
    """Row counts and one content hash over every warehouse table, read back from the database."""
    counts: dict[str, int] = {}
    digest = hashlib.sha256()
    with psycopg.connect(owner_url(warehouse)) as conn:
        conn.execute("SET TimeZone = 'UTC'")
        for table in TABLES:
            query = sql.SQL(
                "SELECT count(*), coalesce(md5(string_agg(t::text, E'\\n' ORDER BY t.{key})), '') "
                "FROM warehouse.{table} t"
            ).format(key=sql.Identifier(PRIMARY_KEYS[table]), table=sql.Identifier(table))
            row = conn.execute(query).fetchone()
            assert row is not None
            counts[table] = int(row[0])
            digest.update(f"{table}:{row[0]}:{row[1]}\n".encode())
    return counts, digest.hexdigest()


def expected() -> dict[str, Any]:
    return yaml.safe_load(EXPECTED.read_text(encoding="utf-8"))


def check(warehouse: str) -> list[str]:
    """Problems found comparing the database with expected.yaml; empty when it matches."""
    want = expected()[warehouse]
    counts, content_hash = fingerprint(warehouse)
    problems = [
        f"{warehouse}.{table}: {counts.get(table)} rows, expected {n}"
        for table, n in want["counts"].items()
        if counts.get(table) != n
    ]
    if content_hash != want["content_hash"]:
        problems.append(f"{warehouse}: content hash {content_hash[:12]} differs from expected.yaml")
    return problems
