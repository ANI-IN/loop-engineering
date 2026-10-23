"""Builds the class deck, or a sample of it, from the outline data in this folder.

Usage:
  uv run python slides/source/build_deck.py --out slides/build/sample.pptx --only 9,11,17,18,19,20,23,24
  uv run python slides/source/build_deck.py --out slides/build/deck.pptx          # every slide

The deck starts from a copy of slides/template.pptx: its masters, layouts, theme, and table style.
The seven example slides are removed, and each outline slide is added on the
layout of the matching example slide (title TITLE_4, section divider SECTION_HEADER_2_1, concept,
diagram, and table TITLE_ONLY, demo OBJECT). The text sits in the course containers measured from
the reference deck (the course template's reference deck, design): the subtitle line, cards, number
circles, the KEY IDEA box, the key-idea bar, two-column cards, the template's table style, and the
DEMO badge. Each slide's `container` label picks the placement routine; every line of the slide's
`on_slide` list must be placed, or the build fails. A slide's optional `diagram` (the annotated
query, the one-run-to-many-runs pills) is drawn from shapes; the DEMO slide carries the laptop
picture of the Harness Engineering deck (slides/assets/). The built file keeps only the layouts
and masters its slides use and names only Fira Sans and Lexend Medium, so PowerPoint can embed
both (slides/scripts/embed_fonts.py).

Sizes never shrink: every text frame has autofit off, body text is at least 18 pt and table text
at least 16 pt. Heights come from a conservative width estimate for Fira Sans; a block that does
not fit the slide is reported as a fit problem (and fails the build with --strict). The real
check is the rendered slide: slides/scripts/check_fit.py measures every text frame in PowerPoint.

Speaker notes: the Time line (computed from the approved minutes, as in the outline) and then
every note line. Reviewer comments in the data become "Provisional:" lines; code-span backticks
are dropped.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

HERE = Path(__file__).resolve().parent
SLIDES_DIR = HERE.parent
TEMPLATE = SLIDES_DIR / "template.pptx"
ASSETS = SLIDES_DIR / "assets"
LAPTOP = ASSETS / "demo-laptop.png"  # from the Harness Engineering deck; see assets/README.md
SAMPLE = (9, 11, 17, 18, 19, 20, 23, 24)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# The outline builder holds the block order, the approved minutes, and the block loader.
outline = _load_module("slides_outline", HERE / "build.py")
template_tools = _load_module("slides_make_template", SLIDES_DIR / "scripts" / "make_template.py")

# Design tokens, measured from the reference deck (the course template's reference deck, design).
NAVY = RGBColor(0x32, 0x41, 0x58)
BLUE = RGBColor(0x38, 0x96, 0xD2)
CARD = RGBColor(0xF0, 0xF3, 0xF6)
CIRCLE = RGBColor(0x78, 0x90, 0x9C)
ACCENT = RGBColor(0xFF, 0xAB, 0x40)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
SCREEN_EDGE = RGBColor(0x21, 0x21, 0x21)  # theme accent 2
SCREEN = RGBColor(0xDD, 0xE4, 0xEB)
FONT = "Fira Sans"
BADGE_FONT = "Lexend Medium"

TITLE_PT = 30
DEMO_TITLE_PT = 25
SUBTITLE_PT = 20
BODY_PT = 18
TABLE_PT = (18, 16)  # tried in order; never below 16
CHEAT_TABLE_PT = (22, 20, 18, 16)  # the cheat sheet is the slide's only content, so it may grow
QUERY_PT = 20
LABEL_PT = 16  # the KEY IDEA label and the illustrative tag
KEY_BODY_PT = 20
BADGE_PT = 14

# Geometry in inches on the 13.333 x 7.5 in slide. The logo sits bottom right below 6.6 in.
LEFT = 0.6
WIDTH = 12.13
TITLE_BOX = (0.5, 0.2, 12.3)
BOTTOM = 6.55
GAP = 0.12
MIN_GAP = 0.05
MAX_GAP = 0.32
LINE = 1.2  # line height as a multiple of the font size (Fira Sans ascent plus descent)
CARD_PAD_X = 0.14
CARD_PAD_Y = 0.06
FUDGE = 1.06  # widen the estimate so wrapped lines are not under-counted

LAYOUT_EXAMPLE = {  # outline layout -> index of the template example slide that carries it
    "title": 0,
    "section": 1,
    "concept": 2,
    "diagram": 2,
    "table": 2,
    "demo": 4,
}
EXAMPLE_TABLE = 5
TEMPLATE_LAYOUTS = {"TITLE_4", "SECTION_HEADER_2_1", "TITLE_ONLY", "OBJECT", "BLANK"}

COMMENT = re.compile(r"<!--(.*?)-->", re.S)
BOLD = re.compile(r"\*\*(.+?)\*\*")
LEAD_LABELS = (
    "Principle:",
    "Think of it as",
    "Trade-offs:",
    "At work:",
    "Key idea:",
    "Lesson:",
    "How to read this:",
    "How it works:",
    "Worked example:",
)


# ------------------------------------------------------------------------------------------------
# Text measurement (an estimate; PowerPoint is the judge)


def _em(ch: str) -> float:
    if ch == " ":
        return 0.25
    if ch in "ijl.,;:'!|`":
        return 0.25
    if ch in 'frt()[]-/"':
        return 0.36
    if ch in "mwMW":
        return 0.82
    if ch.isupper():
        return 0.62
    if ch.isdigit():
        return 0.56
    return 0.52


def text_width(text: str, size: float, bold: bool = False) -> float:
    """Inches the text takes on one line."""
    em = sum(_em(c) for c in text) * (1.05 if bold else 1.0)
    return em * size / 72 * FUDGE


@dataclass
class Run:
    text: str
    bold: bool = False
    italic: bool = False
    color: RGBColor | None = None
    highlight: RGBColor | None = None  # a text highlight behind the run (the trap fragments)


@dataclass
class Para:
    runs: list[Run]
    size: float = BODY_PT
    align: PP_ALIGN = PP_ALIGN.LEFT
    space_before: float = 0.0  # points

    @property
    def text(self) -> str:
        return "".join(r.text for r in self.runs)

    def lines(self, width: float) -> int:
        """Lines after greedy word wrap in `width` inches."""
        words: list[tuple[str, bool]] = []
        for run in self.runs:
            for i, word in enumerate(re.split(r"(\s+)", run.text)):
                if i % 2 == 0 and word:
                    words.append((word, run.bold))
        if not words:
            return 1
        space = text_width(" ", self.size)
        lines, used = 1, 0.0
        for word, bold in words:
            w = text_width(word, self.size, bold)
            if used and used + space + w > width:
                lines += 1
                used = w
            else:
                used = used + space + w if used else w
        return lines

    def height(self, width: float) -> float:
        return self.lines(width) * self.size * LINE / 72 + self.space_before / 72


def rich(text: str, size: float = BODY_PT, color: RGBColor | None = None, **kw) -> Para:
    """A paragraph from text with **bold** markup."""
    runs: list[Run] = []
    pos = 0
    for m in BOLD.finditer(text):
        if m.start() > pos:
            runs.append(Run(text[pos : m.start()], color=color))
        runs.append(Run(m.group(1), bold=True, color=color))
        pos = m.end()
    if pos < len(text):
        runs.append(Run(text[pos:], color=color))
    return Para(runs, size=size, **kw)


def lead_para(
    text: str,
    size: float = BODY_PT,
    lead_color: RGBColor | None = ACCENT,
    color: RGBColor | None = WHITE,
    italic: bool = False,
) -> Para:
    """'Lead: rest' with the lead in bold (and the accent colour on navy)."""
    for label in LEAD_LABELS:
        if text.startswith(label):
            rest = text[len(label) :]
            return Para(
                [
                    Run(label, bold=True, color=lead_color),
                    Run(rest, italic=italic, color=color),
                ],
                size=size,
            )
    m = re.match(r"^([^:]{2,48}):\s", text)
    if m and len(m.group(1).split()) <= 6:
        return Para(
            [
                Run(m.group(1) + ":", bold=True, color=lead_color),
                Run(text[m.end(1) + 1 :], italic=italic, color=color),
            ],
            size=size,
        )
    return Para([Run(text, italic=italic, color=color)], size=size)


# ------------------------------------------------------------------------------------------------
# Blocks: each knows its height for a width and draws itself at (x, y)


@dataclass
class Box:
    """A text container: a card, a bar, a tag, or plain text on navy (fill None)."""

    paras: list[Para]
    name: str
    fill: RGBColor | None = None
    line: RGBColor | None = None
    shape: MSO_SHAPE = MSO_SHAPE.ROUNDED_RECTANGLE
    pad_x: float = CARD_PAD_X
    pad_y: float = CARD_PAD_Y
    anchor: MSO_ANCHOR = MSO_ANCHOR.MIDDLE
    min_height: float = 0.0
    width: float | None = None  # fixed width (tags); None fills the slot

    def height(self, width: float) -> float:
        w = (self.width or width) - 2 * self.pad_x
        text = sum(p.height(w) for p in self.paras)
        return max(self.min_height, text + 2 * self.pad_y + 0.02)

    def draw(self, slide, x: float, y: float, width: float, height: float | None = None):
        w = self.width or width
        h = height or self.height(width)
        if self.fill is None and self.line is None:
            shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        else:
            shape = slide.shapes.add_shape(self.shape, Inches(x), Inches(y), Inches(w), Inches(h))
            if self.shape == MSO_SHAPE.ROUNDED_RECTANGLE:
                shape.adjustments[0] = min(0.5, 0.08 / max(min(w, h), 0.1) * 2)
            if self.fill is None:
                shape.fill.background()
            else:
                shape.fill.solid()
                shape.fill.fore_color.rgb = self.fill
            if self.line is None:
                shape.line.fill.background()
            else:
                shape.line.color.rgb = self.line
                shape.line.width = Pt(2.25)
            shape.shadow.inherit = False
        shape.name = self.name
        fill_frame(shape.text_frame, self.paras, self.pad_x, self.pad_y, self.anchor)
        return shape


def fill_frame(tf, paras: list[Para], pad_x: float, pad_y: float, anchor: MSO_ANCHOR) -> None:
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = tf.margin_right = Inches(pad_x)
    tf.margin_top = tf.margin_bottom = Inches(pad_y)
    tf.vertical_anchor = anchor
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = para.align
        p.line_spacing = 1.0
        p.space_before = Pt(para.space_before)
        p.space_after = Pt(0)
        for r in para.runs:
            run = p.add_run()
            run.text = r.text
            font = run.font
            font.name = FONT
            font.size = Pt(para.size)
            font.bold = r.bold
            font.italic = r.italic
            if r.color is not None:
                font.color.rgb = r.color
            if r.highlight is not None:
                add_highlight(run, r.highlight)


# rPr children that must follow a:highlight in the schema order.
_AFTER_HIGHLIGHT = ("uLnTx", "uLn", "uFillTx", "uFill", "latin", "ea", "cs", "sym", "hlinkClick")


def add_highlight(run, color: RGBColor) -> None:
    r_pr = run._r.get_or_add_rPr()
    highlight = etree.Element(qn("a:highlight"))
    etree.SubElement(highlight, qn("a:srgbClr"), val=str(color))
    for child in r_pr:
        if etree.QName(child).localname in _AFTER_HIGHLIGHT:
            child.addprevious(highlight)
            return
    r_pr.append(highlight)


@dataclass
class Row:
    """Blocks side by side, equal height; `weights` split the width."""

    blocks: list
    name: str = "row"
    gap: float = 0.2
    weights: list[float] | None = None

    def widths(self, width: float) -> list[float]:
        weights = self.weights or [1.0] * len(self.blocks)
        free = width - self.gap * (len(self.blocks) - 1)
        return [free * w / sum(weights) for w in weights]

    def height(self, width: float) -> float:
        return max(b.height(w) for b, w in zip(self.blocks, self.widths(width), strict=True))

    def draw(self, slide, x: float, y: float, width: float, height: float | None = None):
        h = height or self.height(width)
        for b, w in zip(self.blocks, self.widths(width), strict=True):
            b.draw(slide, x, y, w, h)
            x += w + self.gap


@dataclass
class Step:
    """A number circle and its card."""

    number: str
    card: Box
    diameter: float = 0.5
    gap: float = 0.18

    def height(self, width: float) -> float:
        return max(self.diameter, self.card.height(width - self.diameter - self.gap))

    def draw(self, slide, x: float, y: float, width: float, height: float | None = None):
        h = height or self.height(width)
        circle = slide.shapes.add_shape(
            MSO_SHAPE.OVAL,
            Inches(x),
            Inches(y + (h - self.diameter) / 2),
            Inches(self.diameter),
            Inches(self.diameter),
        )
        circle.name = f"number circle {self.number}"
        circle.fill.solid()
        circle.fill.fore_color.rgb = CIRCLE
        circle.line.fill.background()
        circle.shadow.inherit = False
        para = Para([Run(self.number, bold=True, color=WHITE)], size=BODY_PT, align=PP_ALIGN.CENTER)
        fill_frame(circle.text_frame, [para], 0, 0, MSO_ANCHOR.MIDDLE)
        cx = x + self.diameter + self.gap
        self.card.draw(slide, cx, y, width - self.diameter - self.gap, h)


def number_circle(slide, number: str, x: float, y: float, diameter: float, name: str):
    """An accent circle holding a callout number, the same mark in a diagram and its callout."""
    circle = slide.shapes.add_shape(
        MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(diameter), Inches(diameter)
    )
    circle.name = name
    circle.fill.solid()
    circle.fill.fore_color.rgb = ACCENT
    circle.line.fill.background()
    circle.shadow.inherit = False
    para = Para([Run(number, bold=True, color=NAVY)], size=BODY_PT, align=PP_ALIGN.CENTER)
    fill_frame(circle.text_frame, [para], 0, 0, MSO_ANCHOR.MIDDLE)
    return circle


@dataclass
class Callout:
    """A numbered callout: the number circle centred on top, its card below."""

    number: str
    card: Box
    diameter: float = 0.42
    gap: float = 0.08

    def height(self, width: float) -> float:
        return self.diameter + self.gap + self.card.height(width)

    def draw(self, slide, x: float, y: float, width: float, height: float | None = None):
        h = height or self.height(width)
        number_circle(
            slide,
            self.number,
            x + (width - self.diameter) / 2,
            y,
            self.diameter,
            f"callout number {self.number}",
        )
        top = y + self.diameter + self.gap
        self.card.draw(slide, x, top, width, h - self.diameter - self.gap)


@dataclass
class QueryPanel:
    """A query drawn as a teaching diagram: one text line per query line, the fragments where a
    trap hides highlighted, and a numbered marker per trap in a gutter right of the longest line.
    `marks` holds (line index, fragment, callout number); a number's first mark places its marker.
    """

    lines: list[str]
    marks: list[tuple[int, str, int]]
    name: str = "annotated query"
    size: float = QUERY_PT
    pad_x: float = 0.3
    pad_y: float = 0.16
    marker: float = 0.38

    @property
    def line_height(self) -> float:
        return self.size * LINE / 72

    def height(self, width: float) -> float:
        return len(self.lines) * self.line_height + 2 * self.pad_y

    def runs(self, index: int) -> list[Run]:
        text = self.lines[index]
        spans = []
        for line, fragment, _number in self.marks:
            if line == index:
                start = text.find(fragment)
                if start < 0:
                    raise ValueError(f"query line {index}: {fragment!r} not found")
                spans.append((start, start + len(fragment)))
        runs, pos = [], 0
        for start, end in sorted(spans):
            if start > pos:
                runs.append(Run(text[pos:start], color=NAVY))
            runs.append(Run(text[start:end], bold=True, color=NAVY, highlight=ACCENT))
            pos = end
        if pos < len(text):
            runs.append(Run(text[pos:], color=NAVY))
        return runs

    def draw(self, slide, x: float, y: float, width: float, height: float | None = None):
        h = height or self.height(width)
        panel = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(width), Inches(h)
        )
        panel.name = "query panel (overlay)"
        panel.adjustments[0] = min(0.5, 0.08 / max(min(width, h), 0.1) * 2)
        panel.fill.solid()
        panel.fill.fore_color.rgb = CARD
        panel.line.fill.background()
        panel.shadow.inherit = False
        # The plain-text estimate is already widened (FUDGE), enough for the bold fragments too.
        widths = [text_width(line, self.size) for line in self.lines]
        gutter = x + self.pad_x + max(widths) + 0.3
        top = y + (h - len(self.lines) * self.line_height) / 2
        placed: set[int] = set()
        for i, line in enumerate(self.lines):
            ly = top + i * self.line_height
            box = slide.shapes.add_textbox(
                Inches(x + self.pad_x),
                Inches(ly),
                Inches(widths[i] + 0.05),
                Inches(self.line_height),
            )
            box.name = f"query line {i + 1}"
            fill_frame(
                box.text_frame, [Para(self.runs(i), size=self.size)], 0, 0, MSO_ANCHOR.MIDDLE
            )
            box.text_frame.word_wrap = False
            # Markers in reading order: by where the first fragment of each number sits.
            first: dict[int, int] = {}
            for li, fragment, n in self.marks:
                if li == i and n not in placed and n not in first:
                    first[n] = line.find(fragment)
            numbers = sorted(first, key=first.get)
            for k, number in enumerate(numbers):
                placed.add(number)
                number_circle(
                    slide,
                    str(number),
                    gutter + k * (self.marker + 0.1),
                    ly + (self.line_height - self.marker) / 2,
                    self.marker,
                    f"trap marker {number}",
                )


@dataclass
class RunsDiagram:
    """One run pill under the left column, an arrow, and a grid of run pills under the right."""

    name: str = "one run to many runs"
    pill_w: float = 1.2
    pill_h: float = 0.55
    gap: float = 0.2
    columns_gap: float = 0.2  # the Row gap of the two column cards above

    def height(self, width: float) -> float:
        return 2 * self.pill_h + self.gap

    def pill(self, slide, x: float, y: float, name: str) -> None:
        box = Box(
            [Para([Run("run", color=NAVY)], size=BODY_PT, align=PP_ALIGN.CENTER)],
            name,
            fill=CARD,
            pad_x=0.04,
            pad_y=0.0,
        )
        shape = box.draw(slide, x, y, self.pill_w, self.pill_h)
        shape.adjustments[0] = 0.5

    def draw(self, slide, x: float, y: float, width: float, height: float | None = None):
        h = height or self.height(width)
        column = (width - self.columns_gap) / 2
        left_x = x + (column - self.pill_w) / 2
        self.pill(slide, left_x, y + (h - self.pill_h) / 2, "one run pill")
        grid_w = 4 * self.pill_w + 3 * self.gap
        grid_x = x + column + self.columns_gap + (column - grid_w) / 2
        for r in range(2):
            for k in range(4):
                self.pill(
                    slide,
                    grid_x + k * (self.pill_w + self.gap),
                    y + r * (self.pill_h + self.gap),
                    f"many runs pill {r * 4 + k + 1}",
                )
        start, end = left_x + self.pill_w + 0.25, grid_x - 0.25
        arrow_h = 0.5
        arrow = slide.shapes.add_shape(
            MSO_SHAPE.RIGHT_ARROW,
            Inches(start),
            Inches(y + (h - arrow_h) / 2),
            Inches(end - start),
            Inches(arrow_h),
        )
        arrow.name = "arrow from one run to many runs"
        arrow.fill.solid()
        arrow.fill.fore_color.rgb = ACCENT
        arrow.line.fill.background()
        arrow.shadow.inherit = False


@dataclass
class Table:
    """The template's table style; the font is the largest of TABLE_PT that fits `budget`."""

    rows: list[list[str]]
    name: str = "table"
    budget: float | None = None  # inches available; set by the routine
    size: float = TABLE_PT[0]
    pad_x: float = 0.08
    pad_y: float = 0.05
    sizes: tuple[float, ...] = TABLE_PT

    def col_widths(self, width: float) -> list[float]:
        cols = len(self.rows[0])
        need = [
            max(text_width(r[c], self.size, i == 0) for i, r in enumerate(self.rows))
            for c in range(cols)
        ]
        floor = width / cols * 0.6
        weights = [max(n, floor) for n in need]
        weights = [min(w, width * 0.55) for w in weights]
        return [width * w / sum(weights) for w in weights]

    def row_heights(self, width: float) -> list[float]:
        widths = self.col_widths(width)
        heights = []
        for i, row in enumerate(self.rows):
            lines = max(
                Para([Run(cell, bold=i == 0)], size=self.size).lines(w - 2 * self.pad_x)
                for cell, w in zip(row, widths, strict=True)
            )
            heights.append(lines * self.size * LINE / 72 + 2 * self.pad_y + 0.04)
        return heights

    def fit(self, width: float) -> None:
        for size in self.sizes:
            self.size = size
            if self.budget is None or sum(self.row_heights(width)) <= self.budget:
                return

    def height(self, width: float) -> float:
        self.fit(width)
        return sum(self.row_heights(width))

    def draw(self, slide, x: float, y: float, width: float, height: float | None = None):
        self.fit(width)
        widths, heights = self.col_widths(width), self.row_heights(width)
        frame = slide.shapes.add_table(
            len(self.rows),
            len(self.rows[0]),
            Inches(x),
            Inches(y),
            Inches(width),
            Inches(sum(heights)),
        )
        frame.name = self.name
        table = frame.table
        table_style(table)
        for c, w in enumerate(widths):
            table.columns[c].width = Inches(w)
        for r, h in enumerate(heights):
            table.rows[r].height = Inches(h)
            for c, value in enumerate(self.rows[r]):
                cell = table.cell(r, c)
                cell.margin_left = cell.margin_right = Inches(self.pad_x)
                cell.margin_top = cell.margin_bottom = Inches(self.pad_y)
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                # The header text is navy, not the style's white: white on the orange header
                # reads at about 2 to 1 contrast.
                color = NAVY if r == 0 else None
                fill_frame(
                    cell.text_frame,
                    [rich(value, size=self.size, color=color)],
                    self.pad_x,
                    self.pad_y,
                    MSO_ANCHOR.MIDDLE,
                )
                if r == 0:
                    for run in cell.text_frame.paragraphs[0].runs:
                        run.font.bold = True


_TABLE_STYLE = {"id": None}


def table_style(table) -> None:
    """Apply the template example table's style id and flags."""
    tbl_pr = table._tbl.tblPr
    tbl_pr.set("firstRow", "1")
    tbl_pr.set("bandRow", "1")
    style = tbl_pr.find(qn("a:tableStyleId"))
    if style is None:
        style = etree.SubElement(tbl_pr, qn("a:tableStyleId"))
    if _TABLE_STYLE["id"]:
        style.text = _TABLE_STYLE["id"]


# ------------------------------------------------------------------------------------------------
# Content: the slide's lines, with each one marked as placed


@dataclass
class Content:
    lines: list[str]
    tables: list[list[list[str]]]
    used: set[int] = field(default_factory=set)
    tables_used: set[int] = field(default_factory=set)

    @classmethod
    def parse(cls, on_slide: list[str]) -> Content:
        lines, tables, current = [], [], None
        for raw in on_slide:
            text = COMMENT.sub("", raw).strip()
            if not text:
                current = None
                continue
            if text.startswith("|"):
                cells = [c.strip() for c in text.strip("|").split("|")]
                if all(set(c) <= set("-: ") for c in cells):
                    continue
                if current is None:
                    current = []
                    tables.append(current)
                current.append(cells)
            else:
                current = None
                lines.append(text)
        return cls(lines, tables)

    def take(self, prefix: str) -> str | None:
        for i, line in enumerate(self.lines):
            if i not in self.used and line.lstrip("*").startswith(prefix):
                self.used.add(i)
                return line
        return None

    def take_all(self, test: Callable[[str], bool]) -> list[str]:
        out = []
        for i, line in enumerate(self.lines):
            if i not in self.used and test(line):
                self.used.add(i)
                out.append(line)
        return out

    def rest(self) -> list[str]:
        return self.take_all(lambda _line: True)

    def table(self) -> list[list[str]] | None:
        for j, t in enumerate(self.tables):
            if j not in self.tables_used:
                self.tables_used.add(j)
                return t
        return None

    def unplaced(self) -> list[str]:
        lines = [x for i, x in enumerate(self.lines) if i not in self.used]
        tables = [f"table {j + 1}" for j in range(len(self.tables)) if j not in self.tables_used]
        return lines + tables


# ------------------------------------------------------------------------------------------------
# Containers


def subtitle(text: str) -> Box:
    return Box([lead_para(text, size=SUBTITLE_PT)], "subtitle line", pad_x=0, pad_y=0.02)


def plain(text: str, italic: bool = False) -> Box:
    return Box([lead_para(text, italic=italic)], "text line", pad_x=0, pad_y=0.02)


def card(text: str, name: str = "card", size: float = BODY_PT, lead: bool = True) -> Box:
    para = (
        lead_para(text, size=size, lead_color=NAVY, color=NAVY)
        if lead and "**" not in text
        else rich(text, size=size, color=NAVY)
    )
    return Box([para], name, fill=CARD)


def key_bar(text: str, name: str = "key-idea bar") -> Box:
    return Box(
        [lead_para(text, lead_color=NAVY, color=NAVY)],
        name,
        fill=ACCENT,
        shape=MSO_SHAPE.RECTANGLE,
        pad_x=0.18,
        pad_y=0.07,
    )


def key_idea_box(text: str) -> Box:
    body = re.sub(r"^\**KEY IDEA:\**\s*", "", text)
    return Box(
        [
            Para([Run("KEY IDEA", bold=True, color=NAVY)], size=LABEL_PT),
            Para([Run(body, bold=True, color=NAVY)], size=KEY_BODY_PT, space_before=2),
        ],
        "KEY IDEA box",
        fill=CARD,
        line=ACCENT,
        pad_x=0.22,
        pad_y=0.12,
    )


def tag(text: str) -> Box:
    return Box(
        [Para([Run(text, bold=True, color=NAVY)], size=LABEL_PT, align=PP_ALIGN.CENTER)],
        "illustrative tag",
        fill=ACCENT,
        pad_x=0.1,
        pad_y=0.04,
        width=text_width(text, LABEL_PT, True) + 0.4,
    )


def column_header(text: str) -> Box:
    para = Para([Run(text, bold=True, color=ACCENT)], size=BODY_PT)
    return Box([para], "column header", pad_x=CARD_PAD_X, pad_y=0.0)


@dataclass
class Plan:
    """What a routine decided: blocks from the top, an optional block pinned to the bottom."""

    blocks: list
    pinned: object | None = None
    layout: str = "concept"
    title_pt: int = TITLE_PT
    extra: Callable | None = None  # draws non-flow shapes (the demo laptop)
    center: bool = False  # centre the blocks in the free space instead of spreading the gaps


def route(spec: dict) -> Callable[[Content, dict], Plan]:
    label = spec.get("container", "")
    if spec["kind"] == "demo" or label.startswith("demo layout"):
        return demo_routine
    if label.startswith("title slide"):
        return title_routine
    if label.startswith("annotated query"):
        return query_routine
    if label.startswith("two-column cards"):
        return two_column_routine
    if label.startswith("key-idea box"):
        return key_idea_routine
    if label.startswith("step cards"):
        return step_routine
    if label.startswith("table") or label.startswith("two tables"):
        return table_routine
    return generic_routine


def header_names(spec: dict) -> list[str]:
    """'two-column cards: one run | many runs; ...' -> ['One run', 'Many runs']."""
    label = spec.get("container", "")
    head = label.split(":", 1)[1].split(";", 1)[0] if ":" in label else ""
    names = [h.strip() for h in head.split("|") if h.strip()]
    return [n[:1].upper() + n[1:] for n in names]


def concept_lines(c: Content) -> tuple[list, object | None, list]:
    """The concept arc's fixed lines: top blocks, the pinned key-idea bar, bottom blocks."""
    top, bottom = [], []
    principle = c.take("Principle:")
    if principle:
        top.append(subtitle(principle))
    think = c.take("Think of it as")
    if think:
        top.append(plain(think, italic=True))
    for prefix in ("Trade-offs:", "At work:"):
        line = c.take(prefix)
        if line:
            bottom.append(plain(line))
    key = c.take("Key idea:")
    return top, (key_bar(key) if key else None), bottom


def two_column_routine(c: Content, spec: dict) -> Plan:
    top, pinned, bottom = concept_lines(c)
    blocks = list(top)
    table = c.table()
    if table and len(table[0]) == 2:
        # Row-aligned cards: each row's two cells side by side, equal height.
        blocks.append(Row([column_header(h) for h in table[0]], "column headers"))
        for i, row in enumerate(table[1:]):
            boxes = [card(cell, f"two-column card {i + 1}") for cell in row]
            blocks.append(Row(boxes, f"two-column row {i + 1}"))
        return Plan(blocks + bottom, pinned)
    if table:
        c.tables_used.discard(len(c.tables) - 1)
    # Column cards: a line without a dash heads a column; its dash lines are the card's points.
    columns: list[tuple[str, list[str]]] = []
    for line in c.take_all(lambda x: not x.startswith(LEAD_LABELS)):
        if line.startswith("- ") and columns:
            columns[-1][1].append(line[2:])
        else:
            columns.append((line, []))
    if all(not points for _head, points in columns):
        names = header_names(spec)
        columns = [
            (names[i] if i < len(names) else "", [head]) for i, (head, _) in enumerate(columns)
        ]
    words = sum(len(p.split()) for _h, points in columns for p in points)
    size = 22 if words < 50 else BODY_PT
    blocks.append(Row([column_header(h) for h, _p in columns], "column headers"))
    cards = []
    for i, (_head, points) in enumerate(columns):
        paras = [
            Para([Run(p, color=NAVY)], size=size, space_before=0 if j == 0 else 8)
            for j, p in enumerate(points)
        ]
        cards.append(
            Box(
                paras,
                f"column card {i + 1}",
                fill=CARD,
                pad_x=0.25,
                pad_y=0.2,
                anchor=MSO_ANCHOR.TOP,
            )
        )
    blocks.append(Row(cards, "column cards"))
    if spec.get("diagram", {}).get("kind") == "one run to many runs":
        blocks.append(RunsDiagram())
    return Plan(blocks + bottom, pinned)


def _repeats_title(line: str, title: str) -> bool:
    """True when the line only restates the title's question (the title is "lead: question?")."""

    def norm(text: str) -> str:
        return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()

    return bool(norm(line)) and norm(title).endswith(norm(line))


def key_idea_routine(c: Content, spec: dict) -> Plan:
    key = c.take("KEY IDEA:")
    question = c.take_all(lambda line: not line.startswith(("- ", "KEY IDEA")))
    reasons = [r[2:] for r in c.take_all(lambda line: line.startswith("- "))]
    # A question line that repeats the title is placed by the title itself.
    blocks = [subtitle(q) for q in question if not _repeats_title(q, spec["title"])]
    if key:
        blocks.append(key_idea_box(key))
    if reasons:
        cards = [card(r, f"reason card {i + 1}") for i, r in enumerate(reasons)]
        blocks += [Row(cards, "reason cards")] if len(cards) <= 3 else cards
    return Plan(blocks, center=True)


def step_routine(c: Content, spec: dict) -> Plan:
    blocks: list = []
    illustrative = c.take("Illustrative")
    lesson = c.take("Lesson:")
    if illustrative:
        blocks.append(tag(illustrative))
    for line in c.take_all(lambda x: bool(re.match(r"^\d+\.\s", x))):
        number, text = line.split(".", 1)
        blocks.append(Step(number, card(text.strip(), f"step card {number}")))
    for line in c.rest():
        blocks.append(plain(line))
    return Plan(blocks, key_bar(lesson, "lesson bar") if lesson else None)


def table_routine(c: Content, spec: dict) -> Plan:
    blocks: list = []
    read = c.take("How to read this:")
    if read:
        blocks.append(subtitle(read))
    for line in c.take_all(lambda x: x.startswith(('"', "“"))):
        blocks.append(Box([rich(line, size=SUBTITLE_PT, color=NAVY)], "quote card", fill=CARD))
    top, pinned, bottom = concept_lines(c)
    blocks += top
    tables = []
    cheat = spec["kind"] == "cheat"
    while (t := c.table()) is not None:
        table = Table(t, f"table {len(tables) + 1}")
        if cheat:
            table.sizes = CHEAT_TABLE_PT
        tables.append(table)
    if len(tables) == 2:
        blocks.append(Row(tables, "tables", gap=0.3))
    else:
        blocks += tables
    blocks += [plain(line) for line in c.rest()]
    blocks += bottom
    return Plan(blocks, pinned, center=cheat)


def query_routine(c: Content, spec: dict) -> Plan:
    """The question, the annotated query, and one numbered callout per trap below it."""
    diagram = spec["diagram"]
    blocks: list = []
    for line in c.take_all(lambda x: x.startswith(('"', "“"))):
        blocks.append(Box([rich(line, size=SUBTITLE_PT, color=NAVY)], "quote card", fill=CARD))
    blocks.append(QueryPanel(list(diagram["query"]), [tuple(m) for m in diagram["marks"]]))
    callouts = []
    for line in c.take_all(lambda x: bool(re.match(r"^\d+\.\s", x))):
        number, text = line.split(".", 1)
        box = Box(
            [rich(text.strip(), color=NAVY)],
            f"callout card {number}",
            fill=CARD,
            anchor=MSO_ANCHOR.TOP,
            pad_y=0.1,
        )
        callouts.append(Callout(number, box))
    if callouts:
        blocks.append(Row(callouts, "trap callouts", gap=0.18))
    blocks += [plain(line) for line in c.rest()]
    return Plan(blocks)


def generic_routine(c: Content, spec: dict) -> Plan:
    top, pinned, bottom = concept_lines(c)
    blocks = list(top)
    while (t := c.table()) is not None:
        blocks.append(Table(t))
    for line in c.rest():
        blocks.append(card(line.lstrip("- ")))
    return Plan(blocks + bottom, pinned)


def title_routine(c: Content, spec: dict) -> Plan:
    c.rest()
    return Plan([], layout="title")


def demo_routine(c: Content, spec: dict) -> Plan:
    badge = c.take("Badge:")
    c.take_all(lambda line: line.startswith("Title only"))
    text = badge.split(":", 1)[1].strip() if badge else "DEMO"

    def draw(slide):
        laptop(slide, text)

    return Plan([], layout="demo", title_pt=DEMO_TITLE_PT, extra=draw)


# The DEMO slide geometry of the Harness Engineering deck (same 13.333 x 7.5 in slide), in EMU.
LAPTOP_BOX = (2125100, 1368767, 7757549, 4652933)
BADGE_BOX = (5012075, 3305000, 1983600, 510600)


def laptop(slide, badge_text: str) -> None:
    """The laptop picture of the Harness Engineering deck at its position there, with the white
    rounded DEMO badge centred on its screen. Without the picture, a laptop drawn from shapes."""
    if LAPTOP.exists():
        x, y, w, h = LAPTOP_BOX
        picture = slide.shapes.add_picture(str(LAPTOP), Emu(x), Emu(y), Emu(w), Emu(h))
        picture.name = "laptop picture"
        bx, by, bw, bh = BADGE_BOX
        badge = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Emu(bx), Emu(by), Emu(bw), Emu(bh)
        )
    else:
        badge = drawn_laptop(slide)
    badge.name = "DEMO badge (overlay)"
    badge.adjustments[0] = 0.5
    badge.fill.solid()
    badge.fill.fore_color.rgb = WHITE
    badge.line.fill.background()
    badge.shadow.inherit = False
    para = Para([Run(badge_text, color=NAVY)], size=BADGE_PT, align=PP_ALIGN.CENTER)
    fill_frame(badge.text_frame, [para], 0.05, 0.02, MSO_ANCHOR.MIDDLE)
    for run in badge.text_frame.paragraphs[0].runs:
        run.font.name = BADGE_FONT


def drawn_laptop(slide):
    """The stand-in: a laptop drawn from shapes; returns the badge shape to fill."""
    w, h = 8.5, 5.1
    x, y = (13.333 - w) / 2, 1.55
    base_h = 0.32
    lid = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(x + 0.55),
        Inches(y),
        Inches(w - 1.1),
        Inches(h - base_h),
    )
    lid.name = "laptop lid"
    lid.adjustments[0] = 0.04
    lid.fill.solid()
    lid.fill.fore_color.rgb = SCREEN_EDGE
    lid.line.fill.background()
    screen = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(x + 0.8),
        Inches(y + 0.25),
        Inches(w - 1.6),
        Inches(h - base_h - 0.45),
    )
    screen.name = "laptop screen (overlay)"
    screen.fill.solid()
    screen.fill.fore_color.rgb = SCREEN
    screen.line.fill.background()
    base = slide.shapes.add_shape(
        MSO_SHAPE.TRAPEZOID, Inches(x), Inches(y + h - base_h), Inches(w), Inches(base_h)
    )
    base.name = "laptop base"
    base.rotation = 180
    base.fill.solid()
    base.fill.fore_color.rgb = CIRCLE
    base.line.fill.background()
    for shape in (lid, screen, base):
        shape.shadow.inherit = False
    bw, bh = 2.6, 0.62
    return slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches((13.333 - bw) / 2),
        Inches(y + (h - base_h - bh) / 2),
        Inches(bw),
        Inches(bh),
    )


# ------------------------------------------------------------------------------------------------
# Slides


@dataclass
class FitProblem:
    number: int
    title: str
    message: str


def all_slides() -> list[tuple[int, str, dict, str]]:
    """(number, block name, slide dict, time line) for the whole outline, in order."""
    out, t, n = [], 0, 0
    for name in outline.APPROVED:
        for s in outline.load(name):
            n += 1
            secs = int(round(s["minutes"] * 60))
            time_line = (
                f"Time: {s['minutes']:g} minutes ({outline.clock(t)}-{outline.clock(t + secs)})"
            )
            out.append((n, name, s, time_line))
            t += secs
    return out


def notes_text(spec: dict, time_line: str) -> str:
    lines = [time_line]
    for raw in spec["notes"]:
        text = COMMENT.sub(
            lambda m: "Provisional: " + m.group(1).strip().removeprefix("provisional: "), raw
        )
        lines.append(text.replace("`", "").strip())
    return "\n".join(line for line in lines if line)


def title_lines(text: str, size: float) -> int:
    return Para([Run(text)], size=size).lines(TITLE_BOX[2] - 0.2)


def place_title(slide, text: str, size: int) -> float:
    """Sets the layout's title placeholder at the reference position; returns its bottom."""
    title = slide.shapes.title
    x, y, w = TITLE_BOX
    h = title_lines(text, size) * size * LINE / 72 * 0.95 + 0.2
    h = max(h, 0.75)
    title.left, title.top, title.width, title.height = Inches(x), Inches(y), Inches(w), Inches(h)
    tf = title.text_frame
    tf.text = text
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for p in tf.paragraphs:
        for run in p.runs:
            run.font.size = Pt(size)
            run.font.name = FONT
    return y + h


def lay_out(slide, plan: Plan, top: float, number: int, title: str) -> list[FitProblem]:
    """Stack the blocks from `top`, pin the pinned block to the bottom, spread spare space."""
    problems = []
    pinned_h = plan.pinned.height(WIDTH) if plan.pinned else 0.0
    floor = BOTTOM - (pinned_h + GAP if plan.pinned else 0.0)
    available = floor - top
    for b in plan.blocks:
        if isinstance(b, Table):
            b.budget = available - sum(o.height(WIDTH) for o in plan.blocks if o is not b)
        if isinstance(b, Row):
            for inner in b.blocks:
                if isinstance(inner, Table):
                    others = sum(o.height(WIDTH) for o in plan.blocks if o is not b)
                    inner.budget = available - others
    heights = [b.height(WIDTH) for b in plan.blocks]
    gaps = max(len(heights) - 1, 0)
    used = sum(heights) + GAP * gaps
    if gaps and used > available:
        # Tight slide: close the gaps down to MIN_GAP before calling it a fit problem.
        gap = max(MIN_GAP, (available - sum(heights)) / gaps)
    else:
        spare = max(available - used, 0.0)
        gap = GAP + (min(spare / gaps, MAX_GAP - GAP) if gaps else 0.0)
    used = sum(heights) + gap * gaps
    if used > available + 1e-6:
        problems.append(
            FitProblem(number, title, f"content needs {used:.2f} in, {available:.2f} in free")
        )
    y = top
    if plan.center and used < available:
        y += (available - used) / 2
    for b, h in zip(plan.blocks, heights, strict=True):
        width = WIDTH
        x = LEFT
        if isinstance(b, Box) and b.width:
            width = b.width
        b.draw(slide, x, y, width, h)
        y += h + gap
    if plan.pinned:
        plan.pinned.draw(slide, LEFT, BOTTOM - pinned_h, WIDTH, pinned_h)
    return problems


def add_slide(prs, layouts: dict, number: int, spec: dict, time_line: str) -> list[FitProblem]:
    content = Content.parse(spec.get("on_slide", []))
    plan = route(spec)(content, spec)
    left = content.unplaced()
    if left:
        raise ValueError(f"slide {number} {spec['title']!r}: lines not placed: {left}")
    kind = "demo" if plan.layout == "demo" else plan.layout
    if spec["layout"] == "title":
        kind = "title"
    slide = prs.slides.add_slide(layouts[kind])
    problems: list[FitProblem] = []
    if kind == "title":
        holders = {ph.placeholder_format.type: ph for ph in slide.placeholders}
        title = holders.get(3) or holders.get(1)
        lines = [x for x in (COMMENT.sub("", y).strip() for y in spec["on_slide"]) if x]
        title.text = lines[0] if lines else spec["title"]
        sub = holders.get(4)
        if sub is not None:
            sub.text = " ".join(lines[1:])
    else:
        bottom = place_title(slide, spec["title"], plan.title_pt)
        # Drop empty body placeholders so no prompt text shows in the editor.
        for ph in list(slide.placeholders):
            if ph.placeholder_format.type == 2 and not ph.text_frame.text.strip():
                ph._element.getparent().remove(ph._element)
        if plan.extra:
            plan.extra(slide)
        problems = lay_out(slide, plan, bottom + 0.05, number, spec["title"])
    slide.notes_slide.notes_text_frame.text = notes_text(spec, time_line)
    return problems


def build(out: Path, only: set[int] | None = None) -> tuple[int, list[FitProblem]]:
    prs = Presentation(str(TEMPLATE))
    examples = list(prs.slides)
    layouts = {kind: examples[i].slide_layout for kind, i in LAYOUT_EXAMPLE.items()}
    tbl = examples[EXAMPLE_TABLE].shapes[2]._element.graphic.graphicData.tbl
    _TABLE_STYLE["id"] = tbl.tblPr.find(qn("a:tableStyleId")).text
    template_tools.remove_slides(prs)
    problems: list[FitProblem] = []
    count = 0
    for number, _block, spec, time_line in all_slides():
        if only and number not in only:
            continue
        problems += add_slide(prs, layouts, number, spec, time_line)
        count += 1
    keep_deck_fonts(prs)
    prs.core_properties.title = "Module: Loop Engineering"
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out))
    return count, problems


# ------------------------------------------------------------------------------------------------
# Fonts: the deck uses Fira Sans and Lexend Medium only, so both can be embedded and none falls back

DECK_FONTS = {FONT, BADGE_FONT}
FONT_ELEMENTS = {qn(f"a:{tag}") for tag in ("latin", "ea", "cs", "sym", "buFont")}
THEME_FONTS = {qn("a:majorFont"), qn("a:minorFont")}


def _use_fira_sans(element) -> int:
    """Point every named font in the element at Fira Sans, except the deck fonts and the empty
    and theme-reference ("+mn-lt") names. Returns the number changed."""
    changed = 0
    for node in element.iter(*FONT_ELEMENTS):
        face = node.get("typeface", "")
        if face and not face.startswith("+") and face not in DECK_FONTS:
            node.set("typeface", FONT)
            changed += 1
    return changed


def keep_deck_fonts(prs) -> None:
    """Drop what the built slides do not use, so the file holds only the deck fonts.

    The template is a Google Slides export: 3 masters of 34 layouts each, Arial as the default and
    bullet font of every master, layout, and the notes master, Calibri and Roboto in some unused
    layouts, and Google's own embedded font list. The visible text is already Fira Sans; this
    removes the unused layouts and masters, points the remaining default fonts (and the theme's
    major and minor Latin font) at Fira Sans, and drops the old embedded list so PowerPoint embeds
    the installed deck fonts on save (slides/scripts/embed_fonts.py).
    """
    used = {slide.slide_layout.part for slide in prs.slides}
    for master in prs.slide_masters:
        for layout in list(master.slide_layouts):
            if layout.part not in used:
                master.slide_layouts.remove(layout)
    id_list = prs.part._element.sldMasterIdLst
    for master_id in list(id_list):
        master_part = prs.part.related_part(master_id.rId)
        if len(master_part.slide_master.slide_layouts) == 0:
            id_list.remove(master_id)
            prs.part.drop_rel(master_id.rId)
    parts = [prs.part, prs.notes_master.part]
    for master in prs.slide_masters:
        parts += [master.part] + [layout.part for layout in master.slide_layouts]
    for slide in prs.slides:
        parts.append(slide.part)
        if slide.has_notes_slide:
            parts.append(slide.notes_slide.part)
    for part in parts:
        _use_fira_sans(part._element)
    themes = {
        rel.target_part
        for part in [prs.notes_master.part] + [m.part for m in prs.slide_masters]
        for rel in part.rels.values()
        if rel.reltype.endswith("/theme")
    }
    for theme in themes:
        root = etree.fromstring(theme.blob)
        for scheme in root.iter(*THEME_FONTS):
            latin = scheme.find(qn("a:latin"))
            if latin is not None:
                latin.set("typeface", FONT)
        theme._blob = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    for rel in prs.part.rels.values():
        if rel.reltype.endswith("/tableStyles"):  # the table styles name Arial for cell text
            styles = rel.target_part
            root = etree.fromstring(styles.blob)
            _use_fira_sans(root)
            styles._blob = etree.tostring(
                root, xml_declaration=True, encoding="UTF-8", standalone=True
            )
    presentation = prs.part._element
    embedded = presentation.find(qn("p:embeddedFontLst"))
    if embedded is not None:
        rids = [node.get(qn("r:id")) for node in embedded.iter() if node.get(qn("r:id"))]
        presentation.remove(embedded)
        for rid in rids:
            prs.part.drop_rel(rid)
    presentation.set("embedTrueTypeFonts", "1")
    presentation.attrib.pop("saveSubsetFonts", None)  # embed every character, so edits still work


def parse_only(text: str | None) -> set[int] | None:
    if not text:
        return None
    return {int(x) for x in text.split(",") if x.strip()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=SLIDES_DIR / "build" / "sample.pptx")
    ap.add_argument("--only", help="comma-separated slide numbers, such as 9,11,17")
    ap.add_argument("--sample", action="store_true", help="build the eight review slides")
    ap.add_argument("--strict", action="store_true", help="exit 1 on any estimated fit problem")
    a = ap.parse_args(argv)
    only = set(SAMPLE) if a.sample else parse_only(a.only)
    count, problems = build(a.out, only)
    print(f"wrote {a.out.name}: {count} slides")
    for p in problems:
        print(f"  fit: slide {p.number} {p.title!r}: {p.message}")
    print(f"estimated fit problems: {len(problems)}")
    return 1 if problems and a.strict else 0


if __name__ == "__main__":
    sys.exit(main())
