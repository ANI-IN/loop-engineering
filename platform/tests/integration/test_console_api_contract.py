"""The api contract through the console's own client (zero tokens).

The loops track's seam, api_contract_checks.check_console_controls(send), presses every console
control in the demo registry; here `send` is the console client's own `send`, over the real api app
(FastAPI's TestClient). Then each of the console's action methods runs against the same app, so
every request it builds and every reply it reads go through datapilot.contracts.api.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator

import loops_paths  # noqa: F401  (before loops_support)
import pytest
from api_contract_checks import Checked, ContractClient, check_console_controls, console_controls
from fastapi.testclient import TestClient

from datapilot.contracts import api as contract
from datapilot.contracts import registries
from datapilot.contracts.live import SessionPurpose
from datapilot.loop3_events import demos, sessions
from datapilot.loop3_events.api.app import app
from datapilot.settings import PLATFORM

sys.path.insert(0, str(PLATFORM / "console"))

from datapilot_console.api_client import (  # noqa: E402
    OVERBROAD_RULE,
    ApiClient,
    ApiError,
    webhook_demo,
)

pytest_plugins = ["loops_fixtures"]
pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("clean_ops")]


@pytest.fixture
def console_client() -> Iterator[ApiClient]:
    with TestClient(app) as test_client:
        yield ApiClient("http://testserver", http=test_client)


def test_every_console_control_honours_the_contract_through_the_console_client(
    console_client: ApiClient,
) -> None:
    sessions.start_session(SessionPurpose.DEVELOPMENT, "console contract test", "UTC")
    results = check_console_controls(console_client.send)
    assert set(results) == {d.trigger.console for d in console_controls()}
    for console, checked in results.items():
        assert checked.calls and checked.calls[0][0] == "POST", console


def test_the_console_actions_send_and_read_contract_models(console_client: ApiClient) -> None:
    session = sessions.start_session(SessionPurpose.DEVELOPMENT, "console contract test", "UTC")
    assert console_client.healthy()
    asked = console_client.ask("How many orders were placed?", "agent-simple-question")
    assert isinstance(asked, contract.EventSubmitted) and not asked.duplicate
    three = console_client.send_three_times("How many orders were placed?")
    assert [r.duplicate for r in three] == [False, True, True]
    assert three[-1].duplicates_ignored == 2 and len({r.run_id for r in three}) == 1
    assert isinstance(console_client.request_export(), contract.EventSubmitted)
    digest = console_client.run_digest("2026-01-30", str(session.session_id))
    assert console_client.run_digest("2026-01-30", str(session.session_id)).run_id == digest.run_id
    for name in ("large-query", "malicious-sql", "cartesian-query", "failing-grader"):
        assert isinstance(console_client.demo(name), contract.EventSubmitted)
    assert console_client.stop_all().kill_switch == "engaged"
    assert console_client.kill_switch("release").kill_switch == "released"
    experiment = console_client.run_experiment("active", plus_rule=OVERBROAD_RULE)
    assert experiment.kind == "experiment" and experiment.params["plus_rule"] == OVERBROAD_RULE
    assert console_client.run_experiment("candidate").params["target"] == "candidate"
    assert console_client.run_analyzer().kind == "analyzer"
    with pytest.raises(ApiError, match="The api refused the request \\(409\\)"):
        console_client.decide(str(asked.run_id), "approve")  # not awaiting approval
    with pytest.raises(ApiError, match="404"):
        console_client.approve_version("no-such-version")


WEBHOOK_BUTTON = "Events > Send webhook question"


@pytest.mark.parametrize(
    ("levels", "demo_id"),
    [({}, "events-webhook-question"), ({"revenue": "unattended"}, "improve-cleared-unattended")],
)
def test_the_webhook_button_sends_the_question_make_demo_sends(
    console_client: ApiClient, levels: dict[str, str], demo_id: str
) -> None:
    """The button starts the event loop's webhook demo, or the finale once a family is cleared for
    the unattended level; either way its run asks what `make demo NAME=` asks (demos.trigger)."""
    sessions.start_session(SessionPurpose.DEVELOPMENT, "console contract test", "UTC")
    demo = next(d for d in registries.demos().demos if d.id == demo_id)
    assert demo.trigger.console == WEBHOOK_BUTTON and webhook_demo(levels) == demo_id

    def question_of(run_id: object) -> str:
        status, run = console_client.send("GET", f"/runs/{run_id}", None)
        assert status == 200
        return str(contract.RunDetail.model_validate(run).question)

    from_console = console_client.ask_demo(webhook_demo(levels))
    from_make = demos.trigger(ContractClient(console_client.send, Checked()), demo)
    assert question_of(from_console.run_id) == question_of(from_make.run_ids[0])
    if demo_id == "events-webhook-question":
        assert question_of(from_console.run_id) == "How many orders were placed yesterday?"
