"""Two-candidate selection on the dev split only (zero tokens): the selection keys, the sentence
the Improve page shows, and the runner measuring each candidate on dev items alone."""

from __future__ import annotations

import contextlib
from typing import Any

import pytest
from loop4_doubles import answered, experiment, item

from datapilot.contracts import (
    AnswerEnvelope,
    BenchmarkItem,
    ItemResult,
    KnowledgeVersion,
    ProposedRule,
    Split,
)
from datapilot.loop4_hill_climbing import candidates
from datapilot.loop4_hill_climbing import runner as runner_module
from datapilot.loop4_hill_climbing.analyzer import AnalyzerReport
from datapilot.loop4_hill_climbing.candidates import CandidateRun, choose, dev_regressions
from datapilot.loop4_hill_climbing.measurement import Scheme
from datapilot.loop4_hill_climbing.overfit_guard import GuardResult
from datapilot.loop4_hill_climbing.runner import HillClimbingRunner

SPLITS = {"d1": Split.DEV, "d2": Split.DEV, "d3": Split.DEV, "h1": Split.HOLDOUT}
BASELINE = experiment("v1", {"d1": True, "d2": False, "d3": False, "h1": False}, SPLITS)


def _rule(rule_id: str) -> ProposedRule:
    return ProposedRule(
        id=rule_id, title=rule_id, rule_text="x", applies_when="y", expected_effect="z"
    )


def _report(name: str, rules: int) -> AnalyzerReport:
    accepted = [_rule(f"rule-{n}") for n in range(rules)]
    return AnalyzerReport(
        candidate=KnowledgeVersion(version=name),
        accepted=accepted,
        guard=[GuardResult(r.id, True, []) for r in accepted],
    )


def _candidate(label: str, dev: dict[str, bool], rules: int) -> CandidateRun:
    measured = experiment(f"v2-candidate-{label.lower()}", dev, {k: SPLITS[k] for k in dev})
    regressions = dev_regressions(BASELINE, measured)
    return CandidateRun(
        label, measured.knowledge_version, _report(label, rules), measured, regressions
    )


def test_the_pack_asks_for_two_candidates() -> None:
    assert candidates.count() == 2


def test_a_dev_regression_is_an_item_the_baseline_passed() -> None:
    measured = experiment("v2", {"d1": False, "d2": True, "d3": False}, SPLITS)
    assert dev_regressions(BASELINE, measured) == ["d1"]


def test_fewer_dev_regressions_wins_over_more_dev_passes() -> None:
    a = _candidate("A", {"d1": False, "d2": True, "d3": True}, rules=3)
    b = _candidate("B", {"d1": True, "d2": True, "d3": False}, rules=3)
    assert (len(a.regressions), a.dev_passes, b.dev_passes) == (1, 2, 2)
    assert choose([a, b]) is b


def test_more_dev_passes_then_fewer_rules_then_the_first() -> None:
    few = _candidate("A", {"d1": True, "d2": False, "d3": False}, rules=1)
    more = _candidate("B", {"d1": True, "d2": True, "d3": False}, rules=5)
    assert choose([few, more]) is more
    small = _candidate("A", {"d1": True, "d2": True, "d3": False}, rules=4)
    large = _candidate("B", {"d1": True, "d2": True, "d3": False}, rules=6)
    assert choose([large, small]) is small
    twin = _candidate("B", {"d1": True, "d2": True, "d3": False}, rules=4)
    assert choose([small, twin]) is small


def test_the_sentence_names_each_candidate_and_the_choice() -> None:
    a = _candidate("A", {"d1": True, "d2": True, "d3": False}, rules=7)
    b = _candidate("B", {"d1": False, "d2": True, "d3": False}, rules=1)
    assert candidates.sentence([a, b], a, naive=False) == (
        "Candidate A: 2 of 3 dev, 0 regressions, 7 rules; "
        "Candidate B: 1 of 3 dev, 1 regression, 1 rule; chosen: A"
    )


def test_the_naive_sentence_counts_the_rules_the_guard_flags() -> None:
    report = _report("v2", rules=3)
    report.guard = [
        GuardResult(r.id, False, ["quotes benchmark questions"]) for r in report.accepted
    ]
    alone = CandidateRun("A", "v2", report)
    assert candidates.sentence([alone], alone, naive=True) == (
        "Naive analyzer: 3 rules, no critic; the overfit guard flags 3 of 3, not applied."
    )


class _Team:
    def __init__(self) -> None:
        self.names: list[str] = []

    def run(self, failed: Any, active: KnowledgeVersion, name: str) -> AnalyzerReport:
        self.names.append(name)
        return _report(name, rules=len(self.names))


class _Evaluator:
    def evaluate(self, benchmark_item: BenchmarkItem, answer: AnswerEnvelope) -> ItemResult:
        return ItemResult(item_id=benchmark_item.id, passed=True, reason="scripted")


def test_each_candidate_runs_on_the_dev_split_only_under_its_own_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked: list[tuple[str, str]] = []
    saved: list[str] = []

    def target(question: str, version: str) -> AnswerEnvelope:
        asked.append((question, version))
        return answered("SELECT 1")

    monkeypatch.setattr(runner_module.db, "connect", lambda role: contextlib.nullcontext(_Conn()))
    monkeypatch.setattr(
        candidates, "save_selection_draft", lambda conn, version: saved.append(version.version)
    )
    items = [item("d1"), item("d2"), item("d3"), item("h1", Split.HOLDOUT)]
    # The runner now reads the kill switch before each run (review round 1): released here.
    hill = HillClimbingRunner(
        items,
        target,
        _Evaluator(),  # type: ignore[arg-type]
        Scheme(),
        2,
        kill_switch_engaged=lambda: False,
    )
    team = _Team()
    runs = hill.measured_candidates(
        team,
        [],
        KnowledgeVersion(version="v1"),
        "v2",
        BASELINE,
        BASELINE.session_id,  # type: ignore[arg-type]
    )
    assert team.names == saved == ["v2-candidate-a", "v2-candidate-b"]
    assert [r.label for r in runs] == ["A", "B"]
    assert {q for q, _ in asked} == {"Question d1?", "Question d2?", "Question d3?"}
    assert "Question h1?" not in {q for q, _ in asked}, "the holdout never takes part"
    assert all(r.dev is not None and r.dev.splits == [Split.DEV] for r in runs)
    assert choose(runs).label == "A", "a tie on dev goes to fewer rules"


class _Conn:
    def commit(self) -> None:
        return None


def test_the_runner_gives_the_gate_the_flags_of_the_candidates_new_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datapilot.loop4_hill_climbing import versions
    from datapilot.loop4_hill_climbing.analyzer import FailedItem, candidate_version, naive_rules
    from datapilot.loop4_hill_climbing.pack_files import load_benchmark, load_knowledge

    items = load_benchmark()
    dev = next(i for i in items if i.split is Split.DEV)
    failed = [FailedItem(dev, None, ItemResult(item_id=dev.id, passed=False, reason="x"))]
    v1 = load_knowledge("v1")
    stored = {
        "v1": v1,
        "v2-overbroad": load_knowledge("v2-overbroad"),
        "v2": candidate_version(v1, naive_rules(failed), "v2", "naive"),
    }
    monkeypatch.setattr(versions, "get", lambda conn, name: stored[name])
    target = lambda q, v: answered("SELECT 1")  # noqa: E731
    hill = HillClimbingRunner(items, target, _Evaluator(), Scheme(), 1)  # type: ignore[arg-type]
    assert hill.overfit_flags(None, "v2", "v1") == [f"answer-{dev.id}"]  # type: ignore[arg-type]
    assert hill.overfit_flags(None, "v2-overbroad", "v1") == [], "the over-broad rule is general"  # type: ignore[arg-type]
