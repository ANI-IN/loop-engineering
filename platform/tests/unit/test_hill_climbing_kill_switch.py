"""The hill-climbing runner obeys the kill switch, and a promotion holds no transaction through
its confirming re-runs (zero tokens, no database). Review round 1: the runner never read the
switch (F011), and a promotion decided, activated, re-ran live, and only then committed, so a
failed re-run rolled everything back and the next poll decided and spent again (F012)."""

from __future__ import annotations

import contextlib
import uuid
from typing import Any

import pytest
from loop4_doubles import StructuredDouble, answered, experiment, item

from datapilot.contracts import AnswerEnvelope, Diagnosis, ItemResult, Split
from datapilot.loop4_hill_climbing import candidates, eligibility, store, versions
from datapilot.loop4_hill_climbing import runner as runner_module
from datapilot.loop4_hill_climbing.analyzer import (
    AnalyzerTeam,
    CriticReviews,
    Diagnoses,
    ProposedRules,
)
from datapilot.loop4_hill_climbing.measurement import Scheme
from datapilot.loop4_hill_climbing.overfit_guard import OverfitGuard
from datapilot.loop4_hill_climbing.pack_files import load_knowledge
from datapilot.loop4_hill_climbing.runner import (
    KILL_SWITCH_STOP,
    HillClimbingRunner,
    KillSwitchEngaged,
    activate,
)

ITEMS = [item("d1"), item("d2"), item("d3"), item("h1", Split.HOLDOUT)]


class _Evaluator:
    def evaluate(self, benchmark_item: Any, answer: AnswerEnvelope) -> ItemResult:
        return ItemResult(item_id=benchmark_item.id, passed=True, reason="scripted")


class _Conn:
    def __init__(self, log: list[str] | None = None) -> None:
        self.log = log if log is not None else []

    def commit(self) -> None:
        self.log.append("commit")


class _Sink:
    def __init__(self, *args: Any) -> None:
        return None

    def started(self, experiment: Any) -> None:
        return None

    def item_done(self, experiment: Any, item_id: str) -> None:
        return None


@pytest.fixture
def no_database(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    finished: list[str] = []
    conn = _Conn()
    monkeypatch.setattr(runner_module.db, "connect", lambda role: contextlib.nullcontext(conn))
    monkeypatch.setattr(versions, "active_name", lambda c: "v1")
    monkeypatch.setattr(store, "OpsItemSink", _Sink)
    monkeypatch.setattr(
        store,
        "finish_experiment",
        lambda c, result, **kw: finished.append(result.knowledge_version),
    )
    return finished


def _hill(target: Any, engaged: Any) -> HillClimbingRunner:
    return HillClimbingRunner(
        ITEMS,
        target,
        _Evaluator(),  # type: ignore[arg-type]
        Scheme(),
        1,
        kill_switch_engaged=engaged,
    )


def test_an_engaged_switch_fails_a_claimed_request_before_any_model_call(no_database) -> None:
    asked: list[str] = []
    hill = _hill(lambda q, v: asked.append(q) or answered("SELECT 1"), lambda: True)
    for kind in ("experiment", "analyzer"):
        with pytest.raises(KillSwitchEngaged, match=KILL_SWITCH_STOP):
            hill.run({"kind": kind, "params": {}, "session_id": uuid.uuid4()})
    assert asked == [] and no_database == []


def test_an_engaged_switch_stops_an_experiment_between_runs(no_database) -> None:
    switch = {"engaged": False}
    asked: list[str] = []

    def target(question: str, version: str) -> AnswerEnvelope:
        asked.append(question)
        switch["engaged"] = True  # engaged while the first run is in flight
        return answered("SELECT 1")

    hill = _hill(target, lambda: switch["engaged"])
    with pytest.raises(KillSwitchEngaged):
        hill.run({"kind": "experiment", "params": {}, "session_id": uuid.uuid4()})
    assert asked == ["Question d1?"], "no run started after the switch was engaged"
    assert no_database == [], "a stopped experiment is never finished, so never a baseline"


def test_no_promotion_starts_while_the_switch_is_engaged(monkeypatch) -> None:
    def never(role: Any) -> Any:
        raise AssertionError("the promotion step read nothing")

    monkeypatch.setattr(runner_module.db, "connect", never)
    assert _hill(lambda q, v: answered("SELECT 1"), lambda: True).promote_approved() == []


def test_a_promotion_commits_the_decision_and_activation_before_its_re_runs(monkeypatch) -> None:
    log: list[str] = []
    conn = _Conn(log)
    monkeypatch.setattr(versions, "activate", lambda c, name: log.append(f"activate {name}"))
    # the finale's wait for the clearance (a lock on a connection of its own), no database here
    monkeypatch.setattr(runner_module, "clearing", contextlib.nullcontext)
    monkeypatch.setattr(store, "save_clearance_rerun", lambda c, *a: log.append("clearance"))
    monkeypatch.setattr(
        runner_module.autonomy, "mark_eligible", lambda c, family, name: log.append("eligible")
    )

    def clearance(items, candidate, rerun, scheme, families):  # type: ignore[no-untyped-def]
        passes = rerun(ITEMS[3], 3)
        return eligibility.Clearance(cleared=["revenue"], reruns={"h1": passes})

    monkeypatch.setattr(eligibility, "confirmed_clearance", clearance)

    def rerun(benchmark_item: Any, times: int) -> list[bool]:
        log.append("rerun")
        return [True] * times

    candidate = experiment("v2", {"h1": False}, {"h1": Split.HOLDOUT})
    activate(conn, "v2", candidate, items=ITEMS, rerun=rerun, scheme=Scheme())  # type: ignore[arg-type]
    assert log == ["activate v2", "commit", "rerun", "clearance", "eligible", "commit"]


def test_a_re_run_the_switch_stopped_is_not_a_measured_failure(no_database) -> None:
    switch = {"engaged": False}
    stop = runner_module.KillSwitchStop(lambda: switch["engaged"])

    class _Runner:
        def rerun(self, benchmark_item: Any, version: str, times: int) -> list[bool]:
            switch["engaged"] = True
            return [False] * times  # what the stopped runs would score

    checked = stop.rerun(_Runner(), "v2")  # type: ignore[arg-type]
    with pytest.raises(KillSwitchEngaged):
        checked(ITEMS[3], 3)


class _EngagingDouble(StructuredDouble):
    """A model double whose call engages the kill switch while it is out."""

    def __init__(self, replies: dict[type, list[Any]], switch: dict[str, bool]) -> None:
        super().__init__(replies)
        self.switch = switch

    def with_structured_output(self, schema: type, **kwargs: Any) -> Any:
        runnable = super().with_structured_output(schema, **kwargs)
        switch = self.switch

        class _Engaging:
            def invoke(self, messages: list[Any]) -> Any:
                switch["engaged"] = True
                return runnable.invoke(messages)

        return _Engaging()


def test_the_analyzer_team_makes_no_further_model_call_once_the_switch_is_engaged(
    monkeypatch, no_database
) -> None:
    """Review round 2: the team's three model calls (failure analyst, rule writer, critic) ran in
    a row with no check between them, so a switch engaged during the first still sent and billed
    the other two."""
    switch = {"engaged": False}
    diagnosis = Diagnosis(item_id="d1", what_went_wrong="wrong", likely_cause="no rule")
    failure_analyst = _EngagingDouble({Diagnoses: [Diagnoses(diagnoses=[diagnosis])]}, switch)
    rule_writer = StructuredDouble({ProposedRules: [ProposedRules()]})
    critic = StructuredDouble({CriticReviews: [CriticReviews()]})
    team = AnalyzerTeam(failure_analyst, rule_writer, critic, OverfitGuard.from_pack(ITEMS))
    monkeypatch.setattr(runner_module, "live_team", lambda items: team)
    monkeypatch.setattr(candidates, "count", lambda: 1)
    monkeypatch.delenv("BUG_NAIVE_ANALYZER", raising=False)
    baseline = experiment("v1", {"d1": False, "h1": True}, {"d1": Split.DEV, "h1": Split.HOLDOUT})
    monkeypatch.setattr(store, "baseline_for", lambda conn, name: baseline)
    monkeypatch.setattr(versions, "get", lambda conn, name: load_knowledge("v1"))
    monkeypatch.setattr(versions, "next_name", lambda conn: "v2")

    hill = _hill(lambda q, v: answered("SELECT 1"), lambda: switch["engaged"])
    with pytest.raises(KillSwitchEngaged, match=KILL_SWITCH_STOP):
        hill.run({"kind": "analyzer", "params": {}, "session_id": uuid.uuid4()})
    assert len(failure_analyst.seen) == 1
    assert rule_writer.seen == [] and critic.seen == [], "no call after the switch was engaged"
