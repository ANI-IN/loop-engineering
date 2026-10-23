"""Security suite, first part (no database): the syntax-tree layers stop every malicious case and
let every benign case through. The second part (test_security_suite.py) runs the full checker and
the read-only executor on the fixture warehouse."""

from __future__ import annotations

import pytest
from loops_support import FIXTURE_SCHEMA, fixture_config, fixture_snapshot
from security_cases import BENIGN, MALICIOUS

from datapilot.contracts import GraderContext, Severity
from datapilot.loop2_verification.graders import (
    CostGrader,
    ParseGrader,
    SchemaGrader,
    StatementPolicyGrader,
)


@pytest.fixture(autouse=True)
def honest(monkeypatch: pytest.MonkeyPatch) -> None:
    for flag in ("BUG_NAIVE_GUARD", "BUG_NO_COST_GUARD"):
        monkeypatch.delenv(flag, raising=False)


def static_layers() -> list:
    return [ParseGrader(), StatementPolicyGrader(FIXTURE_SCHEMA), SchemaGrader(fixture_snapshot())]


def first_block(sql: str) -> str | None:
    context = GraderContext(question="", sql=sql)
    for grader in static_layers():
        if grader.check(context).severity is Severity.BLOCK:
            return grader.name
    return None


def test_the_suite_is_large_enough() -> None:
    assert len(MALICIOUS) >= 40 and len(BENIGN) >= 40


@pytest.mark.parametrize("sql", MALICIOUS)
def test_every_malicious_case_is_blocked_before_execution(sql: str) -> None:
    assert first_block(sql) is not None, sql


@pytest.mark.parametrize("sql", BENIGN)
def test_every_benign_case_passes_the_static_layers(sql: str) -> None:
    assert first_block(sql) is None, sql


def test_each_static_layer_stops_something_the_earlier_ones_missed() -> None:
    assert first_block("SELECT 1; DELETE FROM orders") == "parse"
    assert first_block("WITH d AS (DELETE FROM orders RETURNING *) SELECT * FROM d") == (
        "statement_policy"
    )
    assert first_block("SELECT usename, passwd FROM pg_shadow") == "schema"
    cartesian = "SELECT count(*) FROM order_items a CROSS JOIN order_items b"
    assert first_block(cartesian) is None

    def no_explain(_sql: str) -> dict:
        raise AssertionError("not reached")

    cost = CostGrader(fixture_config(), no_explain).check(GraderContext(question="", sql=cartesian))
    assert cost.severity is Severity.BLOCK
