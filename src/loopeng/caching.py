"""Prompt caching: the instrument existed, the number was known, the switch was off.

The apparatus was all here. `pricing.py` prices cache writes at 1.25x and reads at 0.10x.
`usage.py` accounts for `cache_creation_input_tokens` and `cache_read_input_tokens` on
every call. `api_probes.probe_prompt_tokens` determines, per level and per model, whether
the rendered prefix clears that model's minimum cacheable length, and
`cacheability_findings` writes the asymmetry out in words.

**And `cache_control` was never set anywhere in `src/`.** Grepped: zero occurrences
outside the pricing and usage bookkeeping. Every call re-sent the full schema-plus-rules
prefix at full input price, on every item, in every cell.

That is a good teaching beat for a workshop about measurement: an instrument that
reported a finding nobody acted on is not much better than no instrument.

WHAT THE MEASUREMENT ACTUALLY SAYS
----------------------------------

From `results/gate0.json`, measured 2026-07-29 with `count_tokens`:

    role      model              minimum   L0 tokens   L3 tokens
    worker    claude-haiku-4-5      4096         286         648
    frontier  claude-sonnet-5       1024         548        1037

So exactly one combination clears its minimum: **frontier at L3**. Haiku's minimum is
four times Sonnet's and its prefix is shorter, so no Haiku prefix in this project can
cache at all. That is the asymmetry the probe already reported — and it means switching
caching on is a real saving on the expensive cells and, correctly, a no-op elsewhere.

WHY THE GATE READS THE PROBE RATHER THAN RE-DERIVING IT
------------------------------------------------------

Token counts are a measurement. Estimating them here from character length would be a
second, worse instrument sitting beside a good one — and it would be wrong in the
direction that matters, because claiming a prefix is cacheable when it is not would make
the reported hit rate a fiction.

So the gate consumes the committed probe. With no probe on disk it refuses to claim
cacheability at all rather than guessing: a request that carries `cache_control` for a
prefix too short to cache is not an error, but it changes the request for no benefit and
poisons the saving figure.

WHAT STAYS OUTSIDE THE CACHED PREFIX
------------------------------------

The retry feedback, necessarily. It is appended as later conversation turns, so the
cached prefix is byte-identical on attempt three and attempt one. Putting the feedback
inside the prefix would break the cache on every retry — which is every call a loop makes
beyond the first, i.e. the ones the whole cost comparison is about.
"""

import json
from pathlib import Path

import structlog

from loopeng.api_probes import CACHE_MINIMUM_TOKENS
from loopeng.pricing import prices_for
from loopeng.registry import spec_for

log = structlog.get_logger(__name__)

# The committed probe output. Gate 0 evidence, cited throughout the design record.
PROBE_PATH = Path("results/gate0.json")

# Anthropic's marker for a cacheable prefix boundary, and the shortest-lived tier —
# which is the one priced in `pricing.cache_write_5m`. A cell of 50 items at the sweep's
# concurrency finishes well inside five minutes, so the reads land.
CACHE_CONTROL = {"type": "ephemeral"}


def probe(path: Path = PROBE_PATH) -> dict:
    """The measured token counts per role and level, or `{}` when none are on disk."""
    path = Path(path)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text()).get("prompts", {}).get("token_counts", {}) or {}
    except (OSError, json.JSONDecodeError):
        return {}


def prefix_is_cacheable(role: str, level: str, *, measured: dict | None = None) -> bool:
    """Does this role's prefix at this level clear the model's minimum cacheable length?

    Answered from the measurement, never from an estimate. `False` when there is no
    measurement, because a `cache_control` marker on a prefix that cannot cache changes
    the request for nothing and makes the reported hit rate a fiction.
    """
    counts = probe() if measured is None else measured
    entry = counts.get(role, {}).get(level)
    if not isinstance(entry, dict) or "tokens" not in entry:
        return False
    minimum = counts[role].get("cache_minimum") or CACHE_MINIMUM_TOKENS.get(
        spec_for(role).model_id
    )
    if minimum is None:
        return False
    return int(entry["tokens"]) >= int(minimum)


def user_content(prompt: str, question: str, *, role: str, level: str) -> str | list[dict]:
    """The first user turn, as one block or as a cacheable prefix plus the question.

    **Returns the plain string unchanged when the prefix cannot cache.** That is not
    tidiness: it keeps the request byte-identical to what the committed reference
    measurements were taken with for every cell that gains nothing from splitting.
    Where it does split, the two adjacent text blocks concatenate to exactly the same
    text the single block carried.
    """
    tail = f"\n\nQuestion: {question}"
    if not prefix_is_cacheable(role, level):
        return f"{prompt}{tail}"
    return [
        # The static schema-plus-rules prefix, identical for every item in the cell.
        {"type": "text", "text": prompt, "cache_control": CACHE_CONTROL},
        # The question, which changes per item and must sit past the boundary.
        {"type": "text", "text": tail},
    ]


def hit_rate(tokens: dict) -> float | None:
    """Cache reads as a share of all prefix input, or None when nothing was cached.

    `None` rather than `0.0`: a cell where caching never applied did not achieve a zero
    hit rate, it had no cache to hit, and a zero on a chart reads as a measurement.
    """
    read = tokens.get("cache_read_input_tokens", 0)
    written = tokens.get("cache_creation_input_tokens", 0)
    if not read and not written:
        return None
    served = read + written
    return read / served if served else None


def saving_usd(tokens: dict, model_id: str) -> float | None:
    """Estimated dollars caching saved on this cell, against paying full input price.

    Estimated, like every dollar figure here — it is the same hand-entered price table.
    `None` when caching did not apply, for the same reason as `hit_rate`.
    """
    read = tokens.get("cache_read_input_tokens", 0)
    written = tokens.get("cache_creation_input_tokens", 0)
    if not read and not written:
        return None
    prices = prices_for(model_id)
    uncached = (read + written) * prices.input
    actual = read * prices.cache_read + written * prices.cache_write_5m
    return (uncached - actual) / 1_000_000


def findings(measured: dict | None = None) -> list[str]:
    """Which combinations cache and which do not, in words, from the measurement."""
    counts = probe() if measured is None else measured
    if not counts:
        return [
            f"No token measurement on disk ({PROBE_PATH}), so caching is switched off "
            f"rather than guessed at. Run the Gate 0 probe to enable it."
        ]
    lines = []
    for role in sorted(counts):
        for level in sorted(k for k in counts[role] if isinstance(counts[role][k], dict)):
            entry = counts[role][level]
            verdict = "caches" if prefix_is_cacheable(role, level, measured=counts) \
                else "does NOT cache"
            lines.append(
                f"{role}/{level}: {entry['tokens']} prefix tokens against a "
                f"{counts[role]['cache_minimum']} minimum — {verdict}"
            )
    return lines
