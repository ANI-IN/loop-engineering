"""The in-app channel: posts in ops.posts, which the console shows."""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from datapilot.config import pack_config


def post(
    conn: psycopg.Connection[Any], *, run_id: str, event_id: str | None, label: str, body: dict
) -> int:
    row = conn.execute(
        "INSERT INTO ops.posts (channel, run_id, event_id, label, body) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING post_id",
        (pack_config()["channel"], run_id, event_id, label, Jsonb(body)),
    ).fetchone()
    return int(row["post_id"])
