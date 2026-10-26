"""The gate itself, driven with a request's planted flags on (zero tokens, no database): a planted
evaluator's experiment never reaches a decision, the naive analyzer's candidate is blocked and
never activated, and the naive analyzer's flag never brands another writer's candidate.

Session 6 review, round 2 (tests): refuse_planted_gate and blocked_if_planted were tested only as
functions, so removing either call from HillClimbingRunner.gate left every test green; and the
code review found the naive analyzer's experiment could block, and retire, the analyzer team's
approved candidate. The database and the gate's statistics here are test doubles."""

from __future__ import annotations

import contextlib
from typing import Any

import pytest
from loop4_doubles import answered, experiment, item

from datapilot import planted
from datapilot.contracts import AnswerEnvelope, ItemResult, Split
from datapilot.loop4_hill_climbing import runner as runner_module
from datapilot.loop4_hill_climbing import store, versions
from datapilot.loop4_hill_climbing.gate import GateDecision, Regressions
from datapilot.loop4_hill_climbing.measurement import Scheme
from datapilot.loop4_hill_climbing.runner import HillClimbingRunner, RequestFailed

pytestmark = pytest.mark.security

ITEMS = [item("d1"), item("h1", Split.HOLDOUT)]
SPLITS = {"d1": Split.DEV, "h1": Split.HOLDOUT}


class _Evaluator:
    def evaluate(self, benchmark_item: Any, answer: AnswerEnvelope) -> ItemResult:
        return ItemResult(item_id=benchmark_item.id, passed=True, reason="scripted")


class _Conn:
    def commit(self) -> None:
        return None


def _promoted() -> GateDecision:
    return GateDecision(
        verdict="promoted",
        ready_for_approval=True,
        reasons=["pass: holdout passes 1 of 1 against 0 for v1"],
        sentence="Promoted: v2 passes.",
        candidate_version="v2",
        active_version="v1",
        candidate_holdout_passes=1,
        active_holdout_passes=0,
        holdout_total=1,
        regressions=Regressions(),
        approved_by="instructor",
    )


@pytest.fixture
def gate(monkeypatch: pytest.MonkeyPatch) -> Any:
    """runner.gate on the v2 candidate, everything but its planted-flag wiring stood in for; the
    returned record says what reached the database."""
    seen: dict[str, Any] = {"baseline": 0, "saved": [], "retired": [], "activated": []}
    writer = {"v2": "naive analyzer"}
    active = experiment("v1", {"d1": True, "h1": False}, SPLITS)
    candidate = experiment("v2", {"d1": True, "h1": True}, SPLITS)

    def baseline_for(conn: Any, name: str) -> Any:
        seen["baseline"] += 1
        return active

    monkeypatch.setattr(runner_module.db, "connect", lambda role: contextlib.nullcontext(_Conn()))
    monkeypatch.setattr(versions, "created_by", lambda conn, name: writer[name])
    monkeypatch.setattr(store, "baseline_for", baseline_for)
    monkeypatch.setattr(store, "record_gate_baseline", lambda conn, c, b: None)
    monkeypatch.setattr(store, "OpsStepSink", lambda conn: None)
    monkeypatch.setattr(runner_module, "find_regressions", lambda *a, **k: Regressions())
    monkeypatch.setattr(runner_module, "decide", lambda *a, **k: _promoted())
    monkeypatch.setattr(
        versions,
        "status_of",
        lambda conn, name: {"status": "approved", "approved_by": "instructor"},
    )
    monkeypatch.setattr(HillClimbingRunner, "overfit_flags", lambda self, conn, name, a: [])
    monkeypatch.setattr(store, "save_decision", lambda conn, d: seen["saved"].append(d))
    monkeypatch.setattr(versions, "retire_blocked", lambda conn, n: seen["retired"].append(n))
    monkeypatch.setattr(
        HillClimbingRunner, "_activate", lambda self, conn, name, *a: seen["activated"].append(name)
    )
    hill = HillClimbingRunner(
        ITEMS,
        lambda q, v: answered("SELECT 1"),
        _Evaluator(),  # type: ignore[arg-type]
        Scheme(),
        1,
        kill_switch_engaged=lambda: False,
    )

    def run(flags: list[str], written_by: str = "naive analyzer") -> dict[str, Any]:
        writer["v2"] = written_by
        with planted.for_this_run(flags):
            seen["decision"] = hill.gate(candidate, "v1", runner=None)  # type: ignore[arg-type]
        return seen

    return run


def test_without_flags_the_stood_in_gate_promotes(gate) -> None:
    seen = gate([], written_by="analyzer team")
    assert seen["decision"].verdict == "promoted" and seen["activated"] == ["v2"]


def test_a_planted_evaluator_never_reaches_the_gates_baseline(gate, monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(store, "baseline_for", lambda conn, name: calls.append(name))
    with pytest.raises(RequestFailed, match="BUG_SQL_TEXT_EVAL"):
        gate(["BUG_SQL_TEXT_EVAL"], written_by="analyzer team")
    assert calls == [], "the gate stopped before it read the baseline"


def test_the_naive_analyzers_candidate_is_blocked_and_never_activated(gate) -> None:
    seen = gate([runner_module.NAIVE_ANALYZER])
    decision = seen["decision"]
    assert decision.verdict == "blocked" and not decision.ready_for_approval
    assert decision.reasons[-1] == "fail: written by the naive analyzer (BUG_NAIVE_ANALYZER)"
    assert [d.verdict for d in seen["saved"]] == ["blocked"] and seen["activated"] == []


def test_the_naive_analyzers_flag_never_decides_another_writers_candidate(gate) -> None:
    """A failed analyzer step left the analyzer team's approved candidate the newest: the naive
    analyzer's experiment ran on it, then blocked and retired it."""
    with pytest.raises(RequestFailed, match="runs only on a version the naive analyzer wrote"):
        gate([runner_module.NAIVE_ANALYZER], written_by="analyzer team")


def test_nothing_is_saved_or_retired_for_another_writers_candidate(gate, monkeypatch) -> None:
    saved: list[Any] = []
    monkeypatch.setattr(store, "save_decision", lambda conn, d: saved.append(d))
    with pytest.raises(RequestFailed):
        gate([runner_module.NAIVE_ANALYZER], written_by="analyzer team")
    assert saved == []


def _candidate_target(hill: HillClimbingRunner) -> str:
    return hill._version_for(_Conn(), {"target": "candidate"}, "v1")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("written_by", "runs"), [("naive analyzer", True), ("analyzer team", False)]
)
def test_the_naive_analyzers_candidate_experiment_runs_only_on_its_own_candidate(
    monkeypatch: pytest.MonkeyPatch, written_by: str, runs: bool
) -> None:
    """The candidate experiment the demo and the console button queue after the analyzer takes
    the newest candidate: with the naive analyzer's flag on, only one the naive analyzer wrote."""
    monkeypatch.setattr(versions, "latest_candidate", lambda conn: "v7")
    monkeypatch.setattr(versions, "created_by", lambda conn, name: written_by)
    hill = HillClimbingRunner(
        ITEMS,
        lambda q, v: answered("SELECT 1"),
        _Evaluator(),  # type: ignore[arg-type]
        Scheme(),
        1,
        kill_switch_engaged=lambda: False,
    )
    with planted.for_this_run([runner_module.NAIVE_ANALYZER]):
        if runs:
            assert _candidate_target(hill) == "v7"
        else:
            with pytest.raises(RequestFailed, match=f"written by {written_by}: nothing was run"):
                _candidate_target(hill)
    assert _candidate_target(hill) == "v7"  # without the flag, whoever wrote it, as before
