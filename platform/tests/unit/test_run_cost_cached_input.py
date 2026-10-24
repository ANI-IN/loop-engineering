"""A run's cost on the console prices each call as the spend ledger does (zero tokens, no
database). Before, the worker priced every input token at the full rate: 68 percent of the
analyst's input was cached, so runs showed about twice what OpenAI bills and `make spend` shows."""

from __future__ import annotations

from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from datapilot.loop1_agent.guard import RunGuard
from datapilot.loop3_events.worker import call_cost
from datapilot.observability import spend

MODEL = "gpt-6-luna"
USAGE = {
    "input_tokens": 10_000,
    "output_tokens": 300,
    "total_tokens": 10_300,
    "input_token_details": {"cache_read": 6_800, "cache_creation": 0},
}


def reply() -> AIMessage:
    return AIMessage("", usage_metadata=USAGE)  # type: ignore[arg-type]


def test_the_run_guard_passes_cached_input_on_with_each_call() -> None:
    seen: list[spend.Usage] = []
    guard = RunGuard(tokens_per_run=60_000, on_usage=seen.append)
    guard.record(reply())
    assert seen == [spend.Usage(10_000, 6_800, 300)]
    assert (guard.tokens_in, guard.tokens_out) == (10_000, 300)


def test_the_run_cost_is_the_ledger_cost_of_the_same_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = tmp_path / "ledger.sqlite"
    monkeypatch.setenv("DATAPILOT_SPEND_LEDGER", str(ledger))
    for name in ("DATAPILOT_BUILD_BUDGET", "DATAPILOT_USE_RESERVE", "DATAPILOT_SESSION_SINCE"):
        monkeypatch.delenv(name, raising=False)
    callback = spend.SpendCallback(component="analyst", model=MODEL, activity="calibration")
    callback.on_chat_model_start({}, [[HumanMessage("how many orders")]], run_id="call-1")
    callback.on_llm_end(LLMResult(generations=[[ChatGeneration(message=reply())]]), run_id="call-1")

    seen: list[spend.Usage] = []
    RunGuard(tokens_per_run=60_000, on_usage=seen.append).record(reply())
    run_cost = call_cost(MODEL, seen[0])
    assert run_cost == pytest.approx(spend.total_usd(ledger))
    full_rate = call_cost(MODEL, spend.Usage(10_000, 0, 300))
    assert run_cost < full_rate


def test_an_unpriced_model_costs_nothing_on_the_run() -> None:
    assert call_cost("scripted", spend.Usage(10, 0, 2)) == 0.0
