"""Prompt caching: what it saves, read off the responses rather than asserted.

**The apparatus was here long before the optimisation was.** `pricing.py` has priced
cache reads and writes since Phase 0, `usage.py` has carried all four token classes on
every call, and a probe reported which prefixes could cache. And `cache_control` was
set nowhere: every call re-sent the full schema-plus-rules prefix at full input price,
on every item, in every cell. An instrument that reported a finding nobody acted on is
not much better than no instrument.

WHAT CHANGED, AND WHY THE MECHANISM IS SMALLER NOW
---------------------------------------------------

Under the Anthropic-only policy, caching had to be switched on explicitly with a
`cache_control` marker, and only fired above a per-model minimum prefix length that
none of the cheap cells cleared. So this module used to hold a marker-placement
function, a documented-minimum table, and a gate that refused to set the marker
without a committed measurement — a lot of machinery whose measured conclusion was
"this saves nothing on any profile you are likely to run."

The agent is now an OpenAI budget model, where **caching is automatic**. There is no
marker to place and no gate to hold. What decides whether it fires is prefix
STABILITY, which is a property of how the prompt is assembled — so the mechanism
moved to `agent.loop.run_question`, which puts the static schema-and-rules block in
the `system` turn ahead of everything that varies, and this module went back to being
what it should have been: reporting.

That is the largest single win available here, and it is part of the argument rather
than a footnote. Cheap models plus a 90% discount on the token class that dominates
the workload is what makes the cost-per-correct-answer chart land the way it does.

WHAT STAYS OUTSIDE THE CACHED PREFIX
------------------------------------

The question, and the retry feedback. Both are appended as later turns, so the cached
prefix is byte-identical on attempt three and attempt one. Putting either inside the
prefix would break the cache on every retry — which is every call a loop makes beyond
the first, i.e. the ones the whole cost comparison is about. `tests/test_caching.py`
asserts the system block does not vary with the question or the attempt history.
"""

import structlog

from loopeng.pricing import prices_for

log = structlog.get_logger(__name__)


def hit_rate(tokens: dict) -> float | None:
    """Cache reads as a share of all prefix input, or None when nothing was cached.

    `None` rather than `0.0`: a cell where caching never applied did not achieve a
    zero hit rate, it had no cache to hit, and a zero on a chart reads as a
    measurement.
    """
    read = tokens.get("cache_read_input_tokens", 0)
    written = tokens.get("cache_creation_input_tokens", 0)
    if not read and not written:
        return None
    served = read + written
    return read / served if served else None


def saving_usd(tokens: dict, model_id: str) -> float | None:
    """Estimated dollars caching saved on this cell, against paying full input price.

    Estimated, like every dollar figure here — it is the same hand-entered price
    table. `None` when caching did not apply, for the same reason as `hit_rate`.
    """
    read = tokens.get("cache_read_input_tokens", 0)
    written = tokens.get("cache_creation_input_tokens", 0)
    if not read and not written:
        return None
    prices = prices_for(model_id)
    uncached = (read + written) * prices.input
    actual = read * prices.cache_read + written * prices.cache_write
    return (uncached - actual) / 1_000_000


def summarise(tokens: dict, model_id: str) -> dict:
    """The cache line for a run summary: rate, saving, and the counts behind both.

    Returned as a dict with an explicit `applied` flag rather than as a formatted
    string, so the caller decides how to render "did not apply" — and cannot
    accidentally render it as a zero.
    """
    rate = hit_rate(tokens)
    return {
        "applied": rate is not None,
        "hit_rate": rate,
        "saving_usd": saving_usd(tokens, model_id),
        "cache_read_input_tokens": tokens.get("cache_read_input_tokens", 0),
        "cache_creation_input_tokens": tokens.get("cache_creation_input_tokens", 0),
        "uncached_input_tokens": tokens.get("input_tokens", 0),
    }
