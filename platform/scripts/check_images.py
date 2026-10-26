"""Check the published images: size, blank areas, clipped edges, and alt text.

Usage: python platform/scripts/check_images.py [--root PATH]

Every PNG in the published image folders (IMAGE_FOLDERS) is checked for:

- size: at least the minimum of its kind (MINIMUMS, each with its reason), and at most
  MAXIMUM_PIXELS, above which no page or slide can show the image readably;
- a blank area: a full-width band of rows, or a full-height band of columns, of one colour that
  covers at least BLANK_FRACTION of the image;
- a clipped edge: content cut by the top or bottom edge, seen as many colour changes along both
  of the two outermost rows (a cut line of text), where a panel or a border gives only a few;
- alt text: every Markdown image reference to the file, in any Markdown page of the repository,
  has non-empty alt text.

It prints one line per problem, then the count per kind, and exits 1 on any problem. Images are
read only; nothing is written.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from PIL import Image

REPO = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())

# The folders whose images a learner sees: pages, the guide, the published solutions, and the
# console's own screenshots (platform/ ships).
IMAGE_FOLDERS = [
    "docs/images",
    "docs/diagrams",
    "guide",
    "final-project/expected",
    "section-*/demo/expected",
    "section-*/diagrams",
    "section-*/assignment/solution/captured",
    "platform/console/screenshots",
    "platform/console/design/screenshots",
]


@dataclass(frozen=True)
class Minimum:
    width: int
    height: int
    reason: str


SCREENSHOT = Minimum(2560, 1440, "a 1280 by 720 capture at device scale factor 2")
# platform/scripts/kit/capture/term_render.py draws 100 columns of 15-point monospace at scale 2,
# about 1,878 pixels wide; the height follows the length of the output (one line is about 175).
TERMINAL = Minimum(1800, 160, "a terminal render: 100 columns at scale 2, as tall as its output")
# The diagrams are exported from their .excalidraw sources at the slide size; the vector source is
# the master, so a larger export is never needed to read them.
DIAGRAM = Minimum(1920, 1080, "a diagram exported from its Excalidraw source at 1920 by 1080")
MINIMUMS = {"screenshot": SCREENSHOT, "terminal": TERMINAL, "diagram": DIAGRAM}
# A diagram step (name-step-N.png) builds the full diagram up on a slide at a fixed layout, so the
# space of the later steps is empty on purpose: the blank-area check skips it.
_DIAGRAM_STEP = re.compile(r"-step-\d+\.png$")

# 40 million pixels is a 1,878-pixel-wide terminal render about 21,000 pixels tall: far more than
# a page or slide shows. Larger images are reported, not decoded.
MAXIMUM_PIXELS = 40_000_000
# A band of one colour across the whole image, a quarter of its height or width, is empty space a
# capture should have cropped (a page shorter than the viewport, a panel that never loaded).
BLANK_FRACTION = 0.25
# Two pixels are the same colour when no channel differs by more than this (compression noise).
SAME_COLOUR = 4
# Neighbouring pixels differ visibly when their channels differ by more than this in total.
VISIBLE_CHANGE = 90
# A cut line of text gives several colour changes per glyph; panels, borders, and scroll bars give
# a handful. This many changes on each of the two outermost rows is read as clipped content.
CLIPPED_CHANGES = 24

_MARKDOWN_IMAGE = re.compile(r"!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_HTML_IMAGE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_HTML_ATTRIBUTE = re.compile(r"\b(src|alt)\s*=\s*([\"'])(.*?)\2", re.IGNORECASE | re.DOTALL)
_FENCE = re.compile(r"^\s*(```|~~~)")


@dataclass(frozen=True)
class Problem:
    path: str
    kind: str  # size, blank area, clipped edge, alt text, unreadable
    detail: str


def image_kind(relative: str) -> str:
    """The kind of image, which sets its minimum size: screenshot, terminal, or diagram."""
    path = PurePosixPath(relative)
    if path.name.endswith("-terminal.png"):
        return "terminal"
    if "diagrams" in path.parts:
        return "diagram"
    return "screenshot"


def published_images(root: Path) -> list[Path]:
    found: set[Path] = set()
    for pattern in IMAGE_FOLDERS:
        for folder in root.glob(pattern):
            if folder.is_dir():
                found.update(p for p in folder.rglob("*.png") if p.is_file())
    return sorted(found)


def _channels(pixel: int | tuple[int, ...]) -> tuple[int, ...]:
    return pixel if isinstance(pixel, tuple) else (pixel,)


def _same(first: tuple[int, ...], second: tuple[int, ...]) -> bool:
    return all(abs(a - b) <= SAME_COLOUR for a, b in zip(first, second, strict=True))


def _uniform_colour(image: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, ...] | None:
    """The colour of the box when every pixel in it is the same colour, else None."""
    extrema = image.crop(box).getextrema()
    if isinstance(extrema[0], int):  # a single-band image gives one (low, high) pair
        extrema = (extrema,)
    if all(high - low <= SAME_COLOUR for low, high in extrema):
        return tuple(low for low, _high in extrema)
    return None


def _longest_band(image: Image.Image, rows: bool) -> int:
    """The longest run of whole rows (or whole columns) that share one uniform colour."""
    width, height = image.size
    length = height if rows else width
    best = run = 0
    colour: tuple[int, ...] | None = None
    for index in range(length):
        box = (0, index, width, index + 1) if rows else (index, 0, index + 1, height)
        current = _uniform_colour(image, box)
        if current is not None and colour is not None and _same(current, colour):
            run += 1
        else:
            run = 1 if current is not None else 0
            colour = current
        best = max(best, run)
    return best


def _changes(image: Image.Image, row: int) -> int:
    width = image.size[0]
    pixels = [_channels(image.getpixel((x, row))) for x in range(width)]
    return sum(
        1
        for left, right in zip(pixels, pixels[1:], strict=False)
        if sum(abs(a - b) for a, b in zip(left, right, strict=True)) > VISIBLE_CHANGE
    )


def _clipped_edges(image: Image.Image) -> list[str]:
    height = image.size[1]
    if height < 2:
        return []
    edges = {"top": (0, 1), "bottom": (height - 1, height - 2)}
    found = []
    for name, (outer, inner) in edges.items():
        counts = (_changes(image, outer), _changes(image, inner))
        if min(counts) >= CLIPPED_CHANGES:
            found.append(f"{name} edge: {min(counts)} colour changes along the outermost rows")
    return found


def check_image(path: Path, relative: str) -> list[Problem]:
    kind = image_kind(relative)
    minimum = MINIMUMS[kind]
    problems: list[Problem] = []
    previous_limit = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = None  # read the header of an oversized image instead of refusing it
    try:
        with Image.open(path) as opened:
            width, height = opened.size
            if width * height > MAXIMUM_PIXELS:
                return [
                    Problem(
                        relative,
                        "size",
                        f"{width}x{height} is over {MAXIMUM_PIXELS:,} pixels: split or crop it",
                    )
                ]
            image = opened.convert("RGBA")
    except OSError as error:
        return [Problem(relative, "unreadable", str(error))]
    finally:
        Image.MAX_IMAGE_PIXELS = previous_limit
    if width < minimum.width or height < minimum.height:
        problems.append(
            Problem(
                relative,
                "size",
                f"{width}x{height}, below {minimum.width}x{minimum.height} ({minimum.reason})",
            )
        )
    step = kind == "diagram" and _DIAGRAM_STEP.search(relative) is not None
    directions = () if step else ((True, height, "rows"), (False, width, "columns"))
    for rows, length, name in directions:
        band = _longest_band(image, rows)
        if band >= BLANK_FRACTION * length:
            problems.append(
                Problem(relative, "blank area", f"{band} of {length} {name} are one colour")
            )
    problems.extend(Problem(relative, "clipped edge", text) for text in _clipped_edges(image))
    return problems


def _image_references(text: str) -> list[tuple[int, str, str]]:
    """(line, target, alt text) for each Markdown or HTML image outside fenced code."""
    found: list[tuple[int, str, str]] = []
    fenced = False
    for number, line in enumerate(text.splitlines(), start=1):
        if _FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        for match in _MARKDOWN_IMAGE.finditer(line):
            found.append((number, match.group(2), match.group(1)))
        for tag in _HTML_IMAGE.finditer(line):
            attributes = {k.lower(): v for k, _q, v in _HTML_ATTRIBUTE.findall(tag.group(0))}
            if "src" in attributes:
                found.append((number, attributes["src"], attributes.get("alt", "")))
    return found


def _markdown_pages(root: Path) -> list[Path]:
    """Every Markdown page outside dot folders (.venv, .git, .claude, .dev)."""
    return sorted(
        p
        for p in root.rglob("*.md")
        if not any(part.startswith(".") for part in p.relative_to(root).parts[:-1])
    )


def alt_text_problems(root: Path, images: set[Path]) -> list[Problem]:
    problems: list[Problem] = []
    for page in _markdown_pages(root):
        text = page.read_text(encoding="utf-8", errors="replace")
        for number, target, alt in _image_references(text):
            if "://" in target or target.startswith("#"):
                continue
            resolved = (page.parent / target.split("#")[0]).resolve()
            if resolved in images and not alt.strip():
                image = resolved.relative_to(root.resolve()).as_posix()
                where = f"{page.relative_to(root).as_posix()}:{number}"
                problems.append(Problem(image, "alt text", f"no alt text at {where}"))
    return problems


def check(root: Path) -> tuple[int, list[Problem]]:
    images = published_images(root)
    problems: list[Problem] = []
    for path in images:
        problems.extend(check_image(path, path.relative_to(root).as_posix()))
    problems.extend(alt_text_problems(root, {p.resolve() for p in images}))
    return len(images), problems


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO, help="the repository to check")
    arguments = parser.parse_args(argv)
    checked, problems = check(arguments.root)
    for problem in problems:
        print(f"x {problem.path}: {problem.kind}: {problem.detail}")
    counts = Counter(problem.kind for problem in problems)
    summary = ", ".join(f"{kind} {count}" for kind, count in sorted(counts.items())) or "none"
    failing = len({problem.path for problem in problems})
    print(f"{checked} images checked, {failing} with problems; problems by kind: {summary}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
