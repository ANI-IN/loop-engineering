"""A model call that fails after it was sent can still be billed, so the ledger records it: with
the usage the error or the partial response reports, or else an estimate from the request, marked
estimated. Recording never hides the call's own error (zero tokens: the errors are stand-ins)."""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

import pytest
from langchain_core.callbacks import CallbackManager
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, LLMResult

from datapilot.observability import spend

MODEL = "gpt-6-luna"


class TimedOut(Exception):
    """Stands in for the software development kit's timeout: no response, so no usage."""


class Refused(Exception):
    """Stands in for a status error whose response body carries the usage."""

    def __init__(self, body: dict[str, object]) -> None:
        super().__init__("refused")
        self.body = body


@pytest.fixture
def ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "ledger.sqlite"
    monkeypatch.setenv("DATAPILOT_SPEND_LEDGER", str(path))
    for name in ("DATAPILOT_BUILD_BUDGET", "DATAPILOT_USE_RESERVE", "DATAPILOT_SESSION_SINCE"):
        monkeypatch.delenv(name, raising=False)
    return path


def rows(path: Path) -> list[tuple[object, ...]]:
    spend.total_usd(path)  # creates the table when nothing was recorded
    with sqlite3.connect(path) as conn:
        return conn.execute(
            "SELECT input_tokens, cached_input_tokens, output_tokens, cache_write_tokens, "
            "estimated, error FROM spend_ledger ORDER BY id"
        ).fetchall()


def callback() -> spend.SpendCallback:
    return spend.SpendCallback(component="analyst", model=MODEL, activity="calibration")


def sent(handler: spend.SpendCallback, text: str, call: str = "call-1") -> None:
    handler.on_chat_model_start({}, [[HumanMessage(text)]], run_id=call)


def test_a_timed_out_call_is_recorded_with_an_estimate(ledger: Path) -> None:
    handler = callback()
    sent(handler, "x" * 400)  # 400 characters, about 100 tokens
    handler.on_llm_error(TimedOut(), run_id="call-1", response=None)
    assert rows(ledger) == [(100, 0, 0, 0, 1, "TimedOut")]
    price = spend.pack_config()["prices"][MODEL]["input"]
    assert spend.total_usd(ledger) == pytest.approx(100 * price / 1_000_000)


def test_a_refused_call_is_recorded_with_the_usage_its_error_reports(ledger: Path) -> None:
    handler = callback()
    sent(handler, "how many orders")
    usage = {
        "input_tokens": 900,
        "output_tokens": 0,
        "input_tokens_details": {"cached_tokens": 512, "cache_write_tokens": 128},
    }
    handler.on_llm_error(Refused({"response": {"usage": usage}}), run_id="call-1")
    assert rows(ledger) == [(900, 512, 0, 128, 0, "Refused")]


def test_a_refusal_for_no_credits_without_usage_is_recorded_at_no_cost(ledger: Path) -> None:
    # OpenAI does not bill a request it refuses before processing it: on 23 October it counted 4
    # extra requests against 28 refusals for no credits. The row still shows the refusal happened.
    handler = callback()
    sent(handler, "y" * 40)
    handler.on_llm_error(Refused({"error": {"code": "insufficient_quota"}}), run_id="call-1")
    assert rows(ledger) == [(0, 0, 0, 0, 0, "Refused")]
    assert spend.total_usd(ledger) == 0


class BadRequestError(Exception):
    """Stands in for the software development kit's 400 status error: rejected, never processed."""

    status_code = 400


def test_a_request_rejected_before_processing_is_recorded_at_no_cost(ledger: Path) -> None:
    # On 23 October a request of about 32 million characters (8 million tokens by the estimate) was
    # rejected as invalid; the old estimate charged 0.81 dollars for a call OpenAI never processed.
    handler = callback()
    sent(handler, "z" * 4_000)
    handler.on_llm_error(BadRequestError("context length exceeded"), run_id="call-1")
    assert rows(ledger) == [(0, 0, 0, 0, 0, "BadRequestError")]
    assert spend.total_usd(ledger) == 0


def test_a_rejected_request_that_reports_usage_keeps_that_usage(ledger: Path) -> None:
    handler = callback()
    sent(handler, "how many orders")
    error = BadRequestError("rejected")
    error.body = {"usage": {"input_tokens": 300, "output_tokens": 0}}  # type: ignore[attr-defined]
    handler.on_llm_error(error, run_id="call-1")
    assert rows(ledger) == [(300, 0, 0, 0, 0, "BadRequestError")]


def test_a_cut_off_stream_is_recorded_with_its_partial_usage(ledger: Path) -> None:
    handler = callback()
    sent(handler, "how many orders")
    usage = {"input_tokens": 700, "output_tokens": 40, "total_tokens": 740}
    partial = ChatGenerationChunk(message=AIMessageChunk("partial", usage_metadata=usage))  # type: ignore[arg-type]
    handler.on_llm_error(TimedOut(), run_id="call-1", response=LLMResult(generations=[[partial]]))
    assert rows(ledger) == [(700, 0, 40, 0, 0, "TimedOut")]


def test_a_call_stopped_before_it_was_sent_is_not_recorded(ledger: Path) -> None:
    callback().on_llm_error(spend.BudgetStop("stopped"), run_id="never-sent")
    assert rows(ledger) == []


def test_a_finished_call_is_recorded_once(ledger: Path) -> None:
    handler = callback()
    sent(handler, "how many orders")
    usage = {"input_tokens": 10, "output_tokens": 2, "total_tokens": 12}
    message = AIMessage("ok", usage_metadata=usage)  # type: ignore[arg-type]
    handler.on_llm_end(LLMResult(generations=[[ChatGeneration(message=message)]]), run_id="call-1")
    handler.on_llm_error(TimedOut(), run_id="call-1")  # a late error for the same call
    assert rows(ledger) == [(10, 0, 2, 0, 0, None)]


def test_recording_a_failed_call_never_hides_its_error(
    ledger: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(**_: object) -> float:
        raise OSError("the ledger is not writable")

    monkeypatch.setattr(spend, "record", broken)
    handler = callback()
    sent(handler, "how many orders")
    handler.on_llm_error(TimedOut(), run_id="call-1")  # logs and raises nothing
    # Through LangChain's own manager, as a chat model calls it: the handler raises nothing, so
    # the original error stays the one the caller re-raises.
    [run] = CallbackManager(handlers=[handler]).on_chat_model_start(
        {}, [[HumanMessage("again")]], run_id=uuid.uuid4()
    )
    run.on_llm_error(TimedOut())


class ClientError(Exception):
    """Stands in for the software development kit's status error: the HTTP status and a body."""

    def __init__(self, status_code: int, body: dict[str, object] | None = None) -> None:
        super().__init__(f"Error code: {status_code}")
        self.status_code = status_code
        self.body = body or {"error": {"message": "Invalid 'input[7].output': string too long."}}


@pytest.mark.parametrize("status", [400, 401, 404, 413, 422, 429])
def test_a_request_the_api_refused_outright_costs_nothing(ledger: Path, status: int) -> None:
    """Live, 23 October: a 33-megabyte request was refused with 400 before any work, and the
    estimate from its request put about 0.81 dollars no one was billed for in the ledger. A client
    error reports no usage because nothing ran; it is recorded at zero, so the call still shows."""
    handler = callback()
    sent(handler, "z" * 4_000_000)  # about a million tokens, never processed
    handler.on_llm_error(ClientError(status), run_id="call-1")
    assert rows(ledger) == [(0, 0, 0, 0, 0, "ClientError")]
    assert spend.total_usd(ledger) == 0


def test_the_software_development_kit_bad_request_counts_as_refused_outright() -> None:
    import httpx
    import openai

    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(400, request=request, json={"error": {"message": "too long"}})
    error = openai.BadRequestError("too long", response=response, body={"error": {}})
    assert spend.rejected_before_processing(error)
    assert not spend.rejected_before_processing(openai.APITimeoutError(request=request))


@pytest.mark.parametrize("status", [500, 502, 503])
def test_a_server_error_without_usage_is_still_estimated(ledger: Path, status: int) -> None:
    handler = callback()
    sent(handler, "w" * 40)
    handler.on_llm_error(ClientError(status, {"error": {"message": "server"}}), run_id="call-1")
    assert rows(ledger) == [(10, 0, 0, 0, 1, "ClientError")]


def test_a_client_error_that_reports_usage_is_recorded_with_it(ledger: Path) -> None:
    handler = callback()
    sent(handler, "how many orders")
    error = ClientError(400, {"response": {"usage": {"input_tokens": 300, "output_tokens": 0}}})
    handler.on_llm_error(error, run_id="call-1")
    assert rows(ledger) == [(300, 0, 0, 0, 0, "ClientError")]


def test_the_estimate_counts_tool_definitions_and_tool_calls() -> None:
    tools = [{"type": "function", "name": "run_sql", "parameters": {"type": "object"}}]
    call = AIMessage("", tool_calls=[{"name": "run_sql", "args": {"sql": "SELECT 1"}, "id": "c1"}])
    bare = spend.estimate_input_tokens([[call]])
    assert spend.estimate_input_tokens([[call]], {"tools": tools}) > bare > 0


def _finished(handler: spend.SpendCallback, tokens_in: int, tokens_out: int) -> None:
    usage = {"input_tokens": tokens_in, "output_tokens": tokens_out}
    usage["total_tokens"] = tokens_in + tokens_out
    message = AIMessage("", usage_metadata=usage)  # type: ignore[arg-type]
    handler.on_llm_end(LLMResult(generations=[[ChatGeneration(message=message)]]), run_id="call-1")


def test_a_finished_call_reporting_zero_input_tokens_records_the_estimate(ledger: Path) -> None:
    """Live, a reply cut off at its cap reported 0 input tokens (run 730953ea); the request was
    sent and billed, so the ledger records the estimate from the request, marked estimated, as it
    does for a failed call, and keeps the output tokens the reply reported."""
    handler = callback()
    sent(handler, "x" * 400)  # about 100 tokens
    _finished(handler, 0, 7)
    assert rows(ledger) == [(100, 0, 7, 0, 1, None)]
    price = spend.pack_config()["prices"][MODEL]
    expected = (100 * price["input"] + 7 * price["output"]) / 1_000_000
    assert spend.total_usd(ledger) == pytest.approx(expected)


def test_a_finished_call_reporting_its_input_tokens_is_not_estimated(ledger: Path) -> None:
    handler = callback()
    sent(handler, "x" * 400)
    _finished(handler, 900, 0)
    assert rows(ledger) == [(900, 0, 0, 0, 0, None)]
