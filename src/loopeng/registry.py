"""Role to model, and the request kwargs each model actually accepts.

Three roles, and the split between them is the whole argument of the session:

    role       model           where it runs                             volume
    agent      gpt-5.6-luna    every loop, every retry, every sweep cell  high
    reference  gpt-6-astra     one bare arm, no loops, held-out only      ~60 calls
    judge      claude-haiku-4-5 triage and failure sorting, never blocks  low

**The agent is a budget model and nothing it does escapes that.** If any part of
the loop quietly escalated to a better model, the claim "cheap plus loops matches
frontier bare" would be measuring something else.

**The reference runs exactly one condition and it is not a contradiction.** Without
a frontier arm there is no bar, and "cheap plus loops matches frontier" is a
sentence with nothing behind it. It is ~60 calls, bare, on the held-out set, and it
is budgeted for.

**The judge is Anthropic, and the different lab is the point.** The README's own
objection to LLM judges is that a judge from the same family as the thing being
judged is not an independent check. Both scoring arms are OpenAI; the judge is not.
It triages and sorts failures. It never gates — see `loopeng.triage`.

WHY A ROLE IS NOT A STRING
--------------------------

The three models do not accept the same request, and the differences are 400s
rather than warnings:

    parameter              gpt-5.6-luna    gpt-6-astra     claude-haiku-4-5
    temperature            400             400             allowed
    max_tokens             deprecated      deprecated      required
    max_completion_tokens  required        required        n/a
    reasoning_effort       none..max       none..max       n/a
    seed                   best-effort     best-effort     n/a

So a role maps to a provider, a model id, *and* the kwargs that are legal for it.
Swapping a model is still one edit; the edit is just larger than a string.

THE TEMPERATURE STORY INVERTED, AND THAT MATTERS
------------------------------------------------

This project used to pin `temperature=0` on the cheap model and could not pin it on
the frontier one, so the caveat was *asymmetric*: one arm's error bars carried
sampling noise, the other's carried sampling noise plus run-to-run variance, and no
cross-model comparison was legitimate.

Under the current policy **no arm can be pinned.** `gpt-5.6-luna` and `gpt-6-astra`
are both reasoning models and both reject a non-default `temperature` with a 400.
That is a real loss and it is stated rather than buried: every interval on every
chart now carries run-to-run variance.

It is also, on the comparison that matters, an improvement. A, B, C and D are now
in the *same* sampling regime from the *same* vendor, so C-vs-D is no longer
confounded by one arm being pinned and the other not. The asymmetry did not get
smaller; it got symmetric, which is a different and more useful thing.

What is left to pin is `seed` and `reasoning_effort`. `seed` is documented as
best-effort rather than a guarantee, so it reduces the floor without removing it —
which is why `scripts/measure_noise_floor.py` measures what is left instead of
this module asserting a number it cannot know.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

OPENAI = "openai"
ANTHROPIC = "anthropic"

# The environment variable holding each vendor's credential.
#
# pydantic derives the same names from the field names on `Settings`, so these two
# spellings are mechanically linked and a test asserts they agree. Written out here
# anyway because every failure message a user reads names the VARIABLE, and a message
# that has to reach into the settings layer to say which one is a message that will
# eventually say the wrong one.
PROVIDER_KEY_VARS = MappingProxyType(
    {OPENAI: "OPENAI_API_KEY", ANTHROPIC: "ANTHROPIC_API_KEY"}
)

# Best-effort determinism, pinned so two runs of the same cell differ as little as
# the vendor allows. It is NOT a guarantee and this project does not treat it as
# one: the residual disagreement is measured, not assumed away.
#
# The value is the warehouse seed, so a run's sampling seed and its data seed are
# the same number and neither can be changed without the other being noticed.
SAMPLING_SEED = 20260729


@dataclass(frozen=True)
class ModelSpec:
    """One role's model, and everything needed to call it correctly."""

    role: str
    provider: str
    model_id: str
    request_kwargs: Mapping[str, Any]
    # Why this model holds this role. Rendered into the run summary and the
    # provenance block, so the reason travels with the number rather than living
    # only in this file.
    note: str


REGISTRY: Mapping[str, ModelSpec] = MappingProxyType(
    {
        "agent": ModelSpec(
            role="agent",
            provider=OPENAI,
            model_id="gpt-5.6-luna",
            request_kwargs=MappingProxyType(
                {
                    # `max_tokens` is deprecated on this family and rejected on
                    # reasoning models. SQL is short; this is headroom, not a target.
                    "max_completion_tokens": 2048,
                    # The cheapest setting, and the correct one. Writing a SELECT
                    # against a schema in the prompt is not a reasoning task, and
                    # paying for reasoning tokens on every retry of every cell is
                    # the largest avoidable line in the agent's bill.
                    #
                    # It also sidesteps a real constraint: the 5.6 family rejects
                    # function tools unless effort is 'none' or the call goes to
                    # /v1/responses. Nothing here uses function tools, but a future
                    # author adding one should not discover that at sweep scale.
                    "reasoning_effort": "none",
                    "seed": SAMPLING_SEED,
                }
            ),
            note=(
                "Budget tier, current generation. Chosen over gpt-4o-mini for the "
                "cache read discount: 90% here against 50% there, on a workload whose "
                "input is a byte-identical prefix on every call."
            ),
        ),
        "reference": ModelSpec(
            role="reference",
            provider=OPENAI,
            model_id="gpt-6-astra",
            request_kwargs=MappingProxyType(
                {
                    # Headroom for reasoning plus the SQL together — this cap covers
                    # both, so it is sized to the pair rather than to the query.
                    "max_completion_tokens": 8192,
                    # Deliberately NOT lowered. The bar has to be the model as it
                    # would actually be deployed, and handicapping it to save money
                    # would make the comparison flattering rather than informative.
                    # The default is what ships.
                    "seed": SAMPLING_SEED,
                }
            ),
            note=(
                "OpenAI's flagship, run bare on the held-out set. Same vendor as the "
                "agent on purpose: C vs D then isolates the loops rather than "
                "confounding them with a change of lab."
            ),
        ),
        "judge": ModelSpec(
            role="judge",
            provider=ANTHROPIC,
            model_id="claude-haiku-4-5",
            request_kwargs=MappingProxyType(
                {
                    "max_tokens": 1024,
                    # Pinned because this model accepts it. The judge sorts failures
                    # into named buckets; a triage label that moves between runs makes
                    # the same failure look like two.
                    "temperature": 0,
                }
            ),
            note=(
                "A different lab from both scoring arms, which is what makes it an "
                "independent read. Triage and failure sorting only — it never gates, "
                "and no number it produces reaches a pass/fail decision."
            ),
        ),
    }
)

# Roles that spend on the measured path. `judge` is excluded: it reads finished
# runs and sorts them, so it is never on the path that produces a cell's outcome.
SCORING_ROLES = ("agent", "reference")


class UnknownRole(KeyError):
    """Raised rather than defaulting, so a typo cannot silently pick a model."""


class ModelVersionMismatch(RuntimeError):
    """The API served a different model than the one requested.

    Raised rather than logged. A silent model swap mid-session would invalidate
    every comparison in the run and nothing on any chart would look wrong — which
    is the worst failure shape this project has, because it is undetectable after
    the fact. The response's own `model` field is the only place the substitution
    is visible, so it is checked on every call.
    """


def spec_for(role: str) -> ModelSpec:
    try:
        return REGISTRY[role]
    except KeyError as exc:
        raise UnknownRole(
            f"unknown role {role!r}; the registry defines {sorted(REGISTRY)}"
        ) from exc


def assert_served_by(spec: ModelSpec, served_model: str | None) -> str:
    """Confirm the response came from the model that was asked for.

    Returns the exact version string the API reported, which is what gets stamped
    into provenance — `gpt-5.6-luna` is what we request, and a dated snapshot is
    often what answers. The snapshot is the more precise fact, so it is the one
    recorded.

    A snapshot of the requested model is accepted; anything else raises. `None` is
    accepted too: a stubbed client in the offline suite reports no model, and
    refusing that would make the check impossible to test without a network.
    """
    if served_model is None:
        return spec.model_id
    if not served_model.startswith(spec.model_id):
        raise ModelVersionMismatch(
            f"role {spec.role!r} requested {spec.model_id!r} and the API served "
            f"{served_model!r}. These are different models, so every number in this "
            f"run would be a mixture of two. Stopping here rather than recording it.\n"
            f"Check the model id in src/loopeng/registry.py against the provider's "
            f"current catalogue — a retired id can be silently rerouted."
        )
    return served_model


def key_variable_for_role(role: str) -> str:
    """The environment variable this role's credential comes from."""
    return PROVIDER_KEY_VARS[spec_for(role).provider]
