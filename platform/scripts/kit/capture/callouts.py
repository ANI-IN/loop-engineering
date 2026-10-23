"""Numbered callouts on a captured image: a filled circle with the number, an arrow to the target,
and an outline around the target.

Targets are boxes in image pixels (capture.py resolves DOM selectors or text matches to bounding
boxes and scales them by the device pixel ratio). The colours are the app's accent and background
tokens (read from its stylesheet with `palette()`, or a neutral blue on near-black), so the
circles read on a dark app and on a white page. The radius grows with the image width, so a
circle stays about 5 mm across when the image is printed at page width. Circles are placed so
that no arrow crosses another arrow or circle (`capturelib.conflicts`).
"""

from __future__ import annotations

import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from capturelib import (
    Box,
    Placement,
    arrow_head,
    callout_radius,
    conflicts,
    font_path,
    place_callout,
)
from PIL import Image, ImageDraw, ImageFont, ImageStat

FALLBACK = {"accent": "#4f8fd6", "bg": "#101418"}


def css_tokens(css: str) -> dict[str, str]:
    """The `--name: #rrggbb;` colour tokens of a stylesheet's :root."""
    found = re.finditer(r"--([a-z0-9-]+):\s*(#[0-9a-fA-F]{3,8})", css)
    return {m.group(1): m.group(2) for m in found}


def palette(
    css_path: Path | None, accent_token: str = "accent", bg_token: str = "bg"
) -> dict[str, str]:
    """{"accent", "bg"} from the app's stylesheet tokens, else the neutral FALLBACK."""
    if css_path is None or not Path(css_path).is_file():
        return dict(FALLBACK)
    tokens = css_tokens(Path(css_path).read_text(encoding="utf-8"))
    return {
        "accent": tokens.get(accent_token, FALLBACK["accent"]),
        "bg": tokens.get(bg_token, FALLBACK["bg"]),
    }


@dataclass(frozen=True)
class Target:
    box: Box  # image pixels
    text: str  # what the numbered list beside the image says


def annotate(
    src: Path,
    out: Path,
    targets: list[Target],
    *,
    colours: dict[str, str] | None = None,
    outline: bool = True,
) -> list[dict[str, Any]]:
    """Draw callouts 1..n on `src`, save to `out`; return [{n, x, y, text}] (circle centres)."""
    src, out = Path(src), Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not targets:
        if src.resolve() != out.resolve():
            shutil.copyfile(src, out)
        return []
    c = colours or dict(FALLBACK)
    blue, dark = c["accent"], c["bg"]
    img = Image.open(src).convert("RGB")
    w, h = img.size
    r = callout_radius(w)
    line = max(4, r // 7)
    path = font_path("DejaVuSans-Bold.ttf")
    font = ImageFont.truetype(path, int(r * 1.15)) if path else ImageFont.load_default(int(r))
    d = ImageDraw.Draw(img)
    gray = img.convert("L")

    def busy(cx: float, cy: float) -> float:
        """How much is drawn under a circle there (pixel spread): low on an empty background."""
        area = gray.crop((int(cx - r), int(cy - r), int(cx + r), int(cy + r)))
        return float(ImageStat.Stat(area).stddev[0])

    def busy_line(cx: float, cy: float, tx: float, ty: float) -> float:
        """How much text an arrow from the circle to the target would cross."""
        total = 0.0
        for k in range(1, 9):
            f = k / 9
            x, y = cx + (tx - cx) * f, cy + (ty - cy) * f
            area = gray.crop((int(x - 6), int(y - 6), int(x + 6), int(y + 6)))
            total += float(ImageStat.Stat(area).stddev[0])
        return total / 4

    boxes = [t.box for t in targets]

    def layout(order: list[int]) -> list[Placement]:
        taken: list[tuple[float, float]] = []
        segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
        out: dict[int, Placement] = {}
        for i in order:
            p = place_callout(
                targets[i].box,
                w,
                h,
                r,
                taken,
                avoid=boxes,
                cost=busy,
                segments=segments,
                line_cost=busy_line,
            )
            taken.append((p.cx, p.cy))
            segments.append(((p.cx, p.cy), (p.tx, p.ty)))
            out[i] = p
        return [out[i] for i in range(len(targets))]

    # Numbers follow the targets' order; the circles are placed in the order that leaves no arrow
    # crossing another arrow or circle (as given, top to bottom, left to right, reversed).
    idx = list(range(len(targets)))
    orders = [
        idx,
        sorted(idx, key=lambda i: (boxes[i].y, boxes[i].x)),
        sorted(idx, key=lambda i: (boxes[i].x, boxes[i].y)),
        idx[::-1],
    ]
    best: list[Placement] | None = None
    for order in orders:
        trial = layout(order)
        if best is None or conflicts(trial, r) < conflicts(best, r):
            best = trial
        if conflicts(best, r) == 0:
            break
    placed = list(zip(targets, best or [], strict=True))
    if best and conflicts(best, r):
        print(f"! {out.name}: an arrow still crosses another arrow or circle", file=sys.stderr)
    # Outlines and arrows first, circles on top, so no arrow crosses a number.
    for t, p in placed:
        if outline:
            b = t.box.inflate(line)
            d.rounded_rectangle(
                (b.x, b.y, b.right, b.bottom), radius=line * 2, outline=dark, width=line + 4
            )
            d.rounded_rectangle(
                (b.x, b.y, b.right, b.bottom), radius=line * 2, outline=blue, width=line
            )
        if (p.tx, p.ty) != (p.cx, p.cy):
            head = max(r * 0.7, 18)
            tail = (p.cx, p.cy)
            dx, dy = p.tx - p.cx, p.ty - p.cy
            dist = max((dx * dx + dy * dy) ** 0.5, 1.0)
            end = (p.tx - dx / dist * head * 0.8, p.ty - dy / dist * head * 0.8)
            d.line([tail, end], fill=dark, width=line + 6)
            d.polygon(arrow_head((p.tx, p.ty), tail, head + 4), fill=dark)
            d.line([tail, end], fill=blue, width=line)
            d.polygon(arrow_head((p.tx, p.ty), tail, head), fill=blue)
    out_list = []
    for n, (t, p) in enumerate(placed, start=1):
        ring = r + max(3, r // 9)
        d.ellipse((p.cx - ring, p.cy - ring, p.cx + ring, p.cy + ring), fill=dark)
        d.ellipse((p.cx - r, p.cy - r, p.cx + r, p.cy + r), fill=blue)
        d.text((p.cx, p.cy), str(n), font=font, fill=dark, anchor="mm")
        out_list.append({"n": n, "x": round(p.cx), "y": round(p.cy), "text": t.text})
    img.save(out)
    return out_list
