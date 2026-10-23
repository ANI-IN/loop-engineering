"""What every page shares: the database pool, the api client, and the one live fragment.

Each page passes its body to `live_page`. The fragment reruns every console.poll_seconds, opens one
pooled connection, reads the open session and a watermark, draws the status line, then the body.
Views are rebuilt only when the watermark (or a page's own switch) changes; otherwise the same
data goes back to the components, which then leave their DOM alone.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
import streamlit as st
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolTimeout

from datapilot import business_date, db
from datapilot.config import pack_config
from datapilot.contracts import registries
from datapilot.contracts.live import LiveSession
from datapilot.settings import get_settings
from datapilot_console import components, ops_reads, views
from datapilot_console.api_client import API_DOWN, ApiClient, ApiError

LIMITS: dict[str, int] = dict(pack_config()["console"])
DB_DOWN = "The ops database did not answer. Start it with make up, then reload this page."
NO_SESSION = "No live session. Run make preflight to start one."


@st.cache_resource
def db_pool() -> ConnectionPool:
    """One small pool of app-role connections for the whole console process."""
    return ConnectionPool(
        db.url_for(db.Role.APP),
        min_size=1,
        max_size=10,
        timeout=2.0,
        open=True,
        kwargs={"row_factory": dict_row, "autocommit": True, "prepare_threshold": 0},
    )


SESSION_PURPOSE = "session-purpose"  # the open live session's purpose, kept by each fragment run


def api() -> ApiClient:
    return ApiClient.from_settings(st.session_state.get(SESSION_PURPOSE))


def display_tz() -> str | None:
    return get_settings().datapilot_display_timezone or None


def check_api() -> None:
    """On a full page run only (never in the timed fragment): does the api answer?"""
    ok = api().healthy()
    st.session_state["api-notice"] = "" if ok else API_DOWN


def act(action: Callable[[], Any]) -> Any:
    """Run one api action; on failure, say what happened and what to do, in the status line and
    under the control."""
    try:
        result = action()
    except ApiError as error:
        st.session_state["api-notice"] = str(error) if str(error) == API_DOWN else ""
        st.session_state["action-error"] = str(error)
        return None
    st.session_state["api-notice"] = ""
    st.session_state["action-error"] = ""
    return result


def show_action_error() -> None:
    message = st.session_state.get("action-error")
    if message:
        st.error(message)


@dataclass
class Live:
    """One fragment run: a connection, the open session, and whether anything changed."""

    conn: psycopg.Connection[Any]
    session: LiveSession | None
    changed: bool

    @property
    def session_id(self) -> Any:
        return self.session.session_id if self.session else None

    def view(self, key: str, build: Callable[[], Any], *depends: Hashable) -> Any:
        """The page's view `key`, rebuilt only when ops changed or one of `depends` did."""
        ss = st.session_state
        token = (key, depends)
        if self.changed or ss.get(f"view-token:{key}") != token or f"view:{key}" not in ss:
            ss[f"view:{key}"] = build()
            ss[f"view-token:{key}"] = token
        return ss[f"view:{key}"]


def _stop_all() -> None:
    act(api().stop_all)


def _release() -> None:
    act(lambda: api().kill_switch("release"))


def _status_view(live: Live) -> dict[str, Any]:
    state = ops_reads.status(live.conn, live.session_id)
    chips = {item.id: item.chip for item in registries.planted().items}
    pack = pack_config()
    return views.status_line_view(
        session=live.session,
        business_date=business_date.status_label(),
        display_tz=display_tz(),
        state=state,
        families=list(pack["autonomy"]["metric_families"]),
        tokens_cap_default=int(pack["budgets"]["tokens_per_day"]),
        planted_chips=chips,
        pacing_seconds=get_settings().demo_pacing_seconds,
        disarm_seconds=LIMITS["kill_switch_disarm_seconds"],
        notice=st.session_state.get("api-notice", ""),
    )


def draw_status_line(data: dict[str, Any]) -> None:
    components.status_line(data, on_stop_all=_stop_all, on_release=_release)


def live_page(page: str, body: Callable[[Live], None]) -> None:
    """Run `body` inside the page's one timed fragment, under the status line."""

    @st.fragment(run_every=LIMITS["poll_seconds"])
    def tick() -> None:
        started = time.perf_counter()
        ss = st.session_state
        try:
            with db_pool().connection() as conn:
                session = views.session_model(ops_reads.open_session(conn))
                sid = session.session_id if session else None
                ss[SESSION_PURPOSE] = session.purpose.value if session else None
                mark = ops_reads.watermark(conn, sid)
                changed = ss.get(f"watermark:{page}") != mark
                ss[f"watermark:{page}"] = mark
                live = Live(conn, session, changed)
                notice = ss.get("api-notice", "")
                draw_status_line(live.view("status-line", lambda: _status_view(live), notice))
                body(live)
        except (psycopg.OperationalError, PoolTimeout):
            draw_status_line(_offline_status())
            st.error(DB_DOWN)
        _probe(page, time.perf_counter() - started)

    tick()


def _offline_status() -> dict[str, Any]:
    pack = pack_config()
    state = {
        "kill_switch": "released",
        "autonomy_level": pack["autonomy"]["default_level"],
        "family_levels": {},
        "tokens_used": 0,
        "token_limit": None,
        "planted_active": [],
    }
    return views.status_line_view(
        session=None,
        business_date=business_date.status_label(),
        display_tz=display_tz(),
        state=state,
        families=list(pack["autonomy"]["metric_families"]),
        tokens_cap_default=int(pack["budgets"]["tokens_per_day"]),
        planted_chips={},
        pacing_seconds=None,
        disarm_seconds=LIMITS["kill_switch_disarm_seconds"],
        notice=DB_DOWN,
    )


def _probe(page: str, seconds: float) -> None:
    """With DATAPILOT_CONSOLE_PROBE=<file>, append each fragment run's duration (the fit and
    timing checks read it); otherwise nothing."""
    target = os.environ.get("DATAPILOT_CONSOLE_PROBE")
    if target:
        with Path(target).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"page": page, "seconds": round(seconds, 4)}) + "\n")
