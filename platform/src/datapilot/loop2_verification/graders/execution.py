"""Grader 6, execution: the query ran on the read-only role; a database error becomes feedback."""

from __future__ import annotations

from datapilot.contracts import GraderContext, GraderResult, Stage
from datapilot.loop2_verification.executor import ExecutionError
from datapilot.loop2_verification.graders._sql import blocked, passed


class ExecutionGrader:
    name = "execution"
    stage = Stage.POST_EXECUTION

    def check(self, context: GraderContext) -> GraderResult:
        error = context.extra.get("execution_error")
        if isinstance(error, ExecutionError):
            return blocked(self.name, f"SQLSTATE {error.sqlstate}: {error.message}", error.feedback)
        if context.result is None:
            return blocked(self.name, "no result", "The query returned no result set.")
        return passed(self.name, f"{context.result.total_row_count} rows")
