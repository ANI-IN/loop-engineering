"""Knowledge versions: the business rules the analyst gets, versioned and gated."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field


class KnowledgeStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    ACTIVE = "active"
    RETIRED = "retired"


class KnowledgeRule(BaseModel):
    id: str
    title: str
    rule_text: str
    applies_when: str
    sql_guidance: str = ""


class KnowledgeVersion(BaseModel):
    version: str
    rules: list[KnowledgeRule] = Field(default_factory=list)
    notes: str = ""

    def prompt_block(self) -> str:
        """The text the dynamic prompt middleware injects on every run."""
        if not self.rules:
            return f"Business knowledge (version {self.version}): none recorded yet."
        lines = [f"Business knowledge (version {self.version}):"]
        for rule in self.rules:
            lines.append(f"- {rule.title}: {rule.rule_text} Applies when: {rule.applies_when}.")
            if rule.sql_guidance:
                lines.append(f"  SQL guidance: {rule.sql_guidance}")
        return "\n".join(lines)


class KnowledgeStore(Protocol):
    def active(self) -> KnowledgeVersion: ...

    def get(self, version: str) -> KnowledgeVersion: ...

    def save_draft(self, version: KnowledgeVersion, *, created_by: str) -> None: ...

    def activate(self, version: str, *, approved_by: str) -> None: ...
