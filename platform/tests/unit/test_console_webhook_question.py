"""Events > Send webhook question sends exactly the question `make demo NAME=` sends, read from the
one table both use (datapilot.demo_questions), never a copy on the page (zero tokens, no api)."""

from __future__ import annotations

import ast
import json
import sys
from typing import Any

import httpx

from datapilot import demo_questions
from datapilot.contracts import registries
from datapilot.settings import PLATFORM

CONSOLE = PLATFORM / "console"
if str(CONSOLE) not in sys.path:
    sys.path.insert(0, str(CONSOLE))

from datapilot_console.api_client import ApiClient, webhook_demo  # noqa: E402

WEBHOOK_BUTTON = "Events > Send webhook question"


def test_the_button_starts_one_of_the_registry_demos_that_name_it() -> None:
    named = {d.id for d in registries.demos().demos if d.trigger.console == WEBHOOK_BUTTON}
    assert named == {"events-webhook-question", "improve-cleared-unattended"}
    assert webhook_demo({}) == "events-webhook-question"
    assert webhook_demo({"revenue": "assisted", "orders": "report_only"}) == (
        "events-webhook-question"
    )
    assert webhook_demo({"revenue": "unattended", "orders": "report_only"}) == (
        "improve-cleared-unattended"
    )


def test_the_webhook_demo_asks_about_the_previous_day() -> None:
    assert demo_questions.question_for("events-webhook-question") == (
        "How many orders were placed yesterday?"
    )
    assert demo_questions.question_for("improve-cleared-unattended") == (
        demo_questions.SPINE_QUESTION
    )


def test_ask_demo_sends_the_demo_question_and_name() -> None:
    sent: list[Any] = []

    def handle(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        reply = {
            "event_id": "e",
            "run_id": "00000000-0000-0000-0000-000000000001",
            "job_id": 1,
            "duplicate": False,
            "duplicates_ignored": 0,
            "created_at": "2026-01-31T13:00:00+00:00",
        }
        return httpx.Response(200, json=reply)

    http = httpx.Client(base_url="http://api.test", transport=httpx.MockTransport(handle))
    ApiClient("http://api.test", http=http).ask_demo("events-webhook-question")
    assert sent[0]["payload"] == {
        "question": "How many orders were placed yesterday?",
        "demo_name": "events-webhook-question",
    }


def test_the_events_page_holds_no_question_of_its_own() -> None:
    source = (CONSOLE / "screens" / "events.py").read_text(encoding="utf-8")
    texts = [
        node.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]
    questions = set(demo_questions.QUESTIONS.values()) | {demo_questions.DEFAULT_QUESTION}
    assert not questions & set(texts), "a demo question copied onto the page"
    assert "SPINE_QUESTION" not in source and "text_input(" not in source
    assert "ask_demo(webhook)" in source
