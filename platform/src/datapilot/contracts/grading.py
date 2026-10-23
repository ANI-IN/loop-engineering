"""The grader protocol of the verification loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from datapilot.contracts.answer import AnswerEnvelope


class Stage(StrEnum):
    PRE_EXECUTION = "pre_execution"
    POST_EXECUTION = "post_execution"
    FINAL_ANSWER = "final_answer"


class Severity(StrEnum):
    INFO = "info"
    BLOCK = "block"  # the query or answer must not proceed; the reason goes back to the agent
    ROUTE = "route"  # proceed only through human approval (the personal-data grader)


@dataclass(frozen=True)
class GraderResult:
    grader: str
    passed: bool
    reason: str
    severity: Severity = Severity.INFO
    feedback_for_agent: str | None = None


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[tuple[Any, ...]]
    total_row_count: int
    truncated: bool


@dataclass
class GraderContext:
    """Everything a grader may read. Graders never call the model."""

    question: str
    sql: str | None = None
    result: QueryResult | None = None
    answer: AnswerEnvelope | None = None
    knowledge_version: str | None = None
    pack: str = "datapilot_us"
    extra: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Grader(Protocol):
    name: str
    stage: Stage

    def check(self, context: GraderContext) -> GraderResult: ...
