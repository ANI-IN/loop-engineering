"""The defense layers, run on fixed statements with no model: which layer stops each one.

Used by the verification loop's demos: malicious SQL (the guard, then the read-only transaction,
then the role's grants) and the cartesian query (the cost guard, then the statement timeout).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import psycopg

from datapilot.contracts import GraderContext, Severity
from datapilot.loop2_verification.config import VerificationConfig
from datapilot.loop2_verification.executor import ExecutionError, Executor
from datapilot.loop2_verification.graders import CostGrader, guard_graders

STACKED_DELETE = "SELECT 1; DELETE FROM orders"
CTE_DELETE = "WITH d AS (DELETE FROM orders RETURNING *) SELECT count(*) FROM d"
RAW_DELETE = "DELETE FROM orders"
CARTESIAN = "SELECT count(*) FROM order_items a CROSS JOIN order_items b CROSS JOIN order_items c"
COUNT_ORDERS = "SELECT count(*) FROM orders"


@dataclass
class LayerReport:
    sql: str
    stopped_by: str | None = None
    layers: list[dict[str, Any]] = field(default_factory=list)
    ms: int = 0

    def add(self, layer: str, stopped: bool, detail: str) -> None:
        self.layers.append({"layer": layer, "stopped": stopped, "detail": detail})
        if stopped and self.stopped_by is None:
            self.stopped_by = layer


def _execute(report: LayerReport, executor: Executor, sql: str, layer: str) -> None:
    try:
        executor.run(sql)
        report.add(layer, False, "ran")
    except ExecutionError as error:
        report.add(layer, True, f"SQLSTATE {error.sqlstate}: {error.message}")


def _role_only(executor: Executor, sql: str) -> LayerReport:
    """A raw write on the agent role with the read-only default switched off: only grants remain."""
    report = LayerReport(sql)
    try:
        with psycopg.connect(executor.url, autocommit=True) as conn:
            conn.execute("SET default_transaction_read_only = off")
            conn.execute("SELECT set_config('search_path', %s, false)", (executor.schema,))
            with conn.transaction(force_rollback=True):
                conn.execute(sql)
            report.add("role grants", False, "the write ran (and was rolled back)")
    except psycopg.Error as error:
        report.add("role grants", True, f"SQLSTATE {error.sqlstate}: {str(error).splitlines()[0]}")
    return report


def malicious_sql(executor: Executor, config: VerificationConfig) -> dict[str, Any]:
    before = executor.run(COUNT_ORDERS).rows[0][0]
    reports = []
    for sql in (STACKED_DELETE, CTE_DELETE):
        report = LayerReport(sql)
        context = GraderContext(question="", sql=sql)
        for grader in guard_graders(config.schema):
            result = grader.check(context)
            report.add(f"guard: {grader.name}", result.severity is Severity.BLOCK, result.reason)
            if report.stopped_by:
                break
        if report.stopped_by is None:
            _execute(report, executor, sql, "read-only transaction")
        reports.append(report)
    reports.append(_role_only(executor, RAW_DELETE))
    after = executor.run(COUNT_ORDERS).rows[0][0]
    return {
        "statements": [r.__dict__ for r in reports],
        "orders_before": before,
        "orders_after": after,
        "unchanged": before == after,
    }


def cartesian_query(executor: Executor, config: VerificationConfig) -> dict[str, Any]:
    report = LayerReport(CARTESIAN)
    started = time.monotonic()
    result = CostGrader(config, executor.explain).check(GraderContext(question="", sql=CARTESIAN))
    report.add("cost guard", result.severity is Severity.BLOCK, result.reason)
    if report.stopped_by is None:
        _execute(report, executor, CARTESIAN, "statement timeout")
    report.ms = round((time.monotonic() - started) * 1000)
    return {"statements": [report.__dict__]}
