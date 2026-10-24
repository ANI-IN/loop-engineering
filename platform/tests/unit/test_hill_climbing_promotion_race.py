"""The background promotion never decides a candidate whose gate is still confirming (zero tokens,
no database). Review round 2: the runner's two threads raced. The tick thread committed the
candidate experiment, then ran the gate's confirming re-runs for minutes; meanwhile the watcher
found the version approved and the experiment finished, counted an apparent regression whose
re-runs had not finished as no regression, and could promote what the gate would block."""

from __future__ import annotations

import contextlib
import threading
import uuid
from typing import Any

import pytest
from loop4_doubles import answered, experiment, item

from datapilot.contracts import AnswerEnvelope, ItemResult, Split
from datapilot.loop4_hill_climbing import runner as runner_module
from datapilot.loop4_hill_climbing import store, versions
from datapilot.loop4_hill_climbing.experiment import Confirmation
from datapilot.loop4_hill_climbing.gate import GateDecision, Regressions
from datapilot.loop4_hill_climbing.measurement import Scheme
from datapilot.loop4_hill_climbing.runner import HillClimbingRunner, gate_finished

ITEMS = [item("d1"), *(item(f"h{n}", Split.HOLDOUT) for n in (1, 2, 3))]
SPLITS = {"d1": Split.DEV, "h1": Split.HOLDOUT, "h2": Split.HOLDOUT, "h3": Split.HOLDOUT}


class _Evaluator:
    def evaluate(self, benchmark_item: Any, answer: AnswerEnvelope) -> ItemResult:
        return ItemResult(item_id=benchmark_item.id, passed=True, reason="scripted")


def _hill() -> HillClimbingRunner:
    return HillClimbingRunner(
        ITEMS,
        lambda q, v: answered("SELECT 1"),
        _Evaluator(),  # type: ignore[arg-type]
        Scheme(),
        1,
        kill_switch_engaged=lambda: False,
    )


def _pair(confirmed: bool | None, *, recorded: bool = True) -> tuple[Any, Any]:
    """The active version's experiment and the candidate's: the candidate passes one more holdout
    item and fails h1, which passed under the active version (an apparent regression)."""
    active = experiment("v1", {"d1": True, "h1": True, "h2": False, "h3": False}, SPLITS)
    candidate = experiment("v2", {"d1": True, "h1": False, "h2": True, "h3": True}, SPLITS)
    candidate.session_id = active.session_id
    if recorded:
        candidate.confirmations["h1"] = Confirmation("h1", Split.HOLDOUT, confirmed=confirmed)
    return active, candidate


@pytest.mark.parametrize(
    ("confirmed", "recorded", "finished"),
    [(None, False, False), (None, True, False), (True, True, True), (False, True, True)],
)
def test_a_gate_is_finished_only_once_every_apparent_regression_is_confirmed_or_cleared(
    confirmed: bool | None, recorded: bool, finished: bool
) -> None:
    active, candidate = _pair(confirmed, recorded=recorded)
    assert gate_finished(active, candidate) is finished


RETIRED: list[str] = []


@pytest.fixture
def decisions(monkeypatch: pytest.MonkeyPatch) -> list[GateDecision]:
    saved: list[GateDecision] = []
    RETIRED.clear()
    monkeypatch.setattr(versions, "active_name", lambda conn: "v1")
    monkeypatch.setattr(store, "save_decision", lambda conn, decision: saved.append(decision))
    monkeypatch.setattr(versions, "retire_blocked", lambda conn, name: RETIRED.append(name))
    monkeypatch.setattr(HillClimbingRunner, "overfit_flags", lambda self, conn, name, active: [])
    monkeypatch.setattr(HillClimbingRunner, "_activate", lambda self, *args: None)
    return saved


def test_the_background_promotion_waits_while_the_gate_still_confirms(
    monkeypatch, decisions
) -> None:
    active, candidate = _pair(None)  # the gate's re-runs for h1 have not finished
    found = {"v1": active, "v2": candidate}
    monkeypatch.setattr(store, "baseline_for", lambda conn, name: found[name])
    assert _hill()._decide_approved(object(), "v2", "instructor") is None  # type: ignore[arg-type]
    assert decisions == [], "nothing is decided before the gate has confirmed every regression"


def test_the_background_promotion_decides_once_the_gate_has_finished(
    monkeypatch, decisions
) -> None:
    active, candidate = _pair(False)  # h1 was cleared by its re-runs
    found = {"v1": active, "v2": candidate}
    monkeypatch.setattr(store, "baseline_for", lambda conn, name: found[name])
    decision = _hill()._decide_approved(object(), "v2", "instructor")  # type: ignore[arg-type]
    assert decision is not None and decision.verdict == "promoted"
    assert [d.candidate_version for d in decisions] == ["v2"]
    assert RETIRED == []


def test_an_approved_version_the_gate_blocks_is_retired_not_left_approved(
    monkeypatch, decisions
) -> None:
    """Review round 2: a blocked version stayed approved, so the next session read it as a
    promotion still to come and held Send webhook question and the autonomy control."""
    active, candidate = _pair(True)  # h1 is a confirmed regression
    found = {"v1": active, "v2": candidate}
    monkeypatch.setattr(store, "baseline_for", lambda conn, name: found[name])
    decision = _hill()._decide_approved(object(), "v2", "instructor")  # type: ignore[arg-type]
    assert decision is not None and decision.verdict == "blocked"
    assert [d.candidate_version for d in decisions] == ["v2"] and RETIRED == ["v2"]


def test_no_background_promotion_runs_while_the_gate_of_an_experiment_runs(monkeypatch) -> None:
    """The race, deterministically: the watcher's poll comes while the gate confirms."""
    hill = _hill()
    polled: list[list[str]] = []
    reads: list[str] = []

    class _Conn:
        def commit(self) -> None:
            return None

        def execute(self, sql: str, *args: Any) -> Any:
            reads.append(sql)
            raise AssertionError("the promotion step read the database during the gate")

    monkeypatch.setattr(runner_module.db, "connect", lambda role: contextlib.nullcontext(_Conn()))
    monkeypatch.setattr(versions, "active_name", lambda conn: "v1")
    monkeypatch.setattr(store, "OpsItemSink", lambda *args: None)
    monkeypatch.setattr(store, "finish_experiment", lambda conn, result, **kw: None)

    def gate(self: HillClimbingRunner, candidate: Any, active: str, runner: Any, stop: Any) -> Any:
        watcher = threading.Thread(target=lambda: polled.append(hill.promote_approved()))
        watcher.start()  # the watcher thread polls while the confirming re-runs run
        watcher.join(timeout=10)
        return GateDecision(
            verdict="blocked",
            ready_for_approval=False,
            reasons=[],
            sentence="Blocked.",
            candidate_version="v2",
            active_version="v1",
            candidate_holdout_passes=0,
            active_holdout_passes=0,
            holdout_total=3,
            regressions=Regressions(dev=[], holdout=[], not_confirmed=[]),
            approved_by=None,
        )

    monkeypatch.setattr(HillClimbingRunner, "gate", gate)
    hill.experiment({"knowledge_version": "v2", "split": "all"}, uuid.uuid4())
    assert polled == [[]] and reads == [], "the watcher waited for the gate"
