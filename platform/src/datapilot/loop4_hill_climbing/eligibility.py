"""Which metric families may reach the unattended level under a knowledge version.

The class rule, on the gate's own confirmed standard: a family is cleared when every one of its
holdout items passes under the version. An item passes when it passed at least
`holdout_pass_threshold` of its `holdout_repeats` runs in the candidate experiment; an item that
fell short gets the confirming re-run (`holdout_regression_reruns` more runs) and passes when the
re-runs meet the same threshold. A family with too few holdout items to judge
(extension.enough_holdout_items) is out before any re-run. The hill-climbing runner records
cleared families in ops.autonomy_policy (autonomy.mark_eligible); this module only decides.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field

from datapilot.contracts import BenchmarkItem, Split
from datapilot.loop4_hill_climbing import extension
from datapilot.loop4_hill_climbing.experiment import ExperimentResult
from datapilot.loop4_hill_climbing.measurement import Scheme

Rerun = Callable[[BenchmarkItem, int], list[bool]]  # (item, times) -> passes under the candidate


def holdout_by_family(items: Iterable[BenchmarkItem]) -> dict[str, list[str]]:
    families: dict[str, list[str]] = {}
    for item in items:
        if item.split is Split.HOLDOUT:
            families.setdefault(item.metric_family, []).append(item.id)
    return families


def eligible_families(
    items: Sequence[BenchmarkItem], passed: Callable[[str], bool], families: Iterable[str]
) -> set[str]:
    """Families of the pack whose every holdout item passed, where the family has enough
    holdout items to judge (extension.enough_holdout_items)."""
    holdout = holdout_by_family(items)
    return {
        family
        for family in families
        if (ids := holdout.get(family))
        and all(passed(item_id) for item_id in ids)
        and extension.enough_holdout_items(len(ids))
    }


@dataclass(frozen=True)
class Clearance:
    cleared: list[str]
    below_minimum: list[str] = field(default_factory=list)  # never re-run, never cleared
    reruns: dict[str, list[bool]] = field(default_factory=dict)  # item id -> confirming re-run


def confirmed_clearance(
    items: Sequence[BenchmarkItem],
    candidate: ExperimentResult,
    rerun: Rerun,
    scheme: Scheme,
    families: Iterable[str],
) -> Clearance:
    """The families the candidate clears for the unattended level. The minimum number of holdout
    items comes first; only the families that meet it are judged, and a family stops at its first
    item that falls short twice, so no model call is spent on a family already lost."""
    measured = [i for i in items if i.id in candidate.results]
    by_id = {i.id: i for i in measured}
    holdout = holdout_by_family(measured)
    judged = [f for f in families if f in holdout]
    enough = [f for f in judged if extension.enough_holdout_items(len(holdout[f]))]
    reruns: dict[str, list[bool]] = {}

    def passes(item_id: str) -> bool:
        if candidate.passed(item_id):
            return True
        if item_id not in reruns:
            times = scheme.regression_reruns(Split.HOLDOUT)
            reruns[item_id] = rerun(by_id[item_id], times)
        return scheme.passes(Split.HOLDOUT, reruns[item_id])

    cleared = [f for f in enough if f in eligible_families(measured, passes, [f])]
    return Clearance(
        cleared=sorted(cleared),
        below_minimum=[f for f in judged if f not in enough],
        reruns=reruns,
    )
