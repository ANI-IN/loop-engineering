"""Fluid-layout checker: open each page at many widths, heights, pixel ratios, and zoom levels in
a real browser (Playwright Chromium) and report every layout problem. No model calls.

A page with no layout tied to a screen size must hold at any width. The sweep runs every `step`
CSS px from `min_width` to `max_width` at each of `heights` (pixel ratio 1), plus each of `dprs`
at a few widths, plus the named `viewports` (display scaling, zoom, phone, class screen sizes).
For each page the rules are:

- no horizontal overflow (document scrollWidth <= window width);
- nothing reaches past the right edge of the window;
- no element is wider than its own box, except inside lists built to scroll (`scroll_selector`);
- no text cut by an ellipsis unless the element carries the full text as a title;
- nothing clips its content vertically;
- pills (`pill_selector`) stay on one line;
- no word of 8 or more letters or digits breaks across lines;
- the page scrolls to its last panel (`panel_selector`).

    uv run python tools/layout-check/layout_check.py --config layout.json [--shots DIR]

Config (JSON): {"pages": [{"name": "home", "url": "http://127.0.0.1:8000/", "root": "body",
"press": []}], "min_width": 320, "max_width": 2560, "step": 40, "heights": [600, 1000],
"dprs": [1.25, 1.5, 2], "dpr_widths": [360, 768, 1280], "viewports": [[1280, 630, 1.5]],
"pill_selector": ".pill, .status", "panel_selector": ".panel, main",
"scroll_selector": "[data-scroll]"}. Exit 1 on any problem.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple


class Viewport(NamedTuple):
    name: str  # file-name part: width x height, then "@<dpr>" when the pixel ratio is not 1
    width: int
    height: int
    dpr: float = 1.0


def vp(width: int, height: int, dpr: float = 1.0) -> Viewport:
    ratio = "" if dpr == 1 else f"@{dpr:g}"
    return Viewport(f"{width}x{height}{ratio}", width, height, dpr)


# A 1920x1080 laptop at 150% and 125% display scaling, a small laptop, class screen sizes, a
# phone, and a 1920x1080 browser at 150% and 175% zoom (zoom = smaller CSS viewport, higher dpr).
DEFAULT_VIEWPORTS = (
    (1280, 630, 1.5), (1536, 730, 1.25), (1024, 768, 1), (1366, 768, 1), (1440, 900, 1),
    (1920, 1080, 1), (390, 844, 3), (1280, 720, 1.5), (1097, 617, 1.75),
)  # fmt: skip


def sweep(
    min_width: int = 320,
    max_width: int = 2560,
    step: int = 40,
    heights: tuple[int, ...] = (600, 1000),
    dprs: tuple[float, ...] = (1.25, 1.5, 2.0),
    dpr_widths: tuple[int, ...] = (360, 768, 1097, 1280, 1536),
) -> list[Viewport]:
    sizes = [vp(w, h) for w in range(min_width, max_width + 1, step) for h in heights]
    sizes += [vp(w, 700, d) for w in dpr_widths for d in dprs]
    return sizes


@dataclass(frozen=True)
class Page:
    name: str
    url: str
    root: str = "body"
    press: tuple[str, ...] = ()


@dataclass(frozen=True)
class Config:
    pages: tuple[Page, ...]
    min_width: int = 320
    max_width: int = 2560
    step: int = 40
    heights: tuple[int, ...] = (600, 1000)
    dprs: tuple[float, ...] = (1.25, 1.5, 2.0)
    dpr_widths: tuple[int, ...] = (360, 768, 1097, 1280, 1536)
    viewports: tuple[tuple[int, int, float], ...] = DEFAULT_VIEWPORTS
    pill_selector: str = ".pill, .status"
    panel_selector: str = ".panel, main"
    scroll_selector: str = "[data-scroll]"
    extra: dict[str, Any] = field(default_factory=dict)

    def all_viewports(self) -> list[Viewport]:
        named = [vp(w, h, d) for w, h, d in self.viewports]
        return named + sweep(
            self.min_width, self.max_width, self.step, self.heights, self.dprs, self.dpr_widths
        )


def load_config(path: Path) -> Config:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    pages = tuple(
        Page(p["name"], p["url"], p.get("root", "body"), tuple(p.get("press", ())))
        for p in raw["pages"]
    )
    keys = {k: v for k, v in raw.items() if k != "pages" and k in Config.__dataclass_fields__}
    for k in ("heights", "dprs", "dpr_widths"):
        if k in keys:
            keys[k] = tuple(keys[k])
    if "viewports" in keys:
        keys["viewports"] = tuple(tuple(v) for v in keys["viewports"])
    return Config(pages=pages, **keys)


MEASURE_JS = r"""(args) => {
  const {root, pill, panel, scroll} = args;
  const w = window.innerWidth;
  const roots = root.split(',').map(s => document.querySelector(s.trim())).filter(Boolean);
  const visible = roots.flatMap(r => [r, ...r.querySelectorAll('*')])
    .filter(e => e.offsetParent !== null || e.tagName === 'BODY');
  const name = e => e.tagName.toLowerCase() +
    (typeof e.className === 'string' && e.className.trim() ?
      '.' + e.className.trim().split(/\s+/).join('.') : '') +
    ' "' + (e.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40) + '"';
  const wide = [], ellipsis = [], offscreen = [], clipped = [];
  for (const e of visible) {
    const r = e.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    const list = e.closest(scroll);
    if (!list && r.right > w + 1) offscreen.push(name(e) + ' right ' + Math.round(r.right));
    if (list && list !== e) continue;
    const cs = getComputedStyle(e);
    if (!list && cs.display !== 'inline' && e.clientWidth > 0 && e.scrollWidth > e.clientWidth + 1)
      wide.push(name(e) + ' ' + e.scrollWidth + '>' + e.clientWidth);
    if (cs.textOverflow === 'ellipsis' && e.scrollWidth > e.clientWidth + 1 && !e.title)
      ellipsis.push(name(e));
    const hidesY = cs.overflowY === 'hidden' || cs.overflowY === 'clip';
    if (!list && hidesY && e.scrollHeight > e.clientHeight + 2) clipped.push(name(e));
  }
  const pills = new Set(document.querySelectorAll(pill));
  const wrappedPills = visible.filter(e => pills.has(e)).filter(e => {
    const cs = getComputedStyle(e);
    const line = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.35;
    return e.getBoundingClientRect().height > line * 1.6;
  }).map(name);
  const brokenWords = [];
  for (const r of roots) {
    const walker = document.createTreeWalker(r, NodeFilter.SHOW_TEXT);
    while (walker.nextNode() && brokenWords.length < 5) {
      const node = walker.currentNode, parent = node.parentElement;
      if (!parent || parent.offsetParent === null || parent.closest(scroll)) continue;
      for (const m of node.textContent.matchAll(/[A-Za-z0-9]{8,}/g)) {
        const range = document.createRange();
        range.setStart(node, m.index);
        range.setEnd(node, m.index + m[0].length);
        const tops = new Set([...range.getClientRects()].map(x => Math.round(x.top)));
        if (tops.size > 1) { brokenWords.push(m[0]); break; }
      }
    }
  }
  const panels = Array.from(document.querySelectorAll(panel)).filter(e => e.offsetParent !== null);
  const bottom = Math.max(0, ...panels.map(p => p.getBoundingClientRect().bottom + window.scrollY));
  window.scrollTo(0, document.documentElement.scrollHeight);
  const reached = window.scrollY + window.innerHeight >= bottom - 2;
  window.scrollTo(0, 0);
  return {scrollWidth: document.documentElement.scrollWidth, width: w, panels: panels.length,
          wide: wide.slice(0, 5), ellipsis: ellipsis.slice(0, 5), offscreen: offscreen.slice(0, 5),
          clipped: clipped.slice(0, 5), wrappedPills: wrappedPills.slice(0, 5), brokenWords,
          reachedBottom: reached};
}"""


def problems(m: dict[str, Any]) -> list[str]:
    """The rule violations in one measurement (the result of MEASURE_JS)."""
    out: list[str] = []
    if m["panels"] < 1:
        out.append("no panel shown")
    if m["scrollWidth"] > m["width"]:
        out.append(f"scrolls sideways: {m['scrollWidth']} > {m['width']}")
    out += [f"wider than its box: {x}" for x in m["wide"]]
    out += [f"cut by an ellipsis without a title: {x}" for x in m["ellipsis"]]
    out += [f"past the right edge: {x}" for x in m["offscreen"]]
    out += [f"clipped: {x}" for x in m["clipped"]]
    out += [f"pill on more than one line: {x}" for x in m["wrappedPills"]]
    out += [f"word broken across lines: {x}" for x in m["brokenWords"]]
    if not m["reachedBottom"]:
        out.append("the page does not scroll to its last panel")
    return out


def check(cfg: Config, shots: Path | None = None) -> tuple[int, int]:
    """(checked, failed) page checks over every viewport; prints each problem."""
    from playwright.sync_api import sync_playwright

    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    checked = failed = 0
    args = {"pill": cfg.pill_selector, "panel": cfg.panel_selector, "scroll": cfg.scroll_selector}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for view in cfg.all_viewports():
            ctx = browser.new_context(
                viewport={"width": view.width, "height": view.height},
                device_scale_factor=view.dpr,
            )
            page = ctx.new_page()
            for p in cfg.pages:
                page.goto(p.url, wait_until="load")
                for key in p.press:
                    page.keyboard.press(key)
                found = problems(page.evaluate(MEASURE_JS, {**args, "root": p.root}))
                checked += 1
                failed += bool(found)
                if found:
                    print(f"{p.name} {view.name}: {'; '.join(found[:3])}")
                if shots:
                    page.screenshot(path=str(shots / f"{p.name}-{view.name}.png"), full_page=True)
            ctx.close()
        browser.close()
    return checked, failed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--shots", type=Path, default=None, help="save a screenshot per check")
    a = ap.parse_args(argv)
    cfg = load_config(a.config)
    checked, failed = check(cfg, a.shots)
    print(f"{checked - failed} of {checked} page checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
