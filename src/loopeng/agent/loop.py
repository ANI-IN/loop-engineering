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

**Not every failed call is worth retrying, and the loop used to retry all of them.** A
bare `except Exception` around `client.messages.create` treated a revoked API key
exactly like a transient 529: three round-trips, then `max_attempts`, and a screen that
said `database said: AuthenticationError` — blaming the warehouse for a credential
problem. At sweep scale that is ~200 doomed calls before a uniformly failed grid.

A retry is only a retry when the next attempt could plausibly differ. `FATAL_CALL_ERRORS`
is the set where it cannot, and the loop stops on the first one with a message naming the
variable and the fix. Retrying those is not a budget guard; it is spend with a guaranteed
zero return.
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

    # The two non-retryable branches. Separate names rather than one, because they are
    # different problems with different fixes and a run labelled `credential` when the
    # request was merely malformed would send an operator to the wrong file.
    CREDENTIAL = "credential"    # 401/403 — the key or the account, not the request
    BAD_REQUEST = "bad_request"  # 400 — the request itself; retrying sends it again


# Failures a retry cannot fix. Named against the client's own exception classes rather
# than against status codes: the SDK already models that mapping, and a second copy of it
# here is a second thing to drift.
CREDENTIAL_ERRORS = (
    anthropic.AuthenticationError,    # 401 — key wrong, revoked, or account unfunded
    anthropic.PermissionDeniedError,  # 403 — the account may not call this model
)

# 400. This is the class Sonnet 5 returns for a pinned temperature, and retrying a
# malformed request is exactly the same waste as retrying a bad key.
BAD_REQUEST_ERRORS = (anthropic.BadRequestError,)

FATAL_CALL_ERRORS = CREDENTIAL_ERRORS + BAD_REQUEST_ERRORS

# Everything else the client can raise is retryable and stays retryable: 429s, 5xx,
# timeouts, connection resets. Listed for the reader rather than matched on — the code
# below reaches them through the `except Exception` fallback, which is deliberately the
# broad arm so a transport failure class we have not met still gets its retry.
RETRYABLE_CALL_ERRORS = (
    anthropic.RateLimitError,        # 429
    anthropic.APITimeoutError,       # no response in time
    anthropic.APIConnectionError,    # transport
    anthropic.APIStatusError,        # 5xx, after the fatal subclasses above are taken
)


def triage_call_failure(
    exc: Exception, *, role: str, model_id: str
) -> tuple[TerminationReason | None, str]:
    """How to stop after a failed model call, and what to say about it.

    Returns `(termination, message)`. A `None` termination means retryable: the tokens
    billed, the attempt is recorded, and the loop goes round again. Anything else stops
    the loop now, and the message names the variable and the fix in the same shape as
    `MissingCredential`, because the person reading it is in the same position.
    """
    if isinstance(exc, CREDENTIAL_ERRORS):
        return TerminationReason.CREDENTIAL, (
            f"{type(exc).__name__}: the Anthropic API rejected the credential for "
            f"{model_id}. ANTHROPIC_API_KEY is set but not usable — it is wrong, "
            f"revoked, or the account cannot call this model.\n"
            f"Fix: check ANTHROPIC_API_KEY in .env (see .env.example), then run "
            f"`uv run python demos/00_preflight/check.py` to confirm both models are "
            f"reachable before spending anything.\n"
            f"This stopped after one call. Retrying a rejected credential bills three "
            f"times for the same refusal.\n"
            f"The API said: {exc}"
        )
    if isinstance(exc, BAD_REQUEST_ERRORS):
        return TerminationReason.BAD_REQUEST, (
            f"{type(exc).__name__}: {model_id} rejected the request itself, so sending "
            f"it again sends the same rejection.\n"
            f"Fix: check the request kwargs for role '{role}' in "
            f"src/loopeng/registry.py. Sonnet 5 returns this for any non-default "
            f"sampling parameter, which is why temperature=0 is pinned on the worker "
            f"role and not on the frontier one.\n"
            f"The API said: {exc}"
        )
    return None, f"{type(exc).__name__}: {exc}"


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

    @property
    def model_call_failed(self) -> bool:
        """True when the API call failed, so no query ever reached the database.

        Read off the recorded outcome rather than inferred from `sql == ""`. An empty
        string is also what a model that answered with nothing produces, and *that*
        failure genuinely is a database failure — the executor rejects the empty query
        and the error text comes from DuckDB. Renderers must not say `database said`
        about a call that never got as far as the database.
        """
        return self.usage.outcome != "ok"


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
            # them would make the loop look cheaper than it is. That holds for the
            # fatal branch too — a refused call still made a round trip.
            fatal, message = triage_call_failure(exc, role=role, model_id=spec.model_id)
            usage = CallUsage(spec.model_id, "error")
            ledger.record(usage)
            attempts.append(Attempt(n=n, sql="", rows=None, error=message, usage=usage))
            if fatal is not None:
                log.error("model_call_refused", question=question[:60], attempt=n,
                          termination=str(fatal), error=str(exc))
                termination = fatal
                break
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
