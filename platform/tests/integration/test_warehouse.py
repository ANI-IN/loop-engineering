"""The seeded warehouses (make seed first): exact contents, the agent role, and the planted data
conditions at full size. Zero model calls."""

from __future__ import annotations

import psycopg
import pytest

from datapilot import db
from datapilot.loop4_hill_climbing.pack_files import load_submodule

pytestmark = pytest.mark.integration
seeding = load_submodule("data_generator", "seed")
ROLES = {"warehouse": db.Role.AGENT, "warehouse_alt": db.Role.AGENT_ALT}
INTERNAL = "lower(c.email) LIKE '%@harborpine.com'"
LOCAL = "(o.order_ts AT TIME ZONE 'America/New_York')"


def _value(warehouse: str, query: str):
    with db.connect(ROLES[warehouse]) as conn:
        row = conn.execute(query).fetchone()
    assert row is not None
    return next(iter(row.values()))


@pytest.mark.parametrize("warehouse", seeding.DATABASES)
def test_the_database_matches_the_expected_counts_and_hash(warehouse: str) -> None:
    assert seeding.check(warehouse) == []


@pytest.mark.parametrize("warehouse", seeding.DATABASES)
def test_the_agent_role_has_its_session_settings(warehouse: str) -> None:
    with db.connect(ROLES[warehouse]) as conn:
        settings = {
            name: conn.execute(f"SHOW {name}").fetchone()[name]  # names are constants above
            for name in (
                "default_transaction_read_only",
                "statement_timeout",
                "idle_in_transaction_session_timeout",
                "temp_file_limit",
                "search_path",
            )
        }
    assert settings == {
        "default_transaction_read_only": "on",
        "statement_timeout": "5s",
        "idle_in_transaction_session_timeout": "10s",
        "temp_file_limit": "100MB",
        "search_path": "warehouse",
    }


@pytest.mark.parametrize("warehouse", seeding.DATABASES)
def test_the_agent_role_reads_tables_and_the_view_but_writes_nothing(warehouse: str) -> None:
    assert _value(warehouse, "SELECT count(*) FROM customers_marketable") > 0
    with db.connect(ROLES[warehouse], autocommit=True) as conn:
        conn.execute("SET default_transaction_read_only = off")  # the seatbelt can be removed
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("DELETE FROM warehouse.orders WHERE order_id = 1")


def test_the_agent_role_has_nothing_on_ops_or_lg() -> None:
    with db.connect(db.Role.AGENT) as conn:
        rows = conn.execute(
            "SELECT n.nspname, has_schema_privilege('datapilot_agent_ro', n.oid, 'USAGE') AS usage "
            "FROM pg_namespace n WHERE n.nspname IN ('ops', 'lg', 'warehouse') ORDER BY 1"
        ).fetchall()
    assert {r["nspname"]: r["usage"] for r in rows} == {
        "lg": False,
        "ops": False,
        "warehouse": True,
    }


def test_the_schema_hides_every_business_rule() -> None:
    with db.connect(db.Role.AGENT) as conn:
        columns = [
            r["column_name"]
            for r in conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'warehouse'"
            ).fetchall()
        ]
        tables = [
            r["table_name"]
            for r in conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'warehouse'"
            ).fetchall()
        ]
        comments = " ".join(
            r["d"] or ""
            for r in conn.execute(
                "SELECT obj_description(c.oid) AS d FROM pg_class c "
                "JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'warehouse' "
                "UNION ALL SELECT col_description(a.attrelid, a.attnum) FROM pg_attribute a "
                "JOIN pg_class c ON c.oid = a.attrelid "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = 'warehouse' AND a.attnum > 0"
            ).fetchall()
        ).lower()
    assert sorted(tables) == [
        "categories", "customers", "customers_marketable", "order_items", "orders", "products"
    ]  # fmt: skip
    assert not [c for c in columns if c in {"is_internal", "cancelled_at"} or "fiscal" in c]
    for word in (
        "fiscal",
        "cancel",
        "internal",
        "harborpine",
        "new_york",
        "eastern",
        "cents",
        "5 =",
    ):
        assert word not in comments, word


@pytest.mark.parametrize("warehouse", seeding.DATABASES)
def test_ten_to_fifteen_percent_of_orders_cross_the_utc_date(warehouse: str) -> None:
    share = _value(
        warehouse,
        f"SELECT avg(({LOCAL}::date <> (o.order_ts AT TIME ZONE 'UTC')::date)::int) "
        "FROM warehouse.orders o",
    )
    assert 0.10 <= share <= 0.15


@pytest.mark.parametrize("day", ["2024-03-10", "2024-11-03", "2025-03-09", "2025-11-02"])
def test_orders_cross_the_utc_date_on_both_daylight_saving_changes(day: str) -> None:
    crossing = _value(
        "warehouse",
        f"SELECT count(*) FROM warehouse.orders o WHERE {LOCAL}::date = DATE '{day}' "
        f"AND {LOCAL}::date <> (o.order_ts AT TIME ZONE 'UTC')::date",
    )
    assert crossing > 10


@pytest.mark.parametrize("warehouse", seeding.DATABASES)
def test_about_six_percent_of_orders_are_cancelled(warehouse: str) -> None:
    share = _value(warehouse, "SELECT avg((status = 5)::int) FROM warehouse.orders")
    assert 0.05 <= share <= 0.08


@pytest.mark.parametrize("warehouse", seeding.DATABASES)
def test_internal_accounts_inflate_revenue_two_to_three_percent(warehouse: str) -> None:
    share = _value(
        warehouse,
        f"SELECT sum(o.subtotal_cents - o.discount_cents) FILTER (WHERE {INTERNAL})::numeric "
        f"/ sum(o.subtotal_cents - o.discount_cents) FILTER (WHERE NOT {INTERNAL}) "
        "FROM warehouse.orders o JOIN warehouse.customers c USING (customer_id) "
        "WHERE o.status <> 5",
    )
    assert 0.02 <= share <= 0.03
    customers = _value(warehouse, f"SELECT avg(({INTERNAL})::int) FROM warehouse.customers c")
    assert 0.004 <= customers <= 0.006


@pytest.mark.parametrize("warehouse", seeding.DATABASES)
@pytest.mark.parametrize("start", ["2023-02-01", "2024-02-01", "2025-02-01"])
def test_internal_accounts_rank_among_the_top_ten_every_fiscal_year(
    warehouse: str, start: str
) -> None:
    internal_in_top = _value(
        warehouse,
        f"SELECT count(*) FILTER (WHERE internal) FROM ("
        f"  SELECT {INTERNAL} AS internal, sum(o.subtotal_cents - o.discount_cents) AS net "
        "  FROM warehouse.orders o JOIN warehouse.customers c USING (customer_id) "
        f"  WHERE o.status <> 5 AND {LOCAL} >= DATE '{start}' "
        f"    AND {LOCAL} < DATE '{start}' + interval '1 year' "
        "  GROUP BY c.customer_id, internal ORDER BY net DESC, c.customer_id LIMIT 10) top",
    )
    assert 2 <= internal_in_top <= 3


@pytest.mark.parametrize("year", [2023, 2024, 2025])
def test_black_friday_and_cyber_monday_spike(year: int) -> None:
    with db.connect(db.Role.AGENT) as conn:
        rows = conn.execute(
            f"SELECT {LOCAL}::date AS day, count(*) AS n FROM warehouse.orders o "
            f"WHERE extract(year FROM {LOCAL}) = %s GROUP BY 1 ORDER BY n DESC LIMIT 2",
            (year,),
        ).fetchall()
        average = conn.execute(
            f"SELECT count(*) / 365.0 AS a FROM warehouse.orders o "
            f"WHERE extract(year FROM {LOCAL}) = %s",
            (year,),
        ).fetchone()["a"]
    assert {r["day"].weekday() for r in rows} == {0, 4}  # Cyber Monday and Black Friday
    assert rows[1]["n"] > 3 * average


def test_january_dips_below_december() -> None:
    december, january = (
        _value(
            "warehouse",
            f"SELECT count(*) FROM warehouse.orders o "
            f"WHERE {LOCAL} >= DATE '{a}' AND {LOCAL} < DATE '{b}'",
        )
        for a, b in (("2024-12-01", "2025-01-01"), ("2025-01-01", "2025-02-01"))
    )
    assert january < december / 2
