"""Events > Request California export sends exactly the export request `make demo NAME=` sends,
read from the one table both use (datapilot.demo_questions), never a copy in the console (zero
tokens, no api)."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

import httpx

from datapilot import demo_questions
from datapilot.contracts import registries
from datapilot.loop3_events import demos
from datapilot.settings import PLATFORM

CONSOLE = PLATFORM / "console"
if str(CONSOLE) not in sys.path:
    sys.path.insert(0, str(CONSOLE))

from datapilot_console.api_client import ApiClient  # noqa: E402

EXPORT_BUTTON = "Events > Request California export"
EXPORT_DEMO = "events-approval-survives-restart"
# The wording the approval moment was verified live with (`make demo NAME=` since the start).
VERIFIED_WORDING = (
    "Export the California customers who may receive marketing, with their email addresses."
)


def _strings(path: Path) -> set[str]:
    return {
        node.value
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def test_the_button_starts_the_approval_demo_as_an_export_event() -> None:
    named = {d.id for d in registries.demos().demos if d.trigger.console == EXPORT_BUTTON}
    assert named == {EXPORT_DEMO}
    demo = next(d for d in registries.demos().demos if d.id == EXPORT_DEMO)
    assert demo.trigger.api == "POST /events (export.requested)"


def test_the_export_request_is_the_wording_verified_live_and_not_a_question() -> None:
    assert demo_questions.EXPORT_QUESTION == VERIFIED_WORDING
    assert demos.EXPORT_QUESTION is demo_questions.EXPORT_QUESTION
    assert EXPORT_DEMO not in demo_questions.QUESTIONS
    assert VERIFIED_WORDING not in demo_questions.QUESTIONS.values()


def test_request_export_sends_the_make_demo_wording_and_name() -> None:
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
    ApiClient("http://api.test", http=http).request_export()
    assert sent[0]["type"] == "export.requested"
    assert sent[0]["payload"] == {"question": VERIFIED_WORDING, "demo_name": EXPORT_DEMO}


def test_neither_the_console_nor_the_demo_trigger_holds_a_copy() -> None:
    client = CONSOLE / "datapilot_console" / "api_client.py"
    copies = [
        client,
        CONSOLE / "screens" / "events.py",
        PLATFORM / "src" / "datapilot" / "loop3_events" / "demos.py",
    ]
    for path in copies:
        assert VERIFIED_WORDING not in _strings(path), f"the export request copied into {path}"
    source = client.read_text(encoding="utf-8")
    assert "EXPORT_REQUEST =" not in source and "spring campaign" not in source
    assert "demo_questions.EXPORT_QUESTION" in source
