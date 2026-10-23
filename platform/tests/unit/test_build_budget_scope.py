"""DATAPILOT_BUILD_BUDGET controls only the build ledger's lines and its stop line. With the switch
off (a learner's machine) and on (the build), the per-run token budget, the model call and tool
call limits, the per-call output-token cap, and the retry cap all hold, each at its pack.yaml
value, while every call goes through the spend ledger (zero tokens: scripted models only). The
daily token budget, which lives in ops.budgets, has the same test on the tests' database
(integration/test_daily_budget_with_build_switch.py)."""

from __future__ import annotations

import asyncio
import itertools
from pathlib import Path
from typing import Any

import pytest
import yaml
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from loops_support import ScriptedChatModel, usage

from datapilot.config import PACKS, pack_config
from datapilot.contracts import KnowledgeVersion
from datapilot.loop1_agent.analyst import AgentLimits, build_analyst
from datapilot.loop1_agent.guard import GuardMiddleware, RunGuard, StopReason
from datapilot.loop1_agent.models import openai_factory
from datapilot.loop2_verification.config import VerificationConfig
from datapilot.loop2_verification.limits import attempt_allowed
from datapilot.observability import spend
from datapilot.settings import Settings

MODEL = next(iter(pack_config()["prices"]))
FILE = yaml.safe_load((PACKS / "datapilot_us" / "pack.yaml").read_text(encoding="utf-8"))


@pytest.fixture(params=["0", "1"], ids=["switch-off-learners", "switch-on-the-build"])
def switch(request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("DATAPILOT_SPEND_LEDGER", str(tmp_path / "ledger.sqlite"))
    monkeypatch.setenv("DATAPILOT_BUILD_BUDGET", request.param)
    monkeypatch.setenv("DATAPILOT_SPEND_ACTIVITY", "development")
    for name in ("DATAPILOT_USE_RESERVE", "DATAPILOT_OVERNIGHT_SINCE"):
        monkeypatch.delenv(name, raising=False)
    return request.param


def ledger() -> Path:
    return spend.ledger_path()


def lookup_tool(ran: list[str]) -> Any:
    @tool
    def lookup(name: str) -> str:
        """Look a table up."""
        ran.append(name)
        return "orders: order_id, status, total_cents"

    return lookup


def asks_forever(per_reply: int = 1, tokens_in: int = 100) -> Any:
    """A model that asks for `per_reply` lookups in every reply and never answers."""
    counter = itertools.count()

    def script(messages: Any) -> AIMessage:
        n = next(counter)
        calls = [
            {"name": "lookup", "args": {"name": f"t{n}-{i}"}, "id": f"c{n}-{i}"}
            for i in range(per_reply)
        ]
        return AIMessage("", tool_calls=calls, usage_metadata=usage(tokens_in, 20))  # type: ignore[arg-type]

    return script


def run_agent(script: Any, *, guard: RunGuard | None = None) -> tuple[ScriptedChatModel, list[str]]:
    """The analyst as the worker builds it, on a scripted model with the spend ledger attached."""
    callback = spend.SpendCallback(component="analyst", model=MODEL, activity="development")
    model = ScriptedChatModel(script=script, callbacks=[callback])
    ran: list[str] = []
    agent = build_analyst(
        model=model,
        tools=[lookup_tool(ran)],
        knowledge=KnowledgeVersion(version="v1"),
        limits=AgentLimits.from_pack(),
        middleware=[GuardMiddleware(guard or RunGuard(tokens_per_run=10**9))],
    )
    asyncio.run(agent.ainvoke({"messages": [HumanMessage("How many orders?")]}))
    return model, ran


def test_the_switch_turns_only_the_lines_and_the_stop_line_on_and_off(switch: str) -> None:
    assert spend.build_budget_on() is (switch == "1")
    per_token = pack_config()["prices"][MODEL]["output"] / 1_000_000
    for _ in range(40):  # past the development line and the 10-dollar stop line
        spend.record(
            component="analyst",
            model=MODEL,
            usage=spend.Usage(0, 0, round(0.30 / per_token)),
            activity="development",
        )
    if switch == "1":
        with pytest.raises(spend.BudgetStop):
            spend.check_budget(activity="development")
    else:
        assert spend.check_budget(activity="development") == pytest.approx(12.0)


def test_the_limits_are_the_pack_values_either_way(switch: str) -> None:
    limits = AgentLimits.from_pack()
    assert limits.model_call_limit == FILE["limits"]["model_call_limit"]
    assert limits.tool_call_limit == FILE["limits"]["tool_call_limit"]
    assert limits.tokens_per_run == FILE["budgets"]["tokens_per_run"]
    assert VerificationConfig.from_pack().max_retries == FILE["limits"]["max_retries"]
    assert pack_config()["budgets"]["tokens_per_day"] == FILE["budgets"]["tokens_per_day"]


def test_the_per_run_token_budget_stops_the_run(switch: str) -> None:
    budget = AgentLimits.from_pack().tokens_per_run
    guard = RunGuard(tokens_per_run=budget)
    model, _ = run_agent(asks_forever(tokens_in=budget // 2), guard=guard)
    assert guard.stop_reason is StopReason.TOKEN_LIMIT
    assert model.calls == 2, "the third call would start past the budget"
    assert [n for _, n, _ in spend.by_activity(ledger())] == [2], "the ledger records each call"


def test_the_model_call_limit_ends_the_run(switch: str) -> None:
    model, _ = run_agent(asks_forever())
    assert model.calls == AgentLimits.from_pack().model_call_limit


def test_the_tool_call_limit_refuses_extra_calls(switch: str) -> None:
    limits = AgentLimits.from_pack()
    model, ran = run_agent(asks_forever(per_reply=2))
    assert 2 * model.calls > limits.tool_call_limit, "the model asked for more than the limit"
    assert len(ran) == limits.tool_call_limit


@pytest.mark.parametrize("agent", ["analyst", "schema_scout", "reviewer"])
def test_the_output_token_cap_is_sent_on_every_call(switch: str, agent: str) -> None:
    settings = Settings(_env_file=None, openai_model="model-from-env", openai_api_key="sk-test")
    payload = openai_factory(settings=settings)(agent)._get_request_payload([HumanMessage("hi")])  # type: ignore[attr-defined]
    assert payload["max_output_tokens"] == FILE["models"][agent]["max_output_tokens"]


def test_a_reply_cut_off_at_the_cap_ends_the_run(switch: str) -> None:
    cut = {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}}
    reply = AIMessage(
        "",
        tool_calls=[{"name": "lookup", "args": {"name": "orders"}, "id": "c"}],
        response_metadata=cut,
        usage_metadata=usage(500, FILE["models"]["analyst"]["max_output_tokens"]),  # type: ignore[arg-type]
    )
    guard = RunGuard(tokens_per_run=10**9)
    model, ran = run_agent(lambda messages: reply, guard=guard)
    assert guard.stop_reason is StopReason.OUTPUT_LIMIT and model.calls == 1 and ran == []


def test_the_retry_cap_holds(switch: str) -> None:
    cap = VerificationConfig.from_pack().max_retries
    assert [attempt_allowed(n, cap) for n in range(1, cap + 2)] == [True] * cap + [False]
