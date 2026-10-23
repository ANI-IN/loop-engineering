"""Clearing a metric family for the unattended level on the gate's own confirmed standard, zero
tokens and no database: every holdout item passes at least 2 of 3 runs, and an item that falls
short counts only when it passes at least 2 of 3 more runs (the confirming re-run). The minimum
number of holdout items (Assignment 4: Hill-climbing loop) is applied before any re-run."""

from __future__ import annotations

import importlib.util
import sys

import pytest
from loop4_doubles import experiment, item

from datapilot.assignments import VARIANTS, WITHHELD_REASON, assignment, solutions_withheld
from datapilot.config import pack_config
from datapilot.contracts import BenchmarkItem, ItemResult, Split
from datapilot.loop4_hill_climbing import eligibility, extension
from datapilot.loop4_hill_climbing.measurement import Scheme
from datapilot.loop4_hill_climbing.pack_files import load_benchmark

FAMILIES = ["revenue", "aov"]


def _holdout(item_id: str, family: str = "revenue") -> BenchmarkItem:
    return item(item_id, Split.HOLDOUT, metric_family=family)


def _candidate(run_passes: dict[str, list[bool]], scheme: Scheme | None = None):
    scheme = scheme or Scheme()
    found = experiment(
        "v2",
        {i: scheme.passes(Split.HOLDOUT, runs) for i, runs in run_passes.items()},
        {i: Split.HOLDOUT for i in run_passes},
    )
    for item_id, runs in run_passes.items():
        found.results[item_id] = ItemResult(
            item_id=item_id, passed=found.passed(item_id), reason="", run_passes=runs
        )
    return found


class _Rerun:
    """Answers each confirming re-run from a script and records what was asked."""

    def __init__(self, script: dict[str, list[bool]]) -> None:
        self.script, self.asked = script, []

    def __call__(self, benchmark_item: BenchmarkItem, times: int) -> list[bool]:
        self.asked.append((benchmark_item.id, times))
        return self.script[benchmark_item.id][:times]


REVENUE = [_holdout("r1"), _holdout("r2"), _holdout("r3")]


def test_a_family_whose_holdout_items_each_pass_two_of_three_is_cleared_without_reruns() -> None:
    candidate = _candidate({"r1": [True, True, True], "r2": [True, False, True], "r3": [True] * 3})
    rerun = _Rerun({})
    clearance = eligibility.confirmed_clearance(REVENUE, candidate, rerun, Scheme(), FAMILIES)
    assert clearance.cleared == ["revenue"] and rerun.asked == []


def test_an_item_that_falls_short_counts_when_the_confirming_rerun_passes_two_of_three() -> None:
    candidate = _candidate({"r1": [True] * 3, "r2": [True, False, False], "r3": [True] * 3})
    rerun = _Rerun({"r2": [True, False, True]})
    clearance = eligibility.confirmed_clearance(REVENUE, candidate, rerun, Scheme(), FAMILIES)
    assert rerun.asked == [("r2", 3)], "the scheme's 3 more runs, for the short item only"
    assert clearance.cleared == ["revenue"]
    assert clearance.reruns == {"r2": [True, False, True]}


def test_an_item_that_falls_short_twice_keeps_its_family_below_the_unattended_level() -> None:
    candidate = _candidate({"r1": [True] * 3, "r2": [False, False, True], "r3": [True] * 3})
    rerun = _Rerun({"r2": [True, False, False]})
    clearance = eligibility.confirmed_clearance(REVENUE, candidate, rerun, Scheme(), FAMILIES)
    assert clearance.cleared == [] and clearance.reruns == {"r2": [True, False, False]}


def test_a_family_stops_at_its_first_item_that_falls_short_twice() -> None:
    candidate = _candidate({"r1": [False] * 3, "r2": [False] * 3, "r3": [True] * 3})
    rerun = _Rerun({"r1": [False] * 3, "r2": [True] * 3})
    eligibility.confirmed_clearance(REVENUE, candidate, rerun, Scheme(), FAMILIES)
    assert rerun.asked == [("r1", 3)], "no more model calls once the family is lost"


def test_the_minimum_number_of_holdout_items_applies_before_any_rerun(monkeypatch) -> None:
    monkeypatch.setattr(extension, "enough_holdout_items", lambda count: count >= 3)
    items = [*REVENUE, _holdout("a1", "aov")]
    candidate = _candidate(
        {"r1": [True] * 3, "r2": [True] * 3, "r3": [True] * 3, "a1": [False, True, False]}
    )
    rerun = _Rerun({"a1": [True] * 3})
    clearance = eligibility.confirmed_clearance(items, candidate, rerun, Scheme(), FAMILIES)
    assert clearance.cleared == ["revenue"] and clearance.below_minimum == ["aov"]
    assert rerun.asked == [], "a family below the minimum is never re-run"


def test_the_class_rule_has_no_minimum_so_one_passing_item_clears_its_family() -> None:
    items = [_holdout("a1", "aov")]
    candidate = _candidate({"a1": [True, True, False]})
    clearance = eligibility.confirmed_clearance(items, candidate, _Rerun({}), Scheme(), FAMILIES)
    assert clearance.cleared == ["aov"] and clearance.below_minimum == []


def test_the_reruns_and_the_threshold_come_from_the_scheme() -> None:
    scheme = Scheme(holdout_repeats=5, holdout_pass_threshold=3, holdout_regression_reruns=5)
    candidate = _candidate({"r1": [True, True, False, False, False]}, scheme)
    rerun = _Rerun({"r1": [True, True, False, False, True]})
    clearance = eligibility.confirmed_clearance(
        [_holdout("r1")], candidate, rerun, scheme, FAMILIES
    )
    assert rerun.asked == [("r1", 5)] and clearance.cleared == ["revenue"]


def test_only_the_packs_families_and_measured_holdout_items_are_judged() -> None:
    items = [*REVENUE, _holdout("x1", "not-in-the-pack"), item("d1", Split.DEV)]
    candidate = _candidate({"r1": [True] * 3, "r2": [True] * 3, "x1": [False] * 3})
    rerun = _Rerun({})
    clearance = eligibility.confirmed_clearance(items, candidate, rerun, Scheme(), FAMILIES)
    # r3 was not measured in this experiment, so revenue is judged on r1 and r2 alone
    assert clearance.cleared == ["revenue"] and rerun.asked == []


# --- Assignment 4: Hill-climbing loop still lines up -------------------------------------------
def _every_holdout_item_fell_short_then_passed():
    items = load_benchmark()
    holdout = {i.id: [False, False, True] for i in items if i.split is Split.HOLDOUT}
    rerun = _Rerun({i: [True, True, True] for i in holdout})
    families = pack_config()["autonomy"]["metric_families"]
    clearance = eligibility.confirmed_clearance(
        items, _candidate(holdout), rerun, Scheme.from_pack(), families
    )
    asked = {benchmark_item_id for benchmark_item_id, _ in rerun.asked}
    by_family = {i.id: i.metric_family for i in items}
    return clearance, {by_family[i] for i in asked}


def test_the_starter_has_no_minimum_so_average_order_value_is_re_run_and_cleared() -> None:
    clearance, rerun_families = _every_holdout_item_fell_short_then_passed()
    assert "aov" in clearance.cleared and "aov" in rerun_families


@pytest.mark.skipif(solutions_withheld(), reason=WITHHELD_REASON)
@pytest.mark.parametrize("variant", VARIANTS)
def test_each_solutions_minimum_applies_before_the_confirmed_standard(
    variant: str, monkeypatch
) -> None:
    path = (
        assignment("hill-climbing-loop").solution(variant)
        / "files/platform/src/datapilot/loop4_hill_climbing/extension.py"
    )
    spec = importlib.util.spec_from_file_location(f"solution_extension_{variant}", path)
    assert spec is not None and spec.loader is not None
    solution = importlib.util.module_from_spec(spec)
    # no bytecode beside the solution: its folder must hold only the solution's own files
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    spec.loader.exec_module(solution)
    config = pack_config()
    patched = {**config, "autonomy": {**config["autonomy"], "minimum_holdout_items": 3}}
    monkeypatch.setattr(solution, "pack_config", lambda: patched)
    monkeypatch.setattr(extension, "enough_holdout_items", solution.enough_holdout_items)
    clearance, rerun_families = _every_holdout_item_fell_short_then_passed()
    assert clearance.below_minimum == ["aov"], "one holdout item: below the minimum"
    assert "aov" not in rerun_families, "a family below the minimum is never re-run"
    assert "aov" not in clearance.cleared and "revenue" in clearance.cleared
