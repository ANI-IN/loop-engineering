"""A Responses API reply cut off at its output-token cap, shaped as the API sends it, behind a real
ChatOpenAI whose client is a stand-in (no network, no tokens). Shared by the unit and integration
tests of the guard's stop reason."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage
from langchain_core.outputs import LLMResult
from langchain_openai import ChatOpenAI
from openai.types.responses import Response

from datapilot.observability.spend import usage_from_message

# The probe's call (run d9f0ab0e): 715 input tokens, 14 output tokens, all of them reasoning.
INPUT_TOKENS, OUTPUT_TOKENS = 715, 14
CAP = 16


def incomplete_response(*, with_usage: bool = True) -> Response:
    """A response that ended at max_output_tokens while the model was still reasoning."""
    body: dict[str, Any] = {
        "id": "resp_cut_off",
        "object": "response",
        "created_at": 1769817600,
        "model": "gpt-6-luna",
        "status": "incomplete",
        "incomplete_details": {"reason": "max_output_tokens"},
        "output": [{"type": "reasoning", "id": "rs_cut_off", "summary": []}],
        "parallel_tool_calls": True,
        "tool_choice": "auto",
        "tools": [],
        "max_output_tokens": CAP,
    }
    if with_usage:
        body["usage"] = {
            "input_tokens": INPUT_TOKENS,
            "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
            "output_tokens": OUTPUT_TOKENS,
            "output_tokens_details": {"reasoning_tokens": OUTPUT_TOKENS},
            "total_tokens": INPUT_TOKENS + OUTPUT_TOKENS,
        }
    return Response.model_validate(body)


class _Raw:
    headers: dict[str, str] = {}

    def __init__(self, response: Response) -> None:
        self.response = response

    def parse(self) -> Response:
        return self.response


class StandInClient:
    """Answers responses.with_raw_response.create with one prepared response, as AsyncOpenAI."""

    def __init__(self, response: Response) -> None:
        self.responses = self
        self.with_raw_response = self
        self.response = response
        self.calls = 0

    async def create(self, **payload: Any) -> _Raw:
        self.calls += 1
        return _Raw(self.response)


class LedgerView(BaseCallbackHandler):
    """Reads each finished call's output tokens the way the spend ledger's SpendCallback does."""

    def __init__(self) -> None:
        self.output_tokens: list[int] = []

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        for generations in response.generations:
            for generation in generations:
                message = getattr(generation, "message", None)
                if isinstance(message, AIMessage):
                    self.output_tokens.append(usage_from_message(message).output_tokens)


def cut_off_model(response: Response, callbacks: Sequence[BaseCallbackHandler] = ()) -> ChatOpenAI:
    """The live model's class and settings, with the stand-in client in place of OpenAI's."""
    model = ChatOpenAI(
        model="gpt-6-luna",
        api_key="sk-test-not-used",  # type: ignore[arg-type]
        use_responses_api=True,
        reasoning={"effort": "low"},
        max_tokens=CAP,  # type: ignore[call-arg]
        callbacks=list(callbacks),
    )
    model.root_async_client = StandInClient(response)
    return model
