"""The run guard: one object per run that every model and tool call checks.

It holds the run's token count and the reason the run must stop, if any. Middleware ends the agent
loop with a before_model jump to end and short-circuits tool calls with a ToolMessage (returning a
Command from a tool wrapper does not end the loop). The event loop adds its own stop sources, such
as the kill switch and the daily budget, through `external_stop`.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from langchain.agents.middleware import AgentMiddleware, hook_config
from langchain_core.messages import AIMessage, ToolMessage

from datapilot.contracts import RunEventKind


class StopReason(StrEnum):
    KILL_SWITCH = "kill_switch"
    DAILY_BUDGET = "daily_budget"
    TOKEN_LIMIT = "token_limit"
    REFUSED_WRITE = "refused_write"  # the database refused a write: never a retry
    OUTPUT_LIMIT = "output_limit"  # a response was cut off at its max_output_tokens


def _never() -> StopReason | None:
    return None


Emit = Callable[[RunEventKind, dict[str, Any]], None]


@dataclass
class RunGuard:
    tokens_per_run: int
    external_stop: Callable[[], StopReason | None] = _never
    on_usage: Callable[[int, int], None] | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    model_calls: int = 0
    stop_reason: StopReason | None = None
    stop_detail: str = ""

    def stop(self, reason: StopReason, detail: str) -> None:
        if self.stop_reason is None:
            self.stop_reason, self.stop_detail = reason, detail

    def check(self) -> StopReason | None:
        if self.stop_reason is None and (reason := self.external_stop()) is not None:
            self.stop(reason, f"stopped: {reason.value}")
        if self.stop_reason is None and self.tokens_in + self.tokens_out >= self.tokens_per_run:
            self.stop(StopReason.TOKEN_LIMIT, f"token budget of {self.tokens_per_run} reached")
        return self.stop_reason

    def record(self, message: AIMessage) -> None:
        meta: dict[str, Any] = dict(message.usage_metadata or {})
        tokens_in = int(meta.get("input_tokens") or 0)
        tokens_out = reported_output_tokens(message) or 0  # the budget counts a missing count as 0
        self.model_calls += 1
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out
        if self.on_usage:
            self.on_usage(tokens_in, tokens_out)


def output_limit_reached(message: AIMessage) -> bool:
    """True when the Responses API ended the response early at max_output_tokens."""
    meta = message.response_metadata or {}
    reason = (meta.get("incomplete_details") or {}).get("reason")
    return meta.get("status") == "incomplete" and reason == "max_output_tokens"


def reported_output_tokens(message: AIMessage) -> int | None:
    """The output tokens a reply reports, or None when it reports none. langchain-openai puts the
    Responses API's usage (usage.output_tokens, reasoning included) in usage_metadata, the field
    the spend ledger reads too; a reply with no count is never read as zero tokens."""
    count = (message.usage_metadata or {}).get("output_tokens")
    if count is None:  # an older shape keeps the API's usage in response_metadata
        meta = message.response_metadata or {}
        usage = meta.get("usage") or meta.get("token_usage") or {}
        count = usage.get("output_tokens", usage.get("completion_tokens"))
    return int(count) if count is not None else None


def cut_off_detail(message: AIMessage) -> str:
    stopped = "a model response was cut off at its output-token cap"
    used = reported_output_tokens(message)
    if used is None:
        return f"{stopped}; it reported no output-token count"
    return f"{stopped} after {used} tokens"


def latest_reply(messages: Sequence[Any]) -> AIMessage | None:
    """The model's reply of this step. A structured answer is followed by the tool message the
    agent adds for it, so the reply can sit behind tool messages."""
    for message in reversed(messages):
        if not isinstance(message, ToolMessage):
            return message if isinstance(message, AIMessage) else None
    return None


def stopped_message(request: Any, text: str) -> ToolMessage:
    return ToolMessage(text, tool_call_id=request.tool_call["id"], status="error")


class GuardMiddleware(AgentMiddleware):
    """Token accounting after each model call; a stop before the next model or tool call."""

    def __init__(self, guard: RunGuard) -> None:
        super().__init__()
        self.guard = guard

    @hook_config(can_jump_to=["end"])
    def before_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        return {"jump_to": "end"} if self.guard.check() else None

    @hook_config(can_jump_to=["end"])
    async def abefore_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        return self.before_model(state, runtime)

    @hook_config(can_jump_to=["end"])
    def after_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        last = latest_reply(state["messages"])
        if last is None:
            return None
        self.guard.record(last)
        if output_limit_reached(last):  # a cut-off reply is never acted on: the run ends here
            self.guard.stop(StopReason.OUTPUT_LIMIT, cut_off_detail(last))
            return {"jump_to": "end"}
        return None

    @hook_config(can_jump_to=["end"])
    async def aafter_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        return self.after_model(state, runtime)

    def wrap_tool_call(self, request: Any, handler: Callable[[Any], Any]) -> Any:
        if self.guard.check():
            return stopped_message(request, f"Run stopped: {self.guard.stop_detail}.")
        return handler(request)

    async def awrap_tool_call(self, request: Any, handler: Callable[[Any], Awaitable[Any]]) -> Any:
        if self.guard.check():
            return stopped_message(request, f"Run stopped: {self.guard.stop_detail}.")
        return await handler(request)


class ToolEventsMiddleware(AgentMiddleware):
    """Writes tool_call_started and tool_call_finished run events, with each call's duration."""

    def __init__(self, emit: Emit) -> None:
        super().__init__()
        self.emit = emit

    def _started(self, request: Any) -> float:
        call = request.tool_call
        self.emit(RunEventKind.TOOL_CALL_STARTED, {"tool": call["name"], "args": call["args"]})
        return time.monotonic()

    def _finished(self, request: Any, started: float, result: Any) -> None:
        status = getattr(result, "status", "success")
        self.emit(
            RunEventKind.TOOL_CALL_FINISHED,
            {
                "tool": request.tool_call["name"],
                "ms": round((time.monotonic() - started) * 1000),
                "status": status,
            },
        )

    def wrap_tool_call(self, request: Any, handler: Callable[[Any], Any]) -> Any:
        started = self._started(request)
        result = handler(request)
        self._finished(request, started, result)
        return result

    async def awrap_tool_call(self, request: Any, handler: Callable[[Any], Awaitable[Any]]) -> Any:
        started = self._started(request)
        result = await handler(request)
        self._finished(request, started, result)
        return result
