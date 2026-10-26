"""make demo, make reset, and make open-code refuse plainly (session 6 review, learner path):
with no live session open a demo stops before any service restart or model call, and a
misspelled demo or section name prints one line naming the valid names, not a traceback."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from datapilot.cli import app as cli
from datapilot.contracts import registries
from datapilot.loop3_events import commands, sessions
from datapilot.names import SECTIONS


class _NoSession:
    """The api with no live session open: GET /sessions/current answers 404."""

    def __init__(self) -> None:
        self.posts: list[str] = []

    def get(self, url: str, **_: Any) -> httpx.Response:
        assert url == "/sessions/current"
        return httpx.Response(404, json={"detail": sessions.NO_SESSION})

    def post(self, url: str, **_: Any) -> httpx.Response:
        self.posts.append(url)
        raise AssertionError("nothing may be sent without a live session")


def test_a_demo_with_no_live_session_refuses_before_anything_is_sent(monkeypatch) -> None:
    restarts: list[list[str]] = []
    client = _NoSession()
    with pytest.raises(commands.DemoRefused) as refused:
        commands.demo(
            "events-approval-survives-restart",  # its planted half restarts the worker
            planted_bugs=True,
            client=client,
            compose=restarts.append,
            say=lambda _line: None,
        )
    assert str(refused.value) == sessions.NO_SESSION
    assert str(refused.value).startswith("No live session is open: run make preflight PURPOSE=")
    assert client.posts == [] and restarts == []


def test_make_demo_prints_the_no_session_sentence_on_one_line(monkeypatch) -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/sessions/current", "nothing else is asked"
        return httpx.Response(404, json={"detail": sessions.NO_SESSION})

    real = httpx.Client

    def client(**kwargs: Any) -> httpx.Client:
        return real(**kwargs, transport=httpx.MockTransport(answer))

    monkeypatch.setattr(commands.httpx, "Client", client)
    result = CliRunner().invoke(cli, ["demo", "agent-simple-question"])
    assert result.exit_code == 1 and "Traceback" not in result.output
    assert result.output.strip().splitlines()[-1] == (
        f"x agent-simple-question: {sessions.NO_SESSION}"
    )


def test_a_misspelled_demo_name_prints_one_line_with_the_valid_names() -> None:
    result = CliRunner().invoke(cli, ["demo", "agent-simple-questoin"])
    assert result.exit_code == 1 and "Traceback" not in result.output
    lines = result.output.strip().splitlines()
    assert len(lines) == 1 and lines[0].startswith("x no demo named 'agent-simple-questoin'")
    assert all(demo.id in lines[0] for demo in registries.demos().demos)


@pytest.mark.parametrize("command", ["reset", "reset-discarding-baseline", "open-code"])
def test_a_misspelled_section_name_prints_one_line_with_the_valid_names(command: str) -> None:
    result = CliRunner().invoke(cli, [command, "agent"])
    assert result.exit_code == 1 and "Traceback" not in result.output
    lines = result.output.strip().splitlines()
    assert len(lines) == 1 and lines[0].startswith("x no section named 'agent'")
    assert all(section.slug in lines[0] for section in SECTIONS)
