"""The Agent and Verify pages show the waiting line only while a run works; a run holding for
approval says it waits for a person, and a queued run that it waits for a worker."""

from __future__ import annotations

import sys

import pytest

from datapilot.contracts.lifecycle import RunStatus
from datapilot.settings import PLATFORM

CONSOLE = PLATFORM / "console"
if str(CONSOLE) not in sys.path:
    sys.path.insert(0, str(CONSOLE))

from datapilot_console import views  # noqa: E402

RUNNING = "Running the agent and the graders. This takes 5 to 15 seconds."


# --- The waiting line only while the run works --------------------------------------------


@pytest.mark.parametrize("status", [RunStatus.RUNNING, RunStatus.VERIFYING])
def test_the_waiting_line_shows_while_the_run_works(status: RunStatus) -> None:
    assert views.waiting_line(status, RUNNING) == RUNNING


def test_a_run_holding_for_approval_says_it_waits_for_a_person() -> None:
    line = views.waiting_line(RunStatus.AWAITING_APPROVAL, RUNNING)
    assert line is not None and line != RUNNING
    assert "approval" in line and "person" in line
    assert "seconds" not in line


@pytest.mark.parametrize("status", [RunStatus.RECEIVED, RunStatus.QUEUED])
def test_a_queued_run_says_it_waits_for_a_worker(status: RunStatus) -> None:
    line = views.waiting_line(status, RUNNING)
    assert line is not None and "worker" in line and "seconds" not in line


@pytest.mark.parametrize(
    "status", [RunStatus.ANSWERED, RunStatus.POSTED, RunStatus.FAILED, RunStatus.ESCALATED]
)
def test_a_finished_run_has_no_waiting_line(status: RunStatus) -> None:
    assert views.waiting_line(status, RUNNING) is None
