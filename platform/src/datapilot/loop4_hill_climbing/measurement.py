"""The measurement scheme, written down before any comparison run and applied identically to the
active and the candidate version (the gate statistics):

- holdout items run 3 times per version and pass on 2 of 3;
- dev items run once;
- an apparent dev regression (passed under the active version, fails under the candidate) is
  confirmed by re-running both versions twice more each: a regression only when the candidate
  fails at least 2 of its 2 re-runs and the active version passes at least 2 of its 2 re-runs, so
  an item that is unstable under both versions never counts;
- an apparent holdout regression is confirmed by re-running the candidate 3 more times: a
  regression when at least 2 of the 3 re-runs fail. The active version is not re-run, because its
  holdout result is already a 2 of 3 measurement.
"""

from __future__ import annotations

from dataclasses import dataclass

from datapilot.config import pack_config
from datapilot.contracts import Split


@dataclass(frozen=True)
class Scheme:
    holdout_repeats: int = 3
    holdout_pass_threshold: int = 2
    dev_regression_reruns: int = 2
    dev_regression_threshold: int = 2
    holdout_regression_reruns: int = 3
    holdout_regression_fail_threshold: int = 2

    @classmethod
    def from_pack(cls) -> Scheme:
        evaluation = pack_config()["evaluation"]
        return cls(
            holdout_repeats=evaluation["holdout_repeats"],
            holdout_pass_threshold=evaluation["holdout_pass_threshold"],
            dev_regression_reruns=evaluation["dev_regression_reruns"],
            dev_regression_threshold=evaluation["dev_regression_threshold"],
            holdout_regression_reruns=evaluation["holdout_regression_reruns"],
            holdout_regression_fail_threshold=evaluation["holdout_regression_fail_threshold"],
        )

    def repeats(self, split: Split) -> int:
        return self.holdout_repeats if split is Split.HOLDOUT else 1

    def passes(self, split: Split, run_passes: list[bool]) -> bool:
        if split is Split.HOLDOUT:
            return sum(run_passes) >= self.holdout_pass_threshold
        return bool(run_passes) and run_passes[0]

    def regression_reruns(self, split: Split) -> int:
        """How many more candidate runs confirm an apparent regression."""
        return (
            self.holdout_regression_reruns if split is Split.HOLDOUT else self.dev_regression_reruns
        )

    def active_reruns(self, split: Split) -> int:
        """How many more active-version runs confirm an apparent regression: a dev item's
        re-runs, none for a holdout item."""
        return 0 if split is Split.HOLDOUT else self.dev_regression_reruns

    def regression_confirmed(
        self, split: Split, reruns: list[bool], active_reruns: list[bool] | None = None
    ) -> bool:
        """Whether the re-runs confirm an apparent regression. A dev item needs the active
        version's re-runs too."""
        if split is Split.HOLDOUT:
            return reruns.count(False) >= self.holdout_regression_fail_threshold
        if active_reruns is None:
            raise ValueError("a dev regression is confirmed by re-running the active version too")
        return self.dev_regression_confirmed(reruns, active_reruns)

    def dev_regression_confirmed(self, reruns: list[bool], active_reruns: list[bool]) -> bool:
        """The candidate fails at least `dev_regression_threshold` of its re-runs and the active
        version passes at least as many of its own (2 of 2 each, by default)."""
        need = self.dev_regression_threshold
        return reruns.count(False) >= need and active_reruns.count(True) >= need
