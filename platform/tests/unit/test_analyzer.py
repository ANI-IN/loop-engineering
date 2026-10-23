"""The analyzer team, the critic's limits, the overfit guard, and the naive analyzer."""

from __future__ import annotations

import json
import random

import pytest
from loop4_doubles import StructuredDouble, answered, experiment, item, warehouse_snapshot

from datapilot import settings as settings_module
from datapilot.config import pack_config
from datapilot.contracts import (
    BenchmarkItem,
    CriticDecision,
    CriticReview,
    Diagnosis,
    ItemResult,
    KnowledgeVersion,
    ProposedRule,
    Split,
)
from datapilot.loop4_hill_climbing.analyzer import (
    AnalyzerTeam,
    CriticReviews,
    Diagnoses,
    FailedItem,
    ProposedRules,
    apply_reviews,
    candidate_version,
    chat_model,
    live_team,
    naive_rules,
)
from datapilot.loop4_hill_climbing.gate import Regressions, decide
from datapilot.loop4_hill_climbing.overfit_guard import OverfitGuard, new_rule_flags, words
from datapilot.loop4_hill_climbing.pack_files import load_benchmark, load_knowledge
from datapilot.loop4_hill_climbing.sql_guidance import GuidanceCheck
from datapilot.observability.spend import SpendCallback

BENCHMARK = load_benchmark()
SPINE = next(i for i in BENCHMARK if i.id == "net-revenue-fiscal-2025")
GUARD = OverfitGuard.from_pack(BENCHMARK)


def rule(
    rule_id: str, text: str = "Revenue excludes cancelled orders.", sql: str = ""
) -> ProposedRule:
    return ProposedRule(
        id=rule_id,
        title=rule_id.replace("-", " "),
        rule_text=text,
        applies_when="a question asks for revenue or order counts",
        sql_guidance=sql,
        evidence_example_ids=["net-revenue-fiscal-2025"],
        expected_effect="revenue answers leave out cancelled orders",
    )


FISCAL = rule(
    "fiscal-year",
    "The fiscal year runs from February 1 to January 31 and is named by the year it ends in.",
    "order_ts AT TIME ZONE 'America/New_York' >= DATE '<year - 1>-02-01'",
)
CANCELLED = rule("cancelled-orders", sql="o.status <> 5")
QUOTING = rule("spine-answer", "When asked what was our net revenue in fiscal year 2025, use v2.")
COPYING = rule("copied", "Use this query.", SPINE.gold_sql or "")


def test_the_guard_passes_general_rules() -> None:
    assert GUARD.check(FISCAL).passed and GUARD.check(CANCELLED).passed


def test_the_guard_rejects_a_rule_quoting_a_question() -> None:
    result = GUARD.check(QUOTING)
    assert not result.passed and "net-revenue-fiscal-2025" in result.reasons[0]


def test_the_guard_rejects_a_rule_copying_gold_sql() -> None:
    result = GUARD.check(COPYING)
    assert not result.passed and result.reasons[-1].startswith("copies gold SQL")


def test_the_critic_keeps_narrows_drops_and_cannot_add() -> None:
    narrowed = rule("cancelled-orders", "Order counts exclude cancelled orders.")
    reviews = [
        CriticReview(rule_id="fiscal-year", decision=CriticDecision.KEEP, reason="general"),
        CriticReview(
            rule_id="cancelled-orders",
            decision=CriticDecision.NARROW,
            reason="scope",
            narrowed=narrowed.model_copy(update={"id": "renamed"}),
        ),
        CriticReview(rule_id="spine-answer", decision=CriticDecision.DROP, reason="specific"),
        CriticReview(rule_id="brand-new", decision=CriticDecision.KEEP, reason="added"),
    ]
    kept, ignored = apply_reviews([FISCAL, CANCELLED, QUOTING, rule("unreviewed")], reviews)
    assert [r.id for r in kept] == ["fiscal-year", "cancelled-orders"]
    assert kept[1].rule_text == "Order counts exclude cancelled orders."
    assert ignored == ["brand-new: the critic cannot add rules"]


def _failed() -> list[FailedItem]:
    result = ItemResult(item_id=SPINE.id, passed=False, reason="warehouse: row 1 differs")
    return [FailedItem(SPINE, answered("SELECT sum(total_cents) FROM warehouse.orders"), result)]


def _team() -> tuple[AnalyzerTeam, StructuredDouble, StructuredDouble, StructuredDouble]:
    analyst = StructuredDouble(
        {
            Diagnoses: [
                Diagnoses(
                    diagnoses=[
                        Diagnosis(
                            item_id=SPINE.id,
                            what_went_wrong="calendar year",
                            likely_cause="no fiscal rule",
                        )
                    ]
                )
            ]
        }
    )
    writer = StructuredDouble({ProposedRules: [ProposedRules(rules=[FISCAL, QUOTING, COPYING])]})
    critic = StructuredDouble(
        {
            CriticReviews: [
                CriticReviews(
                    reviews=[
                        CriticReview(rule_id=r.id, decision=CriticDecision.KEEP, reason="ok")
                        for r in (FISCAL, QUOTING, COPYING)
                    ]
                )
            ]
        }
    )
    return AnalyzerTeam(analyst, writer, critic, GUARD), analyst, writer, critic


def test_the_team_runs_analyst_writer_critic_then_the_guard() -> None:
    team, analyst, writer, critic = _team()
    report = team.run(_failed(), load_knowledge("v1"), "v2")
    assert [r.id for r in report.accepted] == ["fiscal-year"]
    assert [g.passed for g in report.guard] == [True, False, False]
    assert [r.id for r in report.candidate.rules] == ["money-in-cents", "fiscal-year"]
    assert report.candidate.version == "v2" and report.planted_active == []
    assert len(analyst.seen) == len(writer.seen) == len(critic.seen) == 1
    writer_input = writer.seen[0][1][1].content
    assert SPINE.question not in writer_input, "the rule writer never sees the questions"


def test_the_team_refuses_holdout_items() -> None:
    team, *_ = _team()
    holdout = item("h1", Split.HOLDOUT)
    failed = [FailedItem(holdout, None, ItemResult(item_id="h1", passed=False, reason="x"))]
    with pytest.raises(ValueError, match="dev items only"):
        team.run(failed, load_knowledge("v1"), "v2")


def test_the_naive_analyzer_skips_the_critic_and_the_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    """Decision 4 of session report 2 changed this behaviour: the naive analyzer makes no model
    call; it quotes each failed question, and the guard reports on every rule without filtering."""
    monkeypatch.setenv("BUG_NAIVE_ANALYZER", "1")
    team, analyst, writer, critic = _team()
    report = team.run(_failed(), load_knowledge("v1"), "v2-naive")
    assert [r.id for r in report.candidate.rules] == ["money-in-cents", f"answer-{SPINE.id}"]
    assert analyst.seen == [] and writer.seen == [] and critic.seen == []
    assert report.planted_active == ["BUG_NAIVE_ANALYZER"]
    assert report.accepted == report.proposed, "the guard's verdict is not applied"
    assert [g.passed for g in report.guard] == [False]
    assert SPINE.question in report.candidate.rules[1].applies_when


def _dev_failures(items: list[BenchmarkItem]) -> list[FailedItem]:
    wrong = "SELECT round(sum(total_cents) / 100.0, 2) FROM warehouse.orders"
    return [
        FailedItem(i, answered(wrong), ItemResult(item_id=i.id, passed=False, reason="differs"))
        for i in items
    ]


DEV = [i for i in BENCHMARK if i.split is Split.DEV]


def test_every_dev_question_is_long_enough_for_the_guard_to_catch_a_quote() -> None:
    """The guarantee below holds because a quoted dev question always has enough words."""
    shortest = min(len(words(i.question)) for i in DEV)
    assert shortest >= pack_config()["evaluation"]["overfit_question_words"]


@pytest.mark.parametrize("seed", range(12))
def test_every_naive_rule_fails_the_overfit_guard_for_any_failed_dev_items(seed: int) -> None:
    draw = random.Random(seed)
    chosen = DEV if seed == 0 else draw.sample(DEV, draw.randint(1, len(DEV)))
    rules = naive_rules(_dev_failures(chosen))
    assert len(rules) == len(chosen)
    for rule, dev_item in zip(rules, chosen, strict=True):
        result = GUARD.check(rule)
        assert not result.passed, rule.id
        assert result.reasons[0].startswith("quotes benchmark questions")
        assert dev_item.id in result.reasons[0]
        assert dev_item.gold_sql and dev_item.gold_sql not in rule.rule_text


def test_the_naive_analyzer_never_reads_a_reference_query() -> None:
    failure = _dev_failures([SPINE])[0]
    (rule,) = naive_rules([failure])
    text = " ".join([rule.title, rule.rule_text, rule.applies_when, rule.sql_guidance])
    assert "warehouse.customers" not in text and "harborpine" not in text
    assert failure.answer is not None and str(failure.answer.final_sql) in rule.rule_text


def test_a_naive_version_with_a_flat_holdout_is_blocked_by_the_gate() -> None:
    splits = {i.id: i.split for i in BENCHMARK}
    holdout = {i.id: i.id.startswith("net-revenue") for i in BENCHMARK if i.split is Split.HOLDOUT}
    active = experiment("v1", {**{i.id: False for i in DEV}, **holdout}, splits)
    naive = experiment("v2", {**{i.id: True for i in DEV}, **holdout}, splits)
    decision = decide(active, naive, Regressions(), approved_by="instructor")
    assert decision.verdict == "blocked" and not decision.ready_for_approval
    assert decision.sentence.endswith("so it is no better than v1.")


def _naive_version() -> tuple[KnowledgeVersion, KnowledgeVersion]:
    v1 = load_knowledge("v1")
    rules = naive_rules(_dev_failures(DEV))
    return v1, candidate_version(v1, rules, "v2", "naive")


def test_every_new_rule_of_a_naive_version_is_flagged_and_the_active_rules_are_not() -> None:
    v1, naive = _naive_version()
    flags = new_rule_flags(GUARD, naive, v1)
    assert flags == [f"answer-{i.id}" for i in DEV]
    assert "money-in-cents" not in flags


@pytest.mark.parametrize("holdout_passes", [0, 1, 15])
def test_a_naive_version_is_blocked_whatever_its_holdout_count(holdout_passes: int) -> None:
    """Even a holdout better than the active version's: the guard rejects its rules."""
    v1, naive = _naive_version()
    holdout_items = [i for i in BENCHMARK if i.split is Split.HOLDOUT]
    splits = {i.id: i.split for i in BENCHMARK}
    active = experiment("v1", {i.id: False for i in BENCHMARK}, splits)
    passes = {i.id: n < holdout_passes for n, i in enumerate(holdout_items)}
    candidate = experiment("v2", {**{i.id: True for i in DEV}, **passes}, splits)
    flags = new_rule_flags(GUARD, naive, v1)
    decision = decide(
        active, candidate, Regressions(), approved_by="instructor", overfit_flags=flags
    )
    assert decision.verdict == "blocked" and not decision.ready_for_approval
    assert decision.reasons[-1].startswith("fail: overfit guard on the new rules")
    assert decision.sentence.startswith(f"Blocked: v2 has {len(DEV)} rules the overfit guard")
    assert f"answer-{DEV[0].id}" in decision.sentence


def test_an_honest_candidate_with_guard_clean_rules_is_unchanged() -> None:
    v1 = load_knowledge("v1")
    honest = candidate_version(v1, [FISCAL, CANCELLED], "v2", "team")
    assert new_rule_flags(GUARD, honest, v1) == []
    splits = {"d1": Split.DEV, "h1": Split.HOLDOUT}
    active = experiment("v1", {"d1": True, "h1": False}, splits)
    candidate = experiment("v2", {"d1": True, "h1": True}, splits)
    with_flags = decide(active, candidate, Regressions(), approved_by="ani", overfit_flags=[])
    without = decide(active, candidate, Regressions(), approved_by="ani")
    assert with_flags.verdict == without.verdict == "promoted"
    assert with_flags.sentence == without.sentence
    assert with_flags.reasons[-1] == "pass: overfit guard on the new rules"


GOOD_GUIDANCE = "o.status <> 5 AND lower(c.email) NOT LIKE '%@harborpine.com'"
PLACEHOLDER = rule("eligible-orders", sql="status <> 5 AND <documented non-internal predicate>")
INVENTED = rule("internal-accounts", sql="customer_is_internal = false")


def _guided_team(
    reviews: list[CriticReview],
) -> tuple[AnalyzerTeam, StructuredDouble, StructuredDouble]:
    team, *_ = _team()
    writer = StructuredDouble(
        {ProposedRules: [ProposedRules(rules=[CANCELLED, PLACEHOLDER, INVENTED])]}
    )
    critic = StructuredDouble({CriticReviews: [CriticReviews(reviews=reviews)]})
    team.rule_writer, team.critic = writer, critic
    team.guidance = GuidanceCheck(warehouse_snapshot())
    return team, writer, critic


def test_guidance_that_does_not_run_goes_back_to_the_critic_with_its_problems() -> None:
    narrowed = rule("eligible-orders", sql=GOOD_GUIDANCE)
    team, _, critic = _guided_team(
        [
            CriticReview(rule_id="cancelled-orders", decision=CriticDecision.KEEP, reason="ok"),
            CriticReview(
                rule_id="eligible-orders",
                decision=CriticDecision.NARROW,
                reason="guidance from the reference SQL",
                narrowed=narrowed,
            ),
            CriticReview(rule_id="internal-accounts", decision=CriticDecision.KEEP, reason="ok"),
        ]
    )
    report = team.run(_failed(), load_knowledge("v1"), "v2")
    payload = json.loads(critic.seen[0][1][1].content)
    assert set(payload["sql_guidance_problems"]) == {"eligible-orders", "internal-accounts"}
    assert "email" in payload["schema"]["customers"]
    assert [r.id for r in report.accepted] == ["cancelled-orders", "eligible-orders"]
    assert report.accepted[1].sql_guidance == GOOD_GUIDANCE
    invented = "SQL guidance names a column that does not exist: customer_is_internal"
    assert report.guidance_rejections == {"internal-accounts": [invented]}
    assert [g.rule_id for g in report.guard] == ["cancelled-orders", "eligible-orders"]
    assert "internal-accounts" not in {r.id for r in report.candidate.rules}


def test_the_rule_writer_sees_the_schema_and_never_the_questions() -> None:
    team, writer, _ = _guided_team([])
    team.run(_failed(), load_knowledge("v1"), "v2")
    sent = writer.seen[0][1][1].content
    assert "order_ts" in json.loads(sent)["schema"]["orders"]
    assert SPINE.question not in sent


def test_the_analyzer_model_uses_the_responses_api_without_temperature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_MODEL", "gpt-6-luna")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-used")
    settings_module.get_settings.cache_clear()
    try:
        model = chat_model("critic")
    finally:
        settings_module.get_settings.cache_clear()
    assert model.use_responses_api is True
    assert model.reasoning == {"effort": "medium"}
    assert model.temperature is None
    assert any(isinstance(c, SpendCallback) for c in model.callbacks)
    assert model.callbacks[0].component == "analyzer_team.critic"


def test_the_live_team_checks_sql_guidance_against_the_catalog(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_MODEL", "gpt-6-luna")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-used")
    snapshot = GuidanceCheck(warehouse_snapshot())
    monkeypatch.setattr(GuidanceCheck, "from_database", classmethod(lambda cls: snapshot))
    settings_module.get_settings.cache_clear()
    try:
        team = live_team(BENCHMARK)
    finally:
        settings_module.get_settings.cache_clear()
    assert team.guidance is snapshot


def test_a_calibration_step_may_name_another_reasoning_effort(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_MODEL", "gpt-6-luna")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-used")
    settings_module.get_settings.cache_clear()
    try:
        model = chat_model("rule_writer", effort="high")
    finally:
        settings_module.get_settings.cache_clear()
    assert model.reasoning == {"effort": "high"} and model.temperature is None


def test_the_knowledge_versions_load() -> None:
    v1, overbroad = load_knowledge("v1"), load_knowledge("v2-overbroad")
    assert [r.id for r in v1.rules] == ["money-in-cents"]
    assert [r.id for r in overbroad.rules] == ["money-in-cents", "exclude-discounted-orders"]
    assert "discount" in overbroad.prompt_block()
