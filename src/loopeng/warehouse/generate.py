"""Deterministic warehouse generator.

Same seed, same data. The contract enforced by test is content-identity — a
checksum over every table's sorted contents. Byte-identity of the DuckDB file is
tested for separately and reported rather than claimed, because DuckDB may write
version metadata into the header.

The data is deliberately rule-heavy. Each of the seven rules in semantic_model.yaml
has rows on both sides of it, because a rule the data never triggers cannot tell
a spec-withheld run apart from a spec-given one: both produce the same number, and
the sweep reports no gap where the gap is what the workshop is for.

The shape of the warehouse lives in schema.py. This module only fills it.
"""

import csv
import hashlib
import random
import tempfile
from collections.abc import Sequence
from datetime import datetime, timedelta
from pathlib import Path

import duckdb

from loopeng.warehouse.schema import CATEGORIES, CURRENCIES, REGIONS, SCHEMA_DDL, TABLES

_N_PRODUCTS = 200
_N_CUSTOMERS = 500
_N_ORDERS = 5000

_SEASON_START = datetime(2025, 1, 1)
_SEASON_DAYS = 365

# Proportions chosen so that ignoring any single rule visibly moves an aggregate.
# Too rare and the naive answer matches the gold one by luck; too common and the
# rule stops looking like a business subtlety and starts looking like the main
# axis of the data.
_P_INTERNAL = 0.06
_P_CUSTOMER_DELETED = 0.08
_P_ORDER_DELETED = 0.05
_P_REFUNDED = 0.09


def _bulk_insert(
    con: duckdb.DuckDBPyConnection, table: str, rows: Sequence[tuple], staging: Path
) -> None:
    """Load rows via a staged CSV rather than executemany.

    executemany prepares and executes once per row: measured at roughly 0.4ms a
    row, which puts a single 15k-row warehouse at ~9s and the test suite at over
    two minutes. Staging to CSV and letting DuckDB's parallel reader do the load
    is ~85x faster and leaves the offline suite fast enough to run on every edit,
    which is the property that makes it get run at all.

    Types round-trip through CSV because the schema has no floats: integers,
    strings, booleans and whole-second timestamps only. NULLSTR '' is what carries
    the soft-delete NULLs, and the empty-string-versus-NULL ambiguity it would
    normally introduce cannot arise here — no VARCHAR column in this warehouse is
    ever legitimately empty.
    """
    if not rows:
        return
    csv_path = staging / f"{table}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerows(
            ["" if value is None else value for value in row] for row in rows
        )
    con.execute(
        f"COPY {table} FROM '{csv_path.as_posix()}' (FORMAT CSV, HEADER false, NULLSTR '')"
    )


def generate(path: Path, seed: int) -> dict[str, int]:
    """Write a fresh warehouse at `path`. Returns row counts per table."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Replace rather than append. ensure_warehouse may call this on a path that
    # already holds a warehouse from another seed, and appending would double
    # every row while still reporting a plausible-looking count.
    if path.exists():
        path.unlink()

    rng = random.Random(seed)
    con = duckdb.connect(str(path))

    # DuckDB's execute() prepares a single statement, so the DDL is applied one
    # CREATE at a time. schema.py orders them so this works top to bottom.
    for statement in (s.strip() for s in SCHEMA_DDL.split(";")):
        if statement:
            con.execute(statement)

    products = [
        (pid, rng.choice(CATEGORIES), rng.randrange(500, 40_000))
        for pid in range(1, _N_PRODUCTS + 1)
    ]

    customers = []
    for cid in range(1, _N_CUSTOMERS + 1):
        is_internal = rng.random() < _P_INTERNAL
        deleted_at = (
            _SEASON_START + timedelta(days=rng.randrange(_SEASON_DAYS))
            if rng.random() < _P_CUSTOMER_DELETED
            else None
        )
        customers.append((cid, rng.choice(REGIONS), is_internal, deleted_at))

    orders, order_items, refunds = [], [], []
    item_id = 0
    refund_id = 0
    for oid in range(1, _N_ORDERS + 1):
        customer_id = rng.randrange(1, _N_CUSTOMERS + 1)
        status = rng.choices(("completed", "cancelled", "pending"), weights=(80, 12, 8))[0]
        currency = rng.choices(CURRENCIES, weights=(60, 25, 15))[0]
        placed_at = _SEASON_START + timedelta(
            days=rng.randrange(_SEASON_DAYS), hours=rng.randrange(24)
        )
        deleted_at = (
            placed_at + timedelta(days=rng.randrange(1, 30))
            if rng.random() < _P_ORDER_DELETED
            else None
        )

        # Lines first, so the order total is the sum of its lines and the fan-out
        # trap is arithmetically real rather than merely structural.
        n_lines = rng.choices((1, 2, 3, 4), weights=(45, 30, 17, 8))[0]
        total_minor = 0
        for _ in range(n_lines):
            item_id += 1
            product_id = rng.randrange(1, _N_PRODUCTS + 1)
            qty = rng.randrange(1, 5)
            unit_price_minor = products[product_id - 1][2]
            if currency == "JPY":
                # JPY has no minor unit, so the same list price is ~100x smaller
                # in magnitude. Ignoring this is the minor-units trap.
                unit_price_minor = max(1, unit_price_minor // 100)
            order_items.append((item_id, oid, product_id, qty, unit_price_minor))
            total_minor += qty * unit_price_minor

        orders.append((oid, customer_id, status, currency, total_minor, placed_at, deleted_at))

        if status == "completed" and rng.random() < _P_REFUNDED:
            for _ in range(rng.choices((1, 2), weights=(88, 12))[0]):
                refund_id += 1
                refunds.append(
                    (
                        refund_id,
                        oid,
                        max(1, int(total_minor * rng.uniform(0.1, 1.0))),
                        placed_at + timedelta(days=rng.randrange(1, 60)),
                    )
                )

    built = {
        "products": products,
        "customers": customers,
        "orders": orders,
        "order_items": order_items,
        "refunds": refunds,
    }
    with tempfile.TemporaryDirectory(prefix="loopeng-warehouse-") as staging_dir:
        staging = Path(staging_dir)
        for table, rows in built.items():
            _bulk_insert(con, table, rows, staging)

    counts = {
        table: con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLES
    }
    con.close()
    return counts


def content_checksum(path: Path) -> str:
    """SHA-256 over every table's rows, sorted. Independent of file layout.

    This is the determinism contract the tests enforce. Checksumming the file
    bytes instead would couple the contract to DuckDB's storage format, and a
    version bump would then read as a data change.
    """
    con = duckdb.connect(str(path), read_only=True)
    digest = hashlib.sha256()
    for table in TABLES:
        rows = con.execute(f"SELECT * FROM {table} ORDER BY ALL").fetchall()
        digest.update(table.encode())
        for row in rows:
            digest.update(repr(row).encode())
    con.close()
    return digest.hexdigest()
