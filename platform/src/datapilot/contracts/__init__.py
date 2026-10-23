"""Interfaces frozen in milestone B1. Every loop builds on these; nothing here imports a loop."""

from datapilot.contracts.agents import (
    CriticDecision,
    CriticReview,
    Diagnosis,
    ProposedRule,
    ReviewOutcome,
    ReviewVerdict,
    SchemaBrief,
)
from datapilot.contracts.answer import AnswerEnvelope, AnswerStatus
from datapilot.contracts.autonomy import AutonomyLevel, AutonomyPolicy, DemotionReason
from datapilot.contracts.evaluation import BenchmarkItem, Category, Evaluator, ItemResult, Split
from datapilot.contracts.grading import (
    Grader,
    GraderContext,
    GraderResult,
    QueryResult,
    Severity,
    Stage,
)
from datapilot.contracts.knowledge import (
    KnowledgeRule,
    KnowledgeStatus,
    KnowledgeStore,
    KnowledgeVersion,
)
from datapilot.contracts.lifecycle import (
    TERMINAL,
    TRANSITIONS,
    EventType,
    RunEventKind,
    RunStatus,
    can_transition,
)
from datapilot.contracts.pack import DataGenerator, DomainPack, EventSource, Tool

__all__ = [
    "TERMINAL",
    "TRANSITIONS",
    "AnswerEnvelope",
    "AnswerStatus",
    "AutonomyLevel",
    "AutonomyPolicy",
    "BenchmarkItem",
    "Category",
    "CriticDecision",
    "CriticReview",
    "DataGenerator",
    "DemotionReason",
    "Diagnosis",
    "DomainPack",
    "Evaluator",
    "EventSource",
    "EventType",
    "Grader",
    "GraderContext",
    "GraderResult",
    "ItemResult",
    "KnowledgeRule",
    "KnowledgeStatus",
    "KnowledgeStore",
    "KnowledgeVersion",
    "ProposedRule",
    "QueryResult",
    "ReviewOutcome",
    "ReviewVerdict",
    "RunEventKind",
    "RunStatus",
    "SchemaBrief",
    "Severity",
    "Split",
    "Stage",
    "Tool",
    "can_transition",
]
