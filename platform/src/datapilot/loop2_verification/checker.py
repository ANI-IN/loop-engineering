"""The pre-execution graders in order, then the executor, then the execution grader.

Order matters and each layer stops something the earlier ones let through: parse, statement
policy, schema existence, cost, personal data; then the read-only role executes the original text.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from datapilot.contracts import Grader, GraderContext, GraderResult, QueryResult, Severity
from datapilot.loop1_agent.catalog import CatalogSnapshot
from datapilot.loop2_verification.config import VerificationConfig
from datapilot.loop2_verification.executor import ExecutionError, Executor
from datapilot.loop2_verification.graders import (
    CostGrader,
    ExecutionGrader,
    PersonalDataGrader,
    SchemaGrader,
    guard_graders,
)

OnResult = Callable[[GraderResult, GraderContext], None]


@dataclass
class Checked:
    results: list[GraderResult] = field(default_factory=list)
    result: QueryResult | None = None
    refused: ExecutionError | None = None  # a write the database refused: the run must end

    @property
    def failure(self) -> GraderResult | None:
        return next((r for r in self.results if r.severity is Severity.BLOCK), None)

    @property
    def personal_data(self) -> bool:
        return any(r.severity is Severity.ROUTE for r in self.results)


class QueryChecker:
    def __init__(
        self,
        config: VerificationConfig,
        executor: Executor,
        snapshot: CatalogSnapshot,
        *,
        on_result: OnResult | None = None,
    ) -> None:
        self.config = config
        self.executor = executor
        self.snapshot = snapshot
        self.on_result = on_result
        self.static: list[Grader] = [*guard_graders(config.schema), SchemaGrader(snapshot)]
        self.cost = CostGrader(config, self._explain)
        self._refused: ExecutionError | None = None
        self.personal = PersonalDataGrader(config, snapshot)
        self.execution = ExecutionGrader()

    def _context(self, sql: str, question: str, export: bool) -> GraderContext:
        return GraderContext(
            question=question, sql=sql, pack=self.config.pack, extra={"export": export}
        )

    def _grade(self, graders: list[Grader], context: GraderContext, checked: Checked) -> bool:
        for grader in graders:
            result = grader.check(context)
            checked.results.append(result)
            if self.on_result:
                self.on_result(result, context)
            if result.severity is Severity.BLOCK:
                return False
        return True

    def _explain(self, sql: str) -> dict[str, Any]:
        try:
            return self.executor.explain(sql)
        except ExecutionError as error:
            if error.refused_write:
                self._refused = error
            raise

    def check(self, sql: str, *, question: str = "", export: bool = False) -> Checked:
        """Grade, then execute only if no grader blocked. A refused write is marked on the result,
        so the loop can end the run instead of sending the error back."""
        context = self._context(sql, question, export)
        checked = Checked()
        self._refused = None
        if not self._grade([*self.static, self.cost, self.personal], context, checked):
            checked.refused = self._refused
            return checked
        try:
            checked.result = self.executor.run(sql)
        except ExecutionError as error:
            context.extra["execution_error"] = error
            checked.refused = error if error.refused_write else None
        context.result = checked.result
        self._grade([self.execution], context, checked)
        return checked

    def needs_approval(self, sql: str, *, export: bool = False) -> bool:
        """The static graders pass, the personal-data grader routes the query to a human, and the
        cost grader passes it too, so no query a grader would block is offered for approval (it
        runs as an ordinary tool call and the block goes back to the agent as feedback). Only a
        routed query is planned, with EXPLAIN and never executed; it runs again on resume."""
        context = self._context(sql, "", export)
        if any(g.check(context).severity is Severity.BLOCK for g in self.static):
            return False
        if self.personal.check(context).severity is not Severity.ROUTE:
            return False
        return self.cost.check(context).severity is not Severity.BLOCK
