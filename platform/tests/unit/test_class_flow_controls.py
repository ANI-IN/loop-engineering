"""The class path's controls with no database and no model: the finale's refusals, the autonomy
command and console control, the naive analyzer demo's two requests, and the questions the
duplicate-events and kill-switch demos send (zero tokens)."""

from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from datapilot import demo_questions, finale
from datapilot.cli import app as cli
from datapilot.contracts import AutonomyLevel, registries
from datapilot.loop3_events import commands, demos
from datapilot.settings import PLATFORM

CONSOLE = PLATFORM / "console"
if str(CONSOLE) not in sys.path:
    sys.path.insert(0, str(CONSOLE))

from datapilot_console import views  # noqa: E402
from datapilot_console.api_client import ApiClient, webhook_hold  # noqa: E402

READY = finale.FinaleState("released", "unattended", None)
PENDING = finale.FinaleState("released", "unattended", "v8")
REPORT_ONLY = finale.FinaleState("released", "report_only", None)
ENGAGED = finale.FinaleState("engaged", "report_only", None)


# --- the finale's starting state -----------------------------------------------------------------
def test_the_finale_waits_for_a_pending_promotion_first() -> None:
    said = finale.refusal(finale.FinaleState("engaged", "report_only", "v8"))
    assert said is not None and said.startswith("v8 is approved, and its promotion has not")
    # Review round 2 (R2B-18): the Improve page says "v8 is the active version", not "is active".
    assert "Wait until the Improve page says v8 is the active version" in said


def test_the_finale_waits_for_the_clearance_re_runs_after_the_activation() -> None:
    clearing = finale.FinaleState("released", "unattended", None, clearing="v8")
    said = finale.refusal(clearing)
    assert said is not None and said.startswith("v8 is the active version, and its clearance")
    assert webhook_hold("events-webhook-question", clearing) == said


def test_the_wait_for_the_clearance_ends_even_when_no_family_clears() -> None:
    # Review round 2 (R2B-03): the wait names its end in both outcomes, a family cleared or none.
    for state in (PENDING, finale.FinaleState("released", "unattended", None, clearing="v8")):
        said = finale.waiting_for_promotion(state)
        assert said is not None and finale.UNTIL_CLEARED in said
    assert "Not cleared for every family" in finale.UNTIL_CLEARED
    assert "posts at the assisted level" in finale.UNTIL_CLEARED


def test_the_finale_needs_the_kill_switch_released_and_the_unattended_level() -> None:
    engaged = finale.refusal(ENGAGED)
    assert engaged is not None and "kill switch is engaged" in engaged
    assert "Release kill switch" in engaged and "make reset NAME=event-loop" in engaged
    level = finale.refusal(REPORT_ONLY)
    assert level is not None and "at the report-only level" in level
    assert 'make autonomy LEVEL=unattended BY="<your name>"' in level
    assert "Improve > Set the unattended level" in level
    assert finale.refusal(READY) is None


def test_the_webhook_button_holds_only_while_it_would_send_the_wrong_thing() -> None:
    # Section 3: the event loop's question goes at any level, kill switch and all
    assert webhook_hold("events-webhook-question", REPORT_ONLY) is None
    assert webhook_hold("events-webhook-question", ENGAGED) is None
    # approved, promotion pending: neither question may go yet
    assert webhook_hold("events-webhook-question", PENDING) == finale.waiting_for_promotion(PENDING)
    assert webhook_hold("improve-cleared-unattended", PENDING) == finale.refusal(PENDING)
    assert webhook_hold("improve-cleared-unattended", REPORT_ONLY) == finale.refusal(REPORT_ONLY)
    assert webhook_hold("improve-cleared-unattended", READY) is None


def test_make_demo_of_the_finale_checks_its_state_first(monkeypatch: pytest.MonkeyPatch) -> None:
    @contextmanager
    def connect(role: Any, **_: Any) -> Any:
        row = {
            "kill_switch": "released",
            "autonomy_level": "report_only",
            "pending_promotion": None,
            "clearing": None,
        }
        yield SimpleNamespace(execute=lambda *a, **k: SimpleNamespace(fetchone=lambda: row))

    monkeypatch.setattr(commands.db, "connect", connect)
    sent: list[str] = []
    client = SimpleNamespace(post=lambda url, **k: sent.append(url))
    with pytest.raises(commands.FinaleRefused, match="report-only level"):
        commands.demo("improve-cleared-unattended", client=client)
    assert sent == [], "nothing was sent"
    result = CliRunner().invoke(cli, ["demo", "improve-cleared-unattended"])
    assert result.exit_code == 1 and "improve-cleared-unattended not sent" in result.output


# --- the autonomy level: make autonomy and the Improve page's control ----------------------------
class Api:
    def __init__(self, status: int = 200) -> None:
        self.status, self.bodies = status, []

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        self.bodies.append((url, kwargs["json"]))
        if self.status != 200:
            detail = {"detail": "release the kill switch before changing the autonomy level"}
            return httpx.Response(self.status, json=detail)
        level = kwargs["json"]["level"]
        return httpx.Response(200, json={"autonomy_level": level, "label": level})


def test_the_autonomy_command_sets_the_level_through_the_api() -> None:
    api = Api()
    assert commands.set_autonomy("unattended", by="Ana", client=api) is AutonomyLevel.UNATTENDED
    assert commands.set_autonomy("report-only", by="Ana", client=api) is AutonomyLevel.REPORT_ONLY
    assert api.bodies[0] == ("/control/autonomy", {"level": "unattended", "by": "Ana"})
    with pytest.raises(ValueError, match="unknown autonomy level"):
        commands.set_autonomy("full", by="Ana", client=api)
    with pytest.raises(ValueError, match="release the kill switch"):
        commands.set_autonomy("unattended", by="Ana", client=Api(409))


def test_the_console_sets_the_level_with_the_contract_models() -> None:
    sent: list[Any] = []

    def handle(request: httpx.Request) -> httpx.Response:
        sent.append((request.url.path, json.loads(request.content)))
        return httpx.Response(200, json={"autonomy_level": "unattended", "label": "unattended"})

    http = httpx.Client(base_url="http://api.test", transport=httpx.MockTransport(handle))
    ApiClient("http://api.test", http=http).set_autonomy("unattended")
    assert sent == [("/control/autonomy", {"level": "unattended", "by": "console"})]


def test_the_improve_page_control_offers_the_one_level_it_can_set() -> None:
    shown = views.autonomy_control(REPORT_ONLY)
    assert shown["label"] == "Set the unattended level" and shown["target"] == "unattended"
    assert shown["text"] == "The system is at the report-only level." and shown["blocked"] is None
    back = views.autonomy_control(READY)
    assert back["label"] == "Set the report-only level" and back["target"] == "report_only"
    assert views.autonomy_control(ENGAGED)["blocked"] == "Release the kill switch first."
    waiting = views.autonomy_control(finale.FinaleState("released", "report_only", "v8"))
    assert waiting["blocked"] == "Wait until v8 is the active version."
    source = (CONSOLE / "screens" / "improve.py").read_text(encoding="utf-8")
    assert 'set_autonomy(autonomy["target"])' in source and "improve-autonomy" in source


# --- the naive analyzer demo queues both of its steps --------------------------------------------
def test_the_naive_analyzer_demo_queues_the_analyzer_then_the_candidate_experiment() -> None:
    calls: list[tuple[str, dict]] = []

    def post(url: str, **kwargs: Any) -> Any:
        calls.append((url, kwargs.get("json") or {}))
        body = {"request_id": f"req-{len(calls)}"}
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: body)

    demo = registries.demos().by_id("improve-naive-analyzer-blocked")
    done = demos.trigger(SimpleNamespace(post=post), demo)
    assert [url for url, _ in calls] == ["/analyzer/run", "/experiments/run"]
    assert calls[1][1]["target"] == "candidate"
    assert done.request_ids == ["req-1", "req-2"]
    team = registries.demos().by_id("improve-analyzer-team-approve")
    calls.clear()
    demos.trigger(SimpleNamespace(post=post), team)
    assert [url for url, _ in calls] == ["/analyzer/run"], "the team's approval comes first"


# --- the Section 3 demos ask the same question from the console and from make demo -------------
@pytest.mark.parametrize("demo", ["events-duplicate-events", "events-kill-switch-in-flight"])
def test_the_webhook_demos_of_section_3_ask_the_webhook_question(demo: str) -> None:
    assert demo_questions.question_for(demo) == demo_questions.WEBHOOK_QUESTION
    assert demo in demo_questions.QUESTIONS
