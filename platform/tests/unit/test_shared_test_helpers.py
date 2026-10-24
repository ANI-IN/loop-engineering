"""The shared test helpers in platform/tests/conftest.py: a scan of a missing folder fails, command
output is plain text under continuous integration, a planted flag exported in the shell never
reaches a test, and no test without the live marker reaches OpenAI or LangSmith."""

from __future__ import annotations

import os
import socket
import subprocess
import sys

import conftest
import pytest
from conftest import scan
from typer.testing import CliRunner

from datapilot.cli import app
from datapilot.planted import planted
from datapilot.settings import REPO


def test_a_scan_of_a_missing_folder_fails_instead_of_passing_on_nothing() -> None:
    with pytest.raises(FileNotFoundError, match="platform/no-such-folder"):
        scan("anything", "platform/no-such-folder")


def test_help_text_is_plain_when_continuous_integration_forces_a_terminal(monkeypatch) -> None:
    # Typer forces a terminal when GITHUB_ACTIONS or FORCE_COLOR is set, read once at import.
    import typer.rich_utils

    monkeypatch.setattr(typer.rich_utils, "FORCE_TERMINAL", True)
    result = CliRunner().invoke(app, ["preflight", "--help"])
    assert result.exit_code == 0
    assert "\x1b[" not in result.output and "--purpose" in result.output


def test_planted_flags_exported_in_the_shell_never_reach_a_test() -> None:
    assert not any(planted(flag) for flag in ["BUG_NAIVE_GUARD", "BUG_NO_COST_GUARD"])
    assert not planted("DEMO_PACING")


@pytest.mark.slow
def test_the_fixed_path_tests_pass_with_every_planted_flag_exported() -> None:
    # A real run of one fixed-path test with the planted flags exported, as after a rehearsal.
    from datapilot.contracts import registries

    env = {**os.environ, **dict.fromkeys([*registries.planted().flags, "DEMO_PACING"], "1")}
    target = (
        "platform/tests/unit/test_loops_graders.py::"
        "test_cost_grader_rejects_a_join_without_a_condition_before_explain"
    )
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", target],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout[-2000:]
    assert "1 passed" in result.stdout


@pytest.mark.parametrize("host", ["api.openai.com", "api.smith.langchain.com", "eu.langsmith.com"])
def test_a_test_without_the_live_marker_cannot_reach_openai_or_langsmith(host: str) -> None:
    before = len(conftest.reached_hosts)
    with pytest.raises(OSError, match="live marker"):
        socket.getaddrinfo(host, 443)
    assert conftest.reached_hosts[before:] == [(conftest._running["test"], host)]
    del conftest.reached_hosts[before:]  # recorded as it must be; cleared so this test passes


def test_other_hosts_resolve_as_before() -> None:
    assert socket.getaddrinfo("127.0.0.1", 80)
    assert not conftest.MODEL_AND_TRACING_HOSTS.search("langchain.com.example.org")
