"""The console in a real browser against seeded ops rows: screenshots of every page and state,
the Events page fit, and 15 seconds of one-second updates without a remount or greying.

A test launch: this file starts Streamlit on platform/console/app.py with a stub health api (test
code), seeds ops rows with console_seed, and drives headless Chromium with Playwright. Like every
test, it reaches only the tests' own database (port 55432), never the live stack; there it ends
the open session that the rest of the integration suite shares, and it rewrites the tracked
screenshots, so it runs only when asked, under the tests' database lock:

    make test-console

Screenshots go to platform/console/screenshots/; measurements to screenshots/measurements.json.
Each is the whole viewport at device scale factor 2 (1280 by 720 CSS pixels give 2560 by 1440), in
Coordinated Universal Time, nudged by the capture kit's framing so no edge cuts a line of text
(docs/STYLE.md). The fit checks' own screenshots (1280 by 600 among them) are measurements, not
published images: they go to .runs/console-fit/, outside the published image folders.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import console_seed as seed
import httpx
import pytest

from datapilot import db
from datapilot.settings import PLATFORM, REPO

sys.path.insert(0, str(PLATFORM / "scripts" / "kit" / "capture"))
import framing  # noqa: E402  (the capture kit: whole-viewport frames with clean edges)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.skipif(
        os.environ.get("DATAPILOT_CONSOLE_SCREENSHOTS") != "1",
        reason="ends the open session on the tests' own database and rewrites the tracked "
        "screenshots; run it with make test-console",
    ),
]

CONSOLE = PLATFORM / "console"
SHOTS = CONSOLE / "screenshots"
FIT_SHOTS = REPO / ".runs" / "console-fit"
# Streamlit's own frontend probes these under each page path and gets 404; not the console's.
STREAMLIT_PROBES = ("/_stcore/health", "/_stcore/host-config")
MEASURES: dict[str, Any] = {}
OPEN_CONTEXTS: list[Any] = []


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class StubApi(BaseHTTPRequestHandler):
    """Answers /health, records every action; with `down` set it hangs up on every request."""

    calls: list[str] = []
    down = False

    def _reply(self, body: dict[str, Any]) -> None:
        if StubApi.down:
            self.close_connection = True
            return
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802 (http.server's name)
        self._reply({"status": "ok"})

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(length)
        StubApi.calls.append(self.path)
        # A valid contracts.api EventSubmitted: the console client validates every reply.
        self._reply(
            {
                "event_id": "stub",
                "run_id": str(uuid.uuid4()),
                "job_id": 1,
                "duplicate": False,
                "duplicates_ignored": 0,
                "created_at": "2026-10-22T11:59:09+00:00",
            }
        )

    def log_message(self, *args: Any) -> None:
        return


@pytest.fixture(scope="module")
def stub_api() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", _free_port()), StubApi)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


@pytest.fixture(scope="module")
def probe_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("console") / "probe.jsonl"


@pytest.fixture(scope="module")
def console(stub_api: str, probe_file: Path) -> Iterator[str]:
    port = _free_port()
    env = {
        **os.environ,
        "DATAPILOT_API_URL": stub_api,
        "DATAPILOT_CONSOLE_PROBE": str(probe_file),
        "PYTHONUTF8": "1",
    }
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app.py",
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--server.fileWatcherType",
            "none",
        ],
        cwd=CONSOLE,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"{url}/_stcore/health", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.5)
    else:
        process.kill()
        pytest.fail("the console did not start within 60 seconds")
    yield url
    process.kill()
    process.wait(timeout=10)


@pytest.fixture(scope="module")
def conn() -> Iterator[Any]:
    with db.connect(db.Role.APP, autocommit=True) as connection:
        yield connection
        seed.end_sessions(connection)
        seed.clear_budget(connection)
        seed.set_control(connection, level="report_only")


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as playwright:
        chromium = playwright.chromium.launch()
        yield chromium
        chromium.close()


def _page(browser: Any, width: int = 1280, height: int = 720, scale: float = 2.0) -> Any:
    context = browser.new_context(
        viewport={"width": width, "height": height},
        device_scale_factor=scale,
        timezone_id=framing.TIMEZONE,
    )
    OPEN_CONTEXTS.append(context)
    page = context.new_page()
    page.errors = []
    page.on("console", lambda m: page.errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    page.on(
        "response",
        lambda r: (
            page.errors.append(f"{r.status} {r.url}")
            if r.status >= 400 and not r.url.endswith(STREAMLIT_PROBES)
            else None
        ),
    )
    return page


@pytest.fixture(autouse=True)
def close_pages() -> Iterator[None]:
    """One browser tab at a time, as in class: every page a test opened closes after it."""
    yield
    while OPEN_CONTEXTS:
        OPEN_CONTEXTS.pop().close()


def _open(page: Any, console: str, path: str, ready: str) -> None:
    page.goto(f"{console}/{path}")
    page.locator(ready).first.wait_for(timeout=30_000)
    time.sleep(2.5)  # two fragment ticks: every component has its current data


def _shot(page: Any, name: str) -> None:
    """A published screenshot: the page from its top, nudged so no edge cuts a line of text."""
    SHOTS.mkdir(exist_ok=True)
    data, _edges, _nudge = framing.settle(page, 0, nudges=framing.PAGE_TOP_NUDGES)
    (SHOTS / f"{name}.png").write_bytes(data)


def _fit_shot(page: Any, name: str) -> None:
    """A fit check's screenshot, as the page is (never scrolled): a measurement, not published."""
    FIT_SHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=FIT_SHOTS / f"{name}.png")


def _text(page: Any) -> str:
    """Every visible word on the page, including inside the components' shadow roots."""
    return page.evaluate(
        "() => [document.body.innerText, ...[...document.querySelectorAll('*')]"
        ".filter(e => e.shadowRoot).map(e => e.shadowRoot.textContent)].join(' ')"
    )


def _real_errors(page: Any) -> list[str]:
    # Streamlit's frontend logs its own base-path probes as resource 404s without a URL; every
    # other failed request is caught with its URL by the response listener.
    return [
        e
        for e in page.errors
        if e != "Failed to load resource: the server responded with a status of 404 (Not Found)"
    ]


def _fit(page: Any) -> dict[str, Any]:
    status = page.locator(".sl").bounding_box()
    off = page.locator(".offwrap").bounding_box()
    lanes = page.locator(".lanes").bounding_box()
    scrolled = page.evaluate(
        "() => [...document.querySelectorAll('*')].map(e => e.shadowRoot).filter(Boolean)"
        ".flatMap(r => [...r.querySelectorAll('.lane > .list')])"
        ".filter(l => l.scrollHeight > l.clientHeight + 1).length"
    )
    height = page.evaluate("() => window.innerHeight")
    return {
        "viewport_height": height,
        "status_line": [round(status["y"]), round(status["y"] + status["height"])],
        "lanes_end": round(lanes["y"] + lanes["height"]),
        "off_board_end": round(off["y"] + off["height"]),
        # Streamlit scrolls an inner container, not the window: take the largest scroll offset.
        "page_scroll_y": page.evaluate(
            "() => Math.max(window.scrollY, ...[...document.querySelectorAll('*')]"
            ".map(e => e.scrollTop))"
        ),
        "lanes_scrolling_inside": scrolled,
        "fits": off["y"] + off["height"] <= height and status["y"] >= 0,
    }


def test_empty_states(console: str, conn: Any, browser: Any) -> None:
    seed.end_sessions(conn)
    page = _page(browser)
    _open(page, console, "events", ".board")
    _shot(page, "events-no-session")
    assert "No live session. Run make preflight to start one." in _text(page)
    seed.open_session(conn)
    seed.ensure_versions(conn)
    _open(page, console, "", ".sl")
    _shot(page, "agent-empty")
    assert "Ask a question to see the tool calls" in _text(page)
    _open(page, console, "improve", ".nobase")
    _shot(page, "improve-no-baseline")
    body = _text(page)
    assert "No baseline run in this session yet." in body
    assert body.count("Run experiment on the active version") == 1
    assert _real_errors(page) == []


def test_pages_live(console: str, conn: Any, browser: Any) -> None:
    session = seed.open_session(conn, started_at=seed.now() - seed.timedelta(minutes=20))
    seed.events_scene(conn, session)
    seed.improve_scene(conn, session)
    seed.agent_scene(conn, session)
    seed.verify_scene(conn, session, "malicious")
    page = _page(browser)
    _open(page, console, "verify", ".sl")
    _shot(page, "verify-malicious-sql")
    seed.verify_scene(conn, session, "retry")
    time.sleep(2)
    _shot(page, "verify-retry-cap")
    assert "Stopped at the cap: escalated" in _text(page)
    _open(page, console, "", ".asql")
    _shot(page, "agent-confident-wrong-answer")
    assert "Trap: Net revenue" in _text(page)
    _open(page, console, "improve", ".ledger")
    _shot(page, "improve-ledger")
    assert "Regression" in _text(page) and "Gate: blocked." in _text(page)
    page.set_viewport_size({"width": 1280, "height": 720})
    _open(page, console, "events", ".strip")
    _shot(page, "events-live-1280x720")
    assert "2 duplicates absorbed" in _text(page)
    assert _real_errors(page) == []


@pytest.mark.parametrize("height", [720, 600])
def test_events_fit(console: str, conn: Any, browser: Any, height: int) -> None:
    page = _page(browser, height=height)
    _open(page, console, "events", ".strip")
    off = _fit(page)
    _fit_shot(page, f"events-fit-1280x{height}")
    page.locator("button.kill").click()
    time.sleep(0.5)
    armed = _fit(page)
    _fit_shot(page, f"events-fit-1280x{height}-kill-armed")
    page.keyboard.press("Escape")
    MEASURES[f"1280x{height}"] = {"kill switch disarmed": off, "kill switch armed": armed}
    assert off["fits"] and armed["fits"], MEASURES
    assert off["page_scroll_y"] == 0 and armed["page_scroll_y"] == 0


def test_events_fit_at_67_percent_zoom(console: str, browser: Any) -> None:
    # A 1280 by 720 screen at 67 percent zoom shows 1910 by 1075 CSS pixels; at twice that
    # screen's pixels the image is 2560 by 1440, as every published screenshot.
    page = _page(browser, width=1910, height=1075, scale=2 * 1280 / 1910)
    _open(page, console, "events", ".strip")
    found = _fit(page)
    _shot(page, "events-67-percent")
    MEASURES["67 percent zoom (1910x1075)"] = found
    assert found["fits"]


def test_kill_switch_engaged_and_api_down(console: str, conn: Any, browser: Any) -> None:
    seed.set_control(conn, kill_switch="engaged", level="report_only")
    page = _page(browser)
    _open(page, console, "events", ".strip")
    MEASURES["1280x720, kill switch engaged"] = _fit(page)  # before the frame is nudged
    _shot(page, "events-kill-engaged")
    assert "Kill switch engaged." in _text(page)
    seed.set_control(conn, level="assisted")
    StubApi.down = True
    try:
        _open(page, console, "events", ".strip")
        _shot(page, "events-api-down")
        assert "The api did not answer. Start it with make up." in _text(page)
    finally:
        StubApi.down = False


def test_the_capture_runner_frame_rules_on_the_real_console(
    console: str, conn: Any, browser: Any
) -> None:
    """The live capture runner's refusals, in a real browser (live, 24 October: every Section 1
    image showed Streamlit's "Page not found" dialog, opened at /agent; Channel frames missed the
    post)."""
    import live_manifest as manifest

    session = seed.open_session(conn, started_at=seed.now() - seed.timedelta(minutes=5))
    seed.events_scene(conn, session)
    page = _page(browser)
    _open(page, console, "agent", ".sl")
    assert any(found.startswith("a dialog") for found in framing.blockers(page))
    _open(page, console, manifest.page_path("agent"), ".sl")
    assert framing.blockers(page) == []
    _open(page, console, manifest.page_path("events"), ".strip")
    framing.framed_screenshot(page)  # the page's top: the Channel is below the frame
    assert framing.out_of_frame(page, [manifest.STATUS_LINE]) == []
    assert framing.out_of_frame(page, [manifest.CHANNEL]) == [manifest.CHANNEL]
    _data, edges = framing.framed_screenshot(page, top=manifest.CHANNEL)
    assert edges.clean
    assert framing.out_of_frame(page, [manifest.CHANNEL]) == []
    assert framing.out_of_frame(page, ["#no-such-element"]) == ["#no-such-element"]


def test_buttons_call_the_api(console: str, conn: Any, browser: Any) -> None:
    # Its own scene. The scene clears revenue for the unattended level, so the button sends the
    # finale, which since review round 2 waits for the system's unattended level, as
    # `make demo NAME=improve-cleared-unattended` does: set it, so the button is enabled.
    session = seed.open_session(conn, started_at=seed.now() - seed.timedelta(minutes=5))
    seed.events_scene(conn, session)
    seed.set_control(conn, level="unattended")
    StubApi.calls.clear()
    page = _page(browser)
    _open(page, console, "events", ".strip")
    page.get_by_role("button", name="Send webhook question").click()
    page.get_by_role("button", name="Send the same event three times").click()
    time.sleep(2)
    assert StubApi.calls.count("/events") == 4


def test_fifteen_seconds_of_updates(
    console: str, conn: Any, browser: Any, probe_file: Path
) -> None:
    session = seed.open_session(conn, started_at=seed.now() - seed.timedelta(minutes=5))
    seed.events_scene(conn, session)
    page = _page(browser)
    _open(page, console, "events", ".strip")
    page.evaluate(PROBE_START)
    probe_file.write_text("")
    moving = []
    for second in range(15):
        if second % 3 == 0:
            moving.append(seed.add_run(conn, session, "queued", question=f"Update {second}"))
        for run_id in moving:
            row = conn.execute(
                "SELECT status FROM ops.runs WHERE run_id = %s", (run_id,)
            ).fetchone()
            following = {"queued": "running", "running": "verifying", "verifying": "posted"}
            if row["status"] in following:
                seed.set_status(conn, run_id, following[row["status"]])
                break
        time.sleep(1)
    result = page.evaluate(PROBE_END)
    durations = [json.loads(line)["seconds"] for line in probe_file.read_text().splitlines()]
    MEASURES["15 seconds of updates"] = {
        **result,
        "fragment_runs": len(durations),
        "slowest_fragment_seconds": max(durations),
        "median_fragment_seconds": sorted(durations)[len(durations) // 2],
        "console_errors": _real_errors(page),
    }
    (SHOTS / "measurements.json").write_text(json.dumps(MEASURES, indent=2) + "\n")
    _shot(page, "events-after-15-seconds")
    assert result["mounts"] == {"status_line": 1, "run_board": 1}, result
    assert result["same_nodes"] and result["min_opacity"] == 1, result
    assert len(durations) >= 12 and max(durations) < 0.5, durations
    assert _real_errors(page) == []


# The probe of DESIGN.md section 15: mounts, the same root nodes, and effective opacity sampled
# every 50 ms through the shadow hosts.
PROBE_START = """() => {
  const roots = () => [...document.querySelectorAll('*')].filter(e => e.shadowRoot);
  const find = (sel) => roots().map(h => h.shadowRoot.querySelector(sel)).find(Boolean);
  window.__keep = { sl: find('.sl'), board: find('.board') };
  window.__mounts0 = JSON.parse(JSON.stringify(window.__dpProbe || {}));
  window.__minOpacity = 1;
  const opacity = (node) => {
    let o = 1;
    for (let n = node; n; n = n.parentElement || (n.getRootNode() && n.getRootNode().host)) {
      o *= parseFloat(getComputedStyle(n).opacity || '1');
    }
    return o;
  };
  window.__sampler = setInterval(() => {
    for (const n of Object.values(window.__keep)) {
      window.__minOpacity = Math.min(window.__minOpacity, opacity(n));
    }
  }, 50);
}"""
PROBE_END = """() => {
  clearInterval(window.__sampler);
  const probe = window.__dpProbe || {};
  const roots = () => [...document.querySelectorAll('*')].filter(e => e.shadowRoot);
  const find = (sel) => roots().map(h => h.shadowRoot.querySelector(sel)).find(Boolean);
  return {
    mounts: { status_line: probe.status_line.mounts, run_board: probe.run_board.mounts },
    calls: { status_line: probe.status_line.calls, run_board: probe.run_board.calls },
    same_nodes: window.__keep.sl === find('.sl') && window.__keep.board === find('.board')
      && window.__keep.sl.isConnected && window.__keep.board.isConnected,
    min_opacity: window.__minOpacity,
  };
}"""
