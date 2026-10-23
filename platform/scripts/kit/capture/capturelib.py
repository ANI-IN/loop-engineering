"""Pure helpers for the guide image tooling (capture.py, term_render.py, callouts.py).

- Redaction: host paths (`/home/<user>`, `/Users/<user>`, `/mnt/c/Users/<user>`,
  `C:\\Users\\<user>`) become `~`; configured user names become `<user>`.
- Refusal: key-like text (`sk-...`, `lsv2_...`, `ghp_...`, `AKIA...`, bearer tokens, private key
  blocks) raises SecretFound; the message never repeats the key.
- Masking: links that match configured URL patterns (a tracing or dashboard host whose links
  carry account ids) are shortened to `host/…`.
- Terminal text: line ranges ("1-20,40", "-12" for the last 12), ANSI stripping, wrapping.
- Callout geometry: boxes, a radius that stays legible at print size, a circle placed next to its
  target (inside the image, clear of the target and of other circles), an arrow to the target edge.
- images.json: one entry per image, checked ({file, screen, moment, alt, callouts, source_run_id,
  recorded_or_live}).
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Redaction and refusal ------------------------------------------------------------------------

_HOST_PATHS = (
    re.compile(r"/home/[A-Za-z0-9._-]+"),
    re.compile(r"(?<![\w/])/Users/[A-Za-z0-9._-]+"),
    re.compile(r"/mnt/[A-Za-z]/Users/[^/\\\s\"'<>]+", re.IGNORECASE),
    re.compile(r"\b[A-Za-z]:\\Users\\[^\\\s\"'<>]+", re.IGNORECASE),
)
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b")
_SECRETS = (
    ("sk-…", re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{16,}")),
    ("lsv2_…", re.compile(r"(?<![A-Za-z0-9])lsv2_[A-Za-z0-9_]{10,}")),
    ("ls__…", re.compile(r"(?<![A-Za-z0-9])ls__[A-Za-z0-9]{20,}")),
    ("bearer token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{20,}")),
    ("ghp_…", re.compile(r"(?<![A-Za-z0-9])gh[pousr]_[A-Za-z0-9]{30,}")),
    ("AKIA…", re.compile(r"(?<![A-Za-z0-9])AKIA[0-9A-Z]{16}(?![0-9A-Z])")),
    ("private key", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")),
)


class SecretFound(ValueError):
    """Key-like text in something about to be rendered or saved."""


def redact_paths(text: str) -> str:
    """Host home folders become `~`; the rest of the path stays."""
    for pattern in _HOST_PATHS:
        text = pattern.sub("~", text)
    return text


def _name_re(name: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9]){re.escape(name)}(?![A-Za-z0-9])")


def redact_users(text: str, users: Iterable[str]) -> str:
    """Each configured user name, as a whole word (or before `-`/`.`), becomes `<user>`."""
    for name in users:
        if name:
            text = _name_re(name).sub("<user>", text)
    return text


def user_hits(text: str, users: Iterable[str]) -> list[str]:
    return [m.group(0) for name in users if name for m in _name_re(name).finditer(text)]


def host_path_hits(text: str) -> list[str]:
    """Every host path in `text` (a user's home folder on Linux, WSL, or Windows)."""
    return [m.group(0) for pattern in _HOST_PATHS for m in pattern.finditer(text)]


_RESERVED_MAIL = re.compile(
    r"@(?:[A-Za-z0-9-]+\.)*(?:test|example|invalid|localhost|example\.(?:com|org|net))$",
    re.IGNORECASE,
)


def personal_hits(text: str, users: Iterable[str] = ()) -> list[str]:
    """Host paths, configured user names, and email addresses: nothing of this may show on an
    image. Addresses at reserved test domains (seed users such as admin@acme.test) are not
    personal."""
    mails = [m.group(0) for m in _EMAIL.finditer(text)]
    found = host_path_hits(text) + user_hits(text, users)
    return found + [m for m in mails if not _RESERVED_MAIL.search(m)]


_UUID = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE
)


def account_hits(text: str, url_patterns: Iterable[str] = ()) -> list[str]:
    """UUID-like ids (org, project, run) and links matching `url_patterns` (regexes for a
    vendor's workspace links): account details that no image may show."""
    found = [m.group(0) for m in _UUID.finditer(text)]
    for pattern in url_patterns:
        found += [m.group(0) for m in re.finditer(pattern, text, re.IGNORECASE)]
    return found


_URL = re.compile(r"https?://[^\s\"'<>]+")


def mask_urls(text: str, patterns: Iterable[str]) -> str:
    """Every link that matches one of `patterns` becomes `<host>/…`; other links stay."""
    compiled = [re.compile(p, re.IGNORECASE) for p in patterns]

    def one(m: re.Match[str]) -> str:
        url = m.group(0)
        if not any(c.search(url) for c in compiled):
            return url
        return url.split("://", 1)[1].split("/", 1)[0] + "/…"

    return _URL.sub(one, text)


def find_secrets(text: str) -> list[tuple[str, int]]:
    """(kind, line number) for each key-like string; never the string itself."""
    found = []
    for kind, pattern in _SECRETS:
        for m in pattern.finditer(text):
            found.append((kind, text.count("\n", 0, m.start()) + 1))
    return found


def check_no_secrets(text: str, what: str = "text") -> None:
    found = find_secrets(text)
    if found:
        where = ", ".join(f"{kind} on line {line}" for kind, line in found)
        raise SecretFound(f"refusing to render {what}: key-like text ({where})")


# Terminal text --------------------------------------------------------------------------------

_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07")


@dataclass(frozen=True)
class Gap:
    """Lines left out of a selection."""

    count: int


def parse_ranges(spec: str) -> list[tuple[int, int]]:
    """ "1-20,40" -> [(1, 20), (40, 40)]; "-12" -> [(-12, -1)] (the last 12 lines)."""
    out: list[tuple[int, int]] = []
    for part in (p.strip() for p in spec.split(",")):
        if not part:
            continue
        if re.fullmatch(r"-\d+", part):
            out.append((int(part), -1))
            continue
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", part)
        if not m:
            raise ValueError(f"bad line range {part!r}")
        a, b = int(m.group(1)), int(m.group(2) or m.group(1))
        if a < 1 or b < a:
            raise ValueError(f"bad line range {part!r}")
        out.append((a, b))
    return out


def select_lines(
    lines: Sequence[str], ranges: Sequence[tuple[int, int]]
) -> list[tuple[int, str] | Gap]:
    """The chosen lines as (line number, text), with a Gap for each run of left-out lines."""
    n = len(lines)
    if not ranges:
        return [(i + 1, line) for i, line in enumerate(lines)]
    keep: set[int] = set()
    for a, b in ranges:
        if a < 0:
            a, b = max(1, n + a + 1), n + b + 1
        keep.update(range(max(1, a), min(n, b) + 1))
    out: list[tuple[int, str] | Gap] = []
    skipped = 0
    for i, line in enumerate(lines, start=1):
        if i in keep:
            if skipped:
                out.append(Gap(skipped))
                skipped = 0
            out.append((i, line))
        else:
            skipped += 1
    if skipped:
        out.append(Gap(skipped))
    return out


def clean_line(line: str) -> str:
    """No ANSI codes, carriage-return overwrites resolved, tabs expanded."""
    line = _ANSI.sub("", line)
    if "\r" in line:
        line = line.rstrip("\r").split("\r")[-1]
    return line.expandtabs(8)


def wrap_line(line: str, width: int = 100) -> list[str]:
    """Wrap at a space when one is in the second half of the row, else hard at `width`."""
    parts: list[str] = []
    rest = line
    while len(rest) > width:
        cut = rest.rfind(" ", 0, width + 1)
        if cut >= width // 2:
            parts.append(rest[:cut])
            rest = rest[cut + 1 :]
        else:
            parts.append(rest[:width])
            rest = rest[width:]
    parts.append(rest)
    return parts


# Callout geometry -----------------------------------------------------------------------------

MIN_RADIUS = 34
INNER_MAX_COST = 12.0  # a circle goes on its own target only where that part is empty


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    def inflate(self, m: float) -> Box:
        return Box(self.x - m, self.y - m, self.w + 2 * m, self.h + 2 * m)

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px <= self.right and self.y <= py <= self.bottom

    def clamp(self, px: float, py: float) -> tuple[float, float]:
        return min(max(px, self.x), self.right), min(max(py, self.y), self.bottom)

    def on_edge(self, px: float, py: float, tol: float = 1.5) -> bool:
        if not self.inflate(tol).contains(px, py):
            return False
        return (
            min(abs(px - self.x), abs(px - self.right), abs(py - self.y), abs(py - self.bottom))
            <= tol
        )


def scale_box(box: Sequence[float] | Box, dpr: float) -> Box:
    x, y, w, h = (box.x, box.y, box.w, box.h) if isinstance(box, Box) else box
    return Box(x * dpr, y * dpr, w * dpr, h * dpr)


def box_in_crop(box: Box, crop: Box) -> Box | None:
    """`box` in the crop's coordinates, cut to the crop; None when it lies outside."""
    x0, y0 = max(box.x, crop.x), max(box.y, crop.y)
    x1, y1 = min(box.right, crop.right), min(box.bottom, crop.bottom)
    if x1 <= x0 or y1 <= y0:
        return None
    return Box(x0 - crop.x, y0 - crop.y, x1 - x0, y1 - y0)


def target_matches(expected: str | None, found: str) -> bool:
    """Whether the element a callout points at holds the text the callout is about (case and
    spacing ignored); with nothing expected, the element must at least show some text."""
    norm = " ".join(found.split()).casefold()
    if expected is None:
        return bool(norm)
    return " ".join(expected.split()).casefold() in norm


def reading_order(boxes: Sequence[Box], row: float) -> list[int]:
    """Indexes of `boxes` top to bottom, then left to right (rows `row` pixels high)."""
    rows: list[list[int]] = []
    for i in sorted(range(len(boxes)), key=lambda i: boxes[i].y):
        if rows and boxes[i].y - boxes[rows[-1][0]].y <= row:
            rows[-1].append(i)
        else:
            rows.append([i])
    return [i for r in rows for i in sorted(r, key=lambda i: boxes[i].x)]


def stack_layout(pieces: Sequence[Box], gap: float) -> tuple[list[float], float, float]:
    """Pieces of a page stacked top to bottom: each piece's y in the stacked image, the
    stacked width (the widest piece), and the stacked height."""
    ys, y = [], 0.0
    for p in pieces:
        ys.append(y)
        y += p.h + gap
    return ys, max((p.w for p in pieces), default=0.0), max(0.0, y - gap)


def map_to_stack(box: Box, pieces: Sequence[Box], ys: Sequence[float]) -> Box | None:
    """A page box in the stacked image: in the first piece that holds most of it."""
    for p, y in zip(pieces, ys, strict=True):
        part = box_in_crop(box, p)
        if part is not None and part.w * part.h >= 0.5 * box.w * box.h:
            return Box(part.x, part.y + y, part.w, part.h)
    return None


def callout_radius(image_width: int) -> int:
    """About 1.6% of the width: a 3840 px screenshot printed 17 cm wide gets 5 mm circles."""
    return max(MIN_RADIUS, round(image_width * 0.016))


@dataclass(frozen=True)
class Placement:
    cx: float
    cy: float
    tx: float  # arrow tip (on the target's edge; the centre itself when inside the target)
    ty: float


def place_callout(
    target: Box,
    width: int,
    height: int,
    radius: float,
    taken: Iterable[tuple[float, float]],
    avoid: Iterable[Box] = (),
    cost: Callable[[float, float], float] | None = None,
    segments: Iterable[tuple[tuple[float, float], tuple[float, float]]] = (),
    line_cost: Callable[[float, float, float, float], float] | None = None,
) -> Placement:
    """A circle next to `target`: inside the image, outside the target, clear of `taken`.

    Among the free spots, the nearest preferred side wins, unless `cost` (how busy the image is
    under a circle there) or covering one of the `avoid` boxes (the other targets) makes a later
    spot better."""
    taken = list(taken)
    segments = list(segments)
    r = radius
    pad = max(r * 0.8, 24)
    mx = target.x + min(target.w / 2, 3 * r)
    my = target.y + target.h / 2
    candidates: list[tuple[float, float]] = []
    for k in (1, 2, 3, 4):
        d = (r + pad) * k
        candidates += [
            (target.x - d, my),
            (mx, target.y - d),
            (target.x - d * 0.75, target.y - d * 0.75),
            (target.right + d, my),
            (mx, target.bottom + d),
            (target.x - d * 0.75, target.bottom + d * 0.75),
            (target.right + d * 0.75, target.y - d * 0.75),
        ]

    def free(cx: float, cy: float) -> bool:
        if not (r <= cx <= width - r and r <= cy <= height - r):
            return False
        if target.inflate(r).contains(cx, cy):
            return False
        return all(math.hypot(cx - ox, cy - oy) >= 2 * r + 8 for ox, oy in taken)

    def inside(cx: float, cy: float) -> tuple[float, float]:
        return min(max(cx, r), width - r), min(max(cy, r), height - r)

    avoid = [b.inflate(r * 0.6) for b in avoid if b != target]
    best: tuple[float, float, float] | None = None
    pool = candidates + [inside(cx, cy) for cx, cy in candidates]
    # Last resort before the corner: on the target's own right end (a wide row whose right part
    # is empty), with no arrow; only chosen when `cost` finds it emptier than the spots outside.
    interior = [(target.right - r - 8, my)] if cost is not None and target.w >= 6 * r else []

    def ok(cx: float, cy: float, inner: bool) -> bool:
        if inner:
            return (r <= cx <= width - r and r <= cy <= height - r) and all(
                math.hypot(cx - ox, cy - oy) >= 2 * r + 8 for ox, oy in taken
            )
        return free(cx, cy)

    for i, (cx, cy) in enumerate(pool + interior):
        inner = i >= len(pool)
        if not ok(cx, cy, inner):
            continue
        if inner and cost is not None and cost(cx, cy) > INNER_MAX_COST:
            continue
        score = (15.0 if inner else i * 1.5) + (3 * cost(cx, cy) if cost else 0.0)
        score += 1000 * sum(1 for b in avoid if b.contains(cx, cy))
        tx, ty = target.clamp(cx, cy)
        score += 4 * math.hypot(cx - tx, cy - ty) / r  # short arrows
        if line_cost is not None and not inner:
            score += line_cost(cx, cy, tx, ty)  # arrows over empty background
        score += 300 * sum(1 for ox, oy in taken if _seg_dist((cx, cy), (tx, ty), (ox, oy)) < r + 4)
        score += 300 * sum(1 for a, b in segments if _crosses((cx, cy), (tx, ty), a, b))
        # ... and the circle itself sits on no earlier arrow.
        score += 300 * sum(1 for a, b in segments if a != b and _seg_dist(a, b, (cx, cy)) < r + 4)
        if best is None or score < best[0]:
            best = (score, cx, cy)
        if cost is None and not avoid and not taken and not segments:
            break
    if best is not None:
        _, cx, cy = best
        if target.contains(cx, cy):
            return Placement(cx, cy, cx, cy)
        tx, ty = target.clamp(cx, cy)
        return Placement(cx, cy, tx, ty)
    # No room outside: inside the target's top-left corner, kept in the image.
    cx = min(max(target.x + r + 6, r), width - r)
    cy = min(max(target.y + r + 6, r), height - r)
    for ox, oy in taken:
        if math.hypot(cx - ox, cy - oy) < 2 * r + 8:
            cx = min(cx + 2 * r + 8, width - r)
    return Placement(cx, cy, cx, cy)


def _seg_dist(a: tuple[float, float], b: tuple[float, float], p: tuple[float, float]) -> float:
    """Distance from point p to the segment a-b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = dx * dx + dy * dy
    t = 0.0 if n == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / n))
    return math.hypot(a[0] + t * dx - p[0], a[1] + t * dy - p[1])


def _crosses(
    p1: tuple[float, float],
    p2: tuple[float, float],
    q1: tuple[float, float],
    q2: tuple[float, float],
) -> bool:
    """Whether segments p1-p2 and q1-q2 cross."""

    def side(a, b, c) -> float:
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    d1, d2 = side(q1, q2, p1), side(q1, q2, p2)
    d3, d4 = side(p1, p2, q1), side(p1, p2, q2)
    return d1 * d2 < 0 and d3 * d4 < 0


def conflicts(placements: Sequence[Placement], radius: float) -> int:
    """Pairs where one arrow crosses another arrow or runs through another callout's circle."""
    n = 0
    for i, a in enumerate(placements):
        for j, b in enumerate(placements):
            if i == j:
                continue
            seg_a = ((a.cx, a.cy), (a.tx, a.ty))
            if (a.tx, a.ty) != (a.cx, a.cy) and _seg_dist(*seg_a, (b.cx, b.cy)) < radius + 4:
                n += 1
            if i < j and _crosses(*seg_a, (b.cx, b.cy), (b.tx, b.ty)):
                n += 1
    return n


def arrow_head(
    tip: tuple[float, float], tail: tuple[float, float], size: float
) -> list[tuple[float, float]]:
    """Triangle [tip, left, right] pointing from `tail` towards `tip`."""
    dx, dy = tip[0] - tail[0], tip[1] - tail[1]
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    bx, by = tip[0] - ux * size, tip[1] - uy * size
    px, py = -uy * size * 0.55, ux * size * 0.55
    return [tip, (bx + px, by + py), (bx - px, by - py)]


FONT_DIRS = (Path("/usr/share/fonts/truetype/dejavu"), Path("/usr/share/fonts/dejavu"))


def font_path(name: str) -> str | None:
    """A DejaVu font file ("DejaVuSansMono.ttf"), or None when it is not installed."""
    for folder in FONT_DIRS:
        if (folder / name).is_file():
            return str(folder / name)
    return None


# images.json ----------------------------------------------------------------------------------

KINDS = ("recorded", "live")


def image_entry(
    *,
    file: str,
    screen: int | str | None,
    moment: str,
    alt: str,
    callouts: Sequence[dict[str, Any]],
    source_run_id: str | None,
    recorded_or_live: str,
) -> dict[str, Any]:
    """One checked images.json entry, keys in the order the PDF build expects."""
    if not file.endswith(".png") or "/" in file or "\\" in file or ".." in file:
        raise ValueError(f"file must be a bare .png name: {file!r}")
    alt = alt.strip()
    if len(alt.split()) < 6 or not alt.endswith("."):
        raise ValueError(f"alt text must be a concrete sentence: {alt!r}")
    for text in (alt, moment):
        if personal_hits(text) or find_secrets(text):
            raise ValueError("alt or moment text holds a host path, email, or key")
    if recorded_or_live not in KINDS:
        raise ValueError(f"recorded_or_live must be one of {KINDS}")
    clean = []
    for i, c in enumerate(callouts, start=1):
        if int(c["n"]) != i:
            raise ValueError(f"callouts must be numbered 1, 2, ...: got {c['n']} at {i}")
        if not str(c.get("text", "")).strip():
            raise ValueError(f"callout {i} has no text")
        clean.append(
            {
                "n": i,
                "x": int(round(c["x"])),
                "y": int(round(c["y"])),
                "text": str(c["text"]).strip(),
            }
        )
    return {
        "file": file,
        "screen": screen,
        "moment": moment,
        "alt": alt,
        "callouts": clean,
        "source_run_id": source_run_id,
        "recorded_or_live": recorded_or_live,
    }


def merge_entries(
    existing: Sequence[dict[str, Any]], new: Sequence[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Entries of `new` replace those with the same file; others are appended in order."""
    out = list(existing)
    index = {e["file"]: i for i, e in enumerate(out)}
    for e in new:
        if e["file"] in index:
            out[index[e["file"]]] = e
        else:
            index[e["file"]] = len(out)
            out.append(e)
    return out


def load_entries(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []


def save_entries(path: Path, entries: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(list(entries), indent=2, ensure_ascii=False) + "\n"
    if personal_hits(text) or find_secrets(text):
        raise ValueError(f"{path.name}: refusing to write a host path, email, or key")
    path.write_text(text, encoding="utf-8")
