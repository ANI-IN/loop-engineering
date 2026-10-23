"""The verification loop around the analyst.

One run: the analyst works (its queries graded and executed through the checker); its answer
envelope is verified (the final SQL runs again through every grader, then the final-answer grader);
a failure goes back to the analyst as feedback until limits.max_retries attempts are used, then the
run ends escalated. A write the database refused (SQLSTATE 25006 or 42501) is never feedback: the
run ends escalated at once, with no retry. When every grader passes, the reviewer looks once more;
a concern is fed back once within the cap, and if it persists the answer is held for human
approval. A query that reads personal data pauses the run for human approval before it executes
(the checkpointer keeps it).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from langchain.agents.middleware import AgentMiddleware, HumanInTheLoopMiddleware
from langchain_core.messages import HumanMessage
from langgraph.types import Checkpointer, Command

from datapilot import planted
from datapilot.contracts import (
    AnswerEnvelope,
    AnswerStatus,
    Grader,
    GraderContext,
    GraderResult,
    KnowledgeVersion,
    QueryResult,
    ReviewOutcome,
    ReviewVerdict,
    RunEventKind,
    RunStatus,
    Severity,
    can_transition,
)
from datapilot.loop1_agent import extension as agent_extension
from datapilot.loop1_agent.analyst import AgentLimits, RunMetadata, build_analyst
from datapilot.loop1_agent.catalog import CatalogSnapshot
from datapilot.loop1_agent.guard import GuardMiddleware, RunGuard, StopReason, ToolEventsMiddleware
from datapilot.loop1_agent.models import ModelFactory
from datapilot.loop1_agent.scout import scout_tool
from datapilot.loop1_agent.tools import QueryOutcome, Warehouse, analyst_tools, cap_rows
from datapilot.loop2_verification import extension as grader_extension
from datapilot.loop2_verification.checker import QueryChecker
from datapilot.loop2_verification.config import VerificationConfig
from datapilot.loop2_verification.executor import ExecutionError, Executor
from datapilot.loop2_verification.feedback import FeedbackClient, send_grader_feedback
from datapilot.loop2_verification.graders import FinalAnswerGrader, InjectedFailingGrader
from datapilot.loop2_verification.limits import attempt_allowed
from datapilot.loop2_verification.reviewer import Reviewer


class RunHooks(Protocol):
    """Where a run reports its lifecycle: the event loop writes ops.runs and ops.run_events."""

    def status(self, new: RunStatus, **payload: Any) -> None: ...

    def event(self, kind: RunEventKind, payload: dict[str, Any]) -> None: ...


@dataclass
class RunRequest:
    run_id: str
    question: str
    event_id: str | None = None
    demo_name: str | None = None
    export: bool = False
    inject_failing_grader: bool = False
    autonomy_level: str = "report_only"
    tokens_in: int = 0
    tokens_out: int = 0
    # Queries a person already approved in this run: the same text is not asked about again.
    approved_sql: tuple[str, ...] = ()
    # Where this run left off before it paused for an approval: the attempt it reached and whether
    # the reviewer's one concern was already fed back, so a resumed run keeps both limits.
    attempt: int = 1
    concern_fed_back: bool = False


def _same_sql(sql: str) -> str:
    return " ".join(sql.strip().rstrip(";").split())


@dataclass
class ApprovalRequest:
    kind: Literal["tool_call", "held_answer"]
    action: str
    reason: str
    sql: str | None = None
    row_estimate: int | None = None


@dataclass
class RunOutcome:
    status: RunStatus
    envelope: AnswerEnvelope | None = None
    reasons: list[str] = field(default_factory=list)
    approval: ApprovalRequest | None = None
    personal_data: bool = False
    verdict: ReviewVerdict | None = None
    attempts: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    knowledge_version: str = ""
    trace_id: str = ""


@dataclass
class LoopServices:
    """What every run shares in one process."""

    models: ModelFactory
    executor: Executor
    snapshot: CatalogSnapshot
    config: VerificationConfig
    limits: AgentLimits
    knowledge: Callable[[], KnowledgeVersion]
    checkpointer: Checkpointer
    model_name: str
    feedback: FeedbackClient | None = None


ExtraMiddleware = Callable[[RunGuard], Sequence[AgentMiddleware]]


def _no_extra(_guard: RunGuard) -> Sequence[AgentMiddleware]:
    return ()


def _no_stop() -> StopReason | None:
    return None


STOPPED_STATUS = {
    StopReason.KILL_SWITCH: RunStatus.BLOCKED_KILLSWITCH,
    StopReason.DAILY_BUDGET: RunStatus.BLOCKED_BUDGET,
    StopReason.TOKEN_LIMIT: RunStatus.ESCALATED,
    StopReason.REFUSED_WRITE: RunStatus.ESCALATED,
    StopReason.OUTPUT_LIMIT: RunStatus.ESCALATED,
}
REFUSED_STOP = "Run stopped: the database refused a write."


def refused_detail(error: ExecutionError) -> str:
    return (
        f"the database refused a write (SQLSTATE {error.sqlstate}: {error.message}); "
        "the run ends escalated, with no retry"
    )


class VerificationLoop:
    def __init__(
        self,
        services: LoopServices,
        hooks: RunHooks,
        *,
        external_stop: Callable[[], StopReason | None] = _no_stop,
        on_usage: Callable[[int, int], None] | None = None,
        extra_middleware: ExtraMiddleware = _no_extra,
    ) -> None:
        self.s = services
        self.hooks = hooks
        self.external_stop = external_stop
        self.on_usage = on_usage
        self.extra_middleware = extra_middleware
        self.personal_data = False
        self.approved = False  # True once a person approved this run (resumed with approve)

    # --- setup --------------------------------------------------------------------------------
    def _setup(self, request: RunRequest) -> None:
        self.request = request
        self.knowledge = self.s.knowledge()
        self.guard = RunGuard(
            tokens_per_run=self.s.limits.tokens_per_run,
            external_stop=self.external_stop,
            on_usage=self.on_usage,
            tokens_in=request.tokens_in,
            tokens_out=request.tokens_out,
        )
        self.checker = QueryChecker(
            self.s.config, self.s.executor, self.s.snapshot, on_result=self._record_grader
        )
        self.metadata = RunMetadata(
            run_id=request.run_id,
            event_id=request.event_id,
            demo_name=request.demo_name,
            pack=self.s.config.pack,
            knowledge_version=self.knowledge.version,
            autonomy_level=request.autonomy_level,
            planted_active=planted.active(),
            model=self.s.model_name,
        )
        self.trace_id = uuid.UUID(request.run_id)
        guarded = [*self.extra_middleware(self.guard), GuardMiddleware(self.guard)]
        self.guarded = guarded
        warehouse = Warehouse(self.s.snapshot, self.s.executor.url)
        tools = analyst_tools(warehouse, self._run_query, row_cap=self.s.limits.row_cap)
        self.lookups = agent_extension.LookupLog()
        tools += agent_extension.lookup_tools(warehouse, self.lookups)
        if self.s.limits.scout_enabled:
            tools.append(scout_tool(self.s.models, warehouse, middleware=guarded))
        approved = {_same_sql(sql) for sql in request.approved_sql}
        self.approved = self.approved or bool(approved)  # a person approved a query of this run
        approvals = HumanInTheLoopMiddleware(
            {
                "run_query": {
                    "allowed_decisions": ["approve", "reject"],
                    "when": lambda req: (
                        self.checker.needs_approval(
                            str(req.tool_call["args"].get("sql", "")), export=request.export
                        )
                        and _same_sql(str(req.tool_call["args"].get("sql", ""))) not in approved
                    ),
                    "description": "This query reads personal data and needs human approval.",
                }
            }
        )
        self.agent = build_analyst(
            model=self.s.models("analyst"),
            tools=tools,
            knowledge=self.knowledge,
            limits=self.s.limits,
            middleware=[ToolEventsMiddleware(self.hooks.event), *guarded, approvals],
            checkpointer=self.s.checkpointer,
        )

    def _record_grader(self, result: GraderResult, context: GraderContext) -> None:
        if result.severity is Severity.ROUTE:
            self.personal_data = True
        self.hooks.event(
            RunEventKind.GRADER_RESULT,
            {
                "grader": result.grader,
                "passed": result.passed,
                "severity": result.severity.value,
                "reason": result.reason,
                "feedback": result.feedback_for_agent,
                "sql": context.sql,
                "attempt": getattr(self, "attempt", 1),
            },
        )
        send_grader_feedback(self.s.feedback, self.trace_id, result)

    def _run_query(self, sql: str) -> QueryOutcome:
        checked = self.checker.check(
            sql, question=self.request.question, export=self.request.export
        )
        if checked.refused is not None:  # the guard ends the run before the next model call
            self.guard.stop(StopReason.REFUSED_WRITE, refused_detail(checked.refused))
            return QueryOutcome(None, "execution", REFUSED_STOP)
        failure = checked.failure
        if failure is not None:
            return QueryOutcome(None, failure.grader, failure.feedback_for_agent or failure.reason)
        return QueryOutcome(checked.result)

    # --- public entry points -------------------------------------------------------------------
    async def start(self, request: RunRequest) -> RunOutcome:
        self._setup(request)
        if (asked := self._ask_first()) is not None:
            return asked
        payload: Any = {"messages": [HumanMessage(request.question)]}
        state = await self.agent.aget_state(self._config(1))
        if state.next and not any(task.interrupts for task in state.tasks):
            payload = None  # a worker died mid-run: continue from the last checkpoint
        return await self._drive(payload, attempt=request.attempt)

    async def resume(self, request: RunRequest, *, approve: bool, message: str = "") -> RunOutcome:
        """Continue a run paused for approval, from the checkpoint of thread run_id."""
        self._setup(request)
        self.approved = approve
        self.trace_id = uuid.uuid4()
        state = await self.agent.aget_state(self._config(1))
        if not state.next:
            return self._outcome(
                RunStatus.FAILED,
                reasons=["the pending approval was lost: no checkpoint holds this run"],
            )
        decision: dict[str, Any] = {"type": "approve"}
        if not approve:
            decision = {"type": "reject", "message": message or "Rejected by the approver."}
        resumed = Command(resume={"decisions": [decision]})
        return await self._drive(resumed, attempt=request.attempt)

    # --- the loop ------------------------------------------------------------------------------
    def _ask_first(self) -> RunOutcome | None:
        """Question graders run once, before the first model call. A block ends the run with
        needs_clarification: asking costs nothing, and a guess would be a confident wrong answer."""
        context = GraderContext(
            question=self.request.question,
            knowledge_version=self.knowledge.version,
            pack=self.s.config.pack,
            extra={"knowledge": self.knowledge},
        )
        for grader in grader_extension.question_graders():
            result = grader.check(context)
            self._record_grader(result, context)
            if result.severity is Severity.BLOCK:
                self.hooks.status(RunStatus.VERIFYING, attempt=1)
                envelope = AnswerEnvelope(
                    status=AnswerStatus.NEEDS_CLARIFICATION,
                    answer_text=result.reason,
                    clarifying_question=result.feedback_for_agent or result.reason,
                )
                return self._outcome(RunStatus.ANSWERED, envelope=envelope, attempts=1)
        return None

    def _config(self, attempt: int) -> dict[str, Any]:
        return self.metadata.config(
            thread_id=self.request.run_id, trace_id=str(self.trace_id), attempt=attempt
        )

    async def _drive(self, payload: Any, *, attempt: int) -> RunOutcome:
        concern_fed_back = self.request.concern_fed_back
        while True:
            self.attempt = attempt
            state = await self.agent.ainvoke(payload, self._config(attempt))
            if interrupts := state.get("__interrupt__"):
                return self._approval(interrupts[0].value, attempt)
            if self.guard.stop_reason is not None:
                return self._stopped(attempt)
            envelope = state.get("structured_response")
            if not isinstance(envelope, AnswerEnvelope):
                limit = self.s.limits.model_call_limit
                reason = "the analyst returned no answer envelope"
                if self.guard.model_calls >= limit * attempt:
                    reason += f" within the model call limit ({limit})"
                return self._outcome(RunStatus.ESCALATED, reasons=[reason], attempts=attempt)
            envelope = agent_extension.with_matches(envelope, self.lookups)
            if envelope.status is AnswerStatus.ESCALATED:
                reasons = [envelope.answer_text or "the analyst escalated"]
                return self._outcome(RunStatus.ESCALATED, envelope=envelope, reasons=reasons)
            self.hooks.status(RunStatus.VERIFYING, attempt=attempt)
            failure, result = self._verify(envelope)
            if self.guard.stop_reason is StopReason.REFUSED_WRITE:
                return self._outcome(
                    RunStatus.ESCALATED,
                    envelope=envelope,
                    reasons=[self.guard.stop_detail],
                    attempts=attempt,
                )
            if failure is None:
                verdict = await self._review(envelope, result)
                if verdict is not None and verdict.outcome is ReviewOutcome.CONCERN:
                    if not concern_fed_back and attempt_allowed(attempt + 1, self._cap):
                        concern_fed_back = True
                        payload = self._feedback("The reviewer raised a concern", verdict.reasons)
                        attempt = self._retry(attempt)
                        continue
                    return self._held(envelope, verdict, attempt)
                if self.guard.stop_reason is not None:
                    return self._outcome(
                        RunStatus.ESCALATED,
                        envelope=envelope,
                        reasons=[f"stopped during verification: {self.guard.stop_detail}"],
                        attempts=attempt,
                    )
                return self._outcome(
                    RunStatus.ANSWERED, envelope=envelope, verdict=verdict, attempts=attempt
                )
            reasons = [f"{failure.grader}: {failure.reason}"]
            if not attempt_allowed(attempt + 1, self._cap):
                reasons.append(f"retry cap reached after {attempt} attempts")
                return self._outcome(
                    RunStatus.ESCALATED, envelope=envelope, reasons=reasons, attempts=attempt
                )
            if self.guard.check() is not None:
                return self._stopped_while_verifying(envelope, attempt)
            payload = self._feedback(
                f"Verification failed ({failure.grader})",
                [failure.feedback_for_agent or failure.reason],
            )
            attempt = self._retry(attempt)

    @property
    def _cap(self) -> int:
        return self.s.config.max_retries

    def _retry(self, attempt: int) -> int:
        self.hooks.status(RunStatus.RUNNING, attempt=attempt + 1)
        self.trace_id = uuid.uuid4()
        return attempt + 1

    @staticmethod
    def _feedback(title: str, reasons: list[str]) -> dict[str, Any]:
        text = f"{title}: {' '.join(reasons)} Fix it and return a new answer envelope."
        return {"messages": [HumanMessage(text)]}

    def _verify(self, envelope: AnswerEnvelope) -> tuple[GraderResult | None, QueryResult | None]:
        result: QueryResult | None = None
        if envelope.status is AnswerStatus.ANSWERED and envelope.final_sql:
            checked = self.checker.check(
                envelope.final_sql, question=self.request.question, export=self.request.export
            )
            if checked.refused is not None:
                self.guard.stop(StopReason.REFUSED_WRITE, refused_detail(checked.refused))
            if checked.failure is not None:
                return checked.failure, None
            result = checked.result
            if result is not None:
                rows, _ = cap_rows(list(result.rows), self.s.limits.row_cap)
                envelope.columns = result.columns
                envelope.rows_preview = [list(r) for r in rows]
                envelope.row_count = result.total_row_count
        graders: list[Grader] = [FinalAnswerGrader(), *grader_extension.answer_graders()]
        if self.request.inject_failing_grader:
            graders.append(InjectedFailingGrader())
        context = GraderContext(
            question=self.request.question,
            sql=envelope.final_sql,
            result=result,
            answer=envelope,
            knowledge_version=self.knowledge.version,
            pack=self.s.config.pack,
            extra={"approved": self.approved, "export": self.request.export},
        )
        for grader in graders:
            graded = grader.check(context)
            self._record_grader(graded, context)
            if graded.severity is Severity.BLOCK:
                return graded, result
        return None, result

    async def _review(
        self, envelope: AnswerEnvelope, result: QueryResult | None
    ) -> ReviewVerdict | None:
        if not self.s.limits.reviewer_enabled or result is None or not envelope.final_sql:
            return None
        if self.guard.check() is not None:
            return None
        reviewer = Reviewer(self.s.models, middleware=self.guarded)
        verdict = await reviewer.review(
            self.request.question,
            envelope.final_sql,
            result,
            self.knowledge,
            preview_rows=self.s.limits.row_cap,
        )
        if verdict is not None:
            self.hooks.event(
                RunEventKind.REVIEWER_VERDICT,
                {"outcome": verdict.outcome.value, "reasons": verdict.reasons},
            )
        return verdict

    # --- outcomes ------------------------------------------------------------------------------
    def _outcome(self, status: RunStatus, **kwargs: Any) -> RunOutcome:
        return RunOutcome(
            status=status,
            personal_data=self.personal_data,
            tokens_in=self.guard.tokens_in,
            tokens_out=self.guard.tokens_out,
            knowledge_version=self.knowledge.version,
            trace_id=str(self.trace_id),
            **kwargs,
        )

    def _stopped(self, attempt: int) -> RunOutcome:
        reason = self.guard.stop_reason or StopReason.TOKEN_LIMIT
        return self._outcome(
            STOPPED_STATUS[reason], reasons=[self.guard.stop_detail], attempts=attempt
        )

    def _stopped_while_verifying(self, envelope: AnswerEnvelope, attempt: int) -> RunOutcome:
        # A stop seen while verifying ends the run with the stop's own status (blocked by the kill
        # switch) where the lifecycle allows it from verifying, and escalated otherwise.
        reason = self.guard.stop_reason or StopReason.TOKEN_LIMIT
        status = STOPPED_STATUS[reason]
        if not can_transition(RunStatus.VERIFYING, status):
            status = RunStatus.ESCALATED
        return self._outcome(
            status,
            envelope=envelope,
            reasons=[f"stopped during verification: {self.guard.stop_detail}"],
            attempts=attempt,
        )

    def _approval(self, value: dict[str, Any], attempt: int) -> RunOutcome:
        action = value["action_requests"][0]
        sql = str(action["args"].get("sql", ""))
        approval = ApprovalRequest(
            kind="tool_call",
            action=f"run_query: {sql}",
            reason="the query reads personal data",
            sql=sql,
            row_estimate=self._row_count(sql),
        )
        return self._outcome(RunStatus.AWAITING_APPROVAL, approval=approval, attempts=attempt)

    def _held(self, envelope: AnswerEnvelope, verdict: ReviewVerdict, attempt: int) -> RunOutcome:
        approval = ApprovalRequest(
            kind="held_answer",
            action=f"post the answer: {envelope.answer_text}",
            reason="the reviewer's concern persists: " + "; ".join(verdict.reasons),
            sql=envelope.final_sql,
            row_estimate=envelope.row_count,
        )
        return self._outcome(
            RunStatus.AWAITING_APPROVAL,
            envelope=envelope,
            verdict=verdict,
            approval=approval,
            attempts=attempt,
        )

    def _row_count(self, sql: str) -> int | None:
        """The exact number of rows the approver is asked to release (read-only, rolled back)."""
        inner = sql.strip().rstrip(";")
        try:
            result = self.s.executor.run(f"SELECT count(*) FROM ({inner}) AS rows_to_approve")
            return int(result.rows[0][0])
        except (ExecutionError, IndexError):
            return None
