"""The Improve page shows a gate that is ready for human approval as its own state, not as a red
block; red "blocked" only when the gate blocked the candidate."""

from __future__ import annotations

import sys

from datapilot.settings import PLATFORM

CONSOLE = PLATFORM / "console"
if str(CONSOLE) not in sys.path:
    sys.path.insert(0, str(CONSOLE))

from datapilot_console import views, widgets  # noqa: E402

# --- Ready for human approval is its own state, not a red block ---------------------------

READY = "Ready for human approval: v2 passes 9 of 15 holdout items against 6, with no regressions."
BLOCKED = "Blocked: v2 has 1 regression on items that passed under v1."
PROMOTED = (
    "Promoted: v2 passes 9 of 15 holdout items against 6, with no regressions, approved by ani."
)


def test_a_gate_ready_for_approval_is_not_shown_as_blocked() -> None:
    gate = views.gate_view("blocked", READY)
    assert gate["state"] == "ready"
    line = widgets.gate_line(gate)
    assert "Gate: ready for human approval." in line
    assert ":red[" not in line and "blocked" not in line.lower()
    assert line.count("Ready for human approval") == 0


def test_only_a_gate_that_blocked_the_candidate_is_red() -> None:
    gate = views.gate_view("blocked", BLOCKED)
    assert gate["state"] == "blocked"
    line = widgets.gate_line(gate)
    assert line.startswith(":red[") and "Gate: blocked." in line
    assert "Blocked: " not in line, "the gate word is not repeated"


def test_a_promoting_gate_is_green() -> None:
    gate = views.gate_view("promoted", PROMOTED)
    assert gate["state"] == "promoted"
    line = widgets.gate_line(gate)
    assert line.startswith(":green[") and "Gate: passed." in line
