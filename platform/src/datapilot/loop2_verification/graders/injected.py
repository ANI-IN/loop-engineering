"""The injected failing grader (a labelled demo aid): it always fails, for one run only, so the
retry cap can be seen stopping a run. It applies only to a run whose request asks for it."""

from __future__ import annotations

from datapilot.contracts import GraderContext, GraderResult, Stage
from datapilot.loop2_verification.graders._sql import blocked


class InjectedFailingGrader:
    name = "injected_failure"
    stage = Stage.FINAL_ANSWER

    def check(self, context: GraderContext) -> GraderResult:
        return blocked(
            self.name,
            "injected failure (demo aid): this grader always fails",
            "An injected demo grader rejected the answer. Try again.",
        )
