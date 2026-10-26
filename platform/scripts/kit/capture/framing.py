"""Frame a Streamlit page in a fixed viewport so that no edge cuts a line of text.

A screenshot here is always the whole viewport (1280 by 720 CSS pixels at device scale factor 2:
2560 by 1440 pixels), never a crop, so the frame is chosen by scrolling: the element a capture is
about goes to the top (or its end to the bottom) of the visible page, and then the scroll position
is nudged, a few CSS pixels at a time, until neither outermost row of pixels crosses text.

Streamlit scrolls an inner container, not the window, and keeps its header fixed at the top, so
the scroll container is found by measuring (the element with the most room to scroll) and the
header's height is read from the page.

The clipped-edge measure is the one platform/scripts/check_images.py applies (the same constants;
a unit test keeps them equal): a row is cut text when both outermost rows of an edge hold at least
CLIPPED_CHANGES visible colour changes. The same measure is taken at the bottom of the fixed
header too: content scrolled under it is cut there, though the image's own top row is the header.
"""

from __future__ import annotations

import io
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from PIL import Image

VIEWPORT = {"width": 1280, "height": 720}
SCALE = 2
TIMEZONE = "UTC"
# Where the pointer rests while a screenshot is taken: the top-right corner of the fixed header,
# away from every button, link, and strip, so no hover style shows.
POINTER_REST = (1279, 0)

VISIBLE_CHANGE = 90
CLIPPED_CHANGES = 24
# Under the fixed header, and at the bottom, the frame wants empty page: even a box's two side
# borders crossing there mean the box is cut, so at most one visible change is allowed (the image
# check cannot see a cut under the header, since the image's own top row is the header).
HEADER_QUIET = 2
# The nudges tried, in CSS pixels from the placed position, in order: small ones both ways first,
# 3 pixels apart (one line of body text is about 27 pixels and the gap between two lines a few, so
# a gap is always within reach),
# then larger ones upward only, so the element the capture is about moves down and stays in view.
NUDGES = (
    0,
    *(n for step in range(3, 31, 3) for n in (-step, step)),
    *range(-36, -151, -6),
)
# From the page's own top, every downward nudge up to 96 pixels as well, one pixel apart: they only
# take in the page's top padding, and the measure under the fixed header refuses one that hides more.
PAGE_TOP_NUDGES = (*NUDGES, *(n for n in range(1, 97) if n % 3 or n > 30))
# Room left above an element placed at the top, so a downward nudge never hides it under the
# fixed header.
TOP_MARGIN = 36

FIND_SCROLLER = """() => {
  let best = null, room = 0;
  for (const node of document.querySelectorAll('*')) {
    const style = getComputedStyle(node);
    if (!/(auto|scroll)/.test(style.overflowY)) continue;
    const extra = node.scrollHeight - node.clientHeight;
    if (extra > room) { room = extra; best = node; }
  }
  document.querySelectorAll('[data-capture-scroller]').forEach((n) => n.removeAttribute('data-capture-scroller'));
  if (best) best.setAttribute('data-capture-scroller', '1');
  const header = document.querySelector('[data-testid="stHeader"]');
  // Content is cut where it leaves the visible page: the header's bottom, or the scroll
  // container's own top edge when that is lower.
  const headerEnd = header ? Math.max(0, header.getBoundingClientRect().bottom) : 0;
  const headerBottom = Math.max(headerEnd, best ? best.getBoundingClientRect().top : 0);
  // An open dialog lies over the header and the page: nothing scrolls under the header then.
  const modal = !!document.querySelector('[role="dialog"]');
  return { found: !!best, top: best ? best.scrollTop : 0, room, headerBottom, modal };
}"""
# The bottom of the page's last element that has a height (Streamlit keeps empty and skeleton
# containers at the end of a page): `place(bottom=PAGE_END)` puts it at the bottom of the frame.
PAGE_END = "page-end"
LAST_ELEMENT_BOTTOM = """() => {
  const main = document.querySelector('[data-testid="stMain"]');
  if (!main) return null;
  let end = null;
  for (const node of main.querySelectorAll('[data-testid="stElementContainer"]')) {
    const box = node.getBoundingClientRect();
    if (box.height > 1 && node.offsetParent !== null) end = Math.max(end ?? 0, box.bottom);
  }
  return end;
}"""
# Where an element is, measured for in_view(): whether it is on the page at all, whether it has a
# box (a strip past a run board lane's limit is hidden, its count under "N more"), its top and
# bottom, whether an ancestor that clips it (through the components' shadow roots: a run board
# lane scrolls its own list) cuts it, and whether it lies inside an open dialog.
MEASURE = """(node) => {
  const box = node.getBoundingClientRect();
  const shown = node.getClientRects().length > 0 && box.height >= 1;
  const parentOf = (n) => n.parentElement || (n.getRootNode() && n.getRootNode().host) || null;
  let clipped = false;
  for (let up = parentOf(node); up && up !== document.documentElement; up = parentOf(up)) {
    if (/(auto|scroll|hidden|clip)/.test(getComputedStyle(up).overflowY)) {
      const outer = up.getBoundingClientRect();
      if (box.top < outer.top - 0.5 || box.bottom > outer.bottom + 0.5) clipped = true;
    }
  }
  return {
    shown, top: box.top, bottom: box.bottom, clipped,
    inDialog: !!node.closest('[role="dialog"]'), viewportBottom: window.innerHeight,
  };
}"""
# What must never be in a published frame: a dialog (Streamlit's "Page not found" among them), an
# error box, an exception, a toast, or the console's own notice that the api or database is down.
BLOCKERS = """() => {
  const found = [];
  const shown = (node) => node.getClientRects().length > 0;
  const kinds = [
    ['a dialog', '[role="dialog"]'],
    ['an error box', '[data-testid="stAlertContentError"]'],
    ['an exception', '[data-testid="stException"]'],
    ['a toast', '[data-testid="stToast"]'],
  ];
  for (const [what, selector] of kinds) {
    for (const node of document.querySelectorAll(selector)) {
      if (shown(node)) found.push(what + ': ' + (node.innerText || '').trim().slice(0, 120));
    }
  }
  for (const host of document.querySelectorAll('*')) {
    const notice = host.shadowRoot && host.shadowRoot.querySelector('.sl .notice');
    const words = notice ? notice.textContent.trim() : '';
    if (words) found.push('the status line notice: ' + words);
  }
  return found;
}"""
SCROLL_TO = """(y) => {
  const node = document.querySelector('[data-capture-scroller]');
  if (!node) return 0;
  node.scrollTop = Math.max(0, Math.min(y, node.scrollHeight - node.clientHeight));
  return node.scrollTop;
}"""


@dataclass(frozen=True)
class Edges:
    """Colour changes along the two outermost rows of each edge (the smaller of the two), along
    the two rows just under the fixed header (the top of the page in view, when the image has a
    header), and the strokes among the changes there.

    The image check's threshold (CLIPPED_CHANGES) is for whole images. A frame is held to more:
    live, on 24 October, bottoms with 14 to 18 changes, under that threshold, cut lines of text and
    a row of buttons. A cut line of text shows strokes: changes with another change close on both
    sides (STROKE_GAP pixels), as the stems and bowls of letters give; the sides of a box give
    changes in pairs far apart. So:

    - quiet: the bottom row, and the top of the page in view, cross nothing but at most the edge
      of one shape (fewer than QUIET_CHANGES changes): the frame starts and ends in empty page;
    - clean: no stroke at either, under CLIPPED_CHANGES: only the straight sides of boxes cross,
      as when a ledger or a diff is taller than the frame. settle() takes a quiet frame when any
      nudge gives one, and a clean one only when none does."""

    top: int
    bottom: int
    header: int = 0
    has_header: bool = False
    top_strokes: int = 0
    bottom_strokes: int = 0

    @property
    def page_top(self) -> int:
        return self.header if self.has_header else self.top

    @property
    def quiet(self) -> bool:
        return self.clean and max(self.page_top, self.bottom) < QUIET_CHANGES

    @property
    def clean(self) -> bool:
        return (
            max(self.top, self.bottom, self.page_top) < CLIPPED_CHANGES
            and self.top_strokes == 0
            and self.bottom_strokes == 0
        )


QUIET_CHANGES = HEADER_QUIET
# Two changes closer than this (image pixels: 5 CSS pixels at scale 2) belong to one shape.
STROKE_GAP = 10


def _change_columns(pixels: Sequence[tuple[int, ...]]) -> list[int]:
    return [
        x
        for x, (left, right) in enumerate(zip(pixels, pixels[1:], strict=False))
        if sum(abs(a - b) for a, b in zip(left, right, strict=True)) > VISIBLE_CHANGE
    ]


def _changes(pixels: Sequence[tuple[int, ...]]) -> int:
    return len(_change_columns(pixels))


def strokes(columns: Sequence[int]) -> int:
    """Changes with a neighbouring change within STROKE_GAP on both sides: the inside of text."""
    return sum(
        1
        for before, here, after in zip(columns, columns[1:], columns[2:], strict=False)
        if here - before <= STROKE_GAP and after - here <= STROKE_GAP
    )


def edges(image: Image.Image, header_rows: int = 0) -> Edges:
    """The clipped-edge measure of check_images.py, on an image in memory, with the strokes at
    each edge; `header_rows` is the fixed header's height in image pixels (0: no header)."""
    rgba = image.convert("RGBA")
    width, height = rgba.size

    def row(y: int) -> list[int]:
        return _change_columns([rgba.getpixel((x, y)) for x in range(width)])  # type: ignore[misc]

    def pair(first: int, second: int) -> tuple[int, int]:
        one, two = row(first), row(second)
        return min(len(one), len(two)), min(strokes(one), strokes(two))

    if height < 2:
        return Edges(0, 0)
    top, top_strokes = pair(0, 1)
    bottom, bottom_strokes = pair(height - 1, height - 2)
    under = 0 < header_rows < height - 2
    header = 0
    if under:
        header, top_strokes = pair(header_rows, header_rows + 1)
    return Edges(top, bottom, header, under, top_strokes, bottom_strokes)


def edges_of_png(data: bytes, header_rows: int = 0) -> Edges:
    with Image.open(io.BytesIO(data)) as image:
        return edges(image, header_rows)


def pick_nudge(measured: Iterable[tuple[int, Edges]]) -> int | None:
    """The nudge settle() keeps: the first quiet one in the order tried, else the first clean one,
    else None (no frame may be written)."""
    tried = list(measured)
    for nudge, found in tried:
        if found.quiet:
            return nudge
    return next((nudge for nudge, found in tried if found.clean), None)


def new_context(browser: Any, **extra: Any) -> Any:
    """A browser context at the standard: 1280 by 720, scale 2, Coordinated Universal Time."""
    return browser.new_context(
        viewport=dict(VIEWPORT), device_scale_factor=SCALE, timezone_id=TIMEZONE, **extra
    )


def rest_pointer(page: Any) -> None:
    page.mouse.move(*POINTER_REST)


def place(
    page: Any, *, top: str | None = None, bottom: str | None = None, margin: int = TOP_MARGIN
) -> int:
    """Scroll so the first element matching `top` sits `margin` CSS pixels under the fixed header,
    or the end of `bottom` sits `margin` pixels above the bottom of the viewport; with neither, the
    page's own top. Returns the scroll position reached (clamped to the page)."""
    state = page.evaluate(FIND_SCROLLER)
    if not state["found"]:
        return 0
    if top is None and bottom is None:
        return int(page.evaluate(SCROLL_TO, 0))
    if bottom == PAGE_END:
        end = page.evaluate(LAST_ELEMENT_BOTTOM)
        if end is None:
            raise LookupError("the page has no element to end the frame on")
        return int(page.evaluate(SCROLL_TO, state["top"] + end - (VIEWPORT["height"] - margin)))
    # The first match goes to the top; the last match's end goes to the bottom.
    matches = page.locator(top or bottom)  # type: ignore[arg-type]
    locator = matches.first if top is not None else matches.last
    locator.wait_for(timeout=30_000)
    box = locator.bounding_box()
    if box is None:
        raise LookupError(f"{top or bottom} is not on the page")
    if top is not None:
        delta = box["y"] - state["headerBottom"] - margin
    else:
        delta = box["y"] + box["height"] - (VIEWPORT["height"] - margin)
    return int(page.evaluate(SCROLL_TO, state["top"] + delta))


def settle(
    page: Any,
    placed: int,
    *,
    nudges: Sequence[int] = NUDGES,
    pause_ms: int = 150,
    lanes: Sequence[str] = (),
) -> tuple[bytes, Edges, int]:
    """Try the nudges around `placed` until a screenshot's edges are quiet (pick_nudge's order).
    Returns the screenshot, its edges, and the nudge kept: the first clean one when no nudge is
    quiet, and the placed position itself when none is clean (its edges say so, and the runner
    then writes nothing).

    `lanes`: selectors whose run board lane is scrolled to them (reveal) after every scroll and
    before every screenshot. The board refits its lanes to the room left on the screen a few
    times a second, so a lane scrolled once, before the page's scroll moved, can lose its strip."""
    state = page.evaluate(FIND_SCROLLER)
    scale = float(page.evaluate("() => window.devicePixelRatio"))
    # The first two whole rows of page under the header (its bottom may fall inside a pixel row).
    header_rows = 0 if state["modal"] else math.ceil(state["headerBottom"] * scale) + 1
    seen: set[int] = set()
    fallback: int | None = None  # the first clean frame, kept while no quiet one is found
    for nudge in nudges:
        reached = int(page.evaluate(SCROLL_TO, placed + nudge))
        if reached in seen:  # clamped at the top or the bottom of the page: nothing new to see
            continue
        seen.add(reached)
        page.wait_for_timeout(pause_ms)
        reveal(page, lanes)
        rest_pointer(page)
        data = page.screenshot()
        found = edges_of_png(data, header_rows)
        if found.quiet:
            return data, found, nudge
        if found.clean and fallback is None:
            fallback = nudge
    if fallback is not None:
        placed += fallback
    page.evaluate(SCROLL_TO, placed)
    page.wait_for_timeout(pause_ms)
    reveal(page, lanes)
    rest_pointer(page)
    data = page.screenshot()
    return data, edges_of_png(data, header_rows), fallback or 0


def blockers(page: Any, *, allow_dialog: bool = False) -> list[str]:
    """Each dialog, error box, exception, toast, or console notice in view: [] when none. With
    `allow_dialog` (an image of a dialog, such as Review), a dialog other than Streamlit's "Page
    not found" is the moment, not a blocker."""
    found = list(page.evaluate(BLOCKERS))
    if allow_dialog:
        found = [b for b in found if not b.startswith("a dialog") or "Page not found" in b]
    return found


REVEAL = """(node) => {
  const list = node.closest('.list');
  if (!list || list.scrollHeight <= list.clientHeight) return false;
  const offset = node.getBoundingClientRect().top - list.getBoundingClientRect().top;
  const before = list.scrollTop;
  list.scrollTop += offset - 4;
  return list.scrollTop !== before;
}"""


def reveal(page: Any, selectors: Sequence[str]) -> None:
    """Scroll the run board lane that holds each selector's first match (a lane scrolls its own
    list when the board must fit the screen) so the match is at the top of its lane; waits for the
    page to draw only when a lane moved."""
    moved = False
    for selector in selectors:
        found = page.locator(selector)
        if found.count() and found.first.evaluate(REVEAL):
            moved = True
    if moved:
        page.wait_for_timeout(200)


IN_VIEW, OUTSIDE, HIDDEN, MISSING = "in view", "outside the frame", "hidden", "missing"
# Where a selector is when a scroll might still bring it into a frame, or nothing matches it.
NOT_IN_FRAME = (OUTSIDE, MISSING)


def in_view(measure: dict[str, Any] | None, header_bottom: float) -> str:
    """Where a must_see element is, from MEASURE: IN_VIEW when it is wholly in the frame (inside
    the viewport under the fixed header, and inside every ancestor that clips it); OUTSIDE when a
    scroll could bring it in; HIDDEN when it has no box on the page at all, so no frame can show
    it; MISSING when nothing matches.

    An element inside an open dialog is measured from the viewport's top, not the header's bottom:
    the dialog lies over the header (the backdrop greys it), so nothing of the dialog is under it.
    Live, 25 October: the Review dialog's top was at 54 CSS pixels, over a 60-pixel header, and
    the whole dialog in view was refused."""
    if measure is None:
        return MISSING
    if not measure["shown"]:
        return HIDDEN
    clip_top = 0.0 if measure["inDialog"] else header_bottom
    if measure["top"] < clip_top - 0.5 or measure["bottom"] > measure["viewportBottom"] + 0.5:
        return OUTSIDE
    return OUTSIDE if measure["clipped"] else IN_VIEW


def where(page: Any, selectors: Sequence[str]) -> dict[str, str]:
    """For each selector, where its first match is in the current frame (in_view's words)."""
    header_bottom = page.evaluate(FIND_SCROLLER)["headerBottom"]
    found: dict[str, str] = {}
    for selector in selectors:
        matches = page.locator(selector)
        measure = matches.first.evaluate(MEASURE) if matches.count() else None
        found[selector] = in_view(measure, header_bottom)
    return found


def out_of_frame(page: Any, selectors: Sequence[str]) -> list[str]:
    """The selectors whose first match is missing or not wholly in view in the current frame."""
    return [s for s, place in where(page, selectors).items() if place != IN_VIEW]


def framed_screenshot(
    page: Any,
    *,
    top: str | None = None,
    bottom: str | None = None,
    margin: int = TOP_MARGIN,
    lanes: Sequence[str] = (),
) -> tuple[bytes, Edges]:
    """Place, settle, and shoot: the whole viewport, no edge across text when one can be found;
    each of `lanes` revealed in its run board lane before every screenshot (settle)."""
    placed = place(page, top=top, bottom=bottom, margin=margin)
    page_top = top is None and bottom is None
    nudges = PAGE_TOP_NUDGES if page_top else NUDGES
    data, found, _nudge = settle(page, placed, nudges=nudges, lanes=lanes)
    return data, found
