"""The api contract on the real api app (zero tokens): every console control in the demo registry
sends the request its trigger names, built from datapilot.contracts.api, and every response
validates against the declared response model. The stub agent is injected here, at test level
only, to process the runs the controls create; then each run's full record is validated too.

The console engineer runs the same check through the console's client by passing another `send`
to api_contract_checks.check_console_controls.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import Any

import loops_paths  # noqa: F401  (before loops_support)
import pytest
from api_contract_checks import (
    Checked,
    ContractClient,
    ContractError,
    check_console_controls,
    console_controls,
)
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, BaseMessage
from loops_support import human_messages, query_then_answer
from pydantic import ValidationError

from datapilot.contracts import api as contract
from datapilot.contracts.live import SessionPurpose
from datapilot.loop3_events import sessions
from datapilot.loop3_events.api.app import app
from datapilot.loop3_events.worker import Worker, WorkerSettings

pytest_plugins = ["loops_fixtures"]
pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("clean_ops")]


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def send_through(client: TestClient):
    def send(method: str, path: str, body: dict[str, Any] | None) -> tuple[int, Any]:
        response = client.request(method, path, json=body)
        return response.status_code, response.json()

    return send


EXPORT = query_then_answer(
    "SELECT email FROM customers_marketable WHERE state = 'CA'", "Exported the customers."
)
ANSWER = query_then_answer("SELECT 1 AS one", "One.")


def stub_analyst(messages: list[BaseMessage]) -> AIMessage:
    """The test double: exports read personal data, so they wait for approval."""
    asked = str(human_messages(messages)[0].content)
    return (EXPORT if asked.startswith("Export") else ANSWER)(messages)


def test_every_console_control_honours_the_contract(client, services_for) -> None:
    sessions.start_session(SessionPurpose.DEVELOPMENT, "contract test", "UTC")
    send = send_through(client)
    results = check_console_controls(send)
    assert set(results) == {d.trigger.console for d in console_controls()}
    for console, checked in results.items():
        assert checked.calls, console
        assert checked.calls[0][0] == "POST", console  # the control's own request came first

    services = services_for({"analyst": stub_analyst})
    worker = Worker(
        services,
        models_for=lambda _r, _activity: services.models,
        settings=WorkerSettings(poll_seconds=0.05),
    )

    async def drain() -> None:
        while await worker.run_once():
            pass

    asyncio.run(drain())
    checked = Checked()
    contract_client = ContractClient(send, checked)
    listed = contract.RunList.model_validate(
        contract_client.get("/runs", params={"limit": 200}).json()
    )
    assert listed.runs
    for run in listed.runs:  # processed runs carry events, approvals, and posts
        contract_client.get(f"/runs/{run.run_id}").raise_for_status()
    held = [r for r in listed.runs if r.status == "awaiting_approval"]
    assert held, "the export control should leave a run waiting for approval"
    decision = contract.ApprovalIn(decision="reject", decided_by="contract test")
    contract_client.post(f"/approvals/{held[0].run_id}", json=decision.model_dump())
    assert ("POST", "/approvals/{run_id}", "ApprovalDecided") in checked.calls


def test_a_request_outside_the_contract_is_refused_before_it_is_sent(client) -> None:
    contract_client = ContractClient(send_through(client), Checked())
    with pytest.raises(ValidationError):
        contract_client.post("/control/kill-switch", json={"action": "edit"})
    with pytest.raises(ContractError):
        contract_client.post("/demo/malicious-sql", json={"unexpected": True})
