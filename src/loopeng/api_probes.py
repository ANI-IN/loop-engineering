"""Live probes: rate-limit ceilings, and whether prompt caching actually fires.

Both are cheap on purpose. The rate-limit probe reads response headers off **one**
minimal call per role and never loops toward a 429 — deliberately provoking a rate
limit costs money, poisons the pool for whatever runs next, and tells you nothing
the headers do not already say.

**The cacheability probe changed shape, and the new shape is the honest one.**

It used to token-count the rendered prefix and compare it against a documented
minimum, then declare the prefix cacheable if the number cleared the threshold. That
is an *inference*, and it inherited every assumption in it: that the documented
minimum is current, that the prefix reaching the API is the one that was counted, and
that clearing the minimum is sufficient rather than merely necessary. On a project
whose entire subject is the gap between a declared rule and an enforced one, deciding
caching works by reading a number off a documentation page was the wrong instrument.

So it now **makes the same call twice and reads `cached_tokens` off the second one**.
A cache that fires reports the hit; a cache that does not, does not. There is no
threshold to be stale about and no inference to be wrong. It costs two agent calls —
a fraction of a cent — and it answers the question that was actually being asked.

**Named `api_probes`, not `probes`.** There is a second, unrelated `probes` module —
`loopeng.verify.probes`, the OFFLINE rule-surface probes — and the two do genuinely
different things: this one calls the API and costs money, that one is a pure function
over SQL text and costs nothing. Sharing the name made every import site ambiguous and
easy to get wrong in the direction that spends. Deliberately NOT merged: they are not
two halves of one idea.
"""

import structlog

from loopeng.prompts import LEVELS, render_prompt
from loopeng.providers import build_client, complete
from loopeng.registry import REGISTRY, SCORING_ROLES, spec_for
from loopeng.usage import UsageLedger

log = structlog.get_logger(__name__)

# The shortest question that still produces a real request. The probe is about the
# prefix, not about the answer, so the tail is kept minimal and identical between
# the two calls.
PROBE_QUESTION = "Reply with the single word: ok"


def probe_rate_limits(ledger: UsageLedger | None = None) -> dict[str, dict[str, str]]:
    """One minimal call per role; record every rate-limit header it returns.

    Header *names* are recorded rather than asserted. Each vendor documents its own
    set and the exact suffixes differ, so the probe writes down what is actually
    present instead of claiming to know.

    Rate limits are **per-model pools**, so one probe is not enough and every role's
    ceiling is recorded separately. The agent and the reference share a vendor and
    still do not share a bucket.
    """
    observed: dict[str, dict[str, str]] = {}

    for role, spec in sorted(REGISTRY.items()):
        client = build_client(spec)
        raw = _with_raw_response(spec, client)
        if ledger is not None:
            from loopeng.providers import usage_for

            ledger.record(usage_for(spec, raw.parse()))

        headers = {
            name.lower(): value
            for name, value in raw.headers.items()
            if "ratelimit" in name.lower() or name.lower() == "retry-after"
        }
        observed[role] = {"model_id": spec.model_id, **headers}
        log.info("rate_limit_probe", role=role, model=spec.model_id,
                 headers=sorted(headers))

    return observed


def _with_raw_response(spec, client):
    """The minimal call, with headers preserved, in this vendor's shape.

    Both SDKs expose `.with_raw_response`, but they hang it off different methods,
    and the whole point of `loopeng.providers` is that the loops never learn that.
    A probe is the one place where the headers ARE the result, so the vendor branch
    is here rather than pushed into the seam where it would serve nothing else.
    """
    from loopeng.registry import OPENAI

    if spec.provider == OPENAI:
        return client.chat.completions.with_raw_response.create(
            model=spec.model_id,
            messages=[{"role": "user", "content": PROBE_QUESTION}],
            **spec.request_kwargs,
        )
    return client.messages.with_raw_response.create(
        model=spec.model_id,
        messages=[{"role": "user", "content": PROBE_QUESTION}],
        **spec.request_kwargs,
    )


def probe_cache_behaviour(
    ledger: UsageLedger | None = None, *, roles: tuple[str, ...] = SCORING_ROLES
) -> dict[str, dict[str, object]]:
    """Call twice with an identical prefix and report whether the second one hit.

    This is a MEASUREMENT, not a threshold check. The returned `cached_tokens` is
    what the API said it served from cache on the second call; `hit` is simply
    whether that number is above zero.

    Only the scoring roles are probed. The judge sees a different, short prompt and
    is not on the path any cost figure depends on, so measuring its cache behaviour
    would be spending to learn something nothing reads.
    """
    results: dict[str, dict[str, object]] = {}

    for role in roles:
        spec = spec_for(role)
        client = build_client(spec)
        per_level: dict[str, object] = {"model_id": spec.model_id}

        for level in LEVELS:
            system = render_prompt(level)
            messages = [{"role": "user", "content": PROBE_QUESTION}]

            # First call populates. Its own cached_tokens is expected to be zero and
            # is recorded anyway — a non-zero reading here means an earlier run
            # already warmed this prefix, which is worth seeing rather than hiding.
            first = complete(spec, system=system, messages=messages, client=client)
            second = complete(spec, system=system, messages=messages, client=client)

            if ledger is not None:
                ledger.record(first.usage)
                ledger.record(second.usage)

            cached = second.usage.cache_read_input_tokens
            prefix_tokens = (
                second.usage.input_tokens + second.usage.cache_read_input_tokens
            )
            per_level[level] = {
                "prefix_tokens": prefix_tokens,
                "cached_tokens": cached,
                "hit": cached > 0,
                "first_call_cached_tokens": first.usage.cache_read_input_tokens,
            }
            log.info("cache_probe", role=role, level=level,
                     prefix_tokens=prefix_tokens, cached_tokens=cached, hit=cached > 0)

        results[role] = per_level

    return results


def cacheability_findings(probe: dict[str, dict[str, object]]) -> list[str]:
    """Plain-English notes, read out of the measurement rather than restated."""
    findings: list[str] = []
    for level in LEVELS:
        by_role = {
            role: body[level]
            for role, body in probe.items()
            if isinstance(body.get(level), dict)
        }
        if not by_role:
            continue
        hit = {role: bool(entry["hit"]) for role, entry in by_role.items()}

        if all(hit.values()):
            findings.append(
                f"{level} is served from cache on every scoring role. The prefix is "
                "identical across every call in a run, so this is the token class "
                "that dominates the agent's bill and it is being discounted."
            )
        elif not any(hit.values()):
            findings.append(
                f"{level} is not served from cache anywhere. Either the prefix is "
                "below the vendor's minimum cacheable length or something varies "
                "inside it between calls — check that nothing per-item has drifted "
                "into the system block."
            )
        else:
            caches_on = sorted(r for r, v in hit.items() if v)
            not_on = sorted(r for r, v in hit.items() if not v)
            findings.append(
                f"{level} caches on {', '.join(caches_on)} but NOT on "
                f"{', '.join(not_on)}. This is silent — no error, just a different "
                "cost per cell — and it lands directly on the cost comparison."
            )
    return findings
