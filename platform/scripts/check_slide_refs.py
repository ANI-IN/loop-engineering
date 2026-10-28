"""Check that every slide a published page names is a slide of the final class deck.

Usage: python platform/scripts/check_slide_refs.py [--root PATH]

The deck's slides are read from slides/outline.md, its transcript (outline_from_deck.py;
DECISIONS.md, 28 October 2026), so the check needs no deck and runs on a public checkout. A page
names a slide in four ways, and each is checked:

- "slide N", "slides N to M" or "slides N, M and K": every number is a slide of the deck.
- "slide N" with a quoted title after it (slide 72, "Which loop when: ..."): the title is slide
  N's.
- A run-of-show row, "| <time> | N. <label> | ... |": the label is words on slide N (part of its
  title or of a line of its text; "No text" for a slide with none), and the time is the one its
  speaker notes give ("None in the notes" when they give none). A page with such rows names every
  slide once, in order; a "No slide" row is a stretch of the clock no slide's notes cover.
- A quoted slide title of one of the deck's title forms ("Measured: ...", "Cheat Sheet: ..."):
  it begins a title of the deck.

Exits 1 on any problem, else 0.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_links  # noqa: E402

REPO = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
OUTLINE = "slides/outline.md"
# Pages that name slides of something other than the final deck, each with its reason.
EXEMPT = {
    OUTLINE: "the deck's transcript itself",
    "slides/design-system.md": "superseded: the earlier builder, and the reference deck's slides",
}
# The title forms of the deck's slides; a quoted title that starts with one is checked.
TITLE_FORMS = (
    "Measured:",
    "Final:",
    "All results:",
    "Recap:",
    "Assignments:",
    "Problem statement:",
    "Failure story:",
    "Cheat Sheet:",
    "Text-to-SQL:",
    "Text-to-SQL design:",
    "Which loop when:",
    "Use it in your repository:",
    "Final project:",
    "Summary:",
)
NO_TIME = "None in the notes"
NO_TEXT = "No text"

SLIDE_SECTION = re.compile(r"^## Slide (\d+)(?:: `([^`]*)`)?\n(.*?)(?=^## Slide |\Z)", re.M | re.S)
TEXT_BLOCK = re.compile(r"On the slide:\n\n(`{3,})text\n(.*?)\n\1", re.S)
TIMING = re.compile(r"Tim(?:e|ing): [\d.]+ min\w* \(([\d:]+)-([\d:]+)\)")
NUMBERS = re.compile(r"\bslides? (\d+(?:(?:, | and | to |-)\d+)*)\b", re.I)
NUMBER_TITLE = re.compile(r"\bslide (\d+),?\s+\"([^\"]+)\"", re.I)
ROW = re.compile(r"^\| (?P<time>[^|]+?) \| (?P<n>\d+)\. (?P<label>[^|]+?) \|", re.M)
QUOTED = re.compile(r"\"([^\"\n]+(?:\n[^\"\n]+)?)\"")
FENCE = re.compile(r"^(`{3,}).*?^\1", re.M | re.S)


def _plain(text: str) -> str:
    return " ".join(text.replace("’", "'").split()).casefold()


def deck(outline: str) -> dict[int, dict]:
    """Slide number -> its title, its lines of text, and the time its notes give (or None)."""
    slides = {}
    for m in SLIDE_SECTION.finditer(outline):
        body = m[3]
        block = TEXT_BLOCK.search(body)
        lines = block[2].splitlines() if block and block[2] != "(no text)" else []
        timing = TIMING.search(body.split("Speaker notes:", 1)[-1])
        when = None
        if timing:
            when = timing[1] if timing[1] == timing[2] else f"{timing[1]}-{timing[2]}"
        slides[int(m[1])] = {"title": m[2] or "", "lines": lines, "time": when}
    return slides


def _on_slide(label: str, slide: dict) -> bool:
    if not slide["title"] and not slide["lines"]:
        return label == NO_TEXT
    wanted = _plain(label)
    return any(wanted in _plain(text) for text in [slide["title"], *slide["lines"]] if text)


def page_problems(rel: str, text: str, slides: dict[int, dict]) -> list[str]:
    problems = []
    text = FENCE.sub(lambda m: "\n" * m[0].count("\n"), text)  # line numbers stay right
    count = len(slides)
    line_of = lambda pos: text.count("\n", 0, pos) + 1  # noqa: E731
    for m in NUMBERS.finditer(text):
        for n in (int(x) for x in re.findall(r"\d+", m[1])):
            if not 1 <= n <= count:
                problems.append(f"{rel}:{line_of(m.start())}: slide {n}: the deck has {count}")
    numbered = set()  # a title after a slide number is checked against that slide only
    for m in NUMBER_TITLE.finditer(text):
        n, title = int(m[1]), m[2]
        numbered.add(m.start(2) - 1)
        if n in slides and _plain(title) != _plain(slides[n]["title"]):
            problems.append(
                f"{rel}:{line_of(m.start())}: slide {n} is "
                f"{slides[n]['title'] or 'untitled'!r}, not {' '.join(title.split())!r}"
            )
    titles = [_plain(s["title"]) for s in slides.values() if s["title"]]
    for m in QUOTED.finditer(text):
        quoted = " ".join(m[1].split())
        if m.start() in numbered or not quoted.startswith(TITLE_FORMS):
            continue
        if not any(t.startswith(_plain(quoted)) for t in titles):
            problems.append(
                f"{rel}:{line_of(m.start())}: no slide of the deck is titled {quoted!r}"
            )
    rows = list(ROW.finditer(text))
    for m in rows:
        n, where = int(m["n"]), f"{rel}:{line_of(m.start())}"
        if n not in slides:
            problems.append(f"{where}: slide {n}: the deck has {count}")
            continue
        if not _on_slide(m["label"], slides[n]):
            problems.append(f"{where}: {m['label']!r} is not on slide {n}")
        want = slides[n]["time"] or NO_TIME
        if m["time"] != want:
            given = f"runs {want}" if slides[n]["time"] else "has no time"
            problems.append(f"{where}: slide {n} {given} in its notes, not {m['time']}")
    if rows and [int(m["n"]) for m in rows] != list(range(1, count + 1)):
        problems.append(
            f"{rel}: its run of show does not name slides 1 to {count} once each, in order"
        )
    return problems


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO, help="the tree to check")
    root = parser.parse_args(argv).root.resolve()
    slides = deck((root / OUTLINE).read_text(encoding="utf-8"))
    pages = [rel for rel in check_links.shipped_markdown(root) if rel not in EXEMPT]
    problems = []
    for rel in pages:
        problems += page_problems(rel, (root / rel).read_text(encoding="utf-8"), slides)
    for problem in problems:
        print(f"x {problem}")
    found = f"{len(pages)} pages against {len(slides)} slides, {len(problems)} problems"
    print(f"slide references: {found}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
