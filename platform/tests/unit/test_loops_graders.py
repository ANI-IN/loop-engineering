"""The deterministic graders, without a database: what each one stops and lets through."""

from __future__ import annotations

import pytest
from loops_support import FIXTURE_SCHEMA, fixture_config, fixture_snapshot

from datapilot.contracts import AnswerEnvelope, GraderContext, QueryResult, Severity
from datapilot.loop2_verification.graders import (
    CostGrader,
    FinalAnswerGrader,
    InjectedFailingGrader,
    ParseGrader,
    PersonalDataGrader,
    SchemaGrader,
    StatementPolicyGrader,
    guard_graders,
)
from datapilot.loop2_verification.limits import attempt_allowed


def ctx(sql: str, **extra: object) -> GraderContext:
    return GraderContext(question="q", sql=sql, extra=dict(extra))


def cheap_plan(_sql: str) -> dict[str, float]:
    return {"Total Cost": 10.0, "Plan Rows": 5.0}


def test_parse_rejects_two_statements_and_command_fallbacks() -> None:
    grader = ParseGrader()
    assert grader.check(ctx("SELECT 1")).passed
    assert not grader.check(ctx("SELECT 1; DELETE FROM orders")).passed
    assert not grader.check(ctx("DO $$ BEGIN DELETE FROM orders; END $$")).passed
    assert not grader.check(ctx("SELEC 1")).passed
    assert not grader.check(ctx("")).passed


def test_statement_policy_walks_the_whole_tree() -> None:
    grader = StatementPolicyGrader(FIXTURE_SCHEMA)
    cte = "WITH d AS (DELETE FROM orders RETURNING *) SELECT * FROM d"
    result = grader.check(ctx(cte))
    assert not result.passed and "DELETE" in result.reason
    assert result.feedback_for_agent


def test_statement_policy_denies_functions_and_other_schemas() -> None:
    grader = StatementPolicyGrader(FIXTURE_SCHEMA)
    assert not grader.check(ctx("SELECT pg_catalog.pg_sleep(1)")).passed
    assert not grader.check(
        ctx("SELECT set_config('default_transaction_read_only','off',false)")
    ).passed
    assert not grader.check(ctx("SELECT * FROM information_schema.tables")).passed
    assert grader.check(ctx(f"SELECT count(*) FROM {FIXTURE_SCHEMA}.orders")).passed
    assert grader.check(ctx("SELECT 1 UNION SELECT 2")).passed


def test_schema_grader_catches_an_unqualified_system_catalog() -> None:
    sql = "SELECT usename, passwd FROM pg_shadow"
    assert (
        StatementPolicyGrader(FIXTURE_SCHEMA).check(ctx(sql)).passed
    )  # the earlier layer misses it
    result = SchemaGrader(fixture_snapshot()).check(ctx(sql))
    assert not result.passed and "pg_shadow" in result.reason


def test_schema_grader_names_unknown_columns() -> None:
    result = SchemaGrader(fixture_snapshot()).check(ctx("SELECT revenue FROM orders"))
    assert not result.passed and "revenue" in result.reason
    assert (
        SchemaGrader(fixture_snapshot())
        .check(ctx("WITH t AS (SELECT status FROM orders) SELECT status FROM t"))
        .passed
    )


def test_cost_grader_rejects_a_join_without_a_condition_before_explain() -> None:
    def explain_must_not_run(_sql: str) -> dict[str, float]:
        raise AssertionError("the syntax-tree check should stop it first")

    grader = CostGrader(fixture_config(), explain_must_not_run)
    result = grader.check(ctx("SELECT count(*) FROM order_items a CROSS JOIN order_items b"))
    assert not result.passed and "cartesian" in result.reason
    assert not grader.check(ctx("SELECT count(*) FROM orders a, customers b")).passed


def test_cost_grader_accepts_comma_joins_with_a_where_condition() -> None:
    grader = CostGrader(fixture_config(), cheap_plan)
    sql = "SELECT count(*) FROM orders a, customers b WHERE a.customer_id = b.customer_id"
    assert grader.check(ctx(sql)).passed


def test_cost_grader_applies_the_pack_thresholds() -> None:
    config = fixture_config()

    def expensive(_sql: str) -> dict[str, float]:
        return {"Total Cost": config.max_plan_cost + 1, "Plan Rows": 1.0}

    assert not CostGrader(config, expensive).check(ctx("SELECT 1")).passed


def test_personal_data_routes_to_approval() -> None:
    grader = PersonalDataGrader(fixture_config(), fixture_snapshot())
    assert grader.check(ctx("SELECT email FROM customers")).severity is Severity.ROUTE
    assert grader.check(ctx("SELECT * FROM customers")).severity is Severity.ROUTE
    assert grader.check(ctx("SELECT email FROM customers_marketable")).severity is Severity.ROUTE
    assert grader.check(ctx("SELECT state, count(*) FROM customers GROUP BY 1")).severity is (
        Severity.INFO
    )
    nested = "WITH x AS (SELECT email FROM customers) SELECT count(*) FROM x"
    assert grader.check(ctx(nested)).severity is Severity.ROUTE


def test_a_personal_column_used_only_to_filter_is_not_routed() -> None:
    """The internal-accounts rule filters on the email domain; such a query returns no email, so
    it is not held for approval (live, every correct order query was held and could not answer)."""
    grader = PersonalDataGrader(fixture_config(), fixture_snapshot())
    internal = (
        "SELECT count(*) FROM orders o JOIN customers c ON c.customer_id = o.customer_id "
        "WHERE lower(c.email) NOT LIKE '%@harborpine.com'"
    )
    assert grader.check(ctx(internal)).severity is Severity.INFO
    grouped = "SELECT state, count(*) FROM customers WHERE email LIKE '%@x.com' GROUP BY state"
    assert grader.check(ctx(grouped)).severity is Severity.INFO
    shown = "SELECT customer_id, email FROM customers WHERE lower(email) LIKE '%@harborpine.com'"
    assert grader.check(ctx(shown)).severity is Severity.ROUTE
    inner = "SELECT n FROM (SELECT lower(email) AS n FROM customers) AS emails"
    assert grader.check(ctx(inner)).severity is Severity.ROUTE


def test_marketing_exports_must_use_the_marketable_view() -> None:
    grader = PersonalDataGrader(fixture_config(), fixture_snapshot())
    base = grader.check(ctx("SELECT email FROM customers WHERE state = 'CA'", export=True))
    assert not base.passed and "customers_marketable" in (base.feedback_for_agent or "")
    view = grader.check(
        ctx("SELECT email FROM customers_marketable WHERE state = 'CA'", export=True)
    )
    assert view.passed and view.severity is Severity.ROUTE


def answer(text: str, sql: str = "SELECT 1") -> AnswerEnvelope:
    return AnswerEnvelope(status="answered", final_sql=sql, answer_text=text)


def result(columns: list[str], rows: list[tuple]) -> QueryResult:
    return QueryResult(columns=columns, rows=rows, total_row_count=len(rows), truncated=False)


def final(question: str, envelope: AnswerEnvelope, res: QueryResult | None) -> bool:
    context = GraderContext(question=question, answer=envelope, result=res)
    return FinalAnswerGrader().check(context).passed


def test_final_answer_numbers_must_come_from_the_result() -> None:
    res = result(["net_revenue_cents"], [(123456789,)])
    assert final("Net revenue in fiscal year 2025?", answer("Net revenue was $1,234,567.89."), res)
    assert final("Net revenue?", answer("About $1.23 million in fiscal year 2025."), res)
    assert not final("Net revenue?", answer("Net revenue was $2,000,000."), res)


def test_final_answer_checks_ratios_top_n_and_revenue_sign() -> None:
    assert final("Share?", answer("The share is 42.5%."), result(["share"], [(0.425,)]))
    assert not final("Share?", answer("The share is 142%."), result(["share"], [(1.42,)]))
    five = result(["name", "revenue"], [(f"p{i}", 10) for i in range(6)])
    assert not final("Top 5 products by revenue?", answer("The top products are listed."), five)
    negative = result(["revenue"], [(-5,)])
    assert not final("Revenue?", answer("Revenue was listed."), negative)


def test_final_answer_status_rules() -> None:
    clarify = AnswerEnvelope(status="needs_clarification", clarifying_question="Which jacket?")
    assert final("Sales of the jacket?", clarify, None)
    assert not final("q", AnswerEnvelope(status="answered", answer_text="42"), None)


def test_the_injected_grader_always_fails() -> None:
    assert not InjectedFailingGrader().check(ctx("SELECT 1")).passed


def test_retry_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BUG_NO_RETRY_CAP", raising=False)
    assert [attempt_allowed(n, 3) for n in (1, 2, 3, 4)] == [True, True, True, False]


def test_planted_missing_retry_cap_allows_every_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BUG_NO_RETRY_CAP", "1")
    assert attempt_allowed(50, 3)


def test_planted_naive_guard_passes_stacked_and_cte_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    stacked = "SELECT 1; DELETE FROM orders"
    cte = "WITH d AS (DELETE FROM orders RETURNING *) SELECT * FROM d"
    monkeypatch.setenv("BUG_NAIVE_GUARD", "1")
    naive = guard_graders(FIXTURE_SCHEMA)
    assert all(g.check(ctx(s)).passed for g in naive for s in (stacked, cte))
    monkeypatch.setenv("BUG_NAIVE_GUARD", "0")
    tree = guard_graders(FIXTURE_SCHEMA)
    for sql in (stacked, cte):
        assert not all(g.check(ctx(sql)).passed for g in tree)


def test_planted_missing_cost_guard_accepts_a_cartesian_join(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sql = "SELECT count(*) FROM order_items a CROSS JOIN order_items b"
    monkeypatch.setenv("BUG_NO_COST_GUARD", "1")
    assert CostGrader(fixture_config(), cheap_plan).check(ctx(sql)).passed
    monkeypatch.setenv("BUG_NO_COST_GUARD", "0")
    assert not CostGrader(fixture_config(), cheap_plan).check(ctx(sql)).passed
