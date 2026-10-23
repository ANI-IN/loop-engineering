"""A holdout ledger row whose trace is not written yet shows no stray "None" in the trace column."""

from __future__ import annotations

import sys

from datapilot.settings import PLATFORM

CONSOLE = PLATFORM / "console"
if str(CONSOLE) not in sys.path:
    sys.path.insert(0, str(CONSOLE))

# --- A ledger row with no trace yet shows no "None" ----------------------------------------


def test_a_ledger_row_without_a_trace_shows_no_none() -> None:
    js = (CONSOLE / "datapilot_console" / "components" / "holdout_ledger.js").read_text("utf-8")
    assert "'None'" not in js and '"None"' not in js
    assert "Trace pending" in js
