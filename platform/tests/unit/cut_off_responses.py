"""Responses API replies shaped as the API sends them, behind a real ChatOpenAI whose client is a
stand-in (no network, no tokens). Shared by the unit and integration tests of the guard's stop
reason.

The live probe (make calibrate STEP=output-token-cap, runs d9f0ab0e and 730953ea) made two analyst
calls, as the spend ledger shows: the first called list_tables and completed within the cap (715
input tokens, 14 output tokens, the analyst's usual first call), and the second was cut off at the
cap and reported 0 input and 0 output tokens. Run 74fe4786, a minute earlier, made the same first
call and a second one cut off after 16 output tokens."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage
from langchain_core.outputs import LLMResult
from langchain_openai import ChatOpenAI
from openai.types.responses import Response

from datapilot.observability.spend import usage_from_message

INPUT_TOKENS, OUTPUT_TOKENS = 715, 14  # the probe's first call (list_tables), and the old shape
CUT_OFF_INPUT_TOKENS = 790  # the second call's input in run 74fe4786
CAP = 16


def _usage(input_tokens: int, output_tokens: int, reasoning_tokens: int) -> dict[str, Any]:
    return {
        "input_tokens": input_tokens,
        "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
        "output_tokens": output_tokens,
        "output_tokens_details": {"reasoning_tokens": reasoning_tokens},
        "total_tokens": input_tokens + output_tokens,
    }


def _response(name: str, output: list[dict[str, Any]], **fields: Any) -> Response:
    body: dict[str, Any] = {
        "id": f"resp_{name}",
        "object": "response",
        "created_at": 1769817600,
        "model": "gpt-6-luna",
        "status": "completed",
        "output": output,
        "parallel_tool_calls": True,
        "tool_choice": "required",
        "tools": [],
        "max_output_tokens": CAP,
        **fields,
    }
    return Response.model_validate({k: v for k, v in body.items() if v is not None})


def list_tables_response() -> Response:
    """The analyst's first call, completed within the cap: a short reasoning item and a call of
    list_tables with no arguments."""
    output = [
        {"type": "reasoning", "id": "rs_first", "summary": []},
        {
            "type": "function_call",
            "id": "fc_first",
            "call_id": "call_list_tables",
            "name": "list_tables",
            "arguments": "{}",
            "status": "completed",
        },
    ]
    return _response("first", output, usage=_usage(INPUT_TOKENS, OUTPUT_TOKENS, 6))


def incomplete_response(
    *,
    with_usage: bool = True,
    input_tokens: int = INPUT_TOKENS,
    output_tokens: int = OUTPUT_TOKENS,
) -> Response:
    """A response that ended at max_output_tokens while the model was still reasoning."""
    return _response(
        "cut_off",
        [{"type": "reasoning", "id": "rs_cut_off", "summary": []}],
        status="incomplete",
        incomplete_details={"reason": "max_output_tokens"},
        usage=_usage(input_tokens, output_tokens, output_tokens) if with_usage else None,
    )


class _Raw:
    headers: dict[str, str] = {}

    def __init__(self, response: Response) -> None:
        self.response = response

    def parse(self) -> Response:
        return self.response


class StandInClient:
    """Answers responses.with_raw_response.create, as AsyncOpenAI, with the prepared responses in
    order (the last one again once they run out), and keeps each request's payload."""

    def __init__(self, responses: Sequence[Response]) -> None:
        self.responses = self
        self.with_raw_response = self
        self.replies = list(responses)
        self.payloads: list[dict[str, Any]] = []

    @property
    def calls(self) -> int:
        return len(self.payloads)

    async def create(self, **payload: Any) -> _Raw:
        self.payloads.append(payload)
        return _Raw(self.replies[min(len(self.payloads), len(self.replies)) - 1])


class LedgerView(BaseCallbackHandler):
    """Reads each finished call's output tokens the way the spend ledger's SpendCallback does."""

    def __init__(self) -> None:
        self.output_tokens: list[int] = []
        self.messages: list[AIMessage] = []

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        for generations in response.generations:
            for generation in generations:
                message = getattr(generation, "message", None)
                if isinstance(message, AIMessage):
                    self.messages.append(message)
                    self.output_tokens.append(usage_from_message(message).output_tokens)


def cut_off_model(
    response: Response | Sequence[Response], callbacks: Sequence[BaseCallbackHandler] = ()
) -> ChatOpenAI:
    """The live model's class and settings (models.openai_factory), with the stand-in client in
    place of OpenAI's; it answers with `response`, or with each of a sequence in turn."""
    model = ChatOpenAI(
        model="gpt-6-luna",
        api_key="sk-test-not-used",  # type: ignore[arg-type]
        use_responses_api=True,
        reasoning={"effort": "low"},
        max_tokens=CAP,  # type: ignore[call-arg]
        callbacks=list(callbacks),
    )
    replies = [response] if isinstance(response, Response) else list(response)
    model.root_async_client = StandInClient(replies)
    return model


def stand_in(model: ChatOpenAI) -> StandInClient:
    client = model.root_async_client
    assert isinstance(client, StandInClient)
    return client
