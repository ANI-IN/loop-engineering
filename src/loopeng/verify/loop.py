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

import time
from dataclasses import dataclass, field
from pathlib import Path

import structlog

from loopeng.agent.loop import (
    Attempt,
    SupportsMessages,
    TerminationReason,
    backoff_delay,
    build_turns,
    extract_sql,
)
from loopeng.contracts import VerifyContext
from loopeng.prompts import render_prompt
from loopeng.providers import complete, triage_call_failure
from loopeng.registry import spec_for
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
    # The exact version string the API reported. Carried for the same reason
    # `AgentRun` carries it: a silent model swap invalidates every comparison in
    # the run and is invisible anywhere else.
    served_model: str | None = None

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
    role: str = "agent",
    level: str = "L3",
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    budget_usd: float = DEFAULT_BUDGET_USD,
    client: SupportsMessages | None = None,
    item_id: str | None = None,
    timeout_s: float = 30.0,
    verifier=verify,
    sleeper=time.sleep,
) -> VerifiedRun:
    """Run one question until a query both executes and passes the verifiers."""
    raise NotImplementedError(
        "This is the starter branch. Implement run_verified until the suite is green.\n"
        "The tests are the specification: `uv run pytest -q` names every property it "
        "must have, and every one of them exists on `main`.\n"
        "Nothing that MEASURES has been removed — the warehouse, the gold set, the "
        "verifiers, the charts and every guard are intact, because telling whether "
        "your loop works is the subject rather than a convenience."
    )
