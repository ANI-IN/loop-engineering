"""The live-only contract: every demo result is a fresh run of the current live session.

Sessions:
- `make preflight` starts a new live session automatically once every one of its checks passes,
  and ends the previous one. Everything until the next preflight belongs to that session.
- The class, every rehearsal, and the Thursday review each start their own session through their
  own preflight (`make preflight PURPOSE=class|rehearsal|thursday-review|development`).
- The console's status line shows the open session's start time; with no open session it says so
  and tells the instructor to run `make preflight`.

Times: services run in Docker on universal time, so the server never formats a time as "local
time". It sends UTC timestamps (ISO 8601); the console's components format them in the browser
with the viewer's time zone (or DATAPILOT_DISPLAY_TIMEZONE when set). The status line says once,
"Times are in your local time"; a strip reads "Started 11:59:09. Open trace". A rehearsal check
confirms the console's times match the instructor's clock.

Results:
- A result shown in a demo path carries a LiveStamp: its run id, when it started (UTC, formatted
  in the browser), and its LangSmith trace link.
- The console shows only runs and experiments of the open session; the baseline experiment must be
  one started in that session (NoLiveBaseline otherwise), never an older run.
- Demo code never reuses model outputs, answers, grader or reviewer verdicts, analyzer proposals,
  or experiment results from earlier runs, and never reaches test doubles or recorded runs; the
  live-only unit tests enforce it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class SessionPurpose(StrEnum):
    CLASS = "class"
    REHEARSAL = "rehearsal"
    THURSDAY_REVIEW = "thursday-review"
    DEVELOPMENT = "development"


class LiveSession(BaseModel):
    session_id: UUID
    purpose: SessionPurpose
    started_at: datetime
    started_by: str
    timezone: str  # the zone of the machine that ran preflight, kept for the record

    def to_browser(self) -> dict[str, str]:
        """What the status line component receives; it formats started_at in the browser."""
        return {"session_id": str(self.session_id), "started_at_utc": _iso(self.started_at)}


class LiveStamp(BaseModel):
    run_id: UUID
    session_id: UUID
    started_at: datetime
    trace_url: str | None

    def to_browser(self) -> dict[str, str | None]:
        """What a component receives; it shows "Started 11:59:09. Open trace" in local time."""
        return {
            "run_id": str(self.run_id),
            "started_at_utc": _iso(self.started_at),
            "trace_url": self.trace_url,
        }


def _iso(moment: datetime) -> str:
    if moment.tzinfo is None:
        raise ValueError("live timestamps must be time-zone aware (UTC)")
    return moment.astimezone(UTC).isoformat(timespec="seconds")


class NoLiveSession(LookupError):
    """No live session is open: run `make preflight` first."""


class NoLiveBaseline(LookupError):
    """No baseline experiment was started in the current live session. The console says so
    plainly and offers to start one; it never falls back to an older run."""
