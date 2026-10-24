"""A reply cut off at its output-token cap, shaped as the Responses API sends it: the guard's stop
reason names the output tokens the reply reports, the same count the spend ledger records, and says
the count is unknown when the reply reports none, or reports zero, which a reply that reached its
cap cannot have used (zero tokens: a stand-in client, no network).

The live probe's two calls (runs d9f0ab0e and 730953ea) run here through the analyst as the
verification loop builds it: build_analyst's middleware and structured output, the guard, the tool
events, the approval middleware, and the real spend ledger on a temporary file."""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from cut_off_responses import (
    CUT_OFF_INPUT_TOKENS,
    INPUT_TOKENS,
    OUTPUT_TOKENS,
    LedgerView,
    cut_off_model,
    incomplete_response,
    list_tables_response,
    stand_in,
)
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from openai.types.responses import Response

from datapilot.contracts import AnswerEnvelope, KnowledgeVersion
from datapilot.loop1_agent.analyst import AgentLimits, build_analyst
from datapilot.loop1_agent.guard import (
    GuardMiddleware,
    RunGuard,
    StopReason,
    ToolEventsMiddleware,
    cut_off_detail,
)
from datapilot.observability import spend

STOPPED = "a model response was cut off at its output-token cap"
UNKNOWN = f"{STOPPED}; it reported no output-token count"


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
    assert guard.stop_detail == f"{STOPPED} after {OUTPUT_TOKENS} tokens"
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


def test_a_cut_off_reply_reporting_zero_tokens_is_unknown_never_zero() -> None:
    """A reply that reached its cap used tokens, so a reported 0 is a missing count."""
    cut_off = {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}}
    zero = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    reply = AIMessage("", response_metadata=cut_off, usage_metadata=zero)  # type: ignore[arg-type]
    assert cut_off_detail(reply) == UNKNOWN


# --- the live probe's two calls through the analyst as the verification loop builds it ----------


@pytest.fixture
def ledger_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "spend-ledger.sqlite"
    monkeypatch.setenv("DATAPILOT_SPEND_LEDGER", str(path))
    monkeypatch.setenv("DATAPILOT_BUILD_BUDGET", "0")
    monkeypatch.setenv("DATAPILOT_SPEND_ACTIVITY", "development live checks")
    monkeypatch.setenv("DATAPILOT_SESSION_SINCE", "")
    return path


def ledger_rows(path: Path) -> list[tuple[int, int]]:
    with sqlite3.connect(path) as conn:
        query = "SELECT input_tokens, output_tokens FROM spend_ledger ORDER BY id"
        return [(int(i), int(o)) for i, o in conn.execute(query)]


@tool
def list_tables() -> str:
    """List the warehouse tables."""
    return "orders, customers, payments"


def run_the_probe(*responses: Response) -> tuple[RunGuard, LedgerView, Any, dict[str, Any]]:
    """One analyst run as VerificationLoop._setup builds it (tool events, the guard, the approval
    middleware, then build_analyst's prompt, call limits, and structured output), on the live
    model's class with the real spend callback, answered by the stand-in client."""
    view = LedgerView()
    callback = spend.SpendCallback(
        component="analyst",
        model="gpt-6-luna",
        run_id="730953ea-9ff6-415a-a9a5-fb61f7d0be0c",
        activity="development live checks",
    )
    model = cut_off_model(list(responses), [callback, view])
    guard = RunGuard(tokens_per_run=60000)
    events: list[Any] = []
    approvals = HumanInTheLoopMiddleware(
        {"run_query": {"allowed_decisions": ["approve", "reject"], "when": lambda req: False}}
    )
    agent = build_analyst(
        model=model,
        tools=[list_tables],
        knowledge=KnowledgeVersion(version="v1"),
        limits=AgentLimits.from_pack(),
        middleware=[
            ToolEventsMiddleware(lambda kind, payload: events.append(kind)),
            GuardMiddleware(guard),
            approvals,
        ],
    )
    state = asyncio.run(agent.ainvoke({"messages": [HumanMessage("Net revenue in 2025?")]}))
    return guard, view, stand_in(model), state


def test_the_live_probe_cut_off_reporting_zero_tokens_never_reads_after_0_tokens(
    ledger_file: Path,
) -> None:
    """Run 730953ea: list_tables (715 in, 14 out), then a call cut off at the cap that reported 0
    and 0. The ledger records both calls, the cut-off one with the estimate from its request in
    place of the 0 input tokens it reported (review round 1, F014: the live ledger recorded 0, so
    a billed call cost nothing); the reason never says 0 tokens and names the 14 output tokens the
    run's calls reported, the ledger's total for the run."""
    guard, view, client, state = run_the_probe(
        list_tables_response(), incomplete_response(input_tokens=0, output_tokens=0)
    )
    first, cut_off = ledger_rows(ledger_file)
    assert first == (INPUT_TOKENS, OUTPUT_TOKENS) and cut_off[0] > 0 and cut_off[1] == 0
    assert guard.stop_reason is StopReason.OUTPUT_LIMIT and guard.model_calls == 2
    assert "after 0 tokens" not in guard.stop_detail
    assert guard.stop_detail == (
        f"{UNKNOWN}, and the run's model calls so far reported {OUTPUT_TOKENS} output tokens"
    )
    assert guard.tokens_out == sum(out for _, out in ledger_rows(ledger_file))
    # The reply the guard read is the generation the ledger saw: the same usage, not a copy.
    replies = [m for m in state["messages"] if isinstance(m, AIMessage)]
    assert [r.usage_metadata for r in replies] == [m.usage_metadata for m in view.messages]
    # The analyst never streams: every request went out as one call, without stream=True.
    assert client.calls == 2 and not any(p.get("stream") for p in client.payloads)


def test_the_live_probe_cut_off_reporting_its_tokens_names_them(ledger_file: Path) -> None:
    """Run 74fe4786: the same first call, then a call cut off after 16 output tokens."""
    guard, _, _, _ = run_the_probe(
        list_tables_response(),
        incomplete_response(input_tokens=CUT_OFF_INPUT_TOKENS, output_tokens=16),
    )
    assert ledger_rows(ledger_file) == [(INPUT_TOKENS, OUTPUT_TOKENS), (CUT_OFF_INPUT_TOKENS, 16)]
    assert guard.stop_detail == f"{STOPPED} after 16 tokens"
    assert guard.tokens_out == OUTPUT_TOKENS + 16
