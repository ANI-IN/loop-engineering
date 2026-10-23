"""Structured outputs of the helper agents: the schema scout, the reviewer, the analyzer team."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class TableHint(BaseModel):
    table: str
    columns: list[str]
    why: str


class SchemaBrief(BaseModel):
    """The schema scout's answer: candidate tables, columns, and joins. Stateless; advisory."""

    tables: list[TableHint] = Field(default_factory=list)
    joins: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class ReviewOutcome(StrEnum):
    APPROVE = "approve"
    CONCERN = "concern"


class ReviewVerdict(BaseModel):
    """The reviewer's verdict. It runs only after every deterministic grader passed and can never
    pass a failed grader."""

    outcome: ReviewOutcome
    reasons: list[str] = Field(default_factory=list)


class Diagnosis(BaseModel):
    """The failure analyst's reading of one failed dev item. No rules here."""

    item_id: str
    what_went_wrong: str
    likely_cause: str


class ProposedRule(BaseModel):
    id: str
    title: str
    rule_text: str
    applies_when: str
    sql_guidance: str = ""
    evidence_example_ids: list[str] = Field(default_factory=list)
    expected_effect: str


class CriticDecision(StrEnum):
    KEEP = "keep"
    NARROW = "narrow"
    DROP = "drop"


class CriticReview(BaseModel):
    """The critic's decision on one proposed rule. It may keep, narrow, or drop; never add."""

    rule_id: str
    decision: CriticDecision
    reason: str
    narrowed: ProposedRule | None = None
