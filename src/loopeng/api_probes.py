"""Live probes: rate-limit ceilings and prompt cacheability.

Both are cheap on purpose. The rate-limit probe reads response headers off **one**
minimal call per model and never loops toward a 429 — deliberately provoking a rate
limit costs money, poisons the pool for whatever runs next, and tells you nothing
the headers do not already say. The cacheability probe uses `count_tokens`, which
does not run the model at all.

Rate limits are **per-model pools**: Haiku 4.5 and Sonnet 5 do not share a bucket,
so one probe is not enough and both ceilings are recorded.

**Named `api_probes`, not `probes`.** There is a second, unrelated `probes` module —
`loopeng.verify.probes`, the OFFLINE rule-surface probes — and the two do genuinely
different things: this one calls the API and costs money, that one is a pure function
over SQL text and costs nothing. Sharing the name made every import site ambiguous and
README §11's `from loopeng.verify.probes import run_probes` easy to get wrong in the
direction that spends. Deliberately NOT merged: they are not two halves of one idea.
"""

import anthropic
import structlog

from loopeng.prompts import LEVELS, render_prompt
from loopeng.registry import REGISTRY
from loopeng.settings import load_settings
from loopeng.usage import CallUsage, UsageLedger

log = structlog.get_logger(__name__)

# Documented minimum cacheable prefix, per model. These are API facts from the
# prompt-caching docs, not measurements, so they may be written as literals.
CACHE_MINIMUM_TOKENS: dict[str, int] = {
    "claude-haiku-4-5": 4096,
    "claude-sonnet-5": 1024,
}


def _anthropic_client() -> anthropic.Anthropic:
    settings = load_settings()
    return anthropic.Anthropic(api_key=settings.anthropic_api_key.get_secret_value())


def probe_rate_limits(ledger: UsageLedger | None = None) -> dict[str, dict[str, str]]:
    """One minimal call per model; record every rate-limit header it returns.

    Header *names* are recorded rather than asserted. The documented ones are
    `retry-after` and `anthropic-ratelimit-*`, but the exact suffixes are not
    enumerated in any source available here, so the probe writes down what is
    actually present instead of claiming to know.
    """
    client = _anthropic_client()
    observed: dict[str, dict[str, str]] = {}

    for role, spec in sorted(REGISTRY.items()):
        raw = client.messages.with_raw_response.create(
            model=spec.model_id,
            messages=[{"role": "user", "content": "ok"}],
            max_tokens=1,
        )
        response = raw.parse()
        if ledger is not None:
            ledger.record(CallUsage.from_response(spec.model_id, response))

        headers = {
            name.lower(): value
            for name, value in raw.headers.items()
            if "ratelimit" in name.lower() or name.lower() == "retry-after"
        }
        observed[role] = {"model_id": spec.model_id, **headers}
        log.info("rate_limit_probe", role=role, model=spec.model_id, headers=sorted(headers))

    return observed


def probe_prompt_tokens(ledger: UsageLedger | None = None) -> dict[str, dict[str, object]]:
    """Token-count the rendered L0 and L3 prompts against both models.

    `count_tokens` does not run the model, so this is effectively free, but it is
    still a network call and still marked live.

    The finding that matters is asymmetric caching. The minimum cacheable prefix is
    1024 tokens on Sonnet 5 and 4096 on Haiku 4.5, so a prompt landing between those
    two numbers caches on Sonnet and silently does not on Haiku — no error, just a
    different cost per cell, on the exact comparison the workshop is built around.
    """
    client = _anthropic_client()
    results: dict[str, dict[str, object]] = {}

    for role, spec in sorted(REGISTRY.items()):
        minimum = CACHE_MINIMUM_TOKENS[spec.model_id]
        per_level: dict[str, object] = {"model_id": spec.model_id, "cache_minimum": minimum}

        for level in LEVELS:
            prompt = render_prompt(level)
            counted = client.messages.count_tokens(
                model=spec.model_id,
                messages=[{"role": "user", "content": prompt}],
            )
            tokens = counted.input_tokens
            per_level[level] = {
                "tokens": tokens,
                "cacheable": tokens >= minimum,
                "shortfall": max(0, minimum - tokens),
            }
            log.info(
                "prompt_token_probe",
                role=role,
                level=level,
                tokens=tokens,
                cacheable=tokens >= minimum,
            )

        results[role] = per_level

    return results


def cacheability_findings(probe: dict[str, dict[str, object]]) -> list[str]:
    """Plain-English notes, including the asymmetric case flagged explicitly."""
    findings = []
    for level in LEVELS:
        by_role = {
            role: body[level]
            for role, body in probe.items()
            if isinstance(body.get(level), dict)
        }
        cacheable = {role: entry["cacheable"] for role, entry in by_role.items()}
        if len(set(cacheable.values())) > 1:
            caches_on = sorted(r for r, v in cacheable.items() if v)
            not_on = sorted(r for r, v in cacheable.items() if not v)
            findings.append(
                f"{level} caches on {', '.join(caches_on)} but NOT on {', '.join(not_on)}. "
                "This is silent — no error, just a different cost per cell — and it lands "
                "directly on the cost comparison, because the cheaper model is the one "
                "paying full price for its prefix on every call."
            )
        elif all(cacheable.values()):
            findings.append(f"{level} clears the cache minimum on every model.")
        else:
            findings.append(
                f"{level} clears the cache minimum on no model; its prefix is too short "
                "to cache anywhere, so caching cannot reduce sweep cost for this level."
            )
    return findings
