"""The daily token budget (pack budgets.tokens_per_day) per Eastern time calendar day."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import psycopg

from datapilot.config import pack_config

EASTERN = ZoneInfo("America/New_York")


def eastern_day(now: datetime | None = None) -> date:
    return (now or datetime.now(EASTERN)).astimezone(EASTERN).date()


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
