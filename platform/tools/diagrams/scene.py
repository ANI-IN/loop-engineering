"""A small builder for Excalidraw scenes on the course canvas (authoring time only).

Every diagram is a rounded panel 1920 pixels wide. A slide diagram is 1920 by 791, the shape of the
deck's diagram panel (12.13 by 5.0 inches), so 40 pixels on the canvas are 18.2 points on a
slide; a concept diagram is 1920 by 712, the shape of design system 3's concept panel (12.13 by
4.5 inches), where 40 pixels are 18.2 points too; a pattern diagram is 1920 by 540, the shape of a
pattern slide's panel (12.13 by 3.41 inches), with the same 40-pixel labels; a page-only reference
diagram is 1920 by 1080 with labels of 20 pixels or more. The style
is fixed here and written down in docs/diagrams/README.md, "Diagram style": roughness 0 (the
"architect" setting), Nunito for labels and Excalidraw's code font for code, three stroke widths,
one arrow style, and the four loop colours as fills with dark text.

A shape's kind fixes its shape and outline; its loop fixes its fill. Labels are measured in the
browser with the real font before the scene is written, so a label is centred in its shape
exactly as Excalidraw itself would place it.

Elements are tagged with a step number; `Scene.frame(n)` keeps the elements of steps 1 to n, which
gives the "-step-N" build-up frames, all on the same panel so nothing moves between frames.
`Scene.frame(highlight=loop)` mutes every other loop (white fill, blue-grey outline, the labels
still dark), which gives the per-section variants of the four-loop map.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

WIDTH = 1920
SLIDE_HEIGHT = 791  # 1920 by 791 is the 12.13 by 5.0 inch panel: 40 pixels are 18.2 points
PAGE_HEIGHT = 1080  # a page-only reference diagram, too dense for a slide
PATTERN_HEIGHT = 540  # a pattern slide's panel, 12.13 by 3.41 inches: 40 pixels are 18.2 points
CONCEPT_HEIGHT = 712  # a concept slide's panel, 12.13 by 4.5 inches: 40 pixels are 18.2 points
MIN_FONT_SIZE = {SLIDE_HEIGHT: 40, PAGE_HEIGHT: 20, PATTERN_HEIGHT: 40, CONCEPT_HEIGHT: 40}

PANEL = "#F0F3F6"
DARK = "#212121"  # every label, every outline, every arrow
WHITE = "#FFFFFF"
STOP_FILL = "#EEEEEE"  # the template's light grey: a stop, a failure, a trap
MUTED = "#78909C"  # the template's blue-grey: the outline of a muted loop

LABEL_FONT = 6  # Nunito, Excalidraw's "Normal" font
CODE_FONT = 8  # Comic Shanns, Excalidraw's "Code" font
LINE_HEIGHT = 1.25
ROUGHNESS = 0  # "architect": straight, clean lines
OUTLINE = 2  # every shape
EMPHASIS = 4  # a person decides, a stop, the highlighted loop
ARROW = 3  # every arrow and line
ARROWHEAD = "triangle"

# The four loop colours, one per section (the deck's wayfinding), each with dark text on it.
LOOPS: dict[str, tuple[str, str]] = {
    "agent": ("Agent loop", "#3896D2"),
    "verification": ("Verification loop", "#0097A7"),
    "event": ("Event loop", "#FFAB40"),
    "hill-climbing": ("Hill-climbing loop", "#EEFF41"),
}
LOOP_FILLS = {fill for _name, fill in LOOPS.values()}
FILLS = LOOP_FILLS | {WHITE, STOP_FILL, PANEL, "transparent"}
STROKE_WIDTHS = {OUTLINE, EMPHASIS, ARROW}


@dataclass(frozen=True)
class Kind:
    """What a shape means: its shape and its outline, fixed for every diagram. A fill of "loop"
    takes the colour of the shape's loop (white when it belongs to none)."""

    shape: str  # rectangle, ellipse, or diamond
    fill: str
    rounded: bool = True
    stroke_width: int = OUTLINE
    stroke_style: str = "solid"


KINDS: dict[str, Kind] = {
    # An agent: a model decides what happens next.
    "agent": Kind("ellipse", "loop"),
    # Deterministic code: the same input gives the same result.
    "code": Kind("rectangle", "loop"),
    # Stored state: a database, a table, a file, a record. Square corners.
    "store": Kind("rectangle", "loop", rounded=False),
    # A person decides. White, with a thick outline.
    "human": Kind("diamond", WHITE, stroke_width=EMPHASIS),
    # A stop, a failure, or a trap that makes an answer wrong. The label says which.
    "stop": Kind("rectangle", STOP_FILL, stroke_width=EMPHASIS),
    # Deliberately no agent here: a dashed, empty ellipse where an agent could have been.
    "no-agent": Kind("ellipse", "transparent", stroke_style="dashed"),
    # Outside DataPilot: a sender, a service. Square corners, white, a dashed outline.
    "outside": Kind("rectangle", WHITE, rounded=False, stroke_style="dashed"),
    # A state of a run that goes on: rounded, white.
    "state": Kind("rectangle", WHITE),
    # A terminal state of the run lifecycle: white, a thick outline.
    "terminal": Kind("rectangle", WHITE, stroke_width=EMPHASIS),
    # The boundary of a loop or a process: an outline, with its name on top.
    "boundary": Kind("rectangle", "transparent"),
    # A tool boundary: what a helper agent may call, and nothing else.
    "fence": Kind("rectangle", "transparent", stroke_style="dashed"),
    # A loop's name tag: the loop's colour, with its name in words.
    "chip": Kind("rectangle", "loop"),
}

_B62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def fractional_index(position: int) -> str:
    """Excalidraw's ordering key for the element at `position` (a0 ... az, then b00 ...)."""
    if position < len(_B62):
        return "a" + _B62[position]
    rest = position - len(_B62)
    return "b" + _B62[rest // len(_B62)] + _B62[rest % len(_B62)]


def _seed(text: str) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16) % 2_000_000_000 + 1


@dataclass
class Label:
    """A text whose size is measured later; `place` positions it once the size is known."""

    element: dict[str, Any]
    anchor: str  # "container", "center", "left", or "arrow"
    cx: float = 0.0
    cy: float = 0.0


@dataclass
class Scene:
    name: str
    height: int = SLIDE_HEIGHT
    elements: list[dict[str, Any]] = field(default_factory=list)
    steps: dict[str, int] = field(default_factory=dict)
    loops: dict[str, str | None] = field(default_factory=dict)
    kinds: dict[str, str] = field(default_factory=dict)
    labels: list[Label] = field(default_factory=list)
    _count: int = 0
    step: int = 1
    loop: str | None = None  # the loop of the shapes drawn next

    def __post_init__(self) -> None:
        if self.height not in MIN_FONT_SIZE:
            raise ValueError(
                f"{self.name}: a panel is 1920 by 791 (slide), 1920 by 712 (concept), "
                "1920 by 540 (pattern), or 1920 by 1080 (page)"
            )
        panel = self._base("rectangle", "panel", 0, 0, WIDTH, self.height)
        panel.update(
            strokeColor="transparent",
            backgroundColor=PANEL,
            strokeWidth=OUTLINE,
            roundness={"type": 3, "value": 48},
            locked=True,
        )
        self.steps[panel["id"]] = 0
        self.loops[panel["id"]] = None

    @property
    def min_font(self) -> int:
        return MIN_FONT_SIZE[self.height]

    # --- elements ------------------------------------------------------------------------------
    def _id(self, kind: str) -> str:
        self._count += 1
        return f"{self.name}-{kind}-{self._count}"

    def _base(self, etype: str, kind: str, x: float, y: float, w: float, h: float) -> dict:
        element_id = f"{self.name}-{kind}" if kind == "panel" else self._id(etype)
        element: dict[str, Any] = {
            "id": element_id,
            "type": etype,
            "x": round(x, 2),
            "y": round(y, 2),
            "width": round(w, 2),
            "height": round(h, 2),
            "angle": 0,
            "strokeColor": DARK,
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": OUTLINE,
            "strokeStyle": "solid",
            "roughness": ROUGHNESS,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "index": "",
            "roundness": None,
            "seed": _seed(element_id),
            "version": 1,
            "versionNonce": _seed(element_id + "-nonce"),
            "isDeleted": False,
            "boundElements": None,
            "updated": 1,
            "link": None,
            "locked": False,
        }
        self.elements.append(element)
        self.steps[element_id] = self.step
        self.loops[element_id] = self.loop
        self.kinds[element_id] = kind
        return element

    def shape(
        self,
        kind: str,
        x: float,
        y: float,
        w: float,
        h: float,
        label: str = "",
        *,
        size: int | None = None,
        align: str = "center",
        valign: str = "middle",
        code: bool = False,
        loop: str | None = "",
    ) -> dict[str, Any]:
        """A shape of a fixed kind, with an optional label inside it. `loop` overrides the scene's
        current loop for this shape (None: no loop)."""
        style = KINDS[kind]
        saved = self.loop
        if loop != "":
            self.loop = loop
        element = self._base(style.shape, kind, x, y, w, h)
        fill = style.fill
        if fill == "loop":
            fill = LOOPS[self.loop][1] if self.loop else WHITE
        element.update(
            backgroundColor=fill,
            strokeWidth=style.stroke_width,
            strokeStyle=style.stroke_style,
        )
        if style.shape == "rectangle" and style.rounded:
            element["roundness"] = {"type": 3}
        elif style.shape != "rectangle":
            element["roundness"] = {"type": 2}
        if label:
            self._bound_text(
                element, label, size=size or self.min_font, align=align, valign=valign, code=code
            )
        self.loop = saved
        return element

    def chip(self, x: float, y: float, w: float, h: float, loop: str, text: str = "") -> dict:
        """A loop's name tag in the loop's colour: its name in words, so colour is never alone."""
        return self.shape("chip", x, y, w, h, text or LOOPS[loop][0], loop=loop)

    def _text_element(self, text: str, size: int, align: str, *, code: bool = False) -> dict:
        if size < self.min_font:
            raise ValueError(f"{self.name}: label {text!r} is below {self.min_font} pixels")
        element = self._base("text", "text", 0, 0, 0, 0)
        element.update(
            strokeColor=DARK,
            text=text,
            originalText=text,
            fontSize=size,
            fontFamily=CODE_FONT if code else LABEL_FONT,
            textAlign=align,
            verticalAlign="middle",
            containerId=None,
            autoResize=True,
            lineHeight=LINE_HEIGHT,
        )
        return element

    def _bind(self, container: dict, child: dict, kind: str) -> None:
        bound = container["boundElements"] or []
        bound.append({"type": kind, "id": child["id"]})
        container["boundElements"] = bound

    def _bound_text(
        self, container: dict, text: str, *, size: int, align: str, valign: str, code: bool
    ) -> None:
        element = self._text_element(text, size, align, code=code)
        element["containerId"] = container["id"]
        element["verticalAlign"] = valign
        self._bind(container, element, "text")
        self.labels.append(Label(element, "container"))

    def text(
        self,
        x: float,
        y: float,
        text: str,
        *,
        size: int | None = None,
        align: str = "left",
        code: bool = False,
    ) -> dict[str, Any]:
        """A free label. With align "left", (x, y) is its top-left corner; with "center", (x, y)
        is its centre."""
        element = self._text_element(text, size or self.min_font, align, code=code)
        anchor = "center" if align == "center" else "left"
        self.labels.append(Label(element, anchor, x, y))
        return element

    def line(self, points: list[tuple[float, float]]) -> dict:
        return self._linear("line", points, head=None)

    def arrow(
        self,
        points: list[tuple[float, float]],
        label: str = "",
        *,
        both: bool = False,
        size: int | None = None,
        label_at: float | None = None,
    ) -> dict[str, Any]:
        """An arrow through absolute points; a label sits on its middle, over a gap in the line.
        For a straight arrow, `label_at` moves the label along it (0.5 is the middle); a labelled
        straight arrow always gets that middle point, which is where Excalidraw cuts the gap."""
        if label and label_at is None:
            label_at = 0.5
        if label_at is not None and len(points) == 2:
            (x0, y0), (x1, y1) = points
            mid = (x0 + (x1 - x0) * label_at, y0 + (y1 - y0) * label_at)
            points = [points[0], mid, points[1]]
        element = self._linear("arrow", points, head=ARROWHEAD)
        if both:
            element["startArrowhead"] = ARROWHEAD
        if label:
            text = self._text_element(label, size or self.min_font, "center")
            text["containerId"] = element["id"]
            self._bind(element, text, "text")
            self.labels.append(Label(text, "arrow"))
        return element

    def _linear(self, etype: str, points: list[tuple[float, float]], *, head: Any) -> dict:
        x0, y0 = points[0]
        relative = [[round(px - x0, 2), round(py - y0, 2)] for px, py in points]
        xs = [p[0] for p in relative]
        ys = [p[1] for p in relative]
        element = self._base(etype, etype, x0, y0, max(xs) - min(xs), max(ys) - min(ys))
        element.update(
            strokeWidth=ARROW,
            points=relative,
            lastCommittedPoint=None,
            startBinding=None,
            endBinding=None,
            startArrowhead=None,
            endArrowhead=head,
        )
        if etype == "arrow":
            element["elbowed"] = False
        return element

    # --- legend --------------------------------------------------------------------------------
    def legend(self, x: float, y: float, kinds: list[tuple[str, str]], *, gap: int = 46) -> None:
        """A small key: one sample shape per kind, with its meaning in words."""
        for row, (kind, meaning) in enumerate(kinds):
            top = y + row * gap
            if KINDS[kind].shape == "diamond":
                self.shape(kind, x, top - 4, 56, 40)
            else:
                self.shape(kind, x, top, 56, 32)
            self.text(x + 72, top - 1, meaning)

    # --- measuring, placing, and writing -------------------------------------------------------
    def measure_requests(self) -> list[dict[str, Any]]:
        return [
            {
                "text": label.element["text"],
                "fontSize": label.element["fontSize"],
                "fontFamily": label.element["fontFamily"],
                "lineHeight": LINE_HEIGHT,
            }
            for label in self.labels
        ]

    def place(self, sizes: list[dict[str, float]]) -> None:
        """Set each label's measured size and position it in its shape, on its arrow, or at its
        point."""
        by_id = {e["id"]: e for e in self.elements}
        problems: list[str] = []
        for label, size in zip(self.labels, sizes, strict=True):
            element = label.element
            w, h = round(size["width"], 2), round(size["height"], 2)
            element["width"], element["height"] = w, h
            if label.anchor == "container":
                box = by_id[element["containerId"]]
                if box["type"] == "arrow":
                    raise AssertionError("arrow labels use the arrow anchor")
                pad = 12
                if element["textAlign"] == "left":
                    x = box["x"] + pad + (8 if box["type"] == "rectangle" else box["width"] * 0.15)
                else:
                    x = box["x"] + (box["width"] - w) / 2
                if element["verticalAlign"] == "top":
                    y = box["y"] + pad
                else:
                    y = box["y"] + (box["height"] - h) / 2
                problems += self._fits(element, box, w, h)
            elif label.anchor == "arrow":
                arrow = by_id[element["containerId"]]
                mx, my = _arrow_label_point(arrow)
                x, y = mx - w / 2, my - h / 2
            elif label.anchor == "center":
                x, y = label.cx - w / 2, label.cy - h / 2
            else:
                x, y = label.cx, label.cy
            element["x"], element["y"] = round(x, 2), round(y, 2)
            if not (x >= 0 and x + w <= WIDTH and y >= 0 and y + h <= self.height):
                problems.append(f"{self.name}: label {element['text']!r} leaves the panel")
        if problems:
            raise ValueError("\n".join(problems))

    def _fits(self, element: dict, box: dict, w: float, h: float) -> list[str]:
        inner_w, inner_h = box["width"], box["height"]
        if box["type"] == "ellipse":
            inner_w, inner_h = inner_w * 0.76, inner_h * 0.76
        elif box["type"] == "diamond":
            inner_w, inner_h = inner_w * 0.56, inner_h * 0.56
        if element["textAlign"] == "left" and box["type"] == "rectangle":
            inner_w -= 2 * (12 + 8)
        if w > inner_w - 8 or h > inner_h - 4:
            return [
                f"{self.name}: label {element['text']!r} ({w:.0f} by {h:.0f}) does not fit its "
                f"{box['type']} ({box['width']:.0f} by {box['height']:.0f})"
            ]
        return []

    def frame(self, upto: int | None = None, *, highlight: str | None = None) -> dict[str, Any]:
        """The scene with the elements of steps 1 to `upto` (all steps when None). With
        `highlight`, every other loop is muted: a white fill and a blue-grey outline, its labels
        still dark and readable; the highlighted loop's boundary gets the thick outline."""
        kept = [e for e in self.elements if upto is None or self.steps[e["id"]] <= upto]
        kept_ids = {e["id"] for e in kept}
        out = []
        for position, element in enumerate(kept):
            copy = dict(element)
            copy["index"] = fractional_index(position)
            if copy["boundElements"]:
                copy["boundElements"] = [b for b in copy["boundElements"] if b["id"] in kept_ids]
                copy["boundElements"] = copy["boundElements"] or None
            loop = self.loops[element["id"]]
            if highlight is not None and loop is not None and copy["type"] != "text":
                if loop != highlight:
                    if copy["backgroundColor"] in LOOP_FILLS:
                        copy["backgroundColor"] = WHITE
                    copy["strokeColor"] = MUTED
                elif self.kinds[element["id"]] == "boundary":
                    copy["strokeWidth"] = EMPHASIS
            out.append(copy)
        return {
            "type": "excalidraw",
            "version": 2,
            "source": "https://excalidraw.com",
            "elements": out,
            "appState": {"gridSize": 20, "viewBackgroundColor": "#ffffff"},
            "files": {},
        }

    @property
    def last_step(self) -> int:
        return max(self.steps.values())


def _arrow_label_point(arrow: dict[str, Any]) -> tuple[float, float]:
    """Where Excalidraw centres an arrow's label: the middle point, or the middle of the middle
    segment when the arrow has an even number of points."""
    points = arrow["points"]
    if len(points) % 2 == 1:
        px, py = points[len(points) // 2]
    else:
        i = len(points) // 2 - 1
        px = (points[i][0] + points[i + 1][0]) / 2
        py = (points[i][1] + points[i + 1][1]) / 2
    return arrow["x"] + px, arrow["y"] + py
