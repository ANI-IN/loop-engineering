"""The analyzer team: failure analyst, rule writer, critic; then the deterministic overfit guard.

1. The failure analyst reads each failed dev item (never a holdout item) and returns a Diagnosis.
2. The rule writer sees only the diagnoses, never the questions, and proposes general rules.
   Pre-authored rules (the planted over-broad rule) can join its proposals, so the critic judges
   them too.
3. The critic keeps, narrows, or drops each proposed rule; it can never add one. The critic stage
   can drop a rule before the model reads it (extension.screen). A rule whose SQL guidance does
   not run over the schema (sql_guidance.GuidanceCheck) reaches the critic with its problems, to
   narrow; one that still does not run after the critic is dropped, with the problems as reason.
4. The overfit guard rejects any surviving rule that quotes a question or copies gold SQL.

The result is a draft candidate version for the promotion gate and human approval. Each role is
one structured-output call through an injectable chat model.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from datapilot.contracts import (
    AnswerEnvelope,
    BenchmarkItem,
    CriticDecision,
    CriticReview,
    Diagnosis,
    ItemResult,
    KnowledgeRule,
    KnowledgeVersion,
    ProposedRule,
    Split,
)
from datapilot.loop1_agent.guard import output_limit_reached
from datapilot.loop4_hill_climbing import extension
from datapilot.loop4_hill_climbing.overfit_guard import GuardResult, OverfitGuard
from datapilot.loop4_hill_climbing.sql_guidance import GuidanceCheck, GuidanceResult
from datapilot.planted import planted


class Diagnoses(BaseModel):
    diagnoses: list[Diagnosis] = Field(default_factory=list)


class ProposedRules(BaseModel):
    rules: list[ProposedRule] = Field(default_factory=list)


class CriticReviews(BaseModel):
    reviews: list[CriticReview] = Field(default_factory=list)


class StructuredModel(Protocol):
    """A chat model that can return a Pydantic object, such as ChatOpenAI."""

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Any: ...


FAILURE_ANALYST = """You are the failure analyst of a text-to-SQL analytics agent.
For each failed benchmark item you get the question, the agent's SQL, the evaluator's reason,
trap labels from a SQL checker, and the reference SQL. Say what went wrong and the likely cause in
general business terms (a definition, a filter, a time zone, a calendar). In the likely cause,
quote word for word the short fragment of the reference SQL that the agent's SQL lacked or got
wrong (one condition, expression, or join, never the whole query), because the exact columns and
values matter: a definition stated loosely is guessed wrong. Do not propose rules."""

RULE_WRITER = """You are the rule writer. From diagnoses of failed analytics questions, propose
general business rules for the agent's knowledge. A rule must hold for every question it applies
to, not only the diagnosed ones. Never quote a question, never name a specific answer, and cite the
diagnosed item ids as evidence.
The SQL guidance of a rule must run over the real schema: one short condition, expression, or
join, copied from or consistent with the reference SQL fragments the diagnoses quote, using only
the tables and columns listed under schema. Never write a placeholder in angle brackets, never
invent a column, and never write prose there; leave the SQL guidance empty when a rule needs no
SQL."""

CRITIC = """You are the critic. For each proposed rule decide keep, narrow, or drop. Drop a rule
that is too broad, unsupported by the evidence, or specific to one question; narrow a rule whose
idea is right but whose scope is too wide, and return the narrowed rule with the same id. You may
not add rules. Return exactly one review per proposed rule.
A rule listed under sql_guidance_problems has SQL guidance that does not run over the schema:
narrow it with guidance that uses only the tables and columns under schema, as the diagnoses quote
the reference SQL, or with empty guidance, or drop it. A rule whose guidance still does not run is
dropped after you."""


def critic_prompt() -> str:
    """The critic's prompt, plus any guidance an assignment adds (none in class)."""
    guidance = extension.CRITIC_GUIDANCE.strip()
    return f"{CRITIC}\n{guidance}" if guidance else CRITIC


class OutputLimitReached(RuntimeError):
    """A role's response was cut off at its max_output_tokens (pack.yaml), so it is not used."""


def _call(model: StructuredModel, schema: type[BaseModel], system: str, payload: Any) -> Any:
    runnable = model.with_structured_output(schema, method="json_schema", include_raw=True)
    raw = runnable.invoke(
        [SystemMessage(content=system), HumanMessage(content=json.dumps(payload, indent=1))]
    )
    if isinstance(raw, dict) and "raw" in raw:  # the reply, its parse, and any parse error
        if isinstance(raw["raw"], AIMessage) and output_limit_reached(raw["raw"]):
            raise OutputLimitReached(f"the {schema.__name__} reply was cut off at its output cap")
        if raw.get("parsing_error") is not None:
            raise raw["parsing_error"]
        raw = raw["parsed"]
    return raw if isinstance(raw, schema) else schema.model_validate(raw)


@dataclass(frozen=True)
class FailedItem:
    item: BenchmarkItem
    answer: AnswerEnvelope | None
    result: ItemResult

    def for_analyst(self) -> dict[str, Any]:
        return {
            "item_id": self.item.id,
            "question": self.item.question,
            "agent_sql": self.answer.final_sql if self.answer else None,
            "evaluator_reason": self.result.reason,
            "trap_labels": self.result.trap_labels,
            "reference_sql": self.item.gold_sql,
        }


@dataclass
class AnalyzerReport:
    candidate: KnowledgeVersion
    diagnoses: list[Diagnosis] = field(default_factory=list)
    proposed: list[ProposedRule] = field(default_factory=list)
    reviews: list[CriticReview] = field(default_factory=list)
    ignored_reviews: list[str] = field(default_factory=list)
    kept: list[ProposedRule] = field(default_factory=list)  # by the critic
    guidance: list[GuidanceResult] = field(default_factory=list)  # each kept rule's SQL guidance
    guard: list[GuardResult] = field(default_factory=list)
    accepted: list[ProposedRule] = field(default_factory=list)
    planted_active: list[str] = field(default_factory=list)

    @property
    def guidance_rejections(self) -> dict[str, list[str]]:
        return {g.rule_id: g.problems for g in self.guidance if not g.passed}


def apply_reviews(
    proposed: Sequence[ProposedRule], reviews: Sequence[CriticReview]
) -> tuple[list[ProposedRule], list[str]]:
    """Keep, narrow, or drop each proposed rule. A rule without a review is dropped; a review of
    an unknown rule is ignored, so the critic can never add one."""
    by_id = {r.rule_id: r for r in reviews}
    known = {rule.id for rule in proposed}
    ignored = [
        f"{r.rule_id}: the critic cannot add rules" for r in reviews if r.rule_id not in known
    ]
    kept = []
    for rule in proposed:
        review = by_id.get(rule.id)
        if review is None or review.decision is CriticDecision.DROP:
            continue
        if review.decision is CriticDecision.NARROW:
            if review.narrowed is None:
                continue
            kept.append(review.narrowed.model_copy(update={"id": rule.id}))
        else:
            kept.append(rule)
    return kept, ignored


def candidate_version(
    active: KnowledgeVersion, rules: Sequence[ProposedRule], name: str, notes: str
) -> KnowledgeVersion:
    merged = {rule.id: rule for rule in active.rules}
    for rule in rules:
        merged[rule.id] = KnowledgeRule(
            id=rule.id,
            title=rule.title,
            rule_text=rule.rule_text,
            applies_when=rule.applies_when,
            sql_guidance=rule.sql_guidance,
        )
    return KnowledgeVersion(version=name, rules=list(merged.values()), notes=notes)


@dataclass
class AnalyzerTeam:
    failure_analyst: StructuredModel
    rule_writer: StructuredModel
    critic: StructuredModel
    guard: OverfitGuard
    guidance: GuidanceCheck | None = None  # live_team always sets it

    def run(
        self,
        failed: Sequence[FailedItem],
        active: KnowledgeVersion,
        candidate_name: str,
        *,
        extra_proposals: Sequence[ProposedRule] = (),
    ) -> AnalyzerReport:
        holdout = [f.item.id for f in failed if f.item.split is not Split.DEV]
        if holdout:
            raise ValueError(f"the analyzer team reads dev items only, got {holdout}")
        if planted("BUG_NAIVE_ANALYZER"):
            return self._naive(failed, active, candidate_name)
        diagnoses = _call(
            self.failure_analyst, Diagnoses, FAILURE_ANALYST, [f.for_analyst() for f in failed]
        ).diagnoses
        schema = {"schema": self.guidance.schema()} if self.guidance else {}
        proposed = _call(
            self.rule_writer,
            ProposedRules,
            RULE_WRITER,
            {
                "diagnoses": [d.model_dump() for d in diagnoses],
                "active_rules": [r.model_dump() for r in active.rules],
                **schema,
            },
        ).rules
        proposed = [*proposed, *extra_proposals]
        for_critic, screened = extension.screen(proposed, diagnoses, [f.item for f in failed])
        problems = self.guidance.check_all(for_critic) if self.guidance else {}
        reviews = (
            screened
            + _call(
                self.critic,
                CriticReviews,
                critic_prompt(),
                {
                    "proposed_rules": [r.model_dump() for r in for_critic],
                    "diagnoses": [d.model_dump() for d in diagnoses],
                    **({**schema, "sql_guidance_problems": problems} if schema else {}),
                },
            ).reviews
        )
        kept, ignored = apply_reviews(proposed, reviews)
        guidance = [self.guidance.check(rule) for rule in kept] if self.guidance else []
        runs = [r for r in kept if r.id not in {g.rule_id for g in guidance if not g.passed}]
        guard = [self.guard.check(rule) for rule in runs]
        accepted = [rule for rule, g in zip(runs, guard, strict=True) if g.passed]
        notes = f"Analyzer team draft from {len(failed)} failed dev items over {active.version}."
        return AnalyzerReport(
            candidate=candidate_version(active, accepted, candidate_name, notes),
            diagnoses=diagnoses,
            proposed=proposed,
            reviews=reviews,
            ignored_reviews=ignored,
            kept=kept,
            guidance=guidance,
            guard=guard,
            accepted=accepted,
        )

    def _naive(
        self, failed: Sequence[FailedItem], active: KnowledgeVersion, candidate_name: str
    ) -> AnalyzerReport:
        # planted: a rule per failed question, kept with no critic; the guard reports, never filters
        proposed = naive_rules(failed)
        notes = f"Naive analyzer draft from {len(failed)} failed dev items over {active.version}."
        return AnalyzerReport(
            candidate=candidate_version(active, proposed, candidate_name, notes),
            proposed=proposed,
            kept=list(proposed),
            guard=[self.guard.check(rule) for rule in proposed],
            accepted=list(proposed),
            planted_active=["BUG_NAIVE_ANALYZER"],
        )


def naive_rules(failed: Sequence[FailedItem]) -> list[ProposedRule]:
    """The naive analyzer's rules (planted), with no model call: one per failed dev item, quoting
    its question word for word, with the analyst's query that failed. It never reads a reference
    query, so a rule teaches nothing beyond the one question it quotes."""
    rules = []
    for failure in failed:
        question = failure.item.question
        sql = failure.answer.final_sql if failure.answer and failure.answer.final_sql else ""
        failed_query = f" The query that failed was: {sql}" if sql else ""
        rules.append(
            ProposedRule(
                id=f"answer-{failure.item.id}",
                title=f"Answer to: {question}",
                rule_text=f'When the question is "{question}", the last answer was wrong; answer '
                f"it differently.{failed_query}",
                applies_when=f'the question is exactly "{question}"',
                evidence_example_ids=[failure.item.id],
                expected_effect=f"the question {failure.item.id} passes next time",
            )
        )
    return rules


def chat_model(component: str, callbacks: Sequence[Any] = (), effort: str | None = None) -> Any:
    """The analyzer team's model (OPENAI_ANALYZER_MODEL): Responses API, reasoning effort and
    output-token cap from pack.yaml, no temperature, and the spend ledger on every call. A
    calibration step may name another reasoning effort to measure; class runs never do."""
    from langchain_openai import ChatOpenAI

    from datapilot.config import pack_config
    from datapilot.observability.spend import SpendCallback
    from datapilot.settings import get_settings

    settings, models = get_settings(), pack_config()["models"]
    model = settings.analyzer_model
    return ChatOpenAI(
        model=model,
        api_key=settings.openai_api_key,
        use_responses_api=models["use_responses_api"],
        reasoning={"effort": effort or models["analyzer_team"]["reasoning_effort"]},
        # sent to the Responses API as max_output_tokens
        max_tokens=int(models["analyzer_team"]["max_output_tokens"]),
        callbacks=[SpendCallback(component=f"analyzer_team.{component}", model=model), *callbacks],
    )


def live_team(
    items: Sequence[BenchmarkItem], callbacks: Sequence[Any] = (), effort: str | None = None
) -> AnalyzerTeam:
    def build(component: str) -> Any:
        return chat_model(component, callbacks, effort)

    return AnalyzerTeam(
        failure_analyst=build("failure_analyst"),
        rule_writer=build("rule_writer"),
        critic=build("critic"),
        guard=OverfitGuard.from_pack(items),
        guidance=GuidanceCheck.from_database(),
    )
