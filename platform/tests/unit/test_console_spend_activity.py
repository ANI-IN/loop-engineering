"""Runs started from the console record their spend under the activity of the console's live
session, never under the worker's own: the client sends the DataPilot-Spend-Activity header, and
the activity is the session's budget line followed by "console" (zero tokens, no api)."""

from __future__ import annotations

import json
import sys

import httpx
import pytest

from datapilot.contracts.live import SessionPurpose
from datapilot.observability import spend
from datapilot.settings import PLATFORM, get_settings

CONSOLE = PLATFORM / "console"
if str(CONSOLE) not in sys.path:
    sys.path.insert(0, str(CONSOLE))

from datapilot_console.api_client import ApiClient  # noqa: E402

ACCEPTED = {
    "run_id": "0b6f0d55-55c1-4f61-9f6e-3f1f4a0f0f0f",
    "job_id": 1,
    "duplicate": False,
    "duplicates_ignored": 0,
    "created_at": "2026-10-23T06:00:00+00:00",
}


def _client(seen: list[httpx.Request], activity: str | None) -> ApiClient:
    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        body = json.loads(request.content)
        return httpx.Response(200, json=ACCEPTED | {"event_id": body["event_id"]})

    http = httpx.Client(base_url="http://api.test", transport=httpx.MockTransport(handle))
    return ApiClient("http://api.test", http=http, spend_activity=activity)


@pytest.mark.parametrize(
    ("purpose", "activity"),
    [
        (SessionPurpose.DEVELOPMENT, "development live checks-console"),
        (SessionPurpose.REHEARSAL, "rehearsal-console"),
        (SessionPurpose.CLASS, "rehearsal-console"),
        (SessionPurpose.THURSDAY_REVIEW, "rehearsal-console"),
    ],
)
def test_the_console_activity_is_the_session_line_followed_by_console(
    purpose: SessionPurpose, activity: str
) -> None:
    assert spend.starter_activity(purpose.value, "console") == activity
    # the activity counts on the same line as the session's own preflight, so it is never refused
    assert spend.line_for(activity).name == spend.line_for(f"preflight-{purpose.value}").name


def test_without_a_line_for_the_session_the_process_activity_is_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATAPILOT_SPEND_ACTIVITY", "development")
    get_settings.cache_clear()
    try:
        assert spend.starter_activity("no-such-purpose", "console") == "development"
    finally:
        get_settings.cache_clear()


def test_a_console_event_carries_the_session_activity_header() -> None:
    seen: list[httpx.Request] = []
    _client(seen, "rehearsal-console").ask("How many orders?", "agent-simple-question")
    assert seen[0].url.path == "/events"
    assert seen[0].headers[spend.ACTIVITY_HEADER] == "rehearsal-console"


def test_without_a_session_the_console_sends_no_activity_header() -> None:
    seen: list[httpx.Request] = []
    _client(seen, None).ask("How many orders?", "agent-simple-question")
    assert spend.ACTIVITY_HEADER not in seen[0].headers


def test_the_client_from_settings_takes_the_session_purpose() -> None:
    client = ApiClient.from_settings(SessionPurpose.DEVELOPMENT.value)
    assert client.spend_activity == "development live checks-console"
    assert ApiClient.from_settings(None).spend_activity is None


def test_every_console_page_builds_its_client_with_the_session_purpose() -> None:
    source = (CONSOLE / "datapilot_console" / "frame.py").read_text(encoding="utf-8")
    assert "ApiClient.from_settings(st.session_state.get(SESSION_PURPOSE))" in source
    assert "ss[SESSION_PURPOSE] = session.purpose.value if session else None" in source
