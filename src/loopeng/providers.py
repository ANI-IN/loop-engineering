"""One seam between the loops and two model vendors.

The loops are nested and there is exactly one of each. Adding a second vendor must
not become a second copy of `run_question` with different import statements, so
everything vendor-shaped is collected here and the loops above call `complete()`.

WHAT THIS MODULE IS ALLOWED TO KNOW
-----------------------------------

Three things differ between vendors and nothing else is permitted to:

1. **How a request is shaped.** Anthropic takes `system=` as a top-level argument;
   OpenAI takes it as the first message. Both are handed the same neutral
   `(system, messages)` pair and adapt it themselves.
2. **How usage is read off a response.** See the accounting note below — this is
   the part that silently produces wrong dollars if it is got wrong.
3. **Which failures a retry cannot fix.** Both SDKs are generated from the same
   toolchain and expose the same exception hierarchy, but that is a convenience,
   not a contract, so each vendor names its own classes.

Everything else — attempts, budgets, feedback, termination — belongs to the loop
and is written once.

THE ACCOUNTING TRAP, WHICH IS THE REASON THIS FILE IS CAREFUL
-------------------------------------------------------------

The two vendors report cached input tokens with **opposite conventions**, and
getting it wrong is invisible:

    Anthropic   input_tokens EXCLUDES cached tokens; the cache classes are
                reported alongside it and the three are summed to get the total.
    OpenAI      prompt_tokens INCLUDES cached tokens; `cached_tokens` is a
                SUBSET breakdown of it, not an addition to it.

So treating OpenAI's numbers the Anthropic way double-counts every cached token —
once at full input price and once at the cache rate. On this workload the cached
prefix is most of the input on most calls, so the error would be large, would run
in the direction of overstating the agent's cost, and would land directly on the
cost-per-correct-answer chart that closes the session.

`_openai_usage` therefore subtracts, and asserts the subset relation it is relying
on. If OpenAI ever changes the convention, that assertion fails loudly instead of
the charts quietly moving.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import structlog

from loopeng.registry import (
    ANTHROPIC,
    OPENAI,
    PROVIDER_KEY_VARS,
    ModelSpec,
    assert_served_by,
)
from loopeng.settings import Settings, load_settings, require_key
from loopeng.usage import CallUsage

log = structlog.get_logger(__name__)

# What `triage_call_failure` returns for a failure a retry cannot fix. The strings
# are the `TerminationReason` values they map onto — see `loopeng.agent.loop`. They
# are written here as plain strings rather than imported so that this module stays
# below the loops in the import graph.
CREDENTIAL = "credential"
BAD_REQUEST = "bad_request"
MODEL_UNAVAILABLE = "model_unavailable"


class UsageConventionChanged(RuntimeError):
    """A vendor reported cached tokens in a way this module does not model.

    Raised rather than clamped. The two safe-looking repairs — clamping the
    subtraction at zero, or falling back to the other convention — both produce a
    plausible number from an assumption that has just been shown to be false, and
    a plausible wrong number is the thing this entire project is about.
    """


@dataclass(frozen=True)
class Completion:
    """One successful model call: what it said, what it cost, and who answered."""

    text: str
    usage: CallUsage
    # The exact version string the API reported. Often a dated snapshot of the id
    # that was requested, and the more precise of the two, so it is what reaches
    # the provenance block on every result file and every chart.
    served_model: str


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------


def build_client(spec: ModelSpec, settings: Settings | None = None):
    """A vendor client for this role, with the credential checked at the door.

    Imported lazily, per vendor. A checkout that only ever runs the judge should
    not need the OpenAI package importable, and more usefully: the offline suite
    substitutes clients everywhere, so nothing here should run during a test that
    is not about clients.
    """
    settings = load_settings(require_credential=False) if settings is None else settings
    key = require_key(settings, spec.provider).get_secret_value()

    if spec.provider == OPENAI:
        import openai

        return openai.OpenAI(api_key=key)
    if spec.provider == ANTHROPIC:
        import anthropic

        return anthropic.Anthropic(api_key=key)
    raise ValueError(f"unknown provider {spec.provider!r} for role {spec.role!r}")


# ---------------------------------------------------------------------------
# Usage extraction — the careful part. See the module docstring.
# ---------------------------------------------------------------------------


def _int(value: Any) -> int:
    """A count, with None and absence both meaning zero.

    Both SDKs report an inapplicable token class as `None` rather than omitting it,
    and `int(None)` raises, so this is not defensive padding — it is the documented
    shape of both responses.
    """
    return int(value or 0)


def _anthropic_usage(model_id: str, response: Any, outcome: str = "ok") -> CallUsage:
    """Read the four classes off an Anthropic response.

    `input_tokens` already excludes the cache classes, so the fields map straight
    across with no arithmetic.
    """
    usage = getattr(response, "usage", None)
    return CallUsage(
        model_id=model_id,
        outcome=outcome,
        input_tokens=_int(getattr(usage, "input_tokens", 0)),
        output_tokens=_int(getattr(usage, "output_tokens", 0)),
        cache_creation_input_tokens=_int(getattr(usage, "cache_creation_input_tokens", 0)),
        cache_read_input_tokens=_int(getattr(usage, "cache_read_input_tokens", 0)),
    )


def _openai_usage(model_id: str, response: Any, outcome: str = "ok") -> CallUsage:
    """Read the four classes off an OpenAI response, undoing the subset convention.

    `prompt_tokens` is the whole input INCLUDING anything served from cache, and
    `prompt_tokens_details.cached_tokens` says how much of it was. The ledger's
    contract is that the four classes are disjoint and sum to the total, so the
    cached portion is subtracted out of `input_tokens` here rather than at the
    price table, where it would have to be undone again by every other reader.

    `reasoning_tokens` needs no special handling: `completion_tokens` already
    includes it, and it bills at the output rate.
    """
    usage = getattr(response, "usage", None)
    prompt = _int(getattr(usage, "prompt_tokens", 0))
    completion = _int(getattr(usage, "completion_tokens", 0))

    details = getattr(usage, "prompt_tokens_details", None)
    cached = _int(getattr(details, "cached_tokens", 0))
    written = _int(getattr(details, "cache_write_tokens", 0))

    if cached > prompt:
        raise UsageConventionChanged(
            f"{model_id} reported {cached} cached tokens against {prompt} prompt "
            f"tokens. This module models cached_tokens as a SUBSET of prompt_tokens; "
            f"that is no longer true, and every dollar figure downstream depends on "
            f"it. See the accounting note in loopeng.providers."
        )

    return CallUsage(
        model_id=model_id,
        outcome=outcome,
        # The part that was NOT served from cache, and therefore the part billed at
        # full input price.
        input_tokens=prompt - cached,
        output_tokens=completion,
        # Reported since the 2026 usage shape; zero on a response that predates it,
        # which is correct — no write happened that we know of.
        cache_creation_input_tokens=written,
        cache_read_input_tokens=cached,
    )


_USAGE_READERS = {OPENAI: _openai_usage, ANTHROPIC: _anthropic_usage}


def usage_for(spec: ModelSpec, response: Any, outcome: str = "ok") -> CallUsage:
    """The token record for one call, read the way this vendor reports it."""
    return _USAGE_READERS[spec.provider](spec.model_id, response, outcome)


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


def _openai_complete(spec: ModelSpec, client, system: str, messages: Sequence[Mapping]):
    response = client.chat.completions.create(
        model=spec.model_id,
        # The static block goes in the system turn, first and byte-identical on
        # every call. OpenAI caches the longest common prefix automatically, with
        # no marker to set — so prefix STABILITY is the whole mechanism, and
        # anything that varies per item has to sit after this.
        messages=[{"role": "system", "content": system}, *messages],
        **spec.request_kwargs,
    )
    choice = response.choices[0] if response.choices else None
    text = (getattr(getattr(choice, "message", None), "content", None) or "").strip()
    return response, text


def _anthropic_complete(spec: ModelSpec, client, system: str, messages: Sequence[Mapping]):
    response = client.messages.create(
        model=spec.model_id,
        system=system,
        messages=list(messages),
        **spec.request_kwargs,
    )
    text = "".join(
        block.text
        for block in response.content
        if getattr(block, "type", None) == "text"
    ).strip()
    return response, text


_COMPLETERS = {OPENAI: _openai_complete, ANTHROPIC: _anthropic_complete}


def complete(
    spec: ModelSpec,
    *,
    system: str,
    messages: Sequence[Mapping],
    client=None,
) -> Completion:
    """One model call, in whichever vendor's shape this role needs.

    `messages` is the neutral form: `{"role": "user"|"assistant", "content": str}`.
    Both vendors accept exactly that, so no translation is needed beyond where the
    system block goes.

    Raises whatever the vendor raises. The caller records the usage of a failed
    call and decides whether to retry — see `triage_call_failure`.
    """
    client = build_client(spec) if client is None else client
    response, text = _COMPLETERS[spec.provider](spec, client, system, messages)
    served = assert_served_by(spec, getattr(response, "model", None))
    return Completion(text=text, usage=usage_for(spec, response), served_model=served)


# ---------------------------------------------------------------------------
# Failure triage
# ---------------------------------------------------------------------------


def _vendor_errors(provider: str) -> dict[str, tuple]:
    """The exception classes this vendor uses, imported lazily.

    Named against the SDK's own classes rather than against status codes: both SDKs
    already model that mapping, and a second copy of it here is a second thing to
    drift.
    """
    if provider == OPENAI:
        import openai as sdk
    else:
        import anthropic as sdk

    return {
        # 401 / 403 — the key or the account, not the request.
        CREDENTIAL: (sdk.AuthenticationError, sdk.PermissionDeniedError),
        # 400 — the request itself. Sending it again sends the same rejection.
        BAD_REQUEST: (sdk.BadRequestError,),
        # 404 — the model id does not resolve on this account. Previously this fell
        # into the broad retryable arm and was retried three times per item, which
        # at sweep scale is several hundred calls that could not have worked.
        MODEL_UNAVAILABLE: (sdk.NotFoundError,),
    }


def triage_call_failure(
    exc: Exception, *, spec: ModelSpec
) -> tuple[str | None, str]:
    """How to stop after a failed model call, and what to say about it.

    Returns `(termination, message)`. A `None` termination means retryable: the
    tokens billed, the attempt is recorded, and the loop goes round again. Anything
    else stops the loop now, and the message names the variable and the fix in the
    same shape as `MissingCredential`, because the person reading it is in the same
    position.

    Everything not listed — 429, 5xx, timeouts, connection resets — stays retryable
    and reaches the caller's broad arm, so a transport failure class nobody has met
    yet still gets its retry.
    """
    classes = _vendor_errors(spec.provider)
    variable = PROVIDER_KEY_VARS[spec.provider]

    if isinstance(exc, classes[CREDENTIAL]):
        return CREDENTIAL, (
            f"{type(exc).__name__}: the {spec.provider} API rejected the credential "
            f"for {spec.model_id}. {variable} is set but not usable — it is wrong, "
            f"revoked, or the account cannot call this model.\n"
            f"Fix: check {variable} in .env (see .env.example), then run "
            f"`uv run python demos/00_preflight/check.py` to confirm every role is "
            f"reachable before spending anything.\n"
            f"This stopped after one call. Retrying a rejected credential bills "
            f"three times for the same refusal.\n"
            f"The API said: {exc}"
        )

    if isinstance(exc, classes[MODEL_UNAVAILABLE]):
        return MODEL_UNAVAILABLE, (
            f"{type(exc).__name__}: {spec.provider} does not serve "
            f"{spec.model_id!r} to this account. A retired or renamed model id "
            f"looks exactly like this.\n"
            f"Fix: check the model id for role {spec.role!r} in "
            f"src/loopeng/registry.py against the provider's current catalogue.\n"
            f"The API said: {exc}"
        )

    if isinstance(exc, classes[BAD_REQUEST]):
        return BAD_REQUEST, (
            f"{type(exc).__name__}: {spec.model_id} rejected the request itself, so "
            f"sending it again sends the same rejection.\n"
            f"Fix: check the request kwargs for role {spec.role!r} in "
            f"src/loopeng/registry.py. Both OpenAI reasoning models return this for "
            f"a non-default `temperature`, which is why no scoring role pins one.\n"
            f"The API said: {exc}"
        )

    return None, f"{type(exc).__name__}: {exc}"


def retry_after_seconds(
    exc: Exception, attempt: int, *, base: float = 1.0, ceiling: float = 30.0
) -> float:
    """How long to wait before the next attempt.

    The server's own `retry-after` wins. It knows when the pool refills; a client
    doubling a guess is what makes a rate limit last longer than it had to.

    Jitter is added by the caller rather than here, so a test can assert the
    deterministic part of this without stubbing a random source.
    """
    header = getattr(getattr(exc, "response", None), "headers", None)
    if header is not None:
        raw = header.get("retry-after")
        if raw:
            try:
                return min(float(raw), ceiling)
            except (TypeError, ValueError):
                pass
    return min(base * (2 ** (attempt - 1)), ceiling)
