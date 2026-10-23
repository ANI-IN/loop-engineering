"""Benchmark items, item results, and the evaluator protocol of the hill-climbing loop."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field

from datapilot.contracts.answer import AnswerEnvelope, AnswerStatus


class Split(StrEnum):
    DEV = "dev"
    HOLDOUT = "holdout"


class Category(StrEnum):
    SIMPLE_AGGREGATES = "simple_aggregates"
    JOINS_AND_HIERARCHY = "joins_and_hierarchy"
    FISCAL_PERIODS = "fiscal_periods"
    EASTERN_BUSINESS_DAYS = "eastern_business_days"
    CUSTOMER_SEGMENTS = "customer_segments"
    RANKING = "ranking"
    RATIOS = "ratios"
    AMBIGUOUS = "ambiguous"


class BenchmarkItem(BaseModel):
    id: str
    question: str
    gold_sql: str | None = None
    naive_sql: str | None = None
    split: Split
    traps: list[str] = Field(default_factory=list)
    category: Category
    difficulty: int = Field(ge=1, le=3)
    order_matters: bool = False
    numeric_tolerance: float = 0.01
    expected_status: AnswerStatus = AnswerStatus.ANSWERED
    metric_family: str
    paraphrase_group: str | None = None
    notes: str = ""


class ItemResult(BaseModel):
    item_id: str
    passed: bool
    reason: str
    trap_labels: list[str] = Field(default_factory=list)
    run_passes: list[bool] = Field(default_factory=list)  # one entry per repetition


class Evaluator(Protocol):
    def evaluate(self, item: BenchmarkItem, answer: AnswerEnvelope) -> ItemResult:
        """Pass only if the prediction matches gold on both warehouse databases."""
        ...
