from types import SimpleNamespace

import pytest

from loopeng.pricing import PRICES, PRICES_TAKEN_ON, UnknownModelPrice, prices_for
from loopeng.providers import usage_for
from loopeng.registry import spec_for
from loopeng.usage import (
    CallUsage,
    UsageLedger,
    UsageReconciliationError,
    reconcile,
)

AGENT = "gpt-5.6-luna"
REFERENCE = "gpt-6-astra"
JUDGE = "claude-haiku-4-5"


def _anthropic(**usage):
    return SimpleNamespace(usage=SimpleNamespace(**usage))


def _openai(prompt_tokens, completion_tokens, cached_tokens=0, cache_write_tokens=0):
    return SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            prompt_tokens_details=SimpleNamespace(
                cached_tokens=cached_tokens, cache_write_tokens=cache_write_tokens
            ),
        )
    )


# ---- all four token classes are recorded ------------------------------------


def test_all_four_usage_fields_are_read_off_an_anthropic_response():
    """Cache writes bill above base input and reads well below it, so summing
    input_tokens alone is wrong on exactly the cells where caching fires."""
    call = usage_for(
        spec_for("judge"),
        _anthropic(
            input_tokens=100,
            output_tokens=50,
            cache_creation_input_tokens=2000,
            cache_read_input_tokens=4000,
        ),
    )
    assert call.input_tokens == 100
    assert call.output_tokens == 50
    assert call.cache_creation_input_tokens == 2000
    assert call.cache_read_input_tokens == 4000
    assert call.total_tokens == 6150


def test_the_two_vendors_report_cached_tokens_with_opposite_conventions():
    """Anthropic's input_tokens EXCLUDES cached tokens; OpenAI's prompt_tokens
    INCLUDES them. Reading the second the first way double-counts every cached
    token — once at full price and once at the cache rate — and the error runs in
    the direction that overstates the agent's cost."""
    anthropic_call = usage_for(
        spec_for("judge"),
        _anthropic(input_tokens=100, output_tokens=50, cache_read_input_tokens=900),
    )
    openai_call = usage_for(
        spec_for("agent"), _openai(prompt_tokens=1000, completion_tokens=50,
                                   cached_tokens=900)
    )
    # Same underlying call: 1000 tokens of input, 900 of them cached.
    assert anthropic_call.input_tokens == openai_call.input_tokens == 100
    assert (anthropic_call.cache_read_input_tokens
            == openai_call.cache_read_input_tokens == 900)


def test_absent_cache_fields_normalise_to_zero():
    """Both SDKs omit them, or report None, when caching was not in play."""
    call = usage_for(spec_for("judge"), _anthropic(input_tokens=10, output_tokens=5))
    assert call.cache_creation_input_tokens == 0
    assert call.cache_read_input_tokens == 0

    nulled = usage_for(
        spec_for("judge"),
        _anthropic(
            input_tokens=10,
            output_tokens=5,
            cache_creation_input_tokens=None,
            cache_read_input_tokens=None,
        ),
    )
    assert nulled.cache_creation_input_tokens == 0


def test_a_cache_read_always_costs_less_than_the_same_tokens_uncached():
    """The one cache-economics claim that holds on both vendors, and the one the
    saving figure is built on."""
    for model_id in (AGENT, REFERENCE, JUDGE):
        base = CallUsage(model_id, "ok", input_tokens=10_000)
        read = CallUsage(model_id, "ok", cache_read_input_tokens=10_000)
        assert read.cost_usd() < base.cost_usd(), model_id


def test_the_write_premium_exists_on_one_vendor_and_not_the_other():
    """Anthropic bills a 5-minute cache write above base input; OpenAI bills it at
    the ordinary input rate. Recording the classes separately is what lets the same
    cost function be right for both — and this asserts the difference is real rather
    than a rounding artefact nobody would notice if it were flattened."""
    judge_base = CallUsage(JUDGE, "ok", input_tokens=10_000)
    judge_write = CallUsage(JUDGE, "ok", cache_creation_input_tokens=10_000)
    assert judge_write.cost_usd() > judge_base.cost_usd()

    agent_base = CallUsage(AGENT, "ok", input_tokens=10_000)
    agent_write = CallUsage(AGENT, "ok", cache_creation_input_tokens=10_000)
    assert agent_write.cost_usd() == agent_base.cost_usd()


def test_failed_and_timed_out_calls_still_bill():
    """Generated tokens bill whether or not the answer shipped. Dropping them makes
    the loop look cheaper than it is, and that bias runs one way: it flatters
    Haiku-plus-a-loop against Sonnet one-shot, the comparison this project makes."""
    ledger = UsageLedger()
    ledger.record(CallUsage(AGENT, "ok", input_tokens=100, output_tokens=200))
    ledger.record(CallUsage(AGENT, "error", input_tokens=100, output_tokens=180))
    ledger.record(CallUsage(AGENT, "timeout", input_tokens=100, output_tokens=150))
    ledger.record(CallUsage(AGENT, "budget_exhausted", input_tokens=100, output_tokens=90))

    assert ledger.totals()["n_calls"] == 4
    assert ledger.totals()["output_tokens"] == 620
    assert ledger.by_outcome() == {
        "ok": 1,
        "error": 1,
        "timeout": 1,
        "budget_exhausted": 1,
    }

    ok_only = UsageLedger()
    ok_only.record(CallUsage(AGENT, "ok", input_tokens=100, output_tokens=200))
    assert ledger.cost_usd() > ok_only.cost_usd()


def test_cost_counts_every_outcome():
    ledger = UsageLedger()
    for outcome in ("ok", "error", "timeout", "budget_exhausted"):
        ledger.record(CallUsage(AGENT, outcome, input_tokens=1_000, output_tokens=1_000))
    expected = 4 * CallUsage(AGENT, "ok", input_tokens=1_000, output_tokens=1_000).cost_usd()
    assert ledger.cost_usd() == pytest.approx(expected)


# ---- reconciliation is asserted, not eyeballed ------------------------------


def test_reconciliation_passes_when_calls_sum_to_the_cell_total():
    ledger = UsageLedger()
    ledger.record(CallUsage(AGENT, "ok", input_tokens=100, output_tokens=50))
    ledger.record(CallUsage(AGENT, "error", input_tokens=30, output_tokens=10))
    reconcile(ledger, {"input_tokens": 130, "output_tokens": 60, "n_calls": 2})


def test_reconciliation_fails_when_a_call_went_unrecorded():
    """The failure mode this catches: a retry that billed but never reached the
    ledger, so the reported spend is lower than the real one."""
    ledger = UsageLedger()
    ledger.record(CallUsage(AGENT, "ok", input_tokens=100, output_tokens=50))
    with pytest.raises(UsageReconciliationError) as exc:
        reconcile(ledger, {"input_tokens": 130, "output_tokens": 60})
    assert "input_tokens" in str(exc.value)


def test_reconciliation_names_what_disagrees():
    ledger = UsageLedger()
    ledger.record(CallUsage(AGENT, "ok", input_tokens=10, output_tokens=5))
    with pytest.raises(UsageReconciliationError) as exc:
        reconcile(ledger, {"output_tokens": 99})
    message = str(exc.value)
    assert "calls sum to 5" in message and "cell reports 99" in message


# ---- the price table --------------------------------------------------------


def test_every_registry_role_has_a_price():
    """A model with no price entry raises rather than costing nothing, so a missing
    row is loud — but the roles that actually run must never reach that path."""
    from loopeng.registry import REGISTRY

    for spec in REGISTRY.values():
        assert spec.model_id in PRICES, f"{spec.role} has no price row"
    assert set(PRICES) == {AGENT, REFERENCE, JUDGE}


def test_the_table_records_when_it_was_taken():
    """A price table with no date is a table nobody can check."""
    assert PRICES_TAKEN_ON


def test_every_model_prices_all_four_classes():
    for model_id, prices in PRICES.items():
        for field_name in ("input", "output", "cache_write", "cache_read"):
            assert getattr(prices, field_name) > 0, f"{model_id}.{field_name}"


def test_cache_reads_are_always_cheaper_than_full_input():
    """True on both vendors. It is the only cache economics claim that is."""
    for prices in PRICES.values():
        assert prices.cache_read < prices.input


def test_the_write_premium_is_a_per_vendor_fact_not_a_universal_one():
    """Anthropic charges 1.25x to populate the cache; OpenAI charges the ordinary
    input rate. Modelling the second as the first would invent a saving that is not
    there, and modelling the first as the second would understate a real cost.

    This is asserted rather than described because it is the kind of asymmetry that
    gets flattened by a well-meaning refactor into one constant."""
    assert prices_for(JUDGE).cache_write > prices_for(JUDGE).input
    assert prices_for(AGENT).cache_write == prices_for(AGENT).input
    assert prices_for(REFERENCE).cache_write == prices_for(REFERENCE).input


def test_an_unpriced_model_raises_rather_than_costing_nothing():
    """Defaulting to zero would make a sweep look free, which is the most
    misleading way this table could fail."""
    with pytest.raises(UnknownModelPrice):
        prices_for("claude-does-not-exist")


def test_by_model_splits_spend():
    ledger = UsageLedger()
    ledger.record(CallUsage(AGENT, "ok", input_tokens=1_000, output_tokens=1_000))
    ledger.record(CallUsage(REFERENCE, "ok", input_tokens=1_000, output_tokens=1_000))
    by_model = ledger.by_model()
    assert set(by_model) == {AGENT, REFERENCE}
    assert by_model[REFERENCE]["cost_usd_estimated"] > by_model[AGENT]["cost_usd_estimated"]
