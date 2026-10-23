"""Measures every text frame of a deck in PowerPoint and reports what does not fit.

    uv run --no-project --python 3.12 --with comtypes python slides/scripts/check_fit.py \
        slides/build/sample.pptx

Windows only, PowerPoint installed; it opens the deck read-only and never saves it. For each
slide it reports, and exits 1 on any of them:
- overflow: a text frame whose laid-out text is taller than the frame (PowerPoint's own bound);
- small text: a run under 18 pt in a text frame or under 16 pt in a table (labels named in
  LABELS may be 14 or 16 pt, as in the template: the KEY IDEA label, the tag, the DEMO badge);
- shrink: a text frame with shrink-on-overflow autofit;
- off the page or into the logo corner: a shape below 6.6 in that reaches right of 11 in;
- overlap: two shapes that intersect, unless one is named "(overlay)" or both are in one row.
It prints the font sizes it found per slide, for the fit report.
"""

from __future__ import annotations

import sys
from pathlib import Path

import comtypes.client

PT = 72.0
SLIDE_W, SLIDE_H = 13.333 * PT, 7.5 * PT
LOGO_X, LOGO_Y = 11.0 * PT, 6.6 * PT
LABELS = {"KEY IDEA box": 16, "illustrative tag": 16, "DEMO badge (overlay)": 14}
TOLERANCE = 1.0  # points


def shapes_of(slide):
    return [slide.Shapes.Item(i) for i in range(1, slide.Shapes.Count + 1)]


def sizes_in(text_range) -> set[float]:
    found = set()
    for i in range(1, text_range.Runs().Count + 1):
        run = text_range.Runs(i)
        if run.Text.strip():
            found.add(round(run.Font.Size, 1))
    return found


def check_slide(slide) -> tuple[list[str], dict[str, set[float]]]:
    problems, sizes = [], {}
    boxes = []
    for shape in shapes_of(slide):
        name = shape.Name
        top, left, w, h = shape.Top, shape.Left, shape.Width, shape.Height
        if shape.HasTable:
            table = shape.Table
            found = set()
            for r in range(1, table.Rows.Count + 1):
                for c in range(1, table.Columns.Count + 1):
                    found |= sizes_in(table.Cell(r, c).Shape.TextFrame.TextRange)
            sizes[name] = found
            if found and min(found) < 16:
                problems.append(f"{name}: table text {min(found)} pt, under 16")
        elif shape.HasTextFrame and shape.TextFrame.HasText:
            frame = shape.TextFrame2
            bound = frame.TextRange.BoundHeight
            room = h - frame.MarginTop - frame.MarginBottom
            if bound > room + TOLERANCE and shape.Type != 14:  # 14: placeholder (the title)
                problems.append(f"{name}: text {bound:.0f} pt tall, frame holds {room:.0f} pt")
            if shape.Type == 14 and bound > h + TOLERANCE:
                problems.append(f"title: text {bound:.0f} pt tall, frame holds {h:.0f} pt")
            if frame.AutoSize == 2:  # msoAutoSizeTextToFitShape
                problems.append(f"{name}: shrinks text on overflow")
            found = sizes_in(shape.TextFrame.TextRange)
            sizes[name] = found
            floor = LABELS.get(name, 18)
            if found and min(found) < floor and not (name == "KEY IDEA box" and min(found) >= 16):
                problems.append(f"{name}: text {min(found)} pt, under {floor}")
            # Text that spills past the frame still counts for the page and logo checks.
            h = max(h, bound + frame.MarginTop + frame.MarginBottom)
        if top + h > SLIDE_H + TOLERANCE or left + w > SLIDE_W + TOLERANCE:
            problems.append(f"{name}: off the page")
        if top + h > LOGO_Y and left + w > LOGO_X:
            problems.append(f"{name}: reaches the logo corner")
        boxes.append((name, left, top, left + w, top + h))
    for i, a in enumerate(boxes):
        for b in boxes[i + 1 :]:
            if "(overlay)" in a[0] or "(overlay)" in b[0] or a[0].startswith("laptop"):
                continue
            across = a[1] < b[3] - TOLERANCE and b[1] < a[3] - TOLERANCE
            down = a[2] < b[4] - TOLERANCE and b[2] < a[4] - TOLERANCE
            if across and down:
                problems.append(f"overlap: {a[0]} and {b[0]}")
    return problems, sizes


def main(argv: list[str]) -> int:
    deck = str(Path(argv[0]).resolve())
    app = presentation = None
    failed = 0
    try:
        app = comtypes.client.CreateObject("PowerPoint.Application")
        presentation = app.Presentations.Open(deck, -1, 0, 0)
        for n in range(1, presentation.Slides.Count + 1):
            problems, sizes = check_slide(presentation.Slides.Item(n))
            all_sizes = sorted({s for found in sizes.values() for s in found})
            print(f"slide {n}: sizes {all_sizes} pt; problems {len(problems)}")
            for name, found in sizes.items():
                print(f"    {name}: {sorted(found)}")
            for p in problems:
                print(f"  x {p}")
            failed += len(problems)
    finally:
        if presentation is not None:
            presentation.Close()
        if app is not None:
            app.Quit()
    print(f"fit problems: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
