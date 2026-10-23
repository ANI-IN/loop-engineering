"""Test doubles for the hill-climbing loop tests. They live only under platform/tests."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from datapilot.contracts import (
    AnswerEnvelope,
    AnswerStatus,
    BenchmarkItem,
    Category,
    ItemResult,
    QueryResult,
    Split,
)
from datapilot.loop4_hill_climbing.experiment import ExperimentResult


def item(item_id: str = "q1", split: Split = Split.DEV, **kwargs: Any) -> BenchmarkItem:
    values: dict[str, Any] = {
        "question": f"Question {item_id}?",
        "gold_sql": "SELECT 1",
        "category": Category.SIMPLE_AGGREGATES,
        "difficulty": 1,
        "metric_family": "revenue",
    }
    values.update(kwargs)
    return BenchmarkItem(id=item_id, split=split, **values)


def answered(sql: str) -> AnswerEnvelope:
    return AnswerEnvelope(status=AnswerStatus.ANSWERED, final_sql=sql)


@dataclass
class TableRunner:
    """Answers each (sql, warehouse) from a table; unknown SQL raises like a failed query."""

    results: dict[tuple[str, str], list[tuple]]
    calls: list[tuple[str, str]] = field(default_factory=list)

    def run(self, sql: str, warehouse: str, *, max_rows: int) -> QueryResult:
        self.calls.append((sql, warehouse))
        if (sql, warehouse) not in self.results:
            raise RuntimeError(f"syntax error in {sql!r}")
        rows = self.results[(sql, warehouse)]
        return QueryResult(
            columns=[f"c{i}" for i in range(len(rows[0]) if rows else 0)],
            rows=rows[:max_rows],
            total_row_count=len(rows),
            truncated=len(rows) > max_rows,
        )


@dataclass
class ScriptedEvaluator:
    """Passes or fails each item from a script of outcomes, one per call."""

    outcomes: dict[str, list[bool]]
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def evaluate(self, item: BenchmarkItem, answer: AnswerEnvelope) -> ItemResult:
        with self._lock:
            passed = self.outcomes[item.id].pop(0)
        return ItemResult(item_id=item.id, passed=passed, reason="scripted")


class StructuredDouble:
    """Stands in for a chat model: with_structured_output returns a runnable that hands back the
    next scripted object for that schema and records the messages it got."""

    def __init__(self, replies: dict[type, list[BaseModel]]) -> None:
        self.replies = replies
        self.seen: list[tuple[type, list[Any]]] = []

    def with_structured_output(self, schema: type, **kwargs: Any) -> Any:
        double = self

        class _Runnable:
            def invoke(self, messages: list[Any]) -> BaseModel:
                double.seen.append((schema, messages))
                return double.replies[schema].pop(0)

        return _Runnable()


def experiment(
    version: str, passes: dict[str, bool], splits: dict[str, Split], session=None
) -> ExperimentResult:
    from datetime import UTC, datetime

    return ExperimentResult(
        experiment_id=uuid4(),
        session_id=session or SESSION,
        knowledge_version=version,
        splits=[Split.DEV, Split.HOLDOUT],
        results={i: ItemResult(item_id=i, passed=p, reason="") for i, p in passes.items()},
        splits_by_item=splits,
        started_at=datetime.now(UTC),
        wall_seconds=1.0,
    )


SESSION = uuid4()
Target = Callable[[str, str], AnswerEnvelope]


def warehouse_snapshot() -> Any:
    """The catalog snapshot of the class warehouse, read from its schema file with no database:
    the tables and columns `make seed` creates (platform/ops/sql/warehouse_schema.sql)."""
    import sqlglot
    from sqlglot import exp

    from datapilot.loop1_agent.catalog import CatalogSnapshot, Column, Table
    from datapilot.settings import PLATFORM

    text = (PLATFORM / "ops" / "sql" / "warehouse_schema.sql").read_text(encoding="utf-8")
    tables = {}
    for statement in text.split(";"):
        body = "\n".join(
            line for line in statement.splitlines() if not line.strip().startswith("--")
        ).strip()
        if not body.upper().startswith("CREATE TABLE"):
            continue
        schema = sqlglot.parse_one(body, read="postgres").this
        columns = tuple(
            Column(c.name, c.args["kind"].sql("postgres").lower(), True)
            for c in schema.expressions
            if isinstance(c, exp.ColumnDef)
        )
        name = schema.this.name
        tables[name] = Table(name=name, kind="table", comment="", columns=columns)
    return CatalogSnapshot(schema="warehouse", tables=tables)
