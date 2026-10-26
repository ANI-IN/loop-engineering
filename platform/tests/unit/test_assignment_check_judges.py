"""What the four checks judge, zero tokens and no database: the starter fails every requirement
that has nothing to judge, naming its extension point; a grader that does nothing fails the leak
grader's own requirement; an approved case must post the approved data; the drill-down is judged
only on a new run; and the gate's verdict in Assignment 4 still fails a broken solution, while the
model's rule set is named as the cause when it is the cause. Graders, teams, and runners here are
test doubles, in a unit test only; every check runs live."""

from __future__ import annotations

import importlib.util
import os
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import psycopg
import pytest

from datapilot import db, tests_database_guard
from datapilot.assignments import WITHHELD_REASON, assignment, solutions_withheld
from datapilot.assignments.report import Stop
from datapilot.assignments.runner import load_check
from datapilot.contracts import (
    BenchmarkItem,
    CriticDecision,
    GraderResult,
    RunStatus,
    Severity,
    Split,
    Stage,
)
from datapilot.contracts.api import EventSubmitted
from datapilot.settings import REPO

agent_loop = load_check(assignment("agent-loop").check_file)
verification_loop = load_check(assignment("verification-loop").check_file)
event_loop = load_check(assignment("event-loop").check_file)
hill_climbing_loop = load_check(assignment("hill-climbing-loop").check_file)
NOW = datetime(2026, 10, 23, tzinfo=UTC)


# --- Assignment 1: Agent loop ---------------------------------------------------------------------
def test_the_read_only_requirement_fails_while_there_is_no_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(agent_loop, "_warehouse", lambda *marker: None)
    with pytest.raises(NotImplementedError, match="agent-loop-1"):
        agent_loop._read_only_role()


@pytest.fixture
def closed_port_allowed() -> Any:
    """The check's closed address (127.0.0.1, port 1) is refused under pytest as any address but
    the tests' is; a lookup that tries it is what these tests show, so its refusal is expected."""
    start = len(tests_database_guard.refused)
    yield
    closed = f":{agent_loop.CLOSED_PORT}/"  # the check's closed port, on any host
    kept = [a for a in tests_database_guard.refused[start:] if closed not in a]
    tests_database_guard.refused[start:] = kept


def test_the_read_only_requirement_closes_the_port_and_the_superuser_too(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Review of session 6, round 2: an owner address built from POSTGRES_PORT, or the superuser
    address, still reached the database while the lookup ran."""
    monkeypatch.setenv("POSTGRES_PORT", "55432")
    with agent_loop.only_the_agent_role():
        assert os.environ["POSTGRES_PORT"] == agent_loop.CLOSED_PORT
        assert os.environ["DATABASE_URL_SUPERUSER"] == agent_loop.CLOSED
        from datapilot.settings import Settings

        assert Settings(_env_file=None).postgres_port == int(agent_loop.CLOSED_PORT)
    assert os.environ["POSTGRES_PORT"] == "55432"  # put back afterwards


def _lookup_as(url_of: Any) -> Any:
    """A lookup that connects to the address `url_of(warehouse)` gives and finds one value."""

    def lookup(warehouse: Any, kind: str, wording: str) -> Any:
        with psycopg.connect(url_of(warehouse), connect_timeout=2):
            pass
        return SimpleNamespace(candidates=["Alpine Trek 45L Backpack"])

    return lookup


@pytest.mark.parametrize(
    "url_of",
    [
        lambda warehouse: db.url_for(db.Role.OWNER),
        lambda warehouse: os.environ["DATABASE_URL_" + "APP"],
    ],
    ids=["the owner role by its enum", "the application role by a built name"],
)
@pytest.mark.usefixtures("closed_port_allowed")
def test_the_read_only_requirement_fails_a_lookup_that_connects_as_another_role(
    monkeypatch: pytest.MonkeyPatch, url_of: Any
) -> None:
    """Review of session 6, round 1: a text search passed `db.Role["OWNER"]` and
    `os.environ["DATABASE_URL_" + role]`. The check now closes every other role's address while
    the lookup runs, so the role it connects as decides."""
    monkeypatch.setattr(agent_loop, "_warehouse", lambda *marker: None)
    monkeypatch.setattr(agent_loop.extension, "lookup_values", _lookup_as(url_of))
    problem = agent_loop._read_only_role()
    assert problem is not None and "could not connect" in problem
    assert os.environ.get("DATABASE_URL_OWNER") != agent_loop.CLOSED  # put back afterwards


def test_the_read_only_requirement_passes_a_lookup_that_reads_its_own_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(agent_loop, "_warehouse", lambda *marker: SimpleNamespace(url="unused"))

    def lookup(warehouse: Any, kind: str, wording: str) -> Any:
        assert db.url_for(db.Role.OWNER) == agent_loop.CLOSED  # closed while the lookup runs
        return SimpleNamespace(candidates=["Alpine Trek 45L Backpack"])

    monkeypatch.setattr(agent_loop.extension, "lookup_values", lookup)
    assert agent_loop._read_only_role() is None


def test_the_registration_requirement_names_its_extension_point(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(agent_loop, "_warehouse", lambda *marker: None)
    assert agent_loop._registered().startswith("agent-loop-2:")


# --- Assignment 2: Verification loop --------------------------------------------------------------
class _Grader:
    name = "leak grader under test"
    stage = Stage.FINAL_ANSWER

    def __init__(self, check) -> None:
        self.check = check


def _reference_leak_grader():
    path = (
        assignment("verification-loop").solution("reference")
        / "files/platform/src/datapilot/loop2_verification/graders/personal_data_leak.py"
    )
    spec = importlib.util.spec_from_file_location("reference_personal_data_leak", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.PersonalDataLeakGrader()


@pytest.mark.skipif(solutions_withheld(), reason=WITHHELD_REASON)
def test_the_reference_leak_grader_passes_its_requirement(monkeypatch: pytest.MonkeyPatch) -> None:
    grader = _reference_leak_grader()
    monkeypatch.setattr(verification_loop.extension, "answer_graders", lambda: [grader])
    assert verification_loop._leak_grader() is None


def _blocked(context) -> GraderResult:
    return GraderResult("leak", False, "personal data", Severity.BLOCK, "remove it")


@pytest.mark.parametrize(
    ("check", "says"),
    [
        (lambda context: GraderResult("leak", True, "a grader that passes everything"), "fail"),
        (_blocked, "approved"),
        (lambda context: GraderResult("leak", False, "", Severity.INFO, ""), "BLOCK"),
    ],
    ids=["passes everything", "ignores the approval", "never blocks"],
)
def test_a_leak_grader_that_does_not_work_fails_its_requirement(
    monkeypatch: pytest.MonkeyPatch, check, says: str
) -> None:
    monkeypatch.setattr(verification_loop.extension, "answer_graders", lambda: [_Grader(check)])
    problem = verification_loop._leak_grader()
    assert problem is not None and says in problem


def test_the_starter_fails_the_leak_grader_and_the_model_requirements() -> None:
    with pytest.raises(NotImplementedError, match="verification-loop-3"):
        verification_loop._leak_grader()
    with pytest.raises(NotImplementedError, match="verification-loop-1"):
        verification_loop._no_model()


def _posted(text: str, rows: list[list[Any]] | None = None):
    body = {"answer": {"answer_text": text, "rows_preview": rows or []}}
    return SimpleNamespace(
        status=RunStatus.POSTED, posts=[SimpleNamespace(body=body)], tokens_in=0, tokens_out=0
    )


def test_an_approved_email_case_must_post_the_approved_addresses() -> None:
    email_case = verification_loop.LEAKS[3]
    assert email_case.posts_data
    assert verification_loop._approved_post(email_case, _posted("Here they are: a@example.com"))
    assert verification_loop._approved_post(
        email_case, _posted("Here they are.", [["a@example.com"]])
    )
    assert not verification_loop._approved_post(email_case, _posted("I cannot share them."))


def test_an_approved_phone_case_only_has_to_post() -> None:
    phone_case = verification_loop.LEAKS[4]
    assert not phone_case.posts_data, "a customer's phone number may be empty in the warehouse"
    assert verification_loop._approved_post(phone_case, _posted("No phone number is on file."))


def test_the_suite_asks_only_questions_the_schema_answers_plainly() -> None:
    texts = [q.text for q in verification_loop.SUITE]
    assert not any("shipped" in text for text in texts), "the warehouse has no ship date"
    assert any("ship-to state" in text for text in texts)


# --- Assignment 3: Event loop ---------------------------------------------------------------------
class _Absorbed:
    """The api when the drill-down's event id already has a run: both asks are absorbed."""

    def __init__(self) -> None:
        self.run_id = uuid.uuid4()

    def submit(self, type: str, payload: dict[str, Any], event: str) -> EventSubmitted:
        return EventSubmitted(
            event_id=event,
            run_id=self.run_id,
            job_id=None,
            duplicate=True,
            duplicates_ignored=1,
            created_at=NOW,
        )

    def run(self, run_id: str) -> SimpleNamespace:
        """The run as the check reads it after the first ask: no planted bug on."""
        return SimpleNamespace(run_id=run_id, planted_active=[])


def test_a_drill_down_absorbed_into_an_earlier_run_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    posted = SimpleNamespace(status=RunStatus.POSTED, posts=[])
    monkeypatch.setattr(event_loop, "settle", lambda api, run_id, approver: posted)
    monkeypatch.setattr(event_loop, "posted_text", lambda detail: "Water Sports led it")
    drill = {"event_id": "drill-down:2026-01-30", "question": "Which category?"}
    names = event_loop.CategoryNames(("Water Sports",))
    outcome = event_loop.drill_down(_Absorbed(), drill, "Water Sports", names)
    assert outcome.right and not outcome.passed
    assert "earlier run" in outcome.what()
    assert "new run" in outcome.fix()


def test_the_check_clears_the_drill_down_event_ids_its_alerts_named() -> None:
    assert "drill_down" in event_loop.DRILL_DOWN_IDS
    source = assignment("event-loop").check_file.read_text(encoding="utf-8")
    assert "clear_drill_down(" in source.split("def run(ctx)")[1], "cleared before the live step"


def test_the_starter_router_requirement_names_its_extension_point() -> None:
    assert event_loop.Scenario(None).router_table().startswith("event-loop-3:")


def _job_run(monkeypatch: pytest.MonkeyPatch, status: RunStatus) -> None:
    row = {"run_id": uuid.uuid4(), "status": status.value, "answer": None}

    @contextmanager
    def connect(role):
        yield SimpleNamespace(
            execute=lambda *args: SimpleNamespace(fetchone=lambda: row), commit=lambda: None
        )

    monkeypatch.setattr(event_loop.db, "connect", connect)


def test_a_job_run_at_the_daily_budget_stops_the_check_at_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Not a timeout read as a FAIL of the solution: the run is blocked_budget, so the check
    stops (exit 2) and says why, as it does for the runs `settle` waits on."""
    _job_run(monkeypatch, RunStatus.BLOCKED_BUDGET)
    api = SimpleNamespace(engaged_by_check=False, engaged_at_cap=False, slug="event-loop")
    with pytest.raises(Stop, match="blocked_budget"):
        event_loop.run_of("event", api, seconds=1)


def test_a_job_run_blocked_by_an_outside_kill_switch_stops_the_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _job_run(monkeypatch, RunStatus.BLOCKED_KILLSWITCH)
    api = SimpleNamespace(engaged_by_check=False, engaged_at_cap=False, slug="event-loop")
    with pytest.raises(Stop, match="engaged from outside the check"):
        event_loop.run_of("event", api, seconds=1)
    api.engaged_by_check = True  # the check's own kill-switch step: judged as it expects
    assert event_loop.run_of("event", api, seconds=1)["status"] == "blocked_killswitch"


class _Control:
    def __init__(self, switch: str) -> None:
        self.switch = switch
        self.calls: list[str] = []

    def control(self):
        return SimpleNamespace(
            kill_switch=self.switch, autonomy_level=SimpleNamespace(value="assisted")
        )

    def release(self) -> None:
        self.calls.append("release")


def test_on_services_already_running_the_check_never_releases_a_kill_switch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATAPILOT_ASSIGNMENT_STACK", "running")
    api = _Control("engaged")
    ctx = SimpleNamespace(report=None, api=api)
    with pytest.raises(Stop, match="never releases a kill switch"):
        event_loop.run(ctx)
    assert api.calls == []


# --- Assignment 4: Hill-climbing loop -------------------------------------------------------------
def test_the_starter_fails_every_requirement_with_nothing_to_judge() -> None:
    assert hill_climbing_loop.family_items() == [], "the class benchmark has no such family"
    for probe in (hill_climbing_loop._gold_runs, hill_climbing_loop._traps):
        with pytest.raises(NotImplementedError, match="hill-climbing-loop-1"):
            probe()


@pytest.mark.parametrize(
    ("verdict", "regressions", "missing", "eligible", "passed", "says"),
    [
        ("promoted", 0, [], ["repeat_customers"], True, ""),
        ("promoted", 0, ["repeat-rate-fy2025"], [], False, "every repeat-customer item"),
        ("promoted", 0, [], ["aov"], False, "aov"),
        ("blocked", 1, [], [], False, "the model's rule set"),
        ("blocked", 0, [], [], False, "the model's rule set"),
        ("blocked", 0, ["repeat-rate-fy2025"], [], False, "every repeat-customer item"),
    ],
)
def test_the_gate_verdict_still_fails_a_broken_solution(
    verdict: str,
    regressions: int,
    missing: list[str],
    eligible: list[str],
    passed: bool,
    says: str,
) -> None:
    ok, fix = hill_climbing_loop.promotion_verdict(verdict, regressions, missing, eligible)
    assert ok is passed
    assert says in fix


def _item(item_id: str, split: Split) -> BenchmarkItem:
    return BenchmarkItem(
        id=item_id,
        question=f"the question of {item_id}",
        split=split,
        category="ratios",
        difficulty=3,
        metric_family="repeat_customers",
        gold_sql="SELECT 1",
        naive_sql="SELECT 2",
    )


def test_the_planted_rule_cites_the_learners_own_failed_item(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    items = [_item("mine-dev-a", Split.DEV), _item("mine-dev-b", Split.DEV)]
    items.append(_item("mine-holdout", Split.HOLDOUT))
    monkeypatch.setattr(hill_climbing_loop, "family_items", lambda: items)
    planted = hill_climbing_loop.planted_rule
    assert planted(["other-family", "mine-dev-b"]).evidence_example_ids == ["mine-dev-b"]
    assert planted(["other-family"]).evidence_example_ids == ["mine-dev-a"]
    assert planted(["mine-holdout"]).evidence_example_ids == ["mine-dev-a"]


class _Team:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str]]] = []

    def run(self, failed, knowledge, name, *, extra_proposals=()):
        self.calls.append((name, [r.id for r in extra_proposals]))
        candidate = SimpleNamespace(version=name)
        return SimpleNamespace(candidate=candidate, reviews=[], accepted=[], proposed=[])


class _Runner:
    def __init__(self) -> None:
        self.runs: list[tuple[str, list[Split]]] = []

    def run(self, items, version, *, session_id, splits):
        self.runs.append((version, list(splits)))
        return SimpleNamespace(results={}, splits_by_item={})


def test_the_check_writes_the_classes_candidates_each_with_the_planted_rule(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @contextmanager
    def no_database(role):
        yield SimpleNamespace(commit=lambda: None)

    candidates = hill_climbing_loop.candidates
    monkeypatch.setattr(candidates, "count", lambda: 2)
    monkeypatch.setattr(candidates, "save_selection_draft", lambda conn, version: None)
    monkeypatch.setattr(hill_climbing_loop.db, "connect", no_database)
    team, runner = _Team(), _Runner()
    planted = hill_climbing_loop.planted_rule()
    runs = hill_climbing_loop._team_runs(
        team, [], None, "candidate-x", SimpleNamespace(), runner, [], uuid.uuid4(), planted
    )
    assert [r.label for r in runs] == ["A", "B"]
    assert [name for name, _ in team.calls] == [
        "candidate-x-candidate-a",
        "candidate-x-candidate-b",
    ]
    assert all(proposals == [planted.id] for _, proposals in team.calls)
    assert all(splits == [Split.DEV] for _, splits in runner.runs), "never the holdout split"


def test_the_critic_must_drop_the_planted_rule_with_a_reason() -> None:
    def run(decision: CriticDecision, reason: str):
        review = SimpleNamespace(rule_id="planted", decision=decision, reason=reason)
        report = SimpleNamespace(reviews=[review], accepted=[], proposed=[])
        return SimpleNamespace(label="A", report=report)

    critic = hill_climbing_loop._critic_line
    assert critic(run(CriticDecision.DROP, "over-broad"), "planted")[0]
    assert not critic(run(CriticDecision.DROP, ""), "planted")[0]
    assert not critic(run(CriticDecision.KEEP, "fine"), "planted")[0]
    assert not critic(run(CriticDecision.DROP, "over-broad"), "another rule")[0], "not reviewed"


# The minimum-holdout rule, judged on the class benchmark with the learner's family added (three
# holdout items) and the family in the pack: revenue and orders have four holdout items.
def _with_the_family(monkeypatch: pytest.MonkeyPatch) -> None:
    from datapilot.loop4_hill_climbing.pack_files import load_benchmark

    family = [_item(f"repeat-holdout-{n}", Split.HOLDOUT) for n in range(3)]
    family += [_item(f"repeat-dev-{n}", Split.DEV) for n in range(3)]
    monkeypatch.setattr(hill_climbing_loop, "load_benchmark", lambda: [*load_benchmark(), *family])
    pack = hill_climbing_loop.pack_config()
    families = [*pack["autonomy"]["metric_families"], "repeat_customers"]
    with_family = {**pack, "autonomy": {**pack["autonomy"], "metric_families": families}}
    monkeypatch.setattr(hill_climbing_loop, "pack_config", lambda: with_family)


def test_the_class_benchmark_has_families_with_four_holdout_items() -> None:
    from datapilot.loop4_hill_climbing import eligibility
    from datapilot.loop4_hill_climbing.pack_files import load_benchmark

    held = eligibility.holdout_by_family(load_benchmark())
    assert len(held["revenue"]) == 4 and len(held["orders"]) == 4


def test_a_right_minimum_holdout_rule_passes_requirements_6_and_7(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _with_the_family(monkeypatch)
    monkeypatch.setattr(hill_climbing_loop.extension, "enough_holdout_items", lambda n: n >= 3)
    assert hill_climbing_loop._minimum() is None
    assert hill_climbing_loop._eligible() is None


@pytest.mark.parametrize(
    ("rule", "says"),
    [
        (lambda n: n == 3, "refuses 4, 5"),
        (lambda n: 3 <= n <= 4, "refuses 5, 6"),
        (lambda n: n in (3, 5, 6, 7, 8, 9, 10), "refuses 4"),
    ],
)
def test_a_minimum_holdout_rule_that_refuses_larger_families_fails_requirement_7(
    monkeypatch: pytest.MonkeyPatch, rule, says: str
) -> None:
    _with_the_family(monkeypatch)
    monkeypatch.setattr(hill_climbing_loop.extension, "enough_holdout_items", rule)
    assert hill_climbing_loop._minimum() is None, "requirement 6 alone cannot tell"
    fix = hill_climbing_loop._eligible()
    assert fix is not None and says in fix


def test_a_family_with_four_holdout_items_must_be_eligible_when_all_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _with_the_family(monkeypatch)
    monkeypatch.setattr(hill_climbing_loop.extension, "enough_holdout_items", lambda n: n >= 3)
    real = hill_climbing_loop.eligibility.eligible_families
    monkeypatch.setattr(
        hill_climbing_loop.eligibility,
        "eligible_families",
        lambda items, passed, families: real(items, passed, families) - {"revenue"},
    )
    fix = hill_climbing_loop._eligible()
    assert fix is not None and "revenue (4 holdout items)" in fix


# A session's baseline is shared only when it measured today's items as they are.
def _baseline(items: list[BenchmarkItem]):
    return SimpleNamespace(
        results={i.id: object() for i in items}, splits_by_item={i.id: i.split for i in items}
    )


def test_a_baseline_of_the_same_items_is_shared() -> None:
    items = [_item("a", Split.DEV), _item("b", Split.HOLDOUT)]
    stored = {i.id: hill_climbing_loop.item_fingerprint(i) for i in items}
    assert hill_climbing_loop.baseline_mismatch(items, _baseline(items), stored) == []


@pytest.mark.parametrize(
    "change",
    [
        {"gold_sql": "SELECT 3"},
        {"split": Split.DEV},
        {"question": "another question"},
        {"numeric_tolerance": 0.5},
    ],
)
def test_a_baseline_measured_before_an_item_changed_is_not_shared(change: dict) -> None:
    before = [_item("a", Split.DEV), _item("b", Split.HOLDOUT)]
    stored = {i.id: hill_climbing_loop.item_fingerprint(i) for i in before}
    today = [before[0], before[1].model_copy(update=change)]
    assert hill_climbing_loop.baseline_mismatch(today, _baseline(before), stored) == ["b"]


def test_a_baseline_without_fingerprints_or_with_other_items_is_not_shared() -> None:
    items = [_item("a", Split.DEV), _item("b", Split.HOLDOUT)]
    baseline = _baseline(items)
    assert hill_climbing_loop.baseline_mismatch(items, baseline, {}) == ["a", "b"]
    stored = {i.id: hill_climbing_loop.item_fingerprint(i) for i in items}
    added = [*items, _item("c", Split.DEV)]
    assert hill_climbing_loop.baseline_mismatch(added, baseline, stored) == ["c"]
    assert hill_climbing_loop.baseline_mismatch(items[:1], baseline, stored) == ["b"]


def test_a_first_check_prints_its_own_typical_cost() -> None:
    assert "12.62 to 23.95 in seven later checks" in hill_climbing_loop.typical(first=False)
    assert "an estimate" in hill_climbing_loop.typical(first=True)  # no clean first check yet
    assert hill_climbing_loop.typical(first=True) != hill_climbing_loop.typical(first=False)


def _costs_row(name: str) -> str:
    costs = (REPO / "docs" / "costs.md").read_text(encoding="utf-8")
    return next(line for line in costs.splitlines() if line.startswith(f"| {name} |"))


def test_the_printed_typical_costs_are_the_costs_page_figures() -> None:
    """docs/costs.md is the one source: a learner sees the same figure in the terminal and on the
    page the check points to (review of session 6, round 1)."""
    later = _costs_row("Assignment 4, each later check")
    assert "About 13 to 24 cents (12.62 to 23.95, seven checks" in later
    assert hill_climbing_loop.TYPICAL_LATER.startswith("about 13 to 24 cents (12.62 to 23.95")
    assert "About 0.2 cents" in _costs_row("Assignment 3: Event loop")
    source = assignment("event-loop").check_file.read_text(encoding="utf-8")
    assert 'typical="about 0.2 cents"' in source


class _PlanContext:
    """Records what the check prints and when it reaches the live gate, the point after which
    spending can start."""

    analyzer_model = agent_model = "gpt-6-luna"

    def __init__(self) -> None:
        self.events: list[tuple[str, Any]] = []
        self.report = SimpleNamespace(say=lambda text="": self.events.append(("say", text)))

    def live_gate(self, planned, **kwargs) -> None:
        self.events.append(("live gate", (planned, kwargs)))


def _plan(monkeypatch: pytest.MonkeyPatch, shared: object, why: str) -> _PlanContext:
    monkeypatch.setattr(hill_climbing_loop, "session_baseline", lambda items: (shared, why))
    ctx = _PlanContext()
    items = [_item("a", Split.DEV), _item("b", Split.HOLDOUT)]
    hill_climbing_loop.plan_live(ctx, items, ["live nine", "live ten"])
    return ctx


def test_a_new_baseline_gives_its_reason_and_the_first_check_estimate_before_spending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    why = "the session's baseline 1c933bea measured these items otherwise than they are now: b"
    ctx = _plan(monkeypatch, None, why)
    kinds = [kind for kind, _ in ctx.events]
    said = [text for kind, text in ctx.events if kind == "say"]
    reason = next(i for i, (kind, text) in enumerate(ctx.events) if why in str(text))
    assert reason < kinds.index("live gate"), "the reason comes before the gate, before any spend"
    assert f"Baseline: this check runs a new baseline experiment, since {why}." in said
    planned, kwargs = ctx.events[kinds.index("live gate")][1]
    benchmark = next(p for p in planned if "for the benchmark" in p.what)
    assert "the baseline and the candidate" in benchmark.what
    per_experiment = 1 + 3  # the dev item once, the holdout item three times
    assert benchmark.runs == 2 * per_experiment
    assert kwargs["typical"] == hill_climbing_loop.typical(first=True)
    assert kwargs["typical_estimated"] is True


def test_a_shared_baseline_plans_the_candidate_only_at_the_measured_typical_cost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = _plan(monkeypatch, object(), "")
    assert not any("Baseline:" in str(text) for kind, text in ctx.events if kind == "say")
    planned, kwargs = next(value for kind, value in ctx.events if kind == "live gate")
    benchmark = next(p for p in planned if "for the benchmark" in p.what)
    assert "the candidate only" in benchmark.what and benchmark.runs == 1 + 3
    assert kwargs["typical"] == hill_climbing_loop.typical(first=False)
    assert kwargs["typical_estimated"] is False
