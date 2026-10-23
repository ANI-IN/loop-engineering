"""The calibration runner's zero-token parts: the warning line, raw results and the run log, the
streaming sink, and the trap step on a stub target."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field

import pytest
from loop4_doubles import SESSION, ScriptedEvaluator, answered, item
from typer.testing import CliRunner

from datapilot.cli import app
from datapilot.contracts import Split
from datapilot.loop4_hill_climbing import calibration as cal
from datapilot.loop4_hill_climbing.experiment import ExperimentRunner, current_run
from datapilot.loop4_hill_climbing.measurement import Scheme
from datapilot.observability import spend


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    path = tmp_path / "ledger.sqlite"
    monkeypatch.setenv("DATAPILOT_SPEND_LEDGER", str(path))
    monkeypatch.delenv(cal.EXTRA_LEDGERS, raising=False)
    return path


MODEL = next(iter(spend.pack_config()["prices"]))  # the class model's price is the first one


def _spend(dollars: float, path, activity: str = "calibration-test") -> None:
    tokens = round(dollars / spend.pack_config()["prices"][MODEL]["output"] * 1_000_000)
    spend.record(
        component="analyst",
        model=MODEL,
        usage=spend.Usage(0, 0, tokens),
        activity=activity,
        run_id=str(uuid.uuid4()),
        path=path,
    )


def test_a_step_that_would_pass_its_line_does_not_start(ledger) -> None:
    _spend(1.7, ledger)
    assert "has $0.5000 left of $2.20" in cal.guard_budget("small", 0.4, "calibration-traps")
    with pytest.raises(cal.OverWarningLine, match="not started"):
        cal.guard_budget("large", 0.6, "calibration-traps")


def test_past_the_warning_line_the_step_says_to_report(ledger) -> None:
    for activity in ("assignment", "rehearsal"):
        _spend(2.5, ledger, activity)
    _spend(1.0, ledger)
    assert "report the spend to the lead" in cal.guard_budget("step", 0.1, "calibration")


def test_other_ledgers_count_toward_the_stop_line(ledger, tmp_path, monkeypatch) -> None:
    other = tmp_path / "other.sqlite"
    _spend(1.0, ledger)
    _spend(8.95, other, "rehearsal")
    monkeypatch.setenv(cal.EXTRA_LEDGERS, str(other))
    assert cal.total_spent() == pytest.approx(9.95, abs=0.001)
    with pytest.raises(cal.OverWarningLine):
        cal.guard_budget("step", 0.2, "calibration")


def test_the_estimate_uses_the_measured_cost_per_run(ledger) -> None:
    _spend(0.002, ledger)
    _spend(0.004, ledger)
    assert cal.measured_cost_per_run(MODEL) == pytest.approx(0.003, abs=1e-5)
    assert cal.estimate(10, MODEL) == pytest.approx(0.03, abs=1e-4)


def test_the_first_estimate_is_a_guess_until_a_run_is_measured(ledger) -> None:
    guess = spend.cost_usd(MODEL, cal.FIRST_GUESS["analyst"])
    assert cal.estimate(4, MODEL) == pytest.approx(4 * guess)


def test_the_analyzer_at_high_effort_is_estimated_as_one_team_run_and_one_experiment(
    ledger,
) -> None:
    _spend(0.0011, ledger)  # the measured cost of one analyst run in calibration
    items = [item(f"d{n}") for n in range(25)] + [item(f"h{n}", Split.HOLDOUT) for n in range(15)]
    team = spend.cost_usd(MODEL, cal.FIRST_GUESS["analyzer"])
    found = cal.analyzer_effort_estimate(items, Scheme(), MODEL, MODEL)
    assert found == pytest.approx(team + 70 * 0.0011, abs=1e-4)
    assert 0.08 < found < 0.12, "about 0.10 dollars"


def test_the_analyzer_at_high_effort_stops_before_any_call_without_a_starting_experiment(
    monkeypatch,
) -> None:
    from datapilot import db, settings
    from datapilot.loop4_hill_climbing import store

    monkeypatch.setenv("OPENAI_MODEL", MODEL)
    settings.get_settings.cache_clear()

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

    monkeypatch.setattr(db, "connect", lambda role: _Conn())
    monkeypatch.setattr(store, "open_session", lambda conn: SESSION)
    monkeypatch.setattr(cal, "latest_experiment", lambda *args: None)
    monkeypatch.setattr(cal, "use_activity", lambda *args, **kwargs: pytest.fail("no step"))
    try:
        result = CliRunner().invoke(app, ["calibrate", "analyzer-high"])
    finally:
        settings.get_settings.cache_clear()
    assert result.exit_code == 2, result.output
    assert "make calibrate STEP=experiment-starting" in result.output
    assert "Nothing was called" in result.output


def test_each_step_writes_raw_results_and_a_run_log_line(tmp_path) -> None:
    record = cal.StepRecord(
        step="traps",
        activity="calibration-traps",
        session_id=str(SESSION),
        started_at="2026-10-23T09:00:00+00:00",
        finished_at="2026-10-23T09:05:00+00:00",
        estimate_usd=0.1,
        cost_usd=0.08,
        summary="0 trap items passed at least once of 33",
        data={"per_trap": {}},
    )
    path = cal.write(record, tmp_path)
    assert json.loads(path.read_text(encoding="utf-8"))["data"] == {"per_trap": {}}
    log = (tmp_path / "run-log.md").read_text(encoding="utf-8")
    assert "traps (calibration-traps)" in log and path.name in log
    assert cal.raw_records("traps", tmp_path)[0]["summary"].startswith("0 trap items")


def test_the_activity_names_the_step(monkeypatch) -> None:
    monkeypatch.delenv("DATAPILOT_SPEND_ACTIVITY", raising=False)
    assert cal.use_activity("traps") == "calibration-traps"
    from datapilot.settings import get_settings

    assert get_settings().datapilot_spend_activity == "calibration-traps"
    assert cal.use_activity("preflight", prefix="") == "preflight"
    get_settings.cache_clear()


@dataclass
class _Target:
    """A stub target that records the run context the experiment runner gives it."""

    model: str = "stub"
    seen: list[tuple[str, int]] = field(default_factory=list)
    stats: list = field(default_factory=list)

    def __call__(self, question: str, version: str):
        context = current_run.get()
        assert context is not None and context.knowledge_version == version
        self.seen.append((context.item.id, context.repetition))
        return answered("SELECT 1")


def test_the_agents_step_asks_the_undefined_questions_in_every_configuration() -> None:
    from types import SimpleNamespace

    asked: list[tuple[str, bool]] = []

    @dataclass
    class _Agents:
        reviewer: bool = True
        stats: list = field(default_factory=list)

        def with_agents(self, *, scout: bool, reviewer: bool):
            return _Agents(reviewer)

        def __call__(self, question: str, version: str):
            asked.append((question, self.reviewer))
            self.stats.append(
                SimpleNamespace(
                    status="answered",
                    reviewer="approve" if self.reviewer else None,
                    reviewer_reasons=[],
                    run_id="r",
                    item_id=None,
                    tokens_in=10,
                    tokens_out=1,
                    seconds=1.0,
                )
            )
            return answered("SELECT 1")

    evaluator = ScriptedEvaluator({"product-count": [True] * 4})
    ctx = cal.Context(SESSION, [item("product-count")], evaluator, None, 1, print)
    import datapilot.loop4_hill_climbing.calibration as module

    original = module.run_rows
    module.run_rows = lambda target: [vars(s) for s in target.stats]
    try:
        data = cal.agents_step(ctx, _Agents(), ["product-count"], ["Who are our VIP customers?"])
    finally:
        module.run_rows = original
    assert sorted({r for q, r in asked if q.startswith("Who")}) == [False, True]
    undefined = data["configs"]["reviewer off"]["undefined_terms"][0]
    assert undefined["answer_status"] == "answered" and undefined["reviewer"] is None


def test_the_trap_step_runs_each_trap_item_three_times_and_counts_per_trap() -> None:
    items = [
        item("easy"),
        item("revenue-trap", traps=["net_revenue", "cancelled_orders"]),
        item("orders-trap", Split.HOLDOUT, traps=["cancelled_orders"]),
    ]
    lines: list[str] = []
    ctx = cal.Context(
        SESSION,
        items,
        ScriptedEvaluator({"revenue-trap": [False] * 3, "orders-trap": [False, True, False]}),
        None,
        4,
        lines.append,
    )
    target = _Target()
    data = cal.traps_step(ctx, target, 3)
    assert sorted(target.seen) == [
        (i, n) for i in ("orders-trap", "revenue-trap") for n in (1, 2, 3)
    ]
    assert data["per_trap"]["cancelled_orders"] == {"items": 2, "runs": 6, "passed_runs": 1}
    assert data["passed_at_least_once"] == ["orders-trap"]
    assert any("orders-trap" in line and "1 of 3 runs" in line for line in lines)


class _Sink:
    def __init__(self) -> None:
        self.events: list[tuple[str, str | None]] = []

    def started(self, experiment) -> None:
        self.events.append(("started", None))

    def item_done(self, experiment, item_id: str) -> None:
        assert item_id in experiment.results
        self.events.append(("item", item_id))


def test_each_item_reaches_the_sink_as_soon_as_its_runs_finish() -> None:
    sink = _Sink()
    items = [item("d1"), item("h1", Split.HOLDOUT)]
    evaluator = ScriptedEvaluator({"d1": [True], "h1": [True, False, True]})
    runner = ExperimentRunner(_Target(), evaluator, Scheme(), concurrency=2, sink=sink)
    result = runner.run(items, "v1", session_id=SESSION)
    assert sink.events[0] == ("started", None)
    assert sorted(e[1] for e in sink.events[1:]) == ["d1", "h1"]
    assert list(result.results) == ["d1", "h1"] and result.final_sql["h1"] == "SELECT 1"


def test_every_calibration_step_is_a_command() -> None:
    steps = ("canary", "traps", "experiment", "analyzer", "stability", "agents", "confirm")
    words = (
        "experiment-starting",
        "experiment-candidate",
        "stability-starting",
        "stability-candidate",
        "analyzer-high",
    )
    for step in steps + words:
        result = CliRunner().invoke(app, ["calibrate", step, "--help"])
        assert result.exit_code == 0, step


def _record(folder, step: str, stamp: str, data: dict) -> None:
    record = cal.StepRecord(step, f"calibration-{step}", "s", stamp, stamp, 0.0, 0.0, "", data)
    cal.write(record, folder)


def test_the_confirming_rerun_takes_a_real_apparent_regression_first(tmp_path) -> None:
    rows = [
        {"item_id": "steady", "passes": 5, "runs": 5},
        {"item_id": "flaky", "passes": 3, "runs": 5},
    ]
    _record(
        tmp_path, "stability", "2026-10-23T09:00:00", {"knowledge_version": "v2", "items": rows}
    )
    assert cal.confirm_choice(tmp_path) == ("flaky", "v2")
    comparison = {"confirmations": {"h7": {"split": "holdout"}, "d1": {"split": "dev"}}}
    _record(
        tmp_path,
        "experiment",
        "2026-10-23T10:00:00",
        {"knowledge_version": "v3", "comparison": comparison},
    )
    assert cal.confirm_choice(tmp_path) == ("h7", "v3")
    # an item no longer in the benchmark is never chosen
    assert cal.confirm_choice(tmp_path, known={"steady", "flaky"}) == ("flaky", "v2")
