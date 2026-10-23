"""Each assignment check's own spend cap, zero tokens: the cap comes from pack.yaml, the estimate
names it and never prints a ceiling above it, the cap counts only this check's ledger rows with the
build budget on or off, and a check stopped at the cap engages the kill switch, waits for its runs,
puts the stack back, and prints FAIL or NOT RUN for every requirement before it exits stopped (2).
The ledger is a temporary file; the api is a stand-in recording its requests, in a unit test
only."""

from __future__ import annotations

import copy
import io
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from datapilot.assignments import cost
from datapilot.assignments.live import Api
from datapilot.assignments.report import STOPPED, Report, Result, Stop
from datapilot.config import pack_config
from datapilot.contracts import RunStatus
from datapilot.observability import spend

MODEL = "model-under-test"


@pytest.fixture
def ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "ledger.sqlite"
    monkeypatch.setenv("DATAPILOT_SPEND_LEDGER", str(path))
    return path


def _pack() -> dict:
    pack = copy.deepcopy(pack_config())
    pack["budgets"]["tokens_per_run"] = 60_000
    pack["prices"][MODEL] = {"input": 0.10, "cached_input": 0.01, "output": 0.50}
    return pack


def _spend(dollars: float, activity: str = "assignment") -> None:
    """One ledger row costing `dollars` (output tokens at gpt-6-luna's 0.50 per million)."""
    tokens = round(dollars / 0.50 * 1_000_000)
    spend.record(
        component="analyst",
        model="gpt-6-luna",
        usage=spend.Usage(0, 0, tokens),
        activity=activity,
    )


def test_every_check_has_a_spend_cap_of_one_dollar_in_the_pack() -> None:
    assert pack_config()["assignments"]["check_cap_usd"] == 1.00
    assert cost.check_cap_usd() == 1.00


def test_a_pack_without_a_check_cap_stops_before_any_model_call() -> None:
    pack = _pack()
    del pack["assignments"]
    with pytest.raises(Stop, match=r"assignments\.check_cap_usd"):
        cost.check_cap_usd(pack)


def test_the_estimate_names_the_cap_before_the_first_model_call() -> None:
    planned = [cost.Planned("analyst runs", 12, MODEL)]
    lines = cost.estimate_lines(planned, _pack(), cap_usd=1.00)
    assert lines[0] == (
        "This check makes live model calls, about 7.2 cents, and stops at 1.00 dollar"
    )
    assert "the ceiling is 36.0 cents" in lines[-2]
    assert "assignments.check_cap_usd" in lines[-1]


def test_no_printed_ceiling_exceeds_the_cap() -> None:
    planned = [cost.Planned("benchmark runs", 167, MODEL)]  # 501 cents at the output rate
    lines = cost.estimate_lines(planned, _pack(), cap_usd=1.00)
    assert "the ceiling is 100.0 cents" in lines[-2]
    assert "without the cap, 501.0 cents" in lines[-2]
    assert lines[0].endswith("and stops at 1.00 dollar")
    assert cost.estimate_lines(planned, _pack(), cap_usd=1.50)[0].endswith("stops at 1.50 dollars")


def test_the_cap_counts_only_this_checks_rows(ledger: Path) -> None:
    _spend(5.0)  # an earlier check
    mark = cost.ledger_mark()
    _spend(0.30)
    _spend(2.0, activity="development")  # other work on the same machine
    cap = cost.Cap(usd=1.00, mark=mark, activity="assignment", headroom_usd=0.24)
    assert cap.spent() == pytest.approx(0.30)
    cap.check()  # 0.30 plus 0.24 for the runs under way is within 1.00


@pytest.mark.parametrize("build_budget", ["0", "1"])
def test_the_cap_stops_the_check_with_the_build_budget_on_or_off(
    ledger: Path, monkeypatch: pytest.MonkeyPatch, build_budget: str
) -> None:
    monkeypatch.setenv("DATAPILOT_BUILD_BUDGET", build_budget)
    mark = cost.ledger_mark()
    cap = cost.Cap(usd=1.00, mark=mark, activity="assignment", headroom_usd=0.24)
    _spend(0.70)
    cap.check()
    _spend(0.07)  # 0.77 spent: the runs under way could take it past 1.00
    with pytest.raises(cost.CapReached) as reached:
        cap.check()
    assert isinstance(reached.value, Stop)
    assert cap.reached
    with pytest.raises(cost.CapReached):
        cap.check()  # once reached, it stays reached


def test_the_headroom_covers_every_run_the_check_can_have_under_way() -> None:
    pack = _pack()
    headroom = cost.headroom_usd([cost.Planned("analyst runs", 12, MODEL)], pack)
    at_once = max(8, int(pack["evaluation"]["concurrency"]))
    assert headroom == pytest.approx(at_once * 60_000 * 0.50 / 1_000_000)


class _Stack(Api):
    """The api as the check sees it, recording each request; runs end once the switch engages."""

    def __init__(self, cap: cost.Cap) -> None:
        self.calls: list[str] = []
        self.switch = "released"
        self.level = "assisted"
        self.statuses = {"run-1": RunStatus.RUNNING}
        self._setup(cap)

    def control(self):  # type: ignore[override]
        return SimpleNamespace(
            kill_switch=self.switch, autonomy_level=SimpleNamespace(value=self.level)
        )

    def kill_switch(self, action: str) -> None:
        self.calls.append(f"kill switch {action}")
        self.switch = {"arm": "armed", "engage": "engaged", "release": "released"}[action]
        if action == "engage":
            self.level = "report_only"  # engaging drops the system to the report-only level
            self.statuses = dict.fromkeys(self.statuses, RunStatus.BLOCKED_KILLSWITCH)

    def autonomy(self, level: str) -> None:
        self.calls.append(f"autonomy {level}")
        self.level = level

    def run(self, run_id: str):  # type: ignore[override]
        return SimpleNamespace(status=self.statuses[run_id])


def test_reaching_the_cap_engages_the_kill_switch_once_and_starts_no_new_run(
    ledger: Path,
) -> None:
    cap = cost.Cap(usd=1.00, mark=cost.ledger_mark(), activity="assignment", headroom_usd=0.0)
    api = _Stack(cap)
    api.started.add("run-1")
    _spend(1.00)
    for _ in range(2):
        with pytest.raises(cost.CapReached):
            api.guard()
    assert api.calls == ["kill switch arm", "kill switch engage"]
    with pytest.raises(cost.CapReached):
        api.submit("question.asked", {"question": "q"}, "event")


def test_the_wind_down_puts_the_stack_back_as_a_normal_end_would(ledger: Path) -> None:
    cap = cost.Cap(usd=1.00, mark=cost.ledger_mark(), activity="assignment", headroom_usd=0.0)
    api = _Stack(cap)
    api.started.add("run-1")
    _spend(1.00)
    with pytest.raises(cost.CapReached):
        api.guard()
    assert api.wind_down(seconds=5) == []
    assert api.switch == "released" and api.level == "assisted"
    assert api.calls[-2:] == ["kill switch release", "autonomy assisted"]


def test_a_check_with_no_run_of_its_own_leaves_the_kill_switch_alone(ledger: Path) -> None:
    cap = cost.Cap(usd=1.00, mark=cost.ledger_mark(), activity="assignment", headroom_usd=0.0)
    api = _Stack(cap)  # the in-process benchmark of Assignment 4 starts no worker run
    _spend(1.00)
    with pytest.raises(cost.CapReached):
        api.guard()
    assert api.wind_down(seconds=5) == [] and api.calls == []


def test_a_run_still_under_way_keeps_the_kill_switch_engaged(ledger: Path) -> None:
    cap = cost.Cap(usd=1.00, mark=cost.ledger_mark(), activity="assignment", headroom_usd=0.0)
    api = _Stack(cap)
    api.started.add("run-1")
    _spend(1.00)
    with pytest.raises(cost.CapReached):
        api.guard()
    api.statuses["run-1"] = RunStatus.RUNNING  # it did not end
    assert api.wind_down(seconds=0) == ["run-1"]
    assert api.switch == "engaged"


def test_a_stopped_check_prints_every_requirement_and_exits_stopped(ledger: Path) -> None:
    from datapilot.assignments.runner import stop_at_cap

    out = io.StringIO()
    report = Report("Assignment 1: Agent loop", out=out)
    report.add(Result(1, "A deterministic requirement", True))
    report.add(Result(2, "Another one", False, "fix it"))
    mark = cost.ledger_mark()
    cap = cost.Cap(usd=1.00, mark=mark, activity="assignment", headroom_usd=0.0)
    api = _Stack(cap)
    _spend(1.0123)
    with pytest.raises(cost.CapReached) as reached:
        api.guard()
    live = [(3, "Live: the first live requirement"), (4, "Live: the second")]
    code = stop_at_cap(
        reached.value, report, api, live, slug="agent-loop", mark=mark, activity="assignment"
    )
    text = out.getvalue()
    assert code == STOPPED == 2
    assert "Stopped: this check reached its spend cap of 1.00 dollar" in text
    assert "spent 1.0123 dollars (101.23 cents) in 1 model calls" in text
    assert "NOT RUN  3. Live: the first live requirement" in text
    assert "NOT RUN  4. Live: the second" in text
    assert "FAIL  2. Another one" in text
    assert "Result: STOPPED at the spend cap, 1 of 4 requirements passed, 1 failed, 2 not run" in (
        text
    )
    assert "make check-assignment NAME=agent-loop" in text


def test_a_requirement_judged_before_the_stop_keeps_its_line(ledger: Path) -> None:
    from datapilot.assignments.runner import stop_at_cap

    out = io.StringIO()
    report = Report("Assignment 4: Hill-climbing loop", out=out)
    report.add(Result(9, "Live: the critic", True))
    cap = cost.Cap(usd=1.00, mark=cost.ledger_mark(), activity="assignment", headroom_usd=0.0)
    api = _Stack(cap)
    _spend(1.0)
    with pytest.raises(cost.CapReached) as reached:
        api.guard()
    live = [(9, "Live: the critic"), (10, "Live: the gate")]
    stop_at_cap(
        reached.value,
        report,
        api,
        live,
        slug="hill-climbing-loop",
        mark=cap.mark,
        activity="assignment",
    )
    text = out.getvalue()
    assert "NOT RUN  9." not in text and "NOT RUN  10. Live: the gate" in text
    assert "1 of 2 requirements passed, 0 failed, 1 not run" in text


def _hill_climbing_check():
    import importlib.util

    from datapilot.assignments import assignment

    spec = importlib.util.spec_from_file_location(
        "hill_climbing_check_cap", assignment("hill-climbing-loop").check_file
    )
    assert spec is not None and spec.loader is not None
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    return check


def test_the_in_process_benchmark_starts_no_analyst_run_past_the_cap(ledger: Path) -> None:
    check = _hill_climbing_check()
    asked: list[str] = []
    cap = cost.Cap(usd=1.00, mark=cost.ledger_mark(), activity="assignment", headroom_usd=0.0)
    target = check.RecordingTarget(lambda question, version: asked.append(question), cap)
    target("first question", "v1")
    _spend(1.00)
    with pytest.raises(cost.CapReached):
        target("second question", "v1")
    assert asked == ["first question"]


def test_an_experiment_that_met_the_cap_is_never_kept(ledger: Path) -> None:
    check = _hill_climbing_check()
    import uuid

    from datapilot.contracts import Split

    cap = cost.Cap(usd=1.00, mark=cost.ledger_mark(), activity="assignment", headroom_usd=0.0)

    def spending(question: str, version: str):
        _spend(0.60)
        raise RuntimeError("the answer does not matter here")

    runner = check.CappedRunner(target=spending, evaluator=None, concurrency=1, cap=cap)
    items = [SimpleNamespace(id=f"item-{n}", question=f"q{n}", split=Split.DEV) for n in range(2)]
    with pytest.raises(cost.CapReached):  # it went past the cap: the experiment is no result
        runner.run(items, "v1", session_id=uuid.uuid4())
    with pytest.raises(cost.CapReached):  # and nothing more starts
        runner.rerun(items[0], "v1", 3)


def test_every_check_names_its_live_requirements_for_the_stop() -> None:
    import ast

    from datapilot.assignments import assignment
    from datapilot.names import SECTIONS_BY_SLUG

    for slug in SECTIONS_BY_SLUG:
        tree = ast.parse(assignment(slug).check_file.read_text(encoding="utf-8"))
        gates = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "live_gate"
        ]
        live = [g for g in gates if not (isinstance(g.args[0], ast.List) and not g.args[0].elts)]
        assert live, f"{slug}: no live gate with planned runs"
        for gate in live:
            assert any(k.arg == "live" for k in gate.keywords), (
                f"{slug}: live_gate must name the live requirements (live=...) so a stop at the "
                "spend cap prints each one"
            )


# The old recommendation: a 2-dollar limit with a 1-dollar alert (never "1.2 dollars" and the like)
OLD_KEY_LIMIT = re.compile(
    r"(?<![\d.,])2[- ]dollar|\btwo dollars\b|1-dollar alert|alert at 1 dollar\b", re.IGNORECASE
)
WHERE_LEARNERS_READ = ("docs", "guide", "setup", "slides/source", "use-in-your-repo")


def test_no_page_recommends_the_old_learner_key_limit() -> None:
    from datapilot.settings import REPO

    files = [REPO / "README.md", *REPO.glob("section-*/**/*.md")]
    for folder in WHERE_LEARNERS_READ:
        files += [p for p in (REPO / folder).rglob("*") if p.suffix in {".md", ".py"}]
    stale = [
        f"{path.relative_to(REPO)}: {hit.group(0)}"
        for path in files
        for hit in OLD_KEY_LIMIT.finditer(path.read_text(encoding="utf-8"))
    ]
    assert not stale, stale


def test_the_costs_page_states_the_key_limit_and_the_alert_once() -> None:
    from datapilot.settings import REPO

    text = (REPO / "docs" / "costs.md").read_text(encoding="utf-8")
    assert text.count("a spending limit of 3 dollars") == 1
    assert text.count("an alert at 1.50 dollars") == 1
    assert "1.00 dollar" in text  # the check cap, in the learner cost table
