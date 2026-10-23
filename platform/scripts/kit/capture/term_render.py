"""Render terminal output as a clean terminal-style PNG for a guide.

Dark theme, DejaVu Sans Mono, a prompt row with the command, rows wrapped
at about 100 columns, 2x scale. Host home folders are redacted to `~` and `--user` names to
`<user>`; key-like text (sk-..., lsv2_..., ghp_...) is refused and nothing is written.

    uv run python tools/capture/term_render.py terminal.txt out.png \
        --command "make demo" [--lines -12] [--highlight 3,5-7] [--title "Terminal 2"]

`--lines` picks line ranges of the input ("1-20,40"; "-12" is the last 12 lines); left-out lines
show as one muted "... N lines" row. `--highlight` marks input lines with a band and a blue bar.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from capturelib import (
    Gap,
    check_no_secrets,
    clean_line,
    font_path,
    host_path_hits,
    parse_ranges,
    redact_paths,
    redact_users,
    select_lines,
    wrap_line,
)
from PIL import Image, ImageDraw, ImageFont

BG = "#0b0f14"
BAR = "#1d2530"
TEXT = "#f5f7fa"
MUTED = "#b8c2cf"
PROMPT = "#5ee08a"
ACCENT = "#7fd7ff"
BAND = "#1a2533"


@dataclass(frozen=True)
class Row:
    kind: str  # prompt, prompt-cont, line, cont, gap
    text: str
    highlight: bool = False
    lineno: int | None = None


def _ranges(ranges: str | list[tuple[int, int]] | None) -> list[tuple[int, int]]:
    if ranges is None:
        return []
    return parse_ranges(ranges) if isinstance(ranges, str) else list(ranges)


def prepare_rows(
    text: str,
    *,
    command: str | None = None,
    width: int = 100,
    ranges: str | list[tuple[int, int]] | None = None,
    highlight: Iterable[int] = (),
    users: Iterable[str] = (),
) -> list[Row]:
    """The rows to draw. Raises SecretFound on key-like text in the text or the command."""
    check_no_secrets(text, "the terminal text")
    if command:
        check_no_secrets(command, "the command")
    marked = set(highlight)
    rows: list[Row] = []
    if command:
        for i, part in enumerate(
            wrap_line("$ " + redact_users(redact_paths(command.strip()), users), width)
        ):
            rows.append(Row("prompt" if i == 0 else "prompt-cont", part))
    lines = [clean_line(redact_users(redact_paths(line), users)) for line in text.splitlines()]
    if command and lines and lines[0].strip() in (command.strip(), "$ " + command.strip()):
        lines = lines[1:]  # the capture already starts with the command: show it once
    picked = select_lines(lines, _ranges(ranges))
    for k, item in enumerate(picked):
        if isinstance(item, Gap):
            n = item.count
            plural = "line" if n == 1 else "lines"
            if k == 0:
                words = f"… {n} {plural} above"
            elif k == len(picked) - 1:
                words = f"… {n} {plural} below"
            else:
                words = f"… {n} {plural} left out"
            rows.append(Row("gap", words))
            continue
        lineno, line = item
        for i, part in enumerate(wrap_line(line, width)):
            rows.append(Row("line" if i == 0 else "cont", part, lineno in marked, lineno))
    leaks = [h for r in rows for h in host_path_hits(r.text)]
    if leaks:
        raise ValueError("a host path survived redaction")
    return rows


def _font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = font_path(name)
    return ImageFont.truetype(path, size) if path else ImageFont.load_default(size)


def render(
    text: str,
    out: Path,
    *,
    command: str | None = None,
    width: int = 100,
    scale: int = 2,
    ranges: str | list[tuple[int, int]] | None = None,
    highlight: Iterable[int] = (),
    title: str = "Terminal",
    users: Iterable[str] = (),
) -> Path:
    """Write the PNG; nothing is written when the text or command holds key-like text."""
    rows = prepare_rows(
        text, command=command, width=width, ranges=ranges, highlight=highlight, users=users
    )
    size = 15 * scale
    regular = _font("DejaVuSansMono.ttf", size)
    bold = _font("DejaVuSansMono-Bold.ttf", size)
    italic = _font("DejaVuSansMono-Oblique.ttf", size)
    ui = _font("DejaVuSans.ttf", 13 * scale)
    char_w = regular.getlength("M")
    line_h = round(size * 1.42)
    pad = 18 * scale
    bar_h = 30 * scale
    img_w = int(round(2 * pad + width * char_w))
    img_h = bar_h + 2 * pad + max(1, len(rows)) * line_h
    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    radius = 10 * scale
    d.rounded_rectangle((0, 0, img_w - 1, img_h - 1), radius=radius, fill=BG)
    d.rounded_rectangle((0, 0, img_w - 1, bar_h + radius), radius=radius, fill=BAR)
    d.rectangle((0, bar_h, img_w - 1, bar_h + radius), fill=BG)
    for i, colour in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        cx, cy, r = pad + i * 20 * scale, bar_h // 2, 6 * scale
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=colour)
    d.text((img_w / 2, bar_h / 2), title, font=ui, fill=MUTED, anchor="mm")
    y = bar_h + pad
    for row in rows:
        if row.highlight:
            d.rectangle((pad // 2, y, img_w - pad // 2, y + line_h - 1), fill=BAND)
            d.rectangle((pad // 2, y, pad // 2 + 4 * scale, y + line_h - 1), fill=ACCENT)
        x = pad
        if row.kind == "prompt":
            d.text((x, y), "$", font=bold, fill=PROMPT)
            d.text((x + 2 * char_w, y), row.text[2:], font=bold, fill=TEXT)
        elif row.kind == "prompt-cont":
            d.text((x, y), row.text, font=bold, fill=TEXT)
        elif row.kind == "gap":
            d.text((x, y), row.text, font=italic, fill=MUTED)
        else:
            d.text((x, y), row.text, font=regular, fill=TEXT)
        y += line_h
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


def _numbers(spec: str) -> set[int]:
    return {n for a, b in parse_ranges(spec) for n in range(a, b + 1)} if spec else set()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("source", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--command", default=None)
    p.add_argument("--lines", default=None, help='"1-20,40" or "-12" (last 12 lines)')
    p.add_argument("--highlight", default="", help="input line numbers, e.g. 3,5-7")
    p.add_argument("--width", type=int, default=100)
    p.add_argument("--scale", type=int, default=2)
    p.add_argument("--title", default="Terminal")
    p.add_argument("--user", action="append", default=[], help="a user name to redact")
    a = p.parse_args(argv)
    text = a.source.read_text(encoding="utf-8", errors="replace")
    first, _, rest = text.partition("\n")
    if a.command is None and first.startswith("$ "):  # the capture's own prompt line
        a.command, text = first[2:].strip(), rest
    try:
        render(
            text,
            a.out,
            command=a.command,
            width=a.width,
            scale=a.scale,
            ranges=a.lines,
            highlight=_numbers(a.highlight),
            title=a.title,
            users=a.user,
        )
    except ValueError as err:
        print(f"x {err}", file=sys.stderr)
        return 1
    print(f"wrote {a.out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
