import pytest

from loopeng.prompts import LEVELS, render_prompt, render_rules
from loopeng.warehouse.schema import TABLES, load_semantic_model


def test_l0_carries_the_schema():
    prompt = render_prompt("L0")
    for table in TABLES:
        assert f"CREATE TABLE {table}" in prompt


def test_l0_carries_no_rule_text():
    """If L0 leaked the rules, L0 and L3 would score the same and the dial chart
    would measure nothing. This is the same failure as a question that leaks."""
    prompt = render_prompt("L0")
    for name, rule in load_semantic_model()["rules"].items():
        first_clause = " ".join(rule["statement"].split())[:40]
        assert first_clause not in prompt, f"L0 leaks rule {name}"
    assert "usd_factor" not in prompt
    assert "0.0067" not in prompt


def test_l3_carries_every_rule_in_the_semantic_model():
    prompt = render_prompt("L3")
    for name in load_semantic_model()["rules"]:
        assert f"[{name}]" in prompt, f"L3 is missing rule {name}"


def test_l3_carries_the_fx_factors():
    """Conversion is impossible without them, so an L3 prompt without the factors
    would fail the currency items for a reason that is not the model's fault."""
    prompt = render_prompt("L3")
    for factor in load_semantic_model()["usd_factor"].values():
        assert str(factor) in prompt


def test_l3_is_strictly_longer_than_l0():
    assert len(render_prompt("L3")) > len(render_prompt("L0"))


def test_l3_contains_l0():
    """The shared prefix is what makes caching possible at all."""
    l0 = render_prompt("L0")
    schema_part = l0.split("Return only")[0]
    assert schema_part in render_prompt("L3")


def test_rules_render_without_yaml_line_wrapping():
    """The YAML folds statements across lines; a prompt with ragged newlines mid
    sentence reads as damaged and changes the token count."""
    rendered = render_rules()
    assert "\n\n" not in rendered
    for line in rendered.splitlines():
        assert line.strip()


def test_l3_stays_above_sonnets_cache_minimum():
    """Sonnet 5's minimum cacheable prefix is 1024 tokens and the rendered L3 prompt
    measured 1037 on 2026-07-29 — a margin of thirteen tokens, which is not a margin.
    Trimming one rule sentence would drop the only cache that works anywhere, with no
    error and no signal: just a slightly different cost per cell.

    This is a character-count proxy so the guard stays offline and free. The measured
    ratio was 1037 tokens to the rendered length below, so the threshold is set from
    that ratio with the 13-token margin removed — it trips before the real count does.
    The live test in tests/live/test_prompt_tokens.py checks the true token count.
    """
    # WHAT THIS CONSTANT IS: a measured tripwire, not a style rule.
    #
    # On 2026-07-29 the rendered L3 prompt was 2406 characters and counted 1037
    # tokens against Sonnet 5's tokeniser, so 1024 tokens sat at roughly 2375
    # characters. That is the number below. It is fixed rather than derived from the
    # current render, because a threshold computed from the string it is checking
    # always passes and would test nothing.
    #
    # IF THIS TEST FAILS, THE FIRST QUESTION IS NOT "WHAT SHOULD THE CONSTANT BE".
    # It is one of two real changes, and they need different responses:
    #
    #   1. The prompt shrank. A rule was trimmed, reworded, or dropped. Sonnet L3 has
    #      probably fallen below its cache minimum, which is the only cache that fires
    #      anywhere in the sweep. Decide whether the prompt change is wanted.
    #   2. The tokeniser shifted. A new model version tokenises this text differently,
    #      so the chars-per-token ratio this constant encodes is stale. The prompt is
    #      unchanged and fine; the tripwire needs re-measuring.
    #
    # Either way, run `uv run pytest tests/live/test_prompt_tokens.py -m live` to get
    # the true count before touching this line. Adjusting the constant to make the
    # test pass, without establishing which of the two happened, papers over a real
    # change — and the change it papers over is silent by construction, because a
    # cache that stops firing produces no error, just a different cost per cell.
    MIN_CHARS_FOR_1024_TOKENS = 2375

    rendered = render_prompt("L3")
    assert len(rendered) >= MIN_CHARS_FOR_1024_TOKENS, (
        f"the L3 prompt is {len(rendered)} chars, below the ~{MIN_CHARS_FOR_1024_TOKENS} "
        "that rendered to Sonnet's 1024-token cache minimum on 2026-07-29. Caching now "
        "likely fires in zero cells of eight. Re-run tests/live/test_prompt_tokens.py "
        "to get the true count before deciding this is fine."
    )


def test_unknown_level_raises():
    with pytest.raises(ValueError):
        render_prompt("L1")


def test_levels_are_exactly_l0_and_l3():
    assert LEVELS == ("L0", "L3")
