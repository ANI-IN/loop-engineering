"""The stability filter for calibration: run each holdout item several times under one knowledge
version, through the same experiment runner as the gate, and list the items whose pass count is
neither clearly passing nor clearly failing (by default neither at least 4 of 5 nor at most 1 of 5).

Calibration runs it under the starting and the promoted version; an unstable item is replaced by
another from the same metric family, keeping 15 holdout items and at least three revenue items.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from uuid import UUID

from datapilot.config import pack_config
from datapilot.contracts import BenchmarkItem, Split
from datapilot.loop4_hill_climbing.experiment import ExperimentRunner


@dataclass(frozen=True)
class Limits:
    runs: int = 5
    keep_passes_at_least: int = 4
    keep_passes_at_most: int = 1

    @classmethod
    def from_pack(cls) -> Limits:
        evaluation = pack_config()["evaluation"]
        return cls(
            runs=evaluation["stability_runs"],
            keep_passes_at_least=evaluation["stability_keep_passes_at_least"],
            keep_passes_at_most=evaluation["stability_keep_passes_at_most"],
        )

    def stable(self, passes: int) -> bool:
        return passes >= self.keep_passes_at_least or passes <= self.keep_passes_at_most


@dataclass(frozen=True)
class ItemStability:
    item_id: str
    metric_family: str
    passes: int
    runs: int
    stable: bool


@dataclass(frozen=True)
class StabilityReport:
    knowledge_version: str
    items: list[ItemStability]
    limits: Limits

    @property
    def unstable(self) -> list[ItemStability]:
        return [i for i in self.items if not i.stable]

    def lines(self) -> list[str]:
        out = [
            f"{i.item_id:40} {i.metric_family:10} passed {i.passes} of {i.runs}"
            + ("" if i.stable else "  unstable")
            for i in self.items
        ]
        out.append(
            f"stability {self.knowledge_version}: {len(self.unstable)} of {len(self.items)} "
            f"holdout items unstable (kept only at {self.limits.keep_passes_at_least} or more, "
            f"or {self.limits.keep_passes_at_most} or fewer, passes of {self.limits.runs})"
        )
        return out


def stability(
    runner: ExperimentRunner,
    items: Sequence[BenchmarkItem],
    knowledge_version: str,
    *,
    session_id: UUID,
    limits: Limits,
) -> StabilityReport:
    """Run every holdout item `limits.runs` times under one version and classify each one."""
    repeated = replace(runner, scheme=replace(runner.scheme, holdout_repeats=limits.runs))
    result = repeated.run(items, knowledge_version, session_id=session_id, splits=[Split.HOLDOUT])
    families = {i.id: i.metric_family for i in items}
    rows = []
    for item_id, item_result in result.results.items():
        passes = sum(item_result.run_passes)
        rows.append(
            ItemStability(
                item_id=item_id,
                metric_family=families[item_id],
                passes=passes,
                runs=len(item_result.run_passes),
                stable=limits.stable(passes),
            )
        )
    return StabilityReport(knowledge_version=knowledge_version, items=rows, limits=limits)
