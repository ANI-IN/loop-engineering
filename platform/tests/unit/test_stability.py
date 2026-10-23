"""The calibration stability filter, with a stub target and a scripted evaluator (zero tokens)."""

from __future__ import annotations

from loop4_doubles import SESSION, ScriptedEvaluator, answered, item
from typer.testing import CliRunner

from datapilot.cli import app
from datapilot.contracts import Split
from datapilot.loop4_hill_climbing.experiment import ExperimentRunner
from datapilot.loop4_hill_climbing.measurement import Scheme
from datapilot.loop4_hill_climbing.stability import Limits, stability

ITEMS = [
    item("steady-pass", Split.HOLDOUT),
    item("steady-fail", Split.HOLDOUT, metric_family="orders"),
    item("coin-flip", Split.HOLDOUT),
    item("one-pass", Split.HOLDOUT, metric_family="customers"),
    item("dev-only"),
]
OUTCOMES = {
    "steady-pass": [True, True, True, False, True],
    "steady-fail": [False] * 5,
    "coin-flip": [True, False, True, False, False],
    "one-pass": [False, True, False, False, False],
}


def test_the_limits_come_from_the_pack() -> None:
    assert Limits.from_pack() == Limits(runs=5, keep_passes_at_least=4, keep_passes_at_most=1)


def test_stability_runs_each_holdout_item_five_times_and_flags_the_middle() -> None:
    calls: list[str] = []

    def target(question: str, version: str):
        calls.append(version)
        return answered("SELECT 1")

    runner = ExperimentRunner(
        target, ScriptedEvaluator({k: v[:] for k, v in OUTCOMES.items()}), Scheme()
    )
    report = stability(runner, ITEMS, "v1", session_id=SESSION, limits=Limits())
    assert len(calls) == 20 and set(calls) == {"v1"}
    assert {i.item_id: i.passes for i in report.items} == {
        "steady-pass": 4,
        "steady-fail": 0,
        "coin-flip": 2,
        "one-pass": 1,
    }
    assert [i.item_id for i in report.unstable] == ["coin-flip"]
    assert report.unstable[0].metric_family == "revenue"
    assert report.lines()[-1].startswith("stability v1: 1 of 4 holdout items unstable")
    assert runner.scheme.holdout_repeats == 3, "the gate's scheme is left unchanged"


def test_the_command_is_registered() -> None:
    result = CliRunner().invoke(app, ["calibrate", "stability", "--help"])
    assert result.exit_code == 0 and "--version" in result.output and "--target" in result.output
