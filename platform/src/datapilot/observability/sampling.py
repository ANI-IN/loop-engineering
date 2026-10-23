"""Which benchmark runs inside an experiment are traced in LangSmith.

Every demo run and every assignment check run is traced in full. A benchmark run inside an
experiment (the hill-climbing runner's experiments, calibration, and the benchmark inside the check
of Assignment 4: Hill-climbing loop) is traced only as a sample, at `tracing.experiment_sample_rate`
in the pack, so experiments stay well inside the free LangSmith plan's monthly traces. Pass and fail
are scored locally on every run either way; the holdout ledger is the record of an experiment.

The decision is LangSmith's own sampling rule (the one the SDK applies for its tracing sampling
rate) on the run id, made once per run by the experiment runner. It is not the SDK's setting on a
client: that decides each root trace on its own, and one benchmark run makes several (one per
attempt and one for the reviewer), so a run would be kept in part. Here a run is traced whole or not
at all, and a demo in the same process is never sampled.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

NOT_TRACED = "Not traced: experiment runs are traced as a sample"


def experiment_sample_rate(pack: dict[str, Any] | None = None) -> float:
    """The share of benchmark runs inside experiments that are traced, from the pack's tracing
    block; a pack without one traces every run."""
    if pack is None:
        from datapilot.config import pack_config

        pack = pack_config()
    rate = float((pack.get("tracing") or {}).get("experiment_sample_rate", 1.0))
    if not 0.0 <= rate <= 1.0:
        raise ValueError(f"tracing.experiment_sample_rate must be between 0 and 1, not {rate}")
    return rate


def sampled_in(run_id: UUID | str, rate: float) -> bool:
    """Whether this run is traced: LangSmith's sampling rule on the run id, the same choice the SDK
    makes for a trace with this id at this rate."""
    from langsmith._internal._sampling import is_sampled_by_id

    return bool(is_sampled_by_id(str(run_id), rate))


def sample_note(rate: float) -> str:
    """The sentence beside an experiment's trace list."""
    if rate >= 1.0:
        return ""
    if rate <= 0.0:
        return "Experiment runs are not traced."
    return f"Experiment runs are traced as a sample: about 1 run in {round(1 / rate)}."
