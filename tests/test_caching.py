"""Prompt caching: what makes it fire, and what it is worth.

The apparatus was here long before the optimisation was. `pricing.py` has priced
cache reads and writes since Phase 0, `usage.py` has carried all four token classes
on every call, and `cache_control` was set nowhere — so every call re-sent the full
schema-plus-rules prefix at full input price, on every item, in every cell.

**The mechanism is now prefix stability, not a marker.** The agent is an OpenAI
budget model, where caching is automatic: nothing is switched on, and what decides
whether it fires is whether the front of the request is byte-identical between calls.
That makes the property testable offline and worth testing, because the failure mode
is silent — no error, no warning, just full price on every call and a
cost-per-correct-answer chart that quietly moves.

So the tests below assert the shape of the request, not the presence of a flag:

  * the static block is in the system turn, and nothing per-item is in it
  * it does not vary with the question
  * it does not vary with the retry history
  * a cell that never cached reports None rather than a zero
"""

from types import SimpleNamespace

import pytest

from loopeng import caching
from loopeng.agent.loop import Attempt, build_turns, run_question
from loopeng.prompts import render_prompt
from loopeng.usage import CallUsage
from loopeng.warehouse.connect import ensure_warehouse
from tests.fakes import FakeClient, rate_limited


@pytest.fixture(scope="module")
def warehouse(tmp_path_factory):
    return ensure_warehouse(tmp_path_factory.mktemp("wh") / "w.duckdb", seed=20260729)


# ---- the cacheable prefix is the system block, and it is stable -------------


def test_the_static_block_goes_in_the_system_turn(warehouse):
    """It used to be concatenated with the question into one user turn, which put a
    per-item string inside the cached region and defeated caching silently."""
    client = FakeClient("agent", ["SELECT COUNT(*) FROM products"])
    run_question("how many products?", warehouse=warehouse, client=client,
                 max_attempts=1)

    assert client.system_of() == render_prompt("L3")


def test_nothing_per_item_reaches_the_system_block(warehouse):
    """The question is what varies between items. If it is in the prefix, the prefix
    is different on every call and the cache never hits."""
    client = FakeClient("agent", ["SELECT COUNT(*) FROM products"])
    run_question("what share of beauty orders ended up refunded?",
                 warehouse=warehouse, client=client, max_attempts=1)

    assert "beauty" not in client.system_of()
    assert "beauty" in client.turns_of()[0]["content"]


def test_the_prefix_does_not_vary_with_the_question(warehouse):
    """Two different items, one prefix. This is the whole mechanism."""
    prefixes = set()
    for question in ("how many products?", "how many orders in March 2025?"):
        client = FakeClient("agent", ["SELECT COUNT(*) FROM products"])
        run_question(question, warehouse=warehouse, client=client, max_attempts=1)
        prefixes.add(client.system_of())

    assert len(prefixes) == 1


def test_the_prefix_does_not_vary_with_the_retry_history(warehouse):
    """A retry must not perturb the prefix. Every call a loop makes beyond the first
    is a retry, and those are exactly the calls the cost comparison is about."""
    client = FakeClient("agent", ["SELECT * FROM no_such_table",
                                  "SELECT COUNT(*) FROM products"])
    run_question("q", warehouse=warehouse, client=client, max_attempts=2)

    assert client.calls == 2
    assert client.system_of(0) == client.system_of(1)


def test_the_retry_feedback_is_a_later_turn_not_part_of_the_prefix(warehouse):
    """Feedback inside the prefix would break the cache on every retry."""
    client = FakeClient("agent", ["SELECT * FROM no_such_table",
                                  "SELECT COUNT(*) FROM products"])
    run_question("q", warehouse=warehouse, client=client, max_attempts=2)

    assert "That query failed with" not in client.system_of(1)
    assert any("That query failed with" in turn["content"]
               for turn in client.turns_of(1))


def test_the_level_2_loop_keeps_the_same_prefix_discipline(warehouse):
    """It is the loop the sweep cells run, so it is the one whose caching pays."""
    from loopeng.verify.loop import run_verified

    client = FakeClient("agent", ["SELECT COUNT(*) FROM products"])
    run_verified("q", warehouse=warehouse, client=client, max_attempts=1)

    assert client.system_of() == render_prompt("L3")
    assert "Question: q" in client.turns_of()[0]["content"]


def test_no_cache_control_marker_survives_anywhere():
    """The Anthropic-only mechanism is gone. A leftover marker would be dead code
    that reads like an active optimisation."""
    from pathlib import Path

    src = Path(__file__).resolve().parent.parent / "src" / "loopeng"
    setting = [
        str(path.relative_to(src.parent.parent))
        for path in src.rglob("*.py")
        if '"cache_control"' in path.read_text(encoding="utf-8")
    ]
    assert setting == [], f"cache_control is still set in {setting}"


# ---- the OpenAI usage convention, which is the expensive thing to get wrong --


def test_cached_tokens_are_not_double_counted(warehouse):
    """OpenAI's prompt_tokens INCLUDES cached tokens. Treating them the Anthropic way
    bills the cached portion twice — once at full price and once at the cache rate —
    and overstates the agent's cost on the chart that closes the session."""
    client = FakeClient(
        "agent", ["SELECT COUNT(*) FROM products"],
        tokens={"input_tokens": 40, "output_tokens": 10, "cached_tokens": 960},
    )
    run = run_question("q", warehouse=warehouse, client=client, max_attempts=1)

    usage = run.ledger.calls[0]
    # prompt_tokens was 1000; 960 of it was cached, so 40 was billed at full price.
    assert usage.input_tokens == 40
    assert usage.cache_read_input_tokens == 960
    assert usage.total_tokens == 1010


def test_a_broken_subset_relation_raises_rather_than_clamping():
    """If the vendor ever changes the convention, this must fail loudly. Clamping
    would produce a plausible number from an assumption just shown to be false."""
    from loopeng.providers import UsageConventionChanged, usage_for
    from loopeng.registry import spec_for

    response = SimpleNamespace(
        model="gpt-5.6-luna",
        usage=SimpleNamespace(
            prompt_tokens=10,
            completion_tokens=1,
            prompt_tokens_details=SimpleNamespace(cached_tokens=99,
                                                  cache_write_tokens=0),
        ),
    )
    with pytest.raises(UsageConventionChanged):
        usage_for(spec_for("agent"), response)


# ---- what it saved, reported and never zeroed -------------------------------


def test_a_cell_with_no_caching_reports_none_not_zero():
    """It did not achieve a nil hit rate; it had no cache to hit. A zero reads as a
    measurement."""
    assert caching.hit_rate({"input_tokens": 500}) is None
    assert caching.saving_usd({"input_tokens": 500}, "gpt-5.6-luna") is None
    assert caching.summarise({"input_tokens": 500}, "gpt-5.6-luna")["applied"] is False


def test_the_hit_rate_is_reads_over_everything_served():
    tokens = {"cache_read_input_tokens": 49, "cache_creation_input_tokens": 1}
    assert caching.hit_rate(tokens) == pytest.approx(0.98)


def test_the_saving_is_against_paying_full_input_price():
    """On OpenAI a write costs the ordinary input rate and only reads are discounted,
    so the saving is entirely the read discount."""
    from loopeng.pricing import prices_for

    tokens = {"cache_read_input_tokens": 1_000_000, "cache_creation_input_tokens": 0}
    saved = caching.saving_usd(tokens, "gpt-5.6-luna")
    prices = prices_for("gpt-5.6-luna")

    assert saved == pytest.approx(prices.input - prices.cache_read)
    assert saved > 0


def test_an_openai_cache_write_costs_no_premium():
    """Anthropic charges 1.25x to populate; OpenAI charges the ordinary input rate.
    Modelling the second as the first would invent a saving that is not there."""
    from loopeng.pricing import prices_for

    prices = prices_for("gpt-5.6-luna")
    assert prices.cache_write == prices.input

    tokens = {"cache_read_input_tokens": 0, "cache_creation_input_tokens": 1_000_000}
    assert caching.saving_usd(tokens, "gpt-5.6-luna") == pytest.approx(0.0)


def test_the_summary_carries_the_counts_behind_the_rate():
    tokens = {"input_tokens": 40, "cache_read_input_tokens": 960,
              "cache_creation_input_tokens": 0}
    summary = caching.summarise(tokens, "gpt-5.6-luna")

    assert summary["applied"] is True
    assert summary["hit_rate"] == pytest.approx(1.0)
    assert summary["cache_read_input_tokens"] == 960
    assert summary["uncached_input_tokens"] == 40


# ---- backoff, jitter, and a concurrency flag that exists --------------------


def test_a_retryable_failure_waits_before_going_round(warehouse):
    """Retrying a 429 immediately arrives back at the same limit and makes it last
    longer than it had to."""
    slept = []
    client = FakeClient("agent", raises=lambda: rate_limited())
    run_question("q", warehouse=warehouse, client=client, max_attempts=3,
                 sleeper=slept.append)

    assert client.calls == 3
    assert len(slept) == 2, "a sleep between each retry, and none after the last"
    assert slept[1] > slept[0], "the fallback backoff must widen"


def test_no_sleep_after_the_final_attempt(warehouse):
    """Waiting after the last call delays the report and changes nothing."""
    slept = []
    client = FakeClient("agent", raises=RuntimeError("overloaded_error"))
    run_question("q", warehouse=warehouse, client=client, max_attempts=1,
                 sleeper=slept.append)
    assert slept == []


def test_the_servers_retry_after_wins_over_our_guess():
    """It knows when the pool refills and we do not."""
    import httpx2 as httpx

    from loopeng.providers import retry_after_seconds

    response = httpx.Response(
        429, headers={"retry-after": "7"},
        request=httpx.Request("POST", "https://api.openai.com/"),
    )
    assert retry_after_seconds(SimpleNamespace(response=response), 1) == pytest.approx(7.0)


def test_a_missing_or_junk_retry_after_falls_back_to_doubling():
    import httpx2 as httpx

    from loopeng.providers import retry_after_seconds

    plain = SimpleNamespace(response=httpx.Response(
        429, request=httpx.Request("POST", "https://api.openai.com/")))
    assert retry_after_seconds(plain, 1) == pytest.approx(1.0)
    assert retry_after_seconds(plain, 3) == pytest.approx(4.0)

    junk = SimpleNamespace(response=httpx.Response(
        429, headers={"retry-after": "soon"},
        request=httpx.Request("POST", "https://api.openai.com/")))
    assert retry_after_seconds(junk, 1) == pytest.approx(1.0)
    assert retry_after_seconds(SimpleNamespace(), 1) == pytest.approx(1.0)


def test_the_backoff_is_capped():
    """An unbounded doubling turns a transient limit into a hung sweep."""
    from loopeng.providers import retry_after_seconds

    assert retry_after_seconds(SimpleNamespace(), 40) == 30.0


def test_the_backoff_carries_jitter():
    """Without it, every worker rate-limited by the same 429 sleeps the same duration
    and they all arrive back together — one rate limit becomes a sustained one."""
    import random

    from loopeng.agent.loop import BACKOFF_JITTER, backoff_delay

    base = 1.0
    delays = {
        backoff_delay(SimpleNamespace(), 1, rng=random.Random(seed))
        for seed in range(10)
    }
    assert len(delays) > 1, "every worker would sleep in lockstep"
    assert all(base <= d <= base * (1 + BACKOFF_JITTER) for d in delays)


def test_the_level_2_loop_backs_off_too(warehouse):
    """It is the loop the sweep cells run."""
    from loopeng.verify.loop import run_verified

    slept = []
    client = FakeClient("agent", raises=lambda: rate_limited())
    run_verified("q", warehouse=warehouse, client=client, max_attempts=3,
                 sleeper=slept.append)
    assert len(slept) == 2


def test_the_concurrency_flag_exists_and_defaults_to_the_measured_value():
    """The README's advice was unfollowable without editing source."""
    from pathlib import Path

    from loopeng.sweep.runner import CONCURRENCY_PER_MODEL

    entry = (Path(__file__).resolve().parent.parent
             / "demos" / "04_hill_climbing_loop" / "sweep.py").read_text(encoding="utf-8")
    assert '"--concurrency"' in entry
    assert "CONCURRENCY_PER_MODEL" in entry, "the default must be the measured value"
    assert CONCURRENCY_PER_MODEL > 0


def test_the_concurrency_reaches_the_thread_pool(warehouse, tmp_path):
    """A flag that is accepted and then ignored is worse than no flag."""
    import loopeng.sweep.runner as runner_module
    from loopeng.sweep.runner import Cell, run_cell

    seen = {}
    real = runner_module.ThreadPoolExecutor

    def spy(*args, **kwargs):
        seen["max_workers"] = kwargs.get("max_workers")
        return real(*args, **kwargs)

    runner_module.ThreadPoolExecutor = spy
    try:
        run_cell(Cell("agent", "L0", "loop"), [], warehouse,
                 directory=tmp_path, concurrency=3)
    finally:
        runner_module.ThreadPoolExecutor = real

    assert seen["max_workers"] == 3


def test_the_run_report_records_the_concurrency_used():
    """So a cell that behaved differently under a different pool size can be told
    apart from one that did not."""
    import inspect

    from loopeng.sweep.orchestrator import run_sweep

    assert "concurrency" in inspect.signature(run_sweep).parameters


def test_a_failed_call_is_still_recorded(warehouse):
    """The tokens are gone either way, and dropping them makes the loop look cheaper
    than it is — a bias that runs in the direction that flatters the cheap arm."""
    client = FakeClient("agent", raises=lambda: rate_limited())
    run = run_question("q", warehouse=warehouse, client=client, max_attempts=2,
                       sleeper=lambda _: None)

    assert len(run.ledger.calls) == 2
    assert all(call.outcome == "error" for call in run.ledger.calls)


def test_an_attempt_with_no_history_replays_nothing(warehouse):
    """A call that never reached the model produced no query to correct."""
    failed = Attempt(1, "", None, "RateLimitError", CallUsage("gpt-5.6-luna", "error"))
    assert build_turns("q", [failed]) == [{"role": "user", "content": "Question: q"}]
