"""The console design style tile in a real browser: the screenshots of platform/console/DESIGN.md.

A test launch: this file starts Streamlit on platform/console/design_app.py (specimen data only: no
database, no api, no model) and drives headless Chromium with Playwright. Each screenshot is the
whole 1280 by 720 viewport at device scale factor 2 (2560 by 1440 pixels), in Coordinated Universal
Time, framed by the capture kit so that no edge cuts a line of text (docs/STYLE.md). It rewrites the
tracked screenshots in platform/console/design/screenshots/, so it runs only when asked, with the
console's own screenshots:

    make test-console
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from typing import Any

import httpx
import pytest

from datapilot.settings import PLATFORM

sys.path.insert(0, str(PLATFORM / "scripts" / "kit" / "capture"))
import framing  # noqa: E402  (the capture kit: whole-viewport frames with clean edges)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.skipif(
        os.environ.get("DATAPILOT_CONSOLE_SCREENSHOTS") != "1",
        reason="rewrites the tracked style tile screenshots; run it with make test-console",
    ),
]

CONSOLE = PLATFORM / "console"
SHOTS = CONSOLE / "design" / "screenshots"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def style_tile() -> Iterator[str]:
    port = _free_port()
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "design_app.py",
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--server.fileWatcherType",
            "none",
        ],
        cwd=CONSOLE,
        env={**os.environ, "PYTHONUTF8": "1"},
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
        pytest.fail("the style tile did not start within 60 seconds")
    yield url
    process.kill()
    process.wait(timeout=10)


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as playwright:
        chromium = playwright.chromium.launch()
        yield chromium
        chromium.close()


def _open(browser: Any, url: str, **context: Any) -> Any:
    page = (browser.new_context(**context) if context else framing.new_context(browser)).new_page()
    page.goto(url)
    # 90 seconds: on a machine busy with a live class pass, the first render took over 30.
    page.locator(".board .strip").first.wait_for(timeout=90_000)
    time.sleep(2.5)  # two fragment ticks: every component has its current data
    return page


def _shot(page: Any, name: str, *, top: str | None = None, bottom: str | None = None) -> None:
    """The whole viewport, from the page's top, with `top` under the header, or with the end of
    `bottom` near the viewport's bottom, nudged until no edge cuts a line of text."""
    SHOTS.mkdir(parents=True, exist_ok=True)
    # When no frame has clean edges the image is written anyway, and platform/scripts/
    # check_images.py (make check-images) reports it.
    data, _edges = framing.framed_screenshot(page, top=top, bottom=bottom)
    (SHOTS / f"{name}.png").write_bytes(data)


def _heading(words: str) -> str:
    """A Streamlit title, header, or subheader by its words."""
    return f'[data-testid="stHeading"]:has-text("{words}")'


def test_style_tile_screenshots(style_tile: str, browser: Any) -> None:
    page = _open(browser, style_tile)
    _shot(page, "01-events-1280x720")
    time.sleep(15)
    _shot(page, "02-events-1280x720-t15")
    kill = page.locator(".sl button.kill")
    kill.click()
    time.sleep(0.5)
    _shot(page, "03-kill-armed")
    assert "Click again to stop all workers" in kill.inner_text()
    kill.click()
    page.wait_for_function(
        "() => [...document.querySelectorAll('*')].some((e) => e.shadowRoot"
        " && /Release kill switch/.test(e.shadowRoot.textContent))",
        timeout=10_000,
    )
    time.sleep(1.5)
    _shot(page, "04-kill-engaged")
    kill.click()  # release, so the board moves again
    time.sleep(1.5)

    page.locator(".board button.review").first.click()
    page.get_by_role("dialog").wait_for(timeout=10_000)
    time.sleep(1)
    _shot(page, "05-approval-dialog")
    page.keyboard.press("Escape")
    page.get_by_role("dialog").wait_for(state="hidden", timeout=10_000)
    time.sleep(1)

    page.locator(".board button.expand").first.click()
    page.locator(".ledger .rows .row").first.wait_for(timeout=10_000)
    time.sleep(1.5)
    _shot(page, "06-benchmark-expanded")
    _shot(page, "07-benchmark-ledger", top=".ledger .stamps")

    _shot(page, "08-tokens", top=_heading("Console style tile"))
    _shot(page, "09-type", top=_heading("Type and native widgets"))
    _shot(page, "10-annotated", top=_heading("Annotated SQL"))
    _shot(page, "11-holdout", top=_heading("Holdout ledger"))
    page.get_by_text("No baseline in this session", exact=True).click()
    page.locator(".nobase:visible").first.wait_for(timeout=10_000)
    time.sleep(1)
    _shot(page, "12-no-baseline", bottom=".nobase")  # its end low: no empty band under it

    page.get_by_text("No live session", exact=True).click()
    time.sleep(2.5)
    _shot(page, "13-no-session")
    page.context.close()

    # A 1280 by 720 screen at 67 percent zoom shows 1910 by 1075 CSS pixels; at twice that
    # screen's pixels the image is 2560 by 1440, as every published screenshot.
    zoomed = _open(
        browser,
        style_tile,
        viewport={"width": 1910, "height": 1075},
        device_scale_factor=2 * 1280 / 1910,
        timezone_id=framing.TIMEZONE,
    )
    _shot(zoomed, "14-events-67-percent")
    zoomed.context.close()
