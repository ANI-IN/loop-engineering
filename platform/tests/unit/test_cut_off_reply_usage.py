"""A reply cut off at its output-token cap, shaped as the Responses API sends it: the guard's stop
reason names the output tokens the reply reports, the same count the spend ledger records, and says
the count is unknown when the reply reports none (zero tokens: a stand-in client, no network)."""

from __future__ import annotations

import asyncio

from cut_off_responses import (
    INPUT_TOKENS,
    OUTPUT_TOKENS,
    LedgerView,
    cut_off_model,
    incomplete_response,
)
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.messages import AIMessage, HumanMessage
from openai.types.responses import Response

from datapilot.contracts import AnswerEnvelope
from datapilot.loop1_agent.guard import GuardMiddleware, RunGuard, StopReason

UNKNOWN = "a model response was cut off at its output-token cap; it reported no output-token count"


def run_cut_off_agent(response: Response) -> tuple[RunGuard, LedgerView]:
    ledger = LedgerView()
    guard = RunGuard(tokens_per_run=60000)
    agent = create_agent(
        cut_off_model(response, [ledger]),
        [],
        middleware=[GuardMiddleware(guard)],
        response_format=ToolStrategy(AnswerEnvelope),
    )
    asyncio.run(agent.ainvoke({"messages": [HumanMessage("How many orders?")]}))
    return guard, ledger


def test_the_stop_reason_names_the_output_tokens_the_ledger_records() -> None:
    guard, ledger = run_cut_off_agent(incomplete_response())
    assert guard.stop_reason is StopReason.OUTPUT_LIMIT
    assert ledger.output_tokens == [OUTPUT_TOKENS]
    assert guard.stop_detail == (
        f"a model response was cut off at its output-token cap after {OUTPUT_TOKENS} tokens"
    )
    assert (guard.tokens_in, guard.tokens_out) == (INPUT_TOKENS, OUTPUT_TOKENS)


def test_a_cut_off_reply_without_usage_says_the_count_is_unknown() -> None:
    guard, _ = run_cut_off_agent(incomplete_response(with_usage=False))
    assert guard.stop_reason is StopReason.OUTPUT_LIMIT
    assert guard.stop_detail == UNKNOWN


def test_a_cut_off_reply_whose_usage_omits_output_tokens_is_unknown_never_zero() -> None:
    cut_off = {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}}
    reply = AIMessage("", response_metadata=cut_off, usage_metadata=None)
    guard = RunGuard(tokens_per_run=60000)
    assert GuardMiddleware(guard).after_model({"messages": [reply]}, None) == {"jump_to": "end"}
    assert guard.stop_detail == UNKNOWN and "after 0 tokens" not in guard.stop_detail
