from types import SimpleNamespace

import pytest

from loopeng.pricing import PRICES, PRICES_TAKEN_ON, UnknownModelPrice, prices_for
from loopeng.usage import (
    CallUsage,
    UsageLedger,
    UsageReconciliationError,
    reconcile,
)

WORKER = "claude-haiku-4-5"
FRONTIER = "claude-sonnet-5"


def _response(**usage):
    return SimpleNamespace(usage=SimpleNamespace(**usage))


# ---- all four token classes are recorded ------------------------------------


def test_all_four_usage_fields_are_read_off_the_response():
    """Cache writes bill above base input and reads well below it, so summing
    input_tokens alone is wrong on exactly the cells where caching fires."""
    call = CallUsage.from_response(
        WORKER,
        _response(
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


def test_absent_cache_fields_normalise_to_zero():
    """The SDK omits them, or reports None, when caching was not in play."""
    call = CallUsage.from_response(WORKER, _response(input_tokens=10, output_tokens=5))
    assert call.cache_creation_input_tokens == 0
    assert call.cache_read_input_tokens == 0

    nulled = CallUsage.from_response(
        WORKER,
        _response(
            input_tokens=10,
            output_tokens=5,
            cache_creation_input_tokens=None,
            cache_read_input_tokens=None,
        ),
    )
    assert nulled.cache_creation_input_tokens == 0


def test_cache_classes_are_priced_differently_from_base_input():
    """If they were priced the same, recording them separately would be pointless
    and the cost comparison would be wrong wherever caching fires."""
    base = CallUsage(WORKER, "ok", input_tokens=10_000)
    write = CallUsage(WORKER, "ok", cache_creation_input_tokens=10_000)
    read = CallUsage(WORKER, "ok", cache_read_input_tokens=10_000)

    assert write.cost_usd() > base.cost_usd()
    assert read.cost_usd() < base.cost_usd()


# ---- every call counts, including the ones that failed ----------------------


def test_failed_and_timed_out_calls_still_bill():
    """Generated tokens bill whether or not the answer shipped. Dropping them makes
    the loop look cheaper than it is, and that bias runs one way: it flatters
    Haiku-plus-a-loop against Sonnet one-shot, the comparison this project makes."""
    ledger = UsageLedger()
    ledger.record(CallUsage(WORKER, "ok", input_tokens=100, output_tokens=200))
    ledger.record(CallUsage(WORKER, "error", input_tokens=100, output_tokens=180))
    ledger.record(CallUsage(WORKER, "timeout", input_tokens=100, output_tokens=150))
    ledger.record(CallUsage(WORKER, "budget_exhausted", input_tokens=100, output_tokens=90))

    assert ledger.totals()["n_calls"] == 4
    assert ledger.totals()["output_tokens"] == 620
    assert ledger.by_outcome() == {
        "ok": 1,
        "error": 1,
        "timeout": 1,
        "budget_exhausted": 1,
    }

    ok_only = UsageLedger()
    ok_only.record(CallUsage(WORKER, "ok", input_tokens=100, output_tokens=200))
    assert ledger.cost_usd() > ok_only.cost_usd()


def test_cost_counts_every_outcome():
    ledger = UsageLedger()
    for outcome in ("ok", "error", "timeout", "budget_exhausted"):
        ledger.record(CallUsage(WORKER, outcome, input_tokens=1_000, output_tokens=1_000))
    expected = 4 * CallUsage(WORKER, "ok", input_tokens=1_000, output_tokens=1_000).cost_usd()
    assert ledger.cost_usd() == pytest.approx(expected)


# ---- reconciliation is asserted, not eyeballed ------------------------------


def test_reconciliation_passes_when_calls_sum_to_the_cell_total():
    ledger = UsageLedger()
    ledger.record(CallUsage(WORKER, "ok", input_tokens=100, output_tokens=50))
    ledger.record(CallUsage(WORKER, "error", input_tokens=30, output_tokens=10))
    reconcile(ledger, {"input_tokens": 130, "output_tokens": 60, "n_calls": 2})


def test_reconciliation_fails_when_a_call_went_unrecorded():
    """The failure mode this catches: a retry that billed but never reached the
    ledger, so the reported spend is lower than the real one."""
    ledger = UsageLedger()
    ledger.record(CallUsage(WORKER, "ok", input_tokens=100, output_tokens=50))
    with pytest.raises(UsageReconciliationError) as exc:
        reconcile(ledger, {"input_tokens": 130, "output_tokens": 60})
    assert "input_tokens" in str(exc.value)


def test_reconciliation_names_what_disagrees():
    ledger = UsageLedger()
    ledger.record(CallUsage(WORKER, "ok", input_tokens=10, output_tokens=5))
    with pytest.raises(UsageReconciliationError) as exc:
        reconcile(ledger, {"output_tokens": 99})
    message = str(exc.value)
    assert "calls sum to 5" in message and "cell reports 99" in message


# ---- the price table --------------------------------------------------------


def test_both_roles_have_prices():
    assert set(PRICES) == {WORKER, FRONTIER}


def test_the_table_records_when_it_was_taken():
    """A price table with no date is a table nobody can check."""
    assert PRICES_TAKEN_ON


def test_every_model_prices_all_four_classes():
    for model_id, prices in PRICES.items():
        for field_name in ("input", "output", "cache_write_5m", "cache_read"):
            assert getattr(prices, field_name) > 0, f"{model_id}.{field_name}"


def test_cache_reads_are_cheaper_and_writes_dearer_than_input():
    for prices in PRICES.values():
        assert prices.cache_read < prices.input
        assert prices.cache_write_5m > prices.input


def test_an_unpriced_model_raises_rather_than_costing_nothing():
    """Defaulting to zero would make a sweep look free, which is the most
    misleading way this table could fail."""
    with pytest.raises(UnknownModelPrice):
        prices_for("claude-does-not-exist")


def test_by_model_splits_spend():
    ledger = UsageLedger()
    ledger.record(CallUsage(WORKER, "ok", input_tokens=1_000, output_tokens=1_000))
    ledger.record(CallUsage(FRONTIER, "ok", input_tokens=1_000, output_tokens=1_000))
    by_model = ledger.by_model()
    assert set(by_model) == {WORKER, FRONTIER}
    assert by_model[FRONTIER]["cost_usd_estimated"] > by_model[WORKER]["cost_usd_estimated"]
