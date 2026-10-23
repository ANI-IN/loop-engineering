"""The answer envelope: the structured result of every run of the analyst."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AnswerStatus(StrEnum):
    ANSWERED = "answered"
    NEEDS_CLARIFICATION = "needs_clarification"
    REFUSED = "refused"
    ESCALATED = "escalated"


class AnswerEnvelope(BaseModel):
    """What the analyst returns as structured output, and what the graders and the channel read."""

    status: AnswerStatus
    final_sql: str | None = None
    columns: list[str] = Field(default_factory=list)
    rows_preview: list[list[Any]] = Field(default_factory=list)
    row_count: int | None = None
    answer_text: str = ""
    assumptions: list[str] = Field(default_factory=list)
    clarifying_question: str | None = None
