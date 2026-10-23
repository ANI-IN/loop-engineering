"""HD screenshots of a web app for a guide, with numbered callouts, driven by a JSON config.

Playwright Chromium, headless (the page only, no browser chrome), viewport 1024x900 at device
pixel ratio 2 by default (text prints at 8 pt or more on A4). For each shot in the config: open
the page, press the keys it lists, mask links that match `mask_urls`, check the page text, take a
full-page or viewport image (cropped to a selector when asked), resolve each callout target (a
CSS selector and/or a text match) to a box, keep it only when the element holds the text the
callout is about, and draw the callouts (callouts.py). Each image gets an entry in
<out>/images.json.

Before an image is saved, the page text (body, title, tooltips, alt and aria labels) is checked:
a host path, a configured user name, an email address, key-like text, or an account link
(`account_urls`, UUID-like ids) stops the capture and nothing is written.

    uv run python tools/capture/capture.py --config capture.json --out images/s1 \
        [--only NAME ...] [--kind recorded|live] [--source-run ID]

Config (JSON):

    {"base": "http://127.0.0.1:8000",
     "viewport": {"width": 1024, "height": 900, "dpr": 2},
     "css": "path/to/app.css", "accent_token": "accent", "bg_token": "bg",
     "users": ["<your-user-name>"],
     "mask_urls": ["tracing\\\\.example\\\\.com"],
     "account_urls": ["tracing\\\\.example\\\\.com/o/"],
     "shots": [{"name": "s1-screen-1", "path": "/run/1", "press": ["1"], "wait_for": ".panel",
                "full_page": false, "crop": ".panel", "screen": 1,
                "moment": "after the run finished",
                "alt": "Screen 1 after the run: the status pill reads passed.",
                "callouts": [{"label": "Status pill", "sel": ".pill", "must": "passed"},
                             {"label": "Back link", "text": "All runs", "root": "header"}]}]}
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from callouts import Target, annotate, palette
from capturelib import (
    Box,
    account_hits,
    box_in_crop,
    find_secrets,
    image_entry,
    load_entries,
    merge_entries,
    personal_hits,
    reading_order,
    save_entries,
    scale_box,
    target_matches,
)

MAX_CALLOUTS = 7
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class PrivacyError(RuntimeError):
    """Personal or secret text on the page: nothing is saved."""


@dataclass(frozen=True)
class Spec:
    """A callout target: a CSS selector and/or a text match, inside `root` (a selector; the
    whole page by default); `nth` picks among matches (document order, deepest elements);
    `must` is text the element must contain, else the callout is dropped."""

    label: str
    sel: str | None = None
    text: str | None = None
    root: str = "body"
    nth: int = 0
    must: str | None = None

    @property
    def expected(self) -> str | None:
        return self.must or self.text


@dataclass(frozen=True)
class ShotSpec:
    name: str
    path: str
    alt: str
    moment: str = ""
    screen: int | str | None = None
    press: tuple[str, ...] = ()
    wait_for: str | None = None
    full_page: bool = True
    crop: str | None = None
    callouts: tuple[Spec, ...] = ()


@dataclass(frozen=True)
class Config:
    base: str
    shots: tuple[ShotSpec, ...]
    width: int = 1024
    height: int = 900
    dpr: float = 2
    css: str | None = None
    accent_token: str = "accent"
    bg_token: str = "bg"
    users: tuple[str, ...] = ()
    mask_urls: tuple[str, ...] = ()
    account_urls: tuple[str, ...] = ()


def load_config(path: Path) -> Config:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    shots = []
    for s in raw.get("shots", []):
        if not NAME_RE.match(s.get("name", "")):
            raise ValueError(f"shot name must be a plain file stem: {s.get('name')!r}")
        specs = tuple(Spec(**c) for c in s.get("callouts", []))
        if len(specs) > MAX_CALLOUTS:
            raise ValueError(f"{s['name']}: at most {MAX_CALLOUTS} callouts per image")
        for spec in specs:
            if not (spec.sel or spec.text):
                raise ValueError(f"{s['name']}: callout {spec.label!r} needs sel or text")
        shots.append(
            ShotSpec(
                name=s["name"],
                path=s.get("path", "/"),
                alt=s["alt"],
                moment=s.get("moment", ""),
                screen=s.get("screen"),
                press=tuple(s.get("press", ())),
                wait_for=s.get("wait_for"),
                full_page=bool(s.get("full_page", True)),
                crop=s.get("crop"),
                callouts=specs,
            )
        )
    for pattern in [*raw.get("mask_urls", []), *raw.get("account_urls", [])]:
        re.compile(pattern)  # a bad pattern fails here, not mid-capture
    vp = raw.get("viewport", {})
    return Config(
        base=raw["base"].rstrip("/"),
        shots=tuple(shots),
        width=int(vp.get("width", 1024)),
        height=int(vp.get("height", 900)),
        dpr=float(vp.get("dpr", 2)),
        css=raw.get("css"),
        accent_token=raw.get("accent_token", "accent"),
        bg_token=raw.get("bg_token", "bg"),
        users=tuple(raw.get("users", ())),
        mask_urls=tuple(raw.get("mask_urls", ())),
        account_urls=tuple(raw.get("account_urls", ())),
    )


def check_private(text: str, cfg: Config) -> None:
    """Raise PrivacyError when the page text shows something no image may show. The message
    names the kind of problem, never the text itself."""
    if account_hits(text, cfg.account_urls):
        raise PrivacyError("an account link or UUID-like id is on the page")
    if find_secrets(text):
        raise PrivacyError("key-like text is on the page")
    if personal_hits(text, cfg.users):
        raise PrivacyError("a host path, user name, or email address is on the page")


RESOLVE_JS = r"""
(specs) => {
  const vis = e => {
    if (!e || !e.getBoundingClientRect) return false;
    const r = e.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && getComputedStyle(e).visibility !== 'hidden';
  };
  return specs.map(s => {
    const root = document.querySelector(s.root || 'body');
    if (!root) return null;
    let cands = Array.from(root.querySelectorAll(s.sel || '*')).filter(vis);
    if (s.text) {
      cands = cands.filter(e => (e.textContent || '').includes(s.text));
      cands = cands.filter(e => !cands.some(o => o !== e && e.contains(o)));
    }
    const e = cands[s.nth || 0];
    if (!e) return null;
    const r = e.getBoundingClientRect();
    return {x: r.left + window.scrollX, y: r.top + window.scrollY, w: r.width, h: r.height,
            text: (e.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 400)};
  });
}
"""

MASK_JS = r"""
(patterns) => {
  const res = patterns.map(p => new RegExp(p, 'i'));
  const hit = s => res.some(r => r.test(s || ''));
  const short = u => u.replace(/^https?:\/\//, '').split('/')[0] + '/…';
  document.querySelectorAll('a').forEach(a => {
    const href = a.getAttribute('href') || '';
    if (hit(href) || hit(a.textContent)) {
      a.textContent = short(hit(href) ? href : a.textContent.trim());
      a.removeAttribute('title');
      a.setAttribute('href', '#');
    }
  });
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const url = /https?:\/\/[^\s"'<>]+/g;
  while (walker.nextNode()) {
    const n = walker.currentNode;
    if (hit(n.nodeValue)) n.nodeValue = n.nodeValue.replace(url, u => hit(u) ? short(u) : u);
  }
  document.querySelectorAll('[title]').forEach(e => {
    if (hit(e.getAttribute('title'))) e.removeAttribute('title');
  });
}
"""

PAGE_TEXT_JS = r"""
() => {
  const parts = [document.title, document.body ? document.body.innerText : ''];
  document.querySelectorAll('[title],[alt],[aria-label]').forEach(e => {
    ['title', 'alt', 'aria-label'].forEach(a => {
      if (e.getAttribute(a)) parts.push(e.getAttribute(a));
    });
  });
  return parts.join('\n');
}
"""


@dataclass
class Result:
    written: list[str] = field(default_factory=list)
    dropped_callouts: list[str] = field(default_factory=list)


def _targets(
    specs: tuple[Spec, ...], raw: list[Any], dpr: float, crop: Box | None
) -> tuple[list[Target], list[str]]:
    targets, dropped, seen = [], [], set()
    for spec, r in zip(specs, raw, strict=True):
        if r is None or not target_matches(spec.expected, r["text"]):
            dropped.append(spec.label)  # not on the page, or not the text the callout is about
            continue
        box = scale_box((r["x"], r["y"], r["w"], r["h"]), dpr)
        if crop is not None:
            box = box_in_crop(box, crop)
            if box is None:
                dropped.append(spec.label)
                continue
        key = (round(box.x), round(box.y), round(box.w), round(box.h))
        if key not in seen:
            seen.add(key)
            targets.append(Target(box, spec.label))
    order = reading_order([t.box for t in targets], row=24 * dpr)
    return [targets[i] for i in order], dropped


def capture(cfg: Config, out: Path, *, only: set[str] | None = None, kind: str = "recorded",
            source_run: str | None = None) -> Result:  # fmt: skip
    from PIL import Image
    from playwright.sync_api import sync_playwright

    out.mkdir(parents=True, exist_ok=True)
    colours = palette(Path(cfg.css) if cfg.css else None, cfg.accent_token, cfg.bg_token)
    tmp = Path(tempfile.mkdtemp(prefix="capture-"))
    result, entries = Result(), []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(
                viewport={"width": cfg.width, "height": cfg.height},
                device_scale_factor=cfg.dpr,
            )
            page = ctx.new_page()
            for shot in cfg.shots:
                if only and shot.name not in only:
                    continue
                page.goto(cfg.base + shot.path, wait_until="load")
                if shot.wait_for:
                    page.wait_for_selector(shot.wait_for, timeout=15000)
                for key in shot.press:
                    page.keyboard.press(key)
                    page.wait_for_timeout(300)
                if cfg.mask_urls:
                    page.evaluate(MASK_JS, list(cfg.mask_urls))  # before boxes are measured
                check_private(page.evaluate(PAGE_TEXT_JS), cfg)
                page.evaluate("() => window.scrollTo(0, 0)")
                raw_path = tmp / f"{shot.name}-raw.png"
                page.screenshot(path=str(raw_path), full_page=shot.full_page)
                crop = None
                if shot.crop:
                    r = page.locator(shot.crop).first.bounding_box()
                    if r:
                        crop = scale_box((r["x"], r["y"], r["width"], r["height"]), cfg.dpr)
                        with Image.open(raw_path) as img:
                            img.crop((int(crop.x), int(crop.y), int(crop.right),
                                      int(crop.bottom))).save(raw_path)  # fmt: skip
                specs = [s.__dict__ for s in shot.callouts]
                raw = page.evaluate(RESOLVE_JS, specs) if specs else []
                targets, dropped = _targets(shot.callouts, raw, cfg.dpr, crop)
                result.dropped_callouts += [f"{shot.name}: {label}" for label in dropped]
                file = f"{shot.name}.png"
                callouts = annotate(raw_path, out / file, targets, colours=colours)
                entries.append(
                    image_entry(
                        file=file,
                        screen=shot.screen,
                        moment=shot.moment,
                        alt=shot.alt,
                        callouts=callouts,
                        source_run_id=source_run,
                        recorded_or_live=kind,
                    )  # fmt: skip
                )
                result.written.append(file)
            browser.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    path = out / "images.json"
    save_entries(path, merge_entries(load_entries(path), entries))
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--kind", choices=("recorded", "live"), default="recorded")
    ap.add_argument("--source-run", default=None)
    a = ap.parse_args(argv)
    cfg = load_config(a.config)
    try:
        res = capture(cfg, a.out, only=set(a.only) if a.only else None, kind=a.kind,
                      source_run=a.source_run)  # fmt: skip
    except PrivacyError as err:
        print(f"x {err}; nothing saved for that shot", file=sys.stderr)
        return 1
    for name in res.written:
        print(f"wrote {name}")
    for label in res.dropped_callouts:
        print(f"! callout dropped (target missing or its text differs): {label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
