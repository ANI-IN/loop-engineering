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
bare `except Exception` around the model call treated a revoked API key exactly like a
transient 529: three round-trips, then `max_attempts`, and a screen that said
`database said: AuthenticationError` — blaming the warehouse for a credential problem.
At sweep scale that is ~200 doomed calls before a uniformly failed grid.

A retry is only a retry when the next attempt could plausibly differ. The triage in
`loopeng.providers` names the set where it cannot, and the loop stops on the first one
with a message naming the variable and the fix. Retrying those is not a budget guard;
it is spend with a guaranteed zero return.

**ONE LOOP, TWO VENDORS.** The agent is an OpenAI budget model and the judge is
Anthropic, and nothing about that reaches this file. Everything vendor-shaped —
request shape, usage conventions, which failures are fatal — lives behind
`loopeng.providers.complete`. A second copy of this loop with different imports would
be a second place for the termination policy to drift, and the termination policy is
what the session is about.

**WHERE THE STATIC PREFIX GOES, AND WHY IT MOVED.** The schema and the business rules
are byte-identical on every call in a run, and they now sit in the `system` block —
first, ahead of everything that varies. They used to be concatenated with the question
into a single user turn, which put a per-item string inside the cached region and made
the prefix different on every call. OpenAI caches the longest common prefix
automatically, with no marker to set, so prefix STABILITY is the entire mechanism and
that layout defeated it silently: no error, no warning, just full input price on every
call. The retry feedback is appended as later turns for the same reason — feedback
inside the prefix would break the cache on every retry, which is every call a loop
makes beyond the first.
"""

import random
import re
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Protocol

import structlog

from loopeng.prompts import render_prompt
from loopeng.providers import complete, retry_after_seconds, triage_call_failure
from loopeng.registry import spec_for
from loopeng.sql_shape import declares_unbound_parameter
from loopeng.usage import CallUsage, UsageLedger
from loopeng.warehouse.connect import QueryTimeout, run_sql

log = structlog.get_logger(__name__)

DEFAULT_MAX_ATTEMPTS = 3

# Per question, not per run. Sized so one pathological question cannot eat a sweep.
#
# Lowered along with the model policy. The agent is a budget model at $0.20/$1.20 per
# million tokens, so the old $0.10 ceiling was roughly two hundred full attempts —
# a cap that could never bind, which is a cap in name only.
DEFAULT_BUDGET_USD = 0.02

_SQL_FENCE = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)

# Jitter on the retry backoff, as a fraction of the computed delay.
#
# Without it, N workers rate-limited by the same 429 all sleep the same duration and
# arrive back together — the thundering herd that turns one rate limit into a
# sustained one. The sweep runs several requests in flight per model, so this is the
# regime it actually operates in.
BACKOFF_JITTER = 0.25


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

    # The model named an input it was not given rather than inventing one, in SQL,
    # so the query cannot execute. That is a terminal state and it is not a failure.
    #
    # **It existed as a gap for the life of this enum, and the gap is the same one
    # the classifier had.** A declining run fell through to `max_attempts`, which is
    # the default terminal state — so on the reference arm at L0 the distribution read
    # `{success: 41, max_attempts: 19}`, and those nineteen were exactly the
    # nineteen abstentions. The vocabulary that names outcomes could not distinguish
    # RAN OUT OF ROAD from REFUSED TO GUESS, which is the precise distinction this
    # whole project is about.
    #
    # Retrying is pointless and it is not a budget guard: the missing input is missing
    # by construction at this prompt level, and another attempt cannot supply it.
    DECLINED = "declined"

    # The non-retryable branches. Separate names rather than one, because they are
    # different problems with different fixes and a run labelled `credential` when the
    # request was merely malformed would send an operator to the wrong file.
    CREDENTIAL = "credential"                # 401/403 — the key or the account
    BAD_REQUEST = "bad_request"              # 400 — the request itself
    MODEL_UNAVAILABLE = "model_unavailable"  # 404 — the id does not resolve here


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
    # The exact version string the API reported for this run, which is usually a
    # dated snapshot of `model_id`. Recorded because a silent model swap would
    # invalidate every comparison in the run and nothing on any chart would look
    # wrong — see `registry.assert_served_by`.
    served_model: str | None = None

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
    """Just enough of a vendor client for the loop, so tests can substitute.

    Deliberately loose. The two vendors expose different surfaces — `messages.create`
    against `chat.completions.create` — and the loop touches neither directly; it
    hands whatever it is given to `loopeng.providers.complete`, which knows which one
    this role needs.
    """


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


def build_turns(question: str, history: list[Attempt]) -> list[dict]:
    """The conversation turns, everything that varies per item and per attempt.

    The static schema-and-rules block is NOT here — it is the system prompt, so that
    the cacheable prefix is identical across every call in a run. See the module
    docstring.
    """
    turns: list[dict] = [{"role": "user", "content": f"Question: {question}"}]
    for attempt in history:
        # A call that never reached the model produced no query, so there is no
        # turn to replay and nothing the database ever complained about.
        #
        # This used to append `{"role": "assistant", "content": ""}` followed by
        # "That query failed with: RateLimitError: 429 — return a corrected
        # query", which is false twice over: the model wrote nothing to correct,
        # and the *database* never saw it. `Attempt.model_call_failed` already
        # states this rule in its own docstring — "Renderers must not say
        # `database said` about a call that never got as far as the database" —
        # and this builder was the one place ignoring it.
        #
        # The empty assistant turn was the more expensive half. A non-final
        # assistant message with empty content is rejected by both vendors, and
        # `triage_call_failure` maps that 400 to the FATAL `bad_request`, so a
        # transient 429 that should have been retried ended the run instead and
        # pointed the operator at registry.py — the wrong file entirely.
        if attempt.model_call_failed:
            continue
        turns.append({"role": "assistant", "content": attempt.sql})
        # The only feedback this level has. Not a hint, not a rule reminder — the
        # database's own complaint, which is all a Level 1 loop is entitled to.
        turns.append(
            {
                "role": "user",
                "content": (
                    f"That query failed with:\n{attempt.error}\n\n"
                    "Return a corrected query. SQL only."
                ),
            }
        )
    return turns


def backoff_delay(exc: Exception, attempt: int, *, rng: random.Random | None = None) -> float:
    """The retry delay, with jitter, so concurrent workers do not resynchronise."""
    base = retry_after_seconds(exc, attempt)
    rng = random.Random() if rng is None else rng
    return base * (1 + rng.uniform(0, BACKOFF_JITTER))


def run_question(
    question: str,
    *,
    warehouse: Path,
    role: str = "agent",
    level: str = "L3",
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    budget_usd: float = DEFAULT_BUDGET_USD,
    client: SupportsMessages | None = None,
    item_id: str | None = None,
    timeout_s: float = 30.0,
    sleeper=time.sleep,
) -> AgentRun:
    """Run one question to termination. Never raises on a model or SQL failure."""
    spec = spec_for(role)
    system = render_prompt(level)

    ledger = UsageLedger()
    attempts: list[Attempt] = []
    seen_sql: set[str] = set()
    seen_errors: set[str] = set()
    termination = TerminationReason.MAX_ATTEMPTS
    served_model: str | None = None

    for n in range(1, max_attempts + 1):
        # Checked before spending, not after: a budget enforced only in arrears is a
        # report of what was overspent rather than a cap.
        if ledger.cost_usd() >= budget_usd:
            termination = TerminationReason.BUDGET
            break

        try:
            completion = complete(
                spec,
                system=system,
                messages=build_turns(question, attempts),
                client=client,
            )
            usage = completion.usage
            served_model = completion.served_model
            sql = extract_sql(completion.text)
        except Exception as exc:  # noqa: BLE001 - a failed call still billed
            # Recorded, not swallowed: the tokens are gone either way, and dropping
            # them would make the loop look cheaper than it is. That holds for the
            # fatal branch too — a refused call still made a round trip.
            fatal, message = triage_call_failure(exc, spec=spec)
            usage = CallUsage(spec.model_id, "error")
            ledger.record(usage)
            attempts.append(Attempt(n=n, sql="", rows=None, error=message, usage=usage))
            if fatal is not None:
                log.error("model_call_refused", question=question[:60], attempt=n,
                          termination=fatal, error=str(exc))
                termination = TerminationReason(fatal)
                break
            log.warning("model_call_failed", question=question[:60], attempt=n,
                        error=str(exc))
            # Retryable, so wait before going round. Retrying a 429 immediately
            # arrives back at the same limit and makes it last longer.
            if n < max_attempts:
                sleeper(backoff_delay(exc, n))
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

        # Asked before the failure is treated as something to retry. A query naming
        # the input it was not given did not fail; it declined, and another attempt
        # cannot supply what the prompt withheld.
        if declares_unbound_parameter(sql):
            termination = TerminationReason.DECLINED
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
        served_model=served_model,
    )
