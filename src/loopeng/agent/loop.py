"""The Level 1 agent loop: ask, run the SQL, retry when it fails to execute.

**What "loop" means here is the teaching point, so it is worth being exact.** This
level retries on EXECUTION FAILURE only — the SQL did not parse, did not run, or timed
out — and the feedback it gets is the database error, nothing more. It catches
**syntactic** failure.

It cannot catch **semantic** failure: SQL that parses, runs, returns a clean number,
and is wrong. Nothing here compares the answer to anything, because there is nothing
to compare against that the agent is allowed to see. That gap is the whole reason
Level 2 exists.

The loop never touches gold. Classification against gold happens afterwards, in
`loopeng.agent.classify`, on the finished run — the same isolation the VerifyContext
contract enforces for Phase 2.
"""

import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Protocol

import anthropic
import structlog

from loopeng.prompts import render_prompt
from loopeng.registry import spec_for
from loopeng.settings import load_settings
from loopeng.usage import CallUsage, UsageLedger
from loopeng.warehouse.connect import QueryTimeout, run_sql

log = structlog.get_logger(__name__)

DEFAULT_MAX_ATTEMPTS = 3

# Per question, not per run. Sized so one pathological question cannot eat a sweep.
DEFAULT_BUDGET_USD = 0.10

_SQL_FENCE = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


class TerminationReason(StrEnum):
    """Why the loop stopped. Recorded by name on every run.

    A controller whose branches are never counted is the declared-versus-enforced
    defect applied to our own policy: `no_progress` and `budget` either fire or they
    are decoration, and the only way to know is to report the distribution.
    """

    SUCCESS = "success"
    MAX_ATTEMPTS = "max_attempts"
    BUDGET = "budget"
    NO_PROGRESS = "no_progress"


@dataclass(frozen=True)
class Attempt:
    n: int
    sql: str
    rows: list[list] | None
    error: str | None
    usage: CallUsage

    @property
    def executed(self) -> bool:
        return self.error is None


@dataclass(frozen=True)
class AgentRun:
    question: str
    level: str
    role: str
    model_id: str
    attempts: tuple[Attempt, ...]
    termination: TerminationReason
    item_id: str | None = None
    ledger: UsageLedger = field(default_factory=UsageLedger)

    @property
    def final(self) -> Attempt | None:
        return self.attempts[-1] if self.attempts else None

    @property
    def rows(self) -> list[list] | None:
        last = self.final
        return last.rows if last else None

    @property
    def sql(self) -> str | None:
        last = self.final
        return last.sql if last else None

    @property
    def error(self) -> str | None:
        last = self.final
        return last.error if last else None

    def cost_usd(self) -> float:
        """Estimated. Counts every attempt, including the ones that failed."""
        return self.ledger.cost_usd()


class SupportsMessages(Protocol):
    """Just enough of the Anthropic client for the loop, so tests can substitute."""

    @property
    def messages(self): ...


def extract_sql(text: str) -> str:
    """Pull SQL out of whatever the model wrapped it in.

    Models fence code even when told not to. A fence left in place makes the query
    fail to parse, which the loop would then dutifully retry — burning attempts on a
    formatting artefact rather than on anything the model got wrong.
    """
    fenced = _SQL_FENCE.search(text)
    if fenced:
        return fenced.group(1).strip()
    return text.strip()


def _build_messages(question: str, level: str, history: list[Attempt]) -> list[dict]:
    messages: list[dict] = [
        {"role": "user", "content": f"{render_prompt(level)}\n\nQuestion: {question}"}
    ]
    for attempt in history:
        messages.append({"role": "assistant", "content": attempt.sql})
        # The only feedback this level has. Not a hint, not a rule reminder — the
        # database's own complaint, which is all a Level 1 loop is entitled to.
        messages.append(
            {
                "role": "user",
                "content": (
                    f"That query failed with:\n{attempt.error}\n\n"
                    "Return a corrected query. SQL only."
                ),
            }
        )
    return messages


def run_question(
    question: str,
    *,
    warehouse: Path,
    role: str = "worker",
    level: str = "L3",
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    budget_usd: float = DEFAULT_BUDGET_USD,
    client: SupportsMessages | None = None,
    item_id: str | None = None,
    timeout_s: float = 30.0,
) -> AgentRun:
    """Run one question to termination. Never raises on a model or SQL failure."""
    spec = spec_for(role)
    if client is None:
        settings = load_settings()
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key.get_secret_value())

    ledger = UsageLedger()
    attempts: list[Attempt] = []
    seen_sql: set[str] = set()
    seen_errors: set[str] = set()
    termination = TerminationReason.MAX_ATTEMPTS

    for n in range(1, max_attempts + 1):
        # Checked before spending, not after: a budget enforced only in arrears is a
        # report of what was overspent rather than a cap.
        if ledger.cost_usd() >= budget_usd:
            termination = TerminationReason.BUDGET
            break

        try:
            response = client.messages.create(
                model=spec.model_id,
                messages=_build_messages(question, level, attempts),
                **spec.request_kwargs,
            )
            usage = CallUsage.from_response(spec.model_id, response, outcome="ok")
            raw = "".join(
                block.text for block in response.content if getattr(block, "type", None) == "text"
            )
            sql = extract_sql(raw)
        except Exception as exc:  # noqa: BLE001 - a failed call still billed
            # Recorded, not swallowed: the tokens are gone either way, and dropping
            # them would make the loop look cheaper than it is.
            usage = CallUsage(spec.model_id, "error")
            ledger.record(usage)
            attempts.append(
                Attempt(n=n, sql="", rows=None, error=f"{type(exc).__name__}: {exc}", usage=usage)
            )
            log.warning("model_call_failed", question=question[:60], attempt=n, error=str(exc))
            continue

        ledger.record(usage)

        rows: list[list] | None = None
        error: str | None = None
        try:
            rows = [list(row) for row in run_sql(sql, warehouse, timeout_s=timeout_s)]
        except QueryTimeout as exc:
            error = f"QueryTimeout: {exc}"
        except Exception as exc:  # noqa: BLE001 - any DB error is loop feedback
            error = f"{type(exc).__name__}: {exc}"

        attempts.append(Attempt(n=n, sql=sql, rows=rows, error=error, usage=usage))

        if error is None:
            termination = TerminationReason.SUCCESS
            break

        # No progress: the same query twice, or the same complaint twice. Either way
        # the feedback is not moving the model and further attempts only spend.
        if sql in seen_sql or error in seen_errors:
            termination = TerminationReason.NO_PROGRESS
            break
        seen_sql.add(sql)
        seen_errors.add(error)

    return AgentRun(
        question=question,
        level=level,
        role=role,
        model_id=spec.model_id,
        attempts=tuple(attempts),
        termination=termination,
        item_id=item_id,
        ledger=ledger,
    )
