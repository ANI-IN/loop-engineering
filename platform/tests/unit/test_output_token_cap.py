"""The per-call output-token cap: each agent's max_output_tokens from pack.yaml reaches the
Responses API, and a reply cut off at the cap ends the run escalated with its reason, never a crash
(zero tokens: stub models only)."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from loop4_doubles import item
from loops_support import ScriptedChatModel, call, usage

from datapilot import settings as settings_module
from datapilot.config import pack_config
from datapilot.contracts import ItemResult, RunStatus
from datapilot.loop1_agent.guard import (
    GuardMiddleware,
    RunGuard,
    StopReason,
    latest_reply,
    output_limit_reached,
)
from datapilot.loop1_agent.models import openai_factory
from datapilot.loop2_verification.loop import STOPPED_STATUS
from datapilot.loop4_hill_climbing.analyzer import (
    AnalyzerTeam,
    FailedItem,
    OutputLimitReached,
    chat_model,
)
from datapilot.loop4_hill_climbing.overfit_guard import OverfitGuard
from datapilot.loop4_hill_climbing.pack_files import load_knowledge
from datapilot.settings import Settings

AGENTS = ("analyst", "schema_scout", "reviewer")
CUT_OFF = {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}}


def cut_off(tokens_out: int = 16000, **kwargs: Any) -> AIMessage:
    return AIMessage("", response_metadata=CUT_OFF, usage_metadata=usage(500, tokens_out), **kwargs)


def test_every_agent_has_a_cap_well_above_normal_use() -> None:
    models = pack_config()["models"]
    for agent in (*AGENTS, "analyzer_team"):
        assert int(models[agent]["max_output_tokens"]) >= 8000, agent
    # one capped call can never take a whole run's token budget
    assert int(models["analyst"]["max_output_tokens"]) < pack_config()["budgets"]["tokens_per_run"]


@pytest.mark.parametrize("agent", AGENTS)
def test_the_cap_is_sent_as_max_output_tokens_and_temperature_never(agent: str) -> None:
    settings = Settings(_env_file=None, openai_model="model-from-env", openai_api_key="sk-test")
    model = openai_factory(settings=settings)(agent)
    payload = model._get_request_payload([HumanMessage("hello")])  # type: ignore[attr-defined]
    assert payload["max_output_tokens"] == pack_config()["models"][agent]["max_output_tokens"]
    assert not {"temperature", "max_tokens", "max_completion_tokens"} & set(payload)
    assert payload["reasoning"] == {"effort": pack_config()["models"][agent]["reasoning_effort"]}


def test_the_analyzer_team_cap_is_sent_as_max_output_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_MODEL", "gpt-6-luna")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-used")
    settings_module.get_settings.cache_clear()
    try:
        model = chat_model("failure_analyst")
    finally:
        settings_module.get_settings.cache_clear()
    payload = model._get_request_payload([HumanMessage("hello")])
    cap = pack_config()["models"]["analyzer_team"]["max_output_tokens"]
    assert payload["max_output_tokens"] == cap and "temperature" not in payload


def test_only_a_reply_cut_off_at_the_cap_counts_as_cut_off() -> None:
    assert output_limit_reached(cut_off())
    assert not output_limit_reached(AIMessage("done", response_metadata={"status": "completed"}))
    other = {"status": "incomplete", "incomplete_details": {"reason": "content_filter"}}
    assert not output_limit_reached(AIMessage("", response_metadata=other))


def test_the_guard_ends_the_step_and_counts_the_tokens_of_a_cut_off_reply() -> None:
    guard = RunGuard(tokens_per_run=60000)
    middleware = GuardMiddleware(guard)
    assert middleware.after_model({"messages": [cut_off(16000)]}, None) == {"jump_to": "end"}
    assert guard.stop_reason is StopReason.OUTPUT_LIMIT and "output-token cap" in guard.stop_detail
    assert (guard.model_calls, guard.tokens_out) == (1, 16000)
    assert STOPPED_STATUS[StopReason.OUTPUT_LIMIT] is RunStatus.ESCALATED
    assert middleware.before_model({"messages": []}, None) == {"jump_to": "end"}


def test_the_reply_behind_a_structured_answer_is_counted() -> None:
    """A structured answer is followed by the tool message the agent adds; its tokens count."""
    reply = call("AnswerEnvelope", {}, "a1", tokens_in=300, tokens_out=40)
    messages = [HumanMessage("q"), reply, ToolMessage("Returning", tool_call_id="a1")]
    assert latest_reply(messages) is reply
    guard = RunGuard(tokens_per_run=60000)
    assert GuardMiddleware(guard).after_model({"messages": messages}, None) is None
    assert (guard.tokens_in, guard.tokens_out) == (300, 40)


def test_a_cut_off_tool_call_is_never_run() -> None:
    """The reply asks for a tool, but it was cut off: the agent ends instead of running it."""
    ran: list[str] = []

    def run_query(sql: str) -> str:
        """Run a query."""
        ran.append(sql)
        return "rows"

    replies = iter([cut_off(tool_calls=[{"name": "run_query", "args": {"sql": "x"}, "id": "c"}])])
    model = ScriptedChatModel(script=lambda messages: next(replies))
    guard = RunGuard(tokens_per_run=60000)
    agent = create_agent(model, [run_query], middleware=[GuardMiddleware(guard)])
    asyncio.run(agent.ainvoke({"messages": [HumanMessage("How many orders?")]}))
    assert ran == [] and model.calls == 1 and guard.stop_reason is StopReason.OUTPUT_LIMIT


class _CutOffRole:
    """A structured-output stand-in whose reply was cut off at its cap."""

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
        assert kwargs.get("include_raw") is True

        class _Runnable:
            def invoke(self, messages: list[Any]) -> dict[str, Any]:
                return {"raw": cut_off(32000), "parsed": None, "parsing_error": ValueError("cut")}

        return _Runnable()


def test_a_cut_off_analyzer_reply_is_a_named_failure() -> None:
    failed = FailedItem(item("q1"), None, ItemResult(item_id="q1", passed=False, reason="wrong"))
    role = _CutOffRole()
    team = AnalyzerTeam(role, role, role, OverfitGuard.from_pack([]))
    with pytest.raises(OutputLimitReached, match="cut off at its output cap"):
        team.run([failed], load_knowledge("v1"), "v-next")
