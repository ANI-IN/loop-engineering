"""The business date: the one place DataPilot decides what "today" means for business logic.

The warehouse ends on 31 January 2026 and class runs later, so "yesterday", "last month", "this
quarter", the 8 a.m. digest, every scheduled job, and fresh demo orders resolve against
DATAPILOT_BUSINESS_DATE, never the system clock. Real-time timestamps (when a run started) use
datetime.now(UTC) and are not business logic; a unit test fails if business logic reads the clock.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from datapilot.settings import get_settings

EASTERN = ZoneInfo("America/New_York")


def today() -> date:
    return get_settings().datapilot_business_date


def yesterday() -> date:
    return today() - timedelta(days=1)


def at_eastern(day: date, hour: int = 0, minute: int = 0) -> datetime:
    """A moment on a business day in Eastern time, as an aware datetime (for fresh orders)."""
    return datetime.combine(day, time(hour, minute), tzinfo=EASTERN)


def prompt_line() -> str:
    """The sentence the analyst's system prompt carries."""
    return f"Today's business date is {today():%A, %d %B %Y}; resolve relative dates against it."


def status_label() -> str:
    """The console status line text, such as "Business date: 31 January 2026"."""
    day = today()
    return f"Business date: {day.day} {day:%B %Y}"
