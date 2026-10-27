"""The experiment runner, the measurement scheme, regressions, and the promotion gate."""

from __future__ import annotations

import threading
import time
from uuid import uuid4

import pytest
from loop4_doubles import SESSION, ScriptedEvaluator, answered, experiment, item

from datapilot.contracts import Split
from datapilot.loop4_hill_climbing.experiment import ExperimentRunner
from datapilot.loop4_hill_climbing.gate import (
    DevConfirmation,
    Regressions,
    decide,
    find_regressions,
)
from datapilot.loop4_hill_climbing.measurement import Scheme

SCHEME = Scheme(holdout_repeats=3, holdout_pass_threshold=2, dev_regression_reruns=2)


def test_the_scheme_comes_from_the_pack() -> None:
    assert Scheme.from_pack() == SCHEME


def test_holdout_passes_on_two_of_three_and_dev_on_its_one_run() -> None:
    assert SCHEME.passes(Split.HOLDOUT, [True, False, True])
    assert not SCHEME.passes(Split.HOLDOUT, [True, False, False])
    assert SCHEME.passes(Split.DEV, [True]) and not SCHEME.passes(Split.DEV, [False])


def test_a_dev_regression_needs_the_candidate_to_fail_and_the_active_version_to_pass() -> None:
    # Decision 5 on session report 2 changed this rule: the active version is re-run too, and each
    # version must repeat its experiment result on at least 2 of its 2 re-runs.
    assert SCHEME.dev_regression_confirmed([False, False], [True, True])
    assert not SCHEME.dev_regression_confirmed([False, True], [True, True])
    assert not SCHEME.dev_regression_confirmed([False, False], [True, False])
    assert not SCHEME.dev_regression_confirmed([False, False], [False, False])


def test_a_dev_regression_cannot_be_confirmed_without_the_active_re_runs() -> None:
    with pytest.raises(ValueError, match="active version"):
        SCHEME.regression_confirmed(Split.DEV, [False, False])
    assert SCHEME.regression_reruns(Split.DEV) == 2
    assert SCHEME.active_reruns(Split.DEV) == 2 and SCHEME.active_reruns(Split.HOLDOUT) == 0


def _runner(outcomes: dict[str, list[bool]], **kwargs) -> ExperimentRunner:
    calls: list[tuple[str, str]] = []

    def target(question: str, version: str):
        calls.append((question, version))
        return answered("SELECT 1")

    runner = ExperimentRunner(
        target=target, evaluator=ScriptedEvaluator(outcomes), scheme=SCHEME, **kwargs
    )
    runner.calls = calls  # type: ignore[attr-defined]
    return runner


def test_holdout_runs_three_times_and_dev_once() -> None:
    items = [item("d1"), item("h1", Split.HOLDOUT)]
    runner = _runner({"d1": [True], "h1": [True, False, True]})
    result = runner.run(items, "v1", session_id=SESSION)
    assert len(runner.calls) == 4 and {v for _, v in runner.calls} == {"v1"}
    assert result.results["h1"].run_passes == [True, False, True] and result.passed("h1")
    assert result.passes(Split.HOLDOUT) == 1 and result.total(Split.DEV) == 1


def test_run_passes_are_in_repetition_order_whatever_finishes_first() -> None:
    from datapilot.contracts import ItemResult
    from datapilot.loop4_hill_climbing.experiment import current_run

    def target(question: str, version: str):
        context = current_run.get()
        assert context is not None
        time.sleep(0.05 if context.repetition == 1 else 0.0)  # repetition 1 would finish last
        return answered("SELECT 1")

    class ByRepetition:
        """Passes only repetition 1, so an order mix-up shows in run_passes."""

        def evaluate(self, item, answer):
            context = current_run.get()
            assert context is not None
            return ItemResult(item_id=item.id, passed=context.repetition == 1, reason="")

    items = [item("h1", Split.HOLDOUT), item("h2", Split.HOLDOUT)]
    result = ExperimentRunner(target, ByRepetition(), SCHEME, concurrency=6).run(
        items, "v1", session_id=SESSION
    )
    assert result.results["h1"].run_passes == [True, False, False]
    assert result.results["h2"].run_passes == [True, False, False]


def test_the_split_filter_runs_only_the_chosen_split() -> None:
    items = [item("d1"), item("h1", Split.HOLDOUT)]
    result = _runner({"h1": [False] * 3}).run(
        items, "v1", session_id=SESSION, splits=[Split.HOLDOUT]
    )
    assert list(result.results) == ["h1"]


def test_runs_go_concurrently() -> None:
    active, peak, lock = 0, 0, threading.Lock()

    def target(question: str, version: str):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.05)
        with lock:
            active -= 1
        return answered("SELECT 1")

    items = [item(f"d{i}") for i in range(8)]
    evaluator = ScriptedEvaluator({f"d{i}": [True] for i in range(8)})
    ExperimentRunner(target, evaluator, SCHEME, concurrency=4).run(items, "v1", session_id=SESSION)
    assert peak == 4


def test_a_target_error_fails_its_item_only() -> None:
    def target(question: str, version: str):
        raise TimeoutError("model timed out")

    result = ExperimentRunner(target, ScriptedEvaluator({}), SCHEME).run(
        [item("d1")], "v1", session_id=SESSION
    )
    assert not result.passed("d1") and "TimeoutError" in result.results["d1"].reason


class _Tracer:
    def __init__(self, fail: bool = False) -> None:
        self.records, self.fail = [], fail

    def trace(self, record, *, experiment_id):
        if self.fail:
            raise ConnectionError("tracing service down")
        self.records.append(record)
        return f"run-{len(self.records)}"


def test_results_are_local_first_and_a_tracer_failure_changes_nothing() -> None:
    items = [item("d1"), item("h1", Split.HOLDOUT)]
    tracer = _Tracer()
    # every run traced here: since 23 October 2026 the pack's rate traces a sample of experiment
    # runs (test_experiment_trace_sampling.py pins that)
    traced = _runner({"d1": [True], "h1": [True] * 3}, tracer=tracer, trace_sample_rate=1).run(
        items, "v1", session_id=SESSION
    )
    assert len(tracer.records) == 4 and len(traced.trace_links["h1"]) == 3
    broken = _runner(
        {"d1": [True], "h1": [True] * 3}, tracer=_Tracer(fail=True), trace_sample_rate=1
    ).run(items, "v1", session_id=SESSION)
    assert broken.passes(Split.HOLDOUT) == 1 and len(broken.tracer_errors) == 4


SPLITS = {"d1": Split.DEV, "d2": Split.DEV, "h1": Split.HOLDOUT, "h2": Split.HOLDOUT}
ITEMS = [item("d1"), item("d2"), item("h1", Split.HOLDOUT), item("h2", Split.HOLDOUT)]


def _dev_pair(candidate_dev: dict[str, bool]):
    active = experiment("v1", {"d1": True, "d2": True, "h1": True, "h2": False}, SPLITS)
    candidate = experiment("v2", {**candidate_dev, "h1": True, "h2": True}, SPLITS)
    return active, candidate


def test_a_dev_failure_that_passes_on_rerun_is_not_a_regression() -> None:
    # Decision 5 on session report 2: d2 failing 1 of its 2 candidate re-runs no longer confirms.
    active, candidate = _dev_pair({"d1": False, "d2": False})
    reruns = {"d1": [True, True], "d2": [False, True]}
    found = find_regressions(
        ITEMS,
        active,
        candidate,
        lambda i, n: reruns[i.id][:n],
        SCHEME,
        active_rerun=lambda i, n: [True] * n,
    )
    assert found.dev == [] and found.not_confirmed == ["d1", "d2"] and found.holdout == []


def test_a_dev_item_unstable_under_both_versions_is_not_a_regression() -> None:
    """The live check's case: active-products-by-category passed under the active version in the
    baseline, failed under the candidate and its re-runs, and fails under the active version too."""
    active, candidate = _dev_pair({"d1": False, "d2": True})
    asked: list[tuple[str, str, int]] = []

    def candidate_rerun(i, n):
        asked.append(("candidate", i.id, n))
        return [False] * n

    def active_rerun(i, n):
        asked.append(("active", i.id, n))
        return [False, True][:n]

    found = find_regressions(
        ITEMS, active, candidate, candidate_rerun, SCHEME, active_rerun=active_rerun
    )
    assert asked == [("candidate", "d1", 2), ("active", "d1", 2)]
    assert found.dev == [] and found.not_confirmed == ["d1"]
    recorded = candidate.confirmations["d1"]
    assert recorded.reruns == [False, False] and recorded.active_reruns == [False, True]
    assert recorded.confirmed is False


def test_a_dev_regression_counts_when_the_candidate_fails_and_the_active_version_passes() -> None:
    active, candidate = _dev_pair({"d1": False, "d2": True})
    found = find_regressions(
        ITEMS,
        active,
        candidate,
        lambda i, n: [False] * n,
        SCHEME,
        active_rerun=lambda i, n: [True] * n,
    )
    assert found.dev == ["d1"] and found.total == 1
    assert candidate.confirmations["d1"].active_reruns == [True, True]


def test_a_dev_regression_without_an_active_rerun_is_refused() -> None:
    active, candidate = _dev_pair({"d1": False, "d2": True})
    with pytest.raises(ValueError, match="active version"):
        find_regressions(ITEMS, active, candidate, lambda i, n: [False] * n, SCHEME)


def test_a_holdout_confirmation_re_runs_only_the_candidate() -> None:
    active = experiment("v1", {"d1": True, "d2": True, "h1": True, "h2": True}, SPLITS)
    candidate = experiment("v2", {"d1": True, "d2": True, "h1": False, "h2": True}, SPLITS)

    def never(i, n):
        raise AssertionError("the active version is not re-run for a holdout item")

    found = find_regressions(
        ITEMS, active, candidate, lambda i, n: [False] * n, SCHEME, active_rerun=never
    )
    assert found.holdout == ["h1"]
    assert not isinstance(candidate.confirmations["h1"], DevConfirmation)


class _Steps:
    def __init__(self) -> None:
        self.seen: list[tuple[str, list[str]]] = []

    def step(self, experiment_id, confirmation) -> None:
        self.seen.append((confirmation.item_id, list(confirmation.steps)))


def _holdout_pair():
    active = experiment("v1", {"d1": True, "d2": True, "h1": True, "h2": True}, SPLITS)
    candidate = experiment("v2", {"d1": True, "d2": True, "h1": False, "h2": False}, SPLITS)
    return active, candidate


def test_an_apparent_holdout_regression_is_rerun_three_times() -> None:
    active, candidate = _holdout_pair()
    asked: list[tuple[str, int]] = []
    reruns = {"h1": [False, True, False], "h2": [True, False, True]}

    def rerun(i, n):
        asked.append((i.id, n))
        return reruns[i.id]

    found = find_regressions(ITEMS, active, candidate, rerun, SCHEME)
    assert asked == [("h1", 3), ("h2", 3)]
    assert found.holdout == ["h1"] and found.not_confirmed == ["h2"] and found.total == 1


def test_each_confirmation_is_recorded_and_shown_as_steps() -> None:
    active, candidate = _holdout_pair()
    sink = _Steps()
    reruns = {"h1": [False, False, True], "h2": [True, True, False]}
    find_regressions(ITEMS, active, candidate, lambda i, n: reruns[i.id], SCHEME, sink)
    assert sink.seen[:2] == [
        ("h1", ["Apparent regression: confirming with 3 more runs"]),
        (
            "h1",
            [
                "Apparent regression: confirming with 3 more runs",
                "Confirmed regression: failed 2 of 3 more runs",
            ],
        ),
    ]
    assert sink.seen[3][1][-1] == "Not a regression: passed 2 of 3 more runs"
    recorded = candidate.confirmations["h1"]
    assert recorded.reruns == [False, False, True] and recorded.confirmed is True
    assert candidate.confirmations["h2"].confirmed is False


def test_a_dev_confirmation_says_two_more_runs_of_each_version() -> None:
    active = experiment("v1", {"d1": True, "d2": True, "h1": True, "h2": True}, SPLITS)
    candidate = experiment("v2", {"d1": False, "d2": True, "h1": True, "h2": True}, SPLITS)
    find_regressions(
        ITEMS,
        active,
        candidate,
        lambda i, n: [False] * n,
        SCHEME,
        active_rerun=lambda i, n: [True] * n,
    )
    assert candidate.confirmations["d1"].steps == [
        "Apparent regression: confirming with 2 more runs of each version",
        "Confirmed regression: the candidate failed 2 of 2 more runs, the active version passed "
        "2 of 2",
    ]


def _pair(active_h: dict[str, bool], candidate_h: dict[str, bool]):
    base = {"d1": True, "d2": True}
    return experiment("v1", base | active_h, SPLITS), experiment("v2", base | candidate_h, SPLITS)


def test_the_gate_promotes_a_better_clean_approved_candidate() -> None:
    active, candidate = _pair({"h1": False, "h2": False}, {"h1": True, "h2": True})
    decision = decide(active, candidate, Regressions(), approved_by="instructor")
    assert decision.verdict == "promoted"
    assert decision.sentence == (
        "Promoted: v2 passes 2 of 2 holdout items against 0, with no regressions, approved by "
        "instructor."
    )


def test_the_gate_waits_for_human_approval() -> None:
    active, candidate = _pair({"h1": False, "h2": False}, {"h1": True, "h2": True})
    decision = decide(active, candidate, Regressions(), approved_by=None)
    assert decision.verdict == "blocked" and decision.ready_for_approval
    assert decision.sentence.startswith("Ready for human approval")


@pytest.mark.parametrize("name", ["", "  ", "console", "Console"])
def test_the_gate_refuses_an_empty_approver_or_console(name: str) -> None:
    """Owner's decision, 27 October 2026: the approval needs a person's name; "console", which the
    console recorded for every approval before, approves nothing."""
    active, candidate = _pair({"h1": False, "h2": False}, {"h1": True, "h2": True})
    decision = decide(active, candidate, Regressions(), approved_by=name)
    assert decision.verdict == "blocked" and decision.ready_for_approval
    assert decision.approved_by is None
    assert "fail: human approval needs a person's name" in decision.reasons


def test_the_gate_blocks_regressions_even_with_more_holdout_passes() -> None:
    active, candidate = _pair({"h1": False, "h2": False}, {"h1": True, "h2": True})
    decision = decide(active, candidate, Regressions(dev=["d1"]), approved_by="instructor")
    assert decision.verdict == "blocked" and not decision.ready_for_approval
    assert decision.sentence == "Blocked: v2 has 1 regression on items that passed under v1."
    assert "fail: dev regressions 1 (d1)" in decision.reasons


def test_the_gate_blocks_a_candidate_that_is_no_better() -> None:
    active, candidate = _pair({"h1": True, "h2": False}, {"h1": True, "h2": False})
    decision = decide(active, candidate, Regressions(), approved_by="instructor")
    assert decision.verdict == "blocked"
    assert decision.sentence == (
        "Blocked: v2 passes 1 of 2 holdout items against 1, so it is no better than v1."
    )


def test_the_gate_refuses_experiments_from_different_sessions() -> None:
    active = experiment("v1", {"h1": True}, {"h1": Split.HOLDOUT}, session=uuid4())
    candidate = experiment("v2", {"h1": True}, {"h1": Split.HOLDOUT})
    with pytest.raises(ValueError, match="same live session"):
        decide(active, candidate, Regressions(), approved_by="instructor")
