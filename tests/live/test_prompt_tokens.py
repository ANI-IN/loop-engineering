"""The true token count, against the real tokenizer.

The offline guard in tests/test_prompt_rendering.py uses a character-count proxy so
it stays free. This is the one that actually knows.
"""

import pytest

from loopeng.probes import CACHE_MINIMUM_TOKENS, probe_prompt_tokens


@pytest.mark.live
def test_l3_still_clears_sonnets_cache_minimum():
    """Measured 1037 against a minimum of 1024 on 2026-07-29: thirteen tokens. If a
    rule was trimmed, this is where it shows up rather than in a cost column nobody
    reads until after the workshop."""
    probe = probe_prompt_tokens()
    l3 = probe["frontier"]["L3"]
    assert l3["cacheable"], (
        f"L3 is {l3['tokens']} tokens against a {CACHE_MINIMUM_TOKENS['claude-sonnet-5']} "
        "minimum — caching now fires in zero cells of eight"
    )


@pytest.mark.live
def test_the_measured_asymmetry_still_holds():
    """Sonnet caches L3, Haiku does not. Recorded so a later prompt change that
    happens to fix or worsen it is visible rather than silent."""
    probe = probe_prompt_tokens()
    assert probe["frontier"]["L3"]["cacheable"] is True
    assert probe["worker"]["L3"]["cacheable"] is False
    assert probe["frontier"]["L0"]["cacheable"] is False
    assert probe["worker"]["L0"]["cacheable"] is False
