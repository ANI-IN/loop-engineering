"""The personal-data grader fails closed (zero tokens, no database): a projection that can carry a
personal column without naming it (a whole row, a table or alias used as a value, a row turned into
JSON or an array, a LATERAL or correlated reference) goes to human approval whenever the query reads
a table with a personal column. Since review round 2 the whole tree counts, not only the select
lists: a personal column anywhere but a predicate (the FROM clause, a VALUES list, a function
argument), and SQL held in a string. Plain queries that return no personal data are unaffected: the
security suite's benign cases and every gold query of the benchmark pass with no approval."""

from __future__ import annotations

import pytest
from loop4_doubles import warehouse_snapshot
from loops_support import fixture_config, fixture_snapshot
from security_cases import BENIGN, CARRIES_A_PERSONAL_COLUMN

from datapilot.contracts import GraderContext, Severity
from datapilot.loop1_agent.catalog import CatalogSnapshot, Column, Table
from datapilot.loop2_verification.config import VerificationConfig
from datapilot.loop2_verification.graders import PersonalDataGrader
from datapilot.loop4_hill_climbing.pack_files import load_benchmark

# Whole rows of tables with no personal column, and whole rows of a derived table that projects
# none: nothing personal can come back, so nothing is routed.
NO_PERSONAL_COLUMN = [
    "SELECT to_jsonb(o) FROM orders o LIMIT 5",
    "SELECT json_agg(p) FROM products p",
    "SELECT row_to_json(o.*) FROM orders o LIMIT 1",
    "SELECT to_jsonb(s) FROM (SELECT state, count(*) AS n FROM customers GROUP BY state) AS s",
    "SELECT count(*) FROM customers WHERE email = 'a@b.com'",
    "SELECT count(*) FROM customers c WHERE c IS NOT NULL",
]


def ctx(sql: str) -> GraderContext:
    return GraderContext(question="", sql=sql, extra={"export": False})


@pytest.fixture(scope="module")
def grader() -> PersonalDataGrader:
    return PersonalDataGrader(fixture_config(), fixture_snapshot())


@pytest.mark.parametrize("sql", CARRIES_A_PERSONAL_COLUMN)
def test_a_projection_that_can_carry_a_personal_column_needs_approval(grader, sql: str) -> None:
    result = grader.check(ctx(sql))
    assert result.severity is Severity.ROUTE, (sql, result.reason)


@pytest.mark.parametrize("sql", NO_PERSONAL_COLUMN)
def test_a_whole_row_with_no_personal_column_is_not_routed(grader, sql: str) -> None:
    result = grader.check(ctx(sql))
    assert result.severity is Severity.INFO, (sql, result.reason)


@pytest.mark.parametrize("sql", BENIGN)
def test_every_benign_security_case_still_needs_no_approval(grader, sql: str) -> None:
    result = grader.check(ctx(sql))
    assert result.severity is Severity.INFO, (sql, result.reason)


def _class_warehouse() -> CatalogSnapshot:
    """The class warehouse's tables from its schema file, plus the marketing view's columns."""
    snapshot = warehouse_snapshot()
    view = ("customer_id", "first_name", "last_name", "email", "phone", "city", "state", "zip")
    tables = dict(snapshot.tables)
    tables["customers_marketable"] = Table(
        name="customers_marketable",
        kind="view",
        comment="",
        columns=tuple(Column(c, "text", True) for c in (*view, "created_at")),
    )
    return CatalogSnapshot(schema=snapshot.schema, tables=tables)


ITEMS = load_benchmark()


# Review round 2 (minor): a live agent's query of 22 October, which the round 1 grader routed to
# approval: its LATERAL reads only orders.order_ts, and customers only filters out the internal
# accounts.
LIVE_FISCAL_QUARTER_REVENUE = """
SELECT q.quarter_number, ROUND(SUM(o.subtotal_cents - o.discount_cents) / 100.0, 2) AS net_revenue
FROM orders AS o
JOIN customers AS c ON c.customer_id = o.customer_id
CROSS JOIN LATERAL (
  SELECT CASE
    WHEN local_order_date >= DATE '2025-02-01' AND local_order_date < DATE '2025-05-01' THEN 1
    WHEN local_order_date >= DATE '2025-05-01' AND local_order_date < DATE '2025-08-01' THEN 2
    WHEN local_order_date >= DATE '2025-08-01' AND local_order_date < DATE '2025-11-01' THEN 3
    WHEN local_order_date >= DATE '2025-11-01' AND local_order_date < DATE '2026-02-01' THEN 4
  END AS quarter_number
  FROM (SELECT (o.order_ts AT TIME ZONE 'America/New_York')::date AS local_order_date) AS dates
) AS q
WHERE o.status <> 5
  AND c.email NOT ILIKE '%@harborpine%'
  AND q.quarter_number IS NOT NULL
GROUP BY q.quarter_number
ORDER BY q.quarter_number
"""


def test_a_lateral_that_reads_only_order_columns_needs_no_approval() -> None:
    grader = PersonalDataGrader(VerificationConfig.from_pack(), _class_warehouse())
    result = grader.check(ctx(LIVE_FISCAL_QUARTER_REVENUE))
    assert result.severity is Severity.INFO, result.reason


def test_a_lateral_that_returns_a_personal_column_still_needs_approval() -> None:
    grader = PersonalDataGrader(VerificationConfig.from_pack(), _class_warehouse())
    sql = LIVE_FISCAL_QUARTER_REVENUE.replace("AS local_order_date", "AS local_order_date, c.email")
    sql = sql.replace("END AS quarter_number", "END AS quarter_number, dates.email")
    sql = sql.replace("SELECT q.quarter_number,", "SELECT q.email, q.quarter_number,")
    assert grader.check(ctx(sql)).severity is Severity.ROUTE


@pytest.mark.parametrize("item", ITEMS, ids=lambda i: i.id)
def test_every_gold_query_passes_the_grader_with_no_approval(item) -> None:
    grader = PersonalDataGrader(VerificationConfig.from_pack(), _class_warehouse())
    result = grader.check(ctx(item.gold_sql))
    assert result.passed and result.severity is Severity.INFO, (item.id, result.reason)
