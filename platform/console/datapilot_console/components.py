"""The console's four custom components (components v2, inline HTML, CSS, and JS).

The status line with the guarded kill switch, the run board, the annotated SQL, and the holdout
ledger. Sources sit beside this file in components/<name>.{html,css,js}; base.css and base.js hold
the shared tokens, shapes, and helpers and are prepended to each one. No bundler, no build step.
They read Streamlit's theme variables, so .streamlit/config.toml drives them and native widgets
alike. They build their DOM once, update it in place, and write user text with textContent only.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import streamlit as st

_ASSETS = Path(__file__).resolve().parent / "components"


def _asset(name: str) -> str:
    return (_ASSETS / name).read_text(encoding="utf-8")


def _register(name: str) -> Any:
    return st.components.v2.component(
        f"datapilot_console_{name}",
        html=_asset(f"{name}.html"),
        css=_asset("base.css") + _asset(f"{name}.css"),
        js=_asset("base.js") + _asset(f"{name}.js"),
    )


_status_line = _register("status_line")
_run_board = _register("run_board")
_annotated_sql = _register("annotated_sql")
_holdout_ledger = _register("holdout_ledger")


def status_line(
    data: dict[str, Any],
    *,
    on_stop_all: Callable[[], None],
    on_release: Callable[[], None],
    key: str = "status-line",
) -> Any:
    return _status_line(
        key=key, data=data, on_stop_all_change=on_stop_all, on_release_change=on_release
    )


def run_board(
    data: dict[str, Any],
    *,
    on_review: Callable[[], None],
    on_toggle_ledger: Callable[[], None],
    key: str = "run-board",
) -> Any:
    return _run_board(
        key=key, data=data, on_review_change=on_review, on_toggle_ledger_change=on_toggle_ledger
    )


def annotated_sql(data: dict[str, Any], *, key: str) -> Any:
    return _annotated_sql(key=key, data=data)


def holdout_ledger(data: dict[str, Any], *, on_start_baseline: Callable[[], None], key: str) -> Any:
    return _holdout_ledger(key=key, data=data, on_start_baseline_change=on_start_baseline)
