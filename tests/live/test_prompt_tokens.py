"""Does prompt caching actually fire? Measured against the real API.

The offline tests in tests/test_caching.py assert the request SHAPE — that the static
block is in the system turn and does not vary with the question or the retry history.
That is the property caching depends on, and it is checkable for free.

This is the one that confirms the vendor agrees. It calls twice with an identical
prefix and reads `cached_tokens` off the second response. A shape that looks right and
a cache that never fires is exactly the failure the old threshold-based probe could
not see, because it never asked the API anything.
"""

import pytest

from loopeng.api_probes import probe_cache_behaviour


@pytest.mark.live
def test_the_agents_prefix_is_actually_served_from_cache():
    """The agent runs every loop, every retry and every sweep cell, so this is the
    token class that dominates the bill. If it stops caching, the cost-per-correct
    -answer chart moves and nothing else says why."""
    probe = probe_cache_behaviour(roles=("agent",))
    l3 = probe["agent"]["L3"]
    assert l3["hit"], (
        f"the agent's L3 prefix is {l3['prefix_tokens']} tokens and none of it came "
        f"back as cached. Either it is below the vendor's minimum cacheable length, "
        f"or something per-item has drifted into the system block."
    )


@pytest.mark.live
def test_both_prompt_levels_cache():
    """L0 is the shorter prefix and therefore the one that would fall below a minimum
    first. The trap runs both levels, so a level that silently stops caching would
    make the two arms differ in price for a reason that is not the experiment."""
    probe = probe_cache_behaviour(roles=("agent",))
    assert probe["agent"]["L0"]["hit"]
    assert probe["agent"]["L3"]["hit"]
