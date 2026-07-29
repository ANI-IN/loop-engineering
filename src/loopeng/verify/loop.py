"""The Level 2 loop: Level 1, plus verifiers that read a query which *ran*.

Level 1 retries when SQL fails to execute. Level 2 adds the thing Level 1 structurally
cannot do — look at a query that ran cleanly and say it is wrong anyway, naming the
rule it broke.

**This module discharges the Phase 2 obligation recorded at Gate 0.** The design doc
states it directly: the field-name regex on `VerifyContext` constrains the type's
shape, and only *scope* constrains what can reach it. So `build_context` below takes
no gold parameter, and `run_verified` never loads gold — the gold answer is not merely
absent from the context, it is absent from the call stack that builds one. Judgement
against gold happens afterwards, in `loopeng.agent.classify`, on the finished run.

Termination reasons extend Level 1's four. `max_attempts` is raised above 1 here, so
`budget` and `no_progress` become reachable for the first time — at Level 1's cap of 1
they were structurally unable to fire, which means Phase 1 was no evidence they work.
"""

from dataclasses import dataclass, field
from pathlib import Path

import structlog

from loopeng.agent.loop import (
    Attempt,
    SupportsMessages,
    TerminationReason,
    _build_messages,
    extract_sql,
    triage_call_failure,
)
from loopeng.contracts import VerifyContext
from loopeng.registry import spec_for
from loopeng.settings import load_settings
from loopeng.usage import CallUsage, UsageLedger
from loopeng.verify.verifiers import VerifyResult, verify
from loopeng.warehouse.connect import QueryTimeout, run_sql
from loopeng.warehouse.schema import SCHEMA_DDL

log = structlog.get_logger(__name__)

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BUDGET_USD = 0.15


@dataclass(frozen=True)
class VerifiedAttempt:
    attempt: Attempt
    verdict: VerifyResult

    @property
    def accepted(self) -> bool:
        return self.attempt.executed and self.verdict.ok


@dataclass(frozen=True)
class VerifiedRun:
    question: str
    level: str
    role: str
    model_id: str
    attempts: tuple[VerifiedAttempt, ...]
    termination: TerminationReason
    item_id: str | None = None
    ledger: UsageLedger = field(default_factory=UsageLedger)

    @property
    def final(self) -> VerifiedAttempt | None:
        return self.attempts[-1] if self.attempts else None

    @property
    def rows(self):
        last = self.final
        return last.attempt.rows if last else None

    @property
    def sql(self):
        last = self.final
        return last.attempt.sql if last else None

    @property
    def error(self):
        last = self.final
        return last.attempt.error if last else None

    @property
    def rejections(self) -> int:
        """How many times a query that RAN was sent back. Level 1 cannot do this."""
        return sum(1 for a in self.attempts if a.attempt.executed and not a.verdict.ok)

    def cost_usd(self) -> float:
        return self.ledger.cost_usd()


def build_context(
    *,
    question: str,
    sql: str,
    rules: tuple[str, ...],
    attempt: int,
    execution_rows,
    execution_error: str | None,
) -> VerifyContext:
    """Build the verifier's view of an attempt.

    **There is deliberately no gold parameter here, and that is the point.** The
    Gate 0 design note says the field-name regex constrains the type's shape while
    only scope constrains what can reach it — so the guarantee this function provides
    is that the gold answer is not in scope at the construction site. A test asserts
    the signature stays that way.
    """
    return VerifyContext(
        question=question,
        sql=sql,
        schema_ddl=SCHEMA_DDL,
        rules=rules,
        attempt=attempt,
        execution_rows=tuple(tuple(row) for row in execution_rows) if execution_rows else None,
        execution_error=execution_error,
    )


def run_verified(
    question: str,
    *,
    warehouse: Path,
    rules: tuple[str, ...] = (),
    role: str = "worker",
    level: str = "L3",
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    budget_usd: float = DEFAULT_BUDGET_USD,
    client: SupportsMessages | None = None,
    item_id: str | None = None,
    timeout_s: float = 30.0,
    verifier=verify,
) -> VerifiedRun:
    """Run one question until a query both executes and passes the verifiers."""
    spec = spec_for(role)
    if client is None:
        import anthropic

        settings = load_settings()
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key.get_secret_value())

    ledger = UsageLedger()
    attempts: list[VerifiedAttempt] = []
    plain_attempts: list[Attempt] = []
    seen_sql: set[str] = set()
    seen_feedback: set[str] = set()
    termination = TerminationReason.MAX_ATTEMPTS

    for n in range(1, max_attempts + 1):
        if ledger.cost_usd() >= budget_usd:
            termination = TerminationReason.BUDGET
            break

        try:
            response = client.messages.create(
                model=spec.model_id,
                messages=_build_messages(question, level, plain_attempts),
                **spec.request_kwargs,
            )
            usage = CallUsage.from_response(spec.model_id, response, outcome="ok")
            raw = "".join(
                block.text for block in response.content if getattr(block, "type", None) == "text"
            )
            sql = extract_sql(raw)
        except Exception as exc:  # noqa: BLE001 - a failed call still billed
            # Same triage as Level 1, from the same function. This loop runs the sweep
            # cells, so it is the one where retrying a rejected credential is most
            # expensive: 50 items x 3 attempts per cell, all guaranteed to fail.
            fatal, message = triage_call_failure(exc, role=role, model_id=spec.model_id)
            usage = CallUsage(spec.model_id, "error")
            ledger.record(usage)
            failed = Attempt(n=n, sql="", rows=None, error=message, usage=usage)
            plain_attempts.append(failed)
            attempts.append(VerifiedAttempt(failed, VerifyResult(())))
            if fatal is not None:
                log.error("model_call_refused", attempt=n, termination=str(fatal),
                          error=str(exc))
                termination = fatal
                break
            continue

        ledger.record(usage)

        rows = None
        error = None
        try:
            rows = [list(row) for row in run_sql(sql, warehouse, timeout_s=timeout_s)]
        except QueryTimeout as exc:
            error = f"QueryTimeout: {exc}"
        except Exception as exc:  # noqa: BLE001 - any DB error is loop feedback
            error = f"{type(exc).__name__}: {exc}"

        attempt = Attempt(n=n, sql=sql, rows=rows, error=error, usage=usage)
        verdict = verifier(
            build_context(
                question=question,
                sql=sql,
                rules=rules,
                attempt=n,
                execution_rows=rows,
                execution_error=error,
            )
        )
        attempts.append(VerifiedAttempt(attempt, verdict))

        if error is None and verdict.ok:
            termination = TerminationReason.SUCCESS
            break

        # Feedback is the database error when it did not run, and the verifier's
        # complaint when it ran but broke a rule. The model never sees the answer.
        feedback = error or verdict.feedback()
        if sql in seen_sql or feedback in seen_feedback:
            termination = TerminationReason.NO_PROGRESS
            break
        seen_sql.add(sql)
        seen_feedback.add(feedback)

        plain_attempts.append(
            Attempt(n=n, sql=sql, rows=rows, error=feedback, usage=usage)
        )

    return VerifiedRun(
        question=question,
        level=level,
        role=role,
        model_id=spec.model_id,
        attempts=tuple(attempts),
        termination=termination,
        item_id=item_id,
        ledger=ledger,
    )
