"""The promotion gate: a candidate knowledge version replaces the active one only when

1. its holdout passes exceed the active version's,
2. it has zero confirmed regressions on the dev split and on the holdout split,
3. a person approved it, under their name (an empty name or "console" approves nothing), and
4. every rule it adds to the active version passes the overfit guard (overfit_flags, from
   overfit_guard.new_rule_flags), so a version written without the guard is blocked whatever its
   holdout count.

Both experiments must come from the current live session (store.baseline_for raises otherwise).
The decision records every reason and one plain sentence for the console.

An apparent regression (passed under the active version, fails under the candidate) counts only
after confirming re-runs (find_regressions, after decide below):

- a dev item runs once per version, so it is re-run under both versions the same number of times
  (`evaluation.dev_regression_reruns`, 2). It is a confirmed regression only when the candidate
  fails at least `evaluation.dev_regression_threshold` (2) of its re-runs and the active version
  passes at least as many of its own: an item unstable under both versions never counts;
- a holdout item already ran 3 times per version and passed on 2 under the active version, so only
  the candidate is re-run (`evaluation.holdout_regression_reruns`, 3); it counts when at least
  `evaluation.holdout_regression_fail_threshold` (2) of those re-runs fail.

Each confirmation is recorded on the candidate experiment and shown step by step in the ledger.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol
from uuid import UUID

from datapilot.contracts import BenchmarkItem, Split
from datapilot.contracts.api import approver_name
from datapilot.loop4_hill_climbing.experiment import Confirmation, ExperimentResult
from datapilot.loop4_hill_climbing.measurement import Scheme

Rerun = Callable[[BenchmarkItem, int], list[bool]]  # (item, times) -> passes under one version


class StepSink(Protocol):
    """Where each confirmation step goes as it happens, so the console ledger can show it."""

    def step(self, experiment_id: UUID, confirmation: Confirmation) -> None: ...


@dataclass(frozen=True)
class Regressions:
    dev: list[str] = field(default_factory=list)
    holdout: list[str] = field(default_factory=list)
    not_confirmed: list[str] = field(default_factory=list)  # apparent, cleared by the re-runs

    @property
    def total(self) -> int:
        return len(self.dev) + len(self.holdout)


@dataclass
class DevConfirmation(Confirmation):
    """A dev item's confirmation: the candidate's re-runs and, beside them, the active version's."""

    active_reruns: list[bool] = field(default_factory=list)
    active_planned: int = 0  # how many active-version re-runs the scheme asks for

    def as_dict(self) -> dict[str, object]:
        return {
            **super().as_dict(),
            "active_reruns": self.active_reruns,
            "active_runs": self.active_planned or len(self.active_reruns),
            "active_passes": self.active_reruns.count(True),
        }


def confirmation_from(item_id: str, found: dict[str, Any]) -> Confirmation:
    """A confirmation read back from its ledger entry (Confirmation.as_dict)."""
    split, planned = Split(found["split"]), int(found.get("runs") or 0)
    reruns, steps = list(found["reruns"]), list(found["steps"])
    if found.get("active_runs"):
        return DevConfirmation(
            item_id,
            split,
            reruns,
            found["confirmed"],
            steps,
            planned,
            active_reruns=list(found.get("active_reruns") or []),
            active_planned=int(found["active_runs"]),
        )
    return Confirmation(item_id, split, reruns, found["confirmed"], steps, planned)


@dataclass(frozen=True)
class GateDecision:
    verdict: Literal["promoted", "blocked"]
    ready_for_approval: bool
    reasons: list[str]
    sentence: str
    candidate_version: str
    active_version: str
    candidate_holdout_passes: int
    active_holdout_passes: int
    holdout_total: int
    regressions: Regressions
    approved_by: str | None


def decide(
    active: ExperimentResult,
    candidate: ExperimentResult,
    regressions: Regressions,
    *,
    approved_by: str | None,
    overfit_flags: Sequence[str] = (),
) -> GateDecision:
    given = approved_by
    if active.session_id != candidate.session_id:
        raise ValueError("both experiments must come from the same live session")
    approved_by = approver_name(given)
    a, c = active.passes(Split.HOLDOUT), candidate.passes(Split.HOLDOUT)
    total = candidate.total(Split.HOLDOUT)
    better = c > a
    clean = regressions.total == 0
    reasons = [
        f"{'pass' if better else 'fail'}: holdout passes {c} of {total} against {a} for "
        f"{active.knowledge_version}",
        f"{'pass' if not regressions.dev else 'fail'}: dev regressions {len(regressions.dev)}"
        + (f" ({', '.join(regressions.dev)})" if regressions.dev else ""),
        f"{'pass' if not regressions.holdout else 'fail'}: holdout regressions "
        f"{len(regressions.holdout)}"
        + (f" ({', '.join(regressions.holdout)})" if regressions.holdout else ""),
        approval_reason(approved_by, given),
        f"{'pass' if not overfit_flags else 'fail'}: overfit guard on the new rules"
        + (f" ({', '.join(overfit_flags)})" if overfit_flags else ""),
    ]
    ready = better and clean and not overfit_flags
    promoted = ready and bool(approved_by)
    name = candidate.knowledge_version
    if promoted:
        sentence = (
            f"Promoted: {name} passes {c} of {total} holdout items against {a}, with no "
            f"regressions, approved by {approved_by}."
        )
    elif ready:
        sentence = (
            f"Ready for human approval: {name} passes {c} of {total} holdout items against {a}, "
            "with no regressions."
        )
    elif overfit_flags:
        sentence = (
            f"Blocked: {name} has {len(overfit_flags)} rule"
            f"{'s' if len(overfit_flags) != 1 else ''} the overfit guard rejects "
            f"({', '.join(overfit_flags)})."
        )
    elif not clean:
        sentence = (
            f"Blocked: {name} has {regressions.total} regression"
            f"{'s' if regressions.total != 1 else ''} on items that passed under "
            f"{active.knowledge_version}."
        )
    else:
        sentence = (
            f"Blocked: {name} passes {c} of {total} holdout items against {a}, so it is no better "
            f"than {active.knowledge_version}."
        )
    return GateDecision(
        verdict="promoted" if promoted else "blocked",
        ready_for_approval=ready,
        reasons=reasons,
        sentence=sentence,
        candidate_version=name,
        active_version=active.knowledge_version,
        candidate_holdout_passes=c,
        active_holdout_passes=a,
        holdout_total=total,
        regressions=regressions,
        approved_by=approved_by,
    )


def approval_reason(named: str | None, given: str | None) -> str:
    if named:
        return f"pass: human approval by {named}"
    if given is None:
        return "fail: human approval not given yet"
    return "fail: human approval needs a person's name"


def confirming_step(n: int, *, both: bool = False) -> str:
    return f"Apparent regression: confirming with {n} more runs" + (
        " of each version" if both else ""
    )


def outcome_step(
    confirmed: bool, reruns: list[bool], active_reruns: list[bool] | None = None
) -> str:
    failed, n = reruns.count(False), len(reruns)
    if active_reruns is not None:
        head = "Confirmed regression" if confirmed else "Not a regression"
        return (
            f"{head}: the candidate failed {failed} of {n} more runs, the active version passed "
            f"{active_reruns.count(True)} of {len(active_reruns)}"
        )
    if confirmed:
        return f"Confirmed regression: failed {failed} of {n} more runs"
    return f"Not a regression: passed {n - failed} of {n} more runs"


def find_regressions(
    items: Sequence[BenchmarkItem],
    active: ExperimentResult,
    candidate: ExperimentResult,
    rerun: Rerun,
    scheme: Scheme,
    sink: StepSink | None = None,
    *,
    active_rerun: Rerun | None = None,
) -> Regressions:
    """Items that passed under the active version and fail under the candidate, each confirmed by
    re-runs (scheme.regression_reruns, scheme.active_reruns, scheme.regression_confirmed): `rerun`
    re-runs the candidate and `active_rerun` the active version, which every dev item needs. Every
    confirmation is recorded on the candidate experiment and sent to the sink step by step."""
    dev, holdout, not_confirmed = [], [], []
    for item in items:
        if item.id not in active.results or item.id not in candidate.results:
            continue
        if not active.passed(item.id) or candidate.passed(item.id):
            continue
        times, active_times = scheme.regression_reruns(item.split), scheme.active_reruns(item.split)
        confirmation: Confirmation
        if active_times:
            if active_rerun is None:
                raise ValueError(
                    f"{item.id}: a dev regression is confirmed by re-running the active version too"
                )
            confirmation = DevConfirmation(
                item.id,
                item.split,
                steps=[confirming_step(times, both=True)],
                planned=times,
                active_planned=active_times,
            )
        else:
            confirmation = Confirmation(
                item.id, item.split, steps=[confirming_step(times)], planned=times
            )
        candidate.confirmations[item.id] = confirmation
        if sink:
            sink.step(candidate.experiment_id, confirmation)
        confirmation.reruns = rerun(item, times)
        both = None
        if isinstance(confirmation, DevConfirmation) and active_rerun is not None:
            both = confirmation.active_reruns = active_rerun(item, active_times)
        confirmation.confirmed = scheme.regression_confirmed(item.split, confirmation.reruns, both)
        confirmation.steps.append(outcome_step(confirmation.confirmed, confirmation.reruns, both))
        if sink:
            sink.step(candidate.experiment_id, confirmation)
        if not confirmation.confirmed:
            not_confirmed.append(item.id)
        else:
            (holdout if item.split is Split.HOLDOUT else dev).append(item.id)
    return Regressions(dev=dev, holdout=holdout, not_confirmed=not_confirmed)
