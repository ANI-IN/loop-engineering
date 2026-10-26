"""The daily token budget (pack budgets.tokens_per_day) per Eastern time calendar day."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import psycopg

from datapilot.config import pack_config

EASTERN = ZoneInfo("America/New_York")


def eastern_day(now: datetime | None = None) -> date:
    return (now or datetime.now(EASTERN)).astimezone(EASTERN).date()


@dataclass(frozen=True)
class DayBudget:
    day: date
    used: int
    cap: int

    @property
    def left(self) -> int:
        return max(0, self.cap - self.used)


def today(conn: psycopg.Connection[Any], now: datetime | None = None) -> DayBudget:
    """The Eastern time day's count, read without creating its row: before the day's first worker
    run there is none, so nothing is used yet and the cap is the pack's."""
    day = eastern_day(now)
    row = conn.execute(
        "SELECT tokens_used, token_limit FROM ops.budgets WHERE day = %s", (day,)
    ).fetchone()
    if row is None:
        return DayBudget(day, 0, int(pack_config()["budgets"]["tokens_per_day"]))
    return DayBudget(day, int(row["tokens_used"]), int(row["token_limit"]))


def until_next_day(now: datetime | None = None) -> timedelta:
    """The time until midnight Eastern time, when the next day's count starts at zero."""
    here = (now or datetime.now(EASTERN)).astimezone(EASTERN)
    midnight = datetime.combine(here.date() + timedelta(days=1), datetime.min.time(), EASTERN)
    # subtracted in UTC, so a clock change before midnight is counted
    return midnight.astimezone(UTC) - here.astimezone(UTC)


def _ensure(conn: psycopg.Connection[Any], day: date) -> None:
    conn.execute(
        "INSERT INTO ops.budgets (day, token_limit) VALUES (%s, %s) ON CONFLICT (day) DO NOTHING",
        (day, int(pack_config()["budgets"]["tokens_per_day"])),
    )


def exhausted(conn: psycopg.Connection[Any], day: date | None = None) -> bool:
    day = day or eastern_day()
    _ensure(conn, day)
    row = conn.execute(
        "SELECT tokens_used >= token_limit AS spent FROM ops.budgets WHERE day = %s", (day,)
    ).fetchone()
    return bool(row and row["spent"])


def add_usage(conn: psycopg.Connection[Any], tokens: int, day: date | None = None) -> None:
    day = day or eastern_day()
    _ensure(conn, day)
    conn.execute(
        "UPDATE ops.budgets SET tokens_used = tokens_used + %s WHERE day = %s", (tokens, day)
    )
