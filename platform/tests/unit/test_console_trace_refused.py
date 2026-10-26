"""A run whose trace LangSmith refused (its free plan's monthly limit, ops.runs.trace_refused_at)
shows "Trace not received (LangSmith monthly limit)" in the muted style in place of a trace link
that would lead nowhere, and keeps its run label, the proof of the run (finding F022)."""

from __future__ import annotations

import re
import sys
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from datapilot.settings import PLATFORM

CONSOLE = PLATFORM / "console"
if str(CONSOLE) not in sys.path:
    sys.path.insert(0, str(CONSOLE))

from datapilot_console import views  # noqa: E402

COMPONENTS = CONSOLE / "datapilot_console" / "components"
STARTED = datetime(2026, 10, 22, 11, 59, 9, tzinfo=UTC)
SESSION = uuid.uuid4()
TRACE = "https://smith.example/r"


def _run(refused_at: datetime | None, status: str = "posted") -> dict[str, Any]:
    return {
        "run_id": uuid.UUID("1a2b3c4d-0000-4000-8000-000000000000"),
        "question": "How many orders?",
        "status": status,
        "autonomy_level_applied": "report_only",
        "langsmith_url": TRACE,
        "trace_refused_at": refused_at,
        "created_at": STARTED,
        "started_at": STARTED,
        "last_event": None,
    }


def test_a_refused_trace_shows_the_words_and_the_run_label_never_the_link() -> None:
    shown = views.run_stamp(_run(STARTED + timedelta(seconds=40)), SESSION)
    assert shown["trace_url"] is None
    assert shown["trace_note"] == "Trace not received (LangSmith monthly limit)"
    assert shown["run_label"] == "Run 1a2b3c4d"
    assert shown["run_id"] == "1a2b3c4d-0000-4000-8000-000000000000"
    assert shown["started_at_utc"] == "2026-10-22T11:59:09+00:00"


def test_a_trace_with_no_refusal_keeps_its_link_and_adds_nothing() -> None:
    shown = views.run_stamp(_run(None), SESSION)
    assert shown["trace_url"] == TRACE
    assert "trace_note" not in shown and "run_label" not in shown


def test_a_run_row_without_the_column_keeps_its_link() -> None:
    row = _run(None)
    del row["trace_refused_at"]
    assert views.run_stamp(row, SESSION)["trace_url"] == TRACE


def test_the_run_board_strip_carries_the_refused_stamp() -> None:
    strip = views.strip_view(_run(STARTED), SESSION)
    assert strip["label"] == strip["stamp"]["run_label"] == "Run 1a2b3c4d"
    assert strip["stamp"]["trace_url"] is None
    assert strip["stamp"]["trace_note"] == views.TRACE_REFUSED


def test_the_run_detail_sql_header_carries_the_refused_stamp() -> None:
    view = views.sql_view(
        "SELECT 1", [], stamp=views.run_stamp(_run(STARTED), SESSION), display_tz=None
    )
    assert view["stamp"]["trace_url"] is None
    assert view["stamp"]["trace_note"] == views.TRACE_REFUSED


def test_the_stamp_shows_the_words_muted_in_place_of_the_link() -> None:
    js = (COMPONENTS / "base.js").read_text("utf-8")
    body = js[js.index("function stampLine") :]
    body = body[: body.index("\n}\n")]
    # The refusal is checked first, so a refused stamp never builds a link.
    assert body.index("stamp.trace_note") < body.index("stamp.trace_url")
    assert "el('span', 'trace-note', stamp.trace_note)" in body
    assert "el('span', 'run-label', stamp.run_label)" in body
    css = (COMPONENTS / "base.css").read_text("utf-8")
    # Muted: the design system's graphite through the theme variable, never a hex value.
    assert re.search(r"\.trace-note \{ color: var\(--graphite\); \}", css)
    assert ".stamp.refused { white-space: normal; }" in css
    assert ".run-label { white-space: nowrap; }" in css
