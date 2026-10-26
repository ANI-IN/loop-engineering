"""Builds slides/outline.md from the block modules in this folder and checks every rule a script can.

Usage:
  python3 build.py OUT_PATH            # build the whole outline (all blocks must exist)
  python3 build.py --check s1 [s2 ...] # check only these blocks, write nothing
  python3 build.py --samples OUT_PATH  # the sample block module: one slide of every type

Two rule sets. A block module that sets RULES = "design system" follows the design system and the
slide schema in slides/design-system.md: the block plan of the rebuild (BLOCK_PLAN, with a block
total in minutes instead of fixed minutes per position), the eighteen slide types, and the speaker
notes standard. A module without RULES follows the first outline's rules, described below, which
stay selectable until every block module is rewritten. The whole outline is built under one rule
set: when the blocks disagree, the build names each block and its rule set and writes nothing.

First outline rules. Each block module (opening, s1, s2, s3, s4, closing) defines SLIDES, a list of
dicts:
  kind      one of: title, opening, agenda, story, question, concept, cheat, demo, questions,
            reference, break, poll, closing
  title     slide title, at most 10 words
  layout    title | blank | concept | diagram | demo | table
  minutes   the approved minutes (fixed per position)
  says      the one-line summary for the table (same no-repo rule as the slide)
  src       reviewer metadata: where the content is grounded (paths allowed here only)
  on_slide  list of lines that appear on the slide (text, a Markdown table, or a diagram spec)
  container the template container layout, such as "two-column: how it works | worked example"
  table     True when on_slide is mostly a table (only the max cap is lifted for kinds without a range)
  notes     list of note lines after the Time line, each starting with its label
  diagram   optional: a teaching diagram the deck builder draws from shapes, with "kind",
            "describe" (printed in the outline), and for an annotated query its "query" lines and
            "marks"; its code is not counted in the words on the slide
"""

from __future__ import annotations

import importlib
import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
REGISTRY = HERE.parents[1] / "platform" / "demos" / "registry.yaml"
# The one link a slide may carry: a DEMO slide's "Link: <label> | <address>" to its demo page.
GITHUB = "https://github.com/ANI-IN/loop-engineering"
LINK = re.compile(r"^Link:\s*(?P<label>[^|]+?)\s*\|\s*(?P<url>\S+)\s*$")

APPROVED = {
    "opening": [0.5, 0.5, 0.5, 1, 0.5, 0.5, 0.5, 1, 0.5, 1, 1, 0.5, 0.5, 0.5, 0.5, 0.5],
    "s1": [0.5, 2, 2.5, 4.5, 4, 4, 4.5, 1, 17, 3, 1, 0.5, 0.5],
    "s2": [0.5, 2, 2.5, 5, 4.5, 4, 4.5, 1, 18, 5, 1, 1, 1],
    "break1": [10],
    "s3": [0.5, 2, 2.5, 5, 4.5, 4.5, 4.5, 0.5, 22, 6, 1, 1, 1],
    "poll": [5],
    "break2": [10],
    "s4": [0.5, 1.5, 2, 4, 4, 4, 3.5, 0.5, 20, 3, 1, 0.5, 0.5],
    "closing": [1.5, 1.5, 1.5, 1, 1.5, 1, 1, 1],
}
BLOCK_NAMES = {
    "opening": "Opening",
    "s1": "Section 1: Agent loop",
    "s2": "Section 2: Verification loop",
    "break1": "Break",
    "s3": "Section 3: Event loop",
    "poll": "Poll",
    "break2": "Break",
    "s4": "Section 4: Hill-climbing loop",
    "closing": "Closing",
}
SECTION_META = {
    "s1": ("agent-loop", "0:45"),
    "s2": ("verification-loop", "1:31"),
    "s3": ("event-loop", "2:34"),
    "s4": ("hill-climbing-loop", "3:40"),
}
# Words on the slide, by kind: (min, max). HTML comments are not counted.
SLIDE_RANGES = {
    "concept": (60, 125),
    "story": (60, 100),
    "question": (50, 80),
    "opening_content": (40, 80),
    "closing": (50, 100),
    "agenda": (0, 30),
    "questions": (0, 30),
    "break": (0, 30),
    "poll": (0, 30),
    "opening": (0, 50),
    "title": (0, 30),
    "demo": (40, 120),
    "diagram": (0, 40),
}
# Lines a slide of this kind must hold (each a prefix of some on_slide line).
REQUIRED = {
    "concept": (
        "Principle:",
        "Why it matters:",
        "Evidence:",
        "At work:",
        "Key idea:",
    ),
    "demo": ("Badge:", "What to watch for", "Guaranteed moment:", "Link:"),
    "story": ("Illustrative", "Lesson:"),
    "question": ("KEY IDEA:",),
    "reference": ("How to read this:",),
    "cheat": ("| Move | Principle | Anti-pattern it prevents | Check question |",),
}
MAX_TABLE_ROWS = 5
COMMENT = re.compile(r"<!--.*?-->")
# A value the next live session still changes; the text says what to refresh. Every other marker
# was resolved by the calibration report, so a "provisional" marker is a problem.
REFRESH = "<!-- refresh after the session: {} -->"
PROVISIONAL = re.compile(r"<!--\s*provisional", re.I)
# Notes words (after the Time line), by kind: (min, max).
NOTE_WORDS = {
    "concept": (350, 650),
    "reference": (250, 650),
    "agenda": (150, 300),
    "story": (150, 300),
    "question": (150, 300),
}
MAKEFILE = HERE.parents[1] / "Makefile"


def make_targets(makefile: Path = MAKEFILE) -> list[str]:
    """Every target the Makefile defines or declares phony, longest first."""
    if not makefile.is_file():
        return []
    text = makefile.read_text(encoding="utf-8")
    found = set(re.findall(r"^([a-z][\w-]*)\s*:(?!=)", text, re.M))
    for line in re.findall(r"^\.PHONY:(.*(?:\\\n.*)*)", text, re.M):
        found |= set(re.findall(r"[a-z][\w-]*", line))
    return sorted(found, key=lambda t: (-len(t), t))


def make_command(targets: list[str]) -> str:
    """A make command: "make" and a target of the Makefile ("make demo", "make reset"), not prose
    such as "make the"; any word when the Makefile cannot be read."""
    if not targets:
        return r"\bmake [a-z]"
    return r"\bmake (?:" + "|".join(re.escape(t) for t in targets) + r")(?![\w-])"


MAKE = make_command(make_targets())
NO_REPO = re.compile(
    rf"(?:{MAKE}|\b[\w-]+/[\w./-]+|\.(?:py|ya?ml|md|toml|sql|sh)\b|\blines? \d+|`)"
)
NOTE_REPO = re.compile(rf"{MAKE}|\bplatform/|\b[\w-]+/[\w./-]*\.(?:py|ya?ml|md|toml|sql|sh)\b")
WORD = re.compile(r"[A-Za-z0-9][\w'’.-]*")


def words(text: str) -> int:
    return len(WORD.findall(text))


def clock(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}" + (f":{s:02d}" if s else "")


def registry_moments() -> dict[str, str]:
    """Each demo's guaranteed moment from the demo registry, keyed by its title in lower case."""
    import yaml

    demos = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    return {d["title"].lower(): " ".join(d["guaranteed_moment"].split()) for d in demos}


def with_registry_moments(slide: dict) -> dict:
    """A DEMO slide's notes with each demo's guaranteed moment from the registry inserted after its
    "Demo: <title>." line, so the notes quote the single source of truth word for word."""
    moments = registry_moments()
    notes = []
    for line in slide["notes"]:
        notes.append(line)
        m = re.match(r"^Demo: (.+)\.$", line)
        if m and line != slide["notes"][-1]:
            moment = moments.get(m.group(1).lower())
            if moment is None:
                raise ValueError(f"no demo titled {m.group(1)!r} in the demo registry")
            notes.append(f"Guaranteed moment, from the demo registry: {moment}")
    return {**slide, "notes": notes}


def time_line(minutes: float, start: int) -> str:
    """A slide's first notes line, such as "Time: 1 minute (0:08-0:09)"."""
    unit = "minute" if minutes == 1 else "minutes"
    end = start + int(round(minutes * 60))
    return f"Time: {minutes:g} {unit} ({clock(start)}-{clock(end)})"


def module_of(name: str):
    """The module that holds a block, or None when it does not exist yet."""
    module = "breaks" if name.startswith("break") or name == "poll" else name
    path = HERE / f"{module}.py"
    if not path.is_file():
        return None
    loaded = sys.modules.get(module)
    if loaded is not None and Path(getattr(loaded, "__file__", "") or "").resolve() == path:
        return loaded
    # Loaded from this folder's file, whatever else is on the path: another module of the same
    # name (the console's design package, in a test run) is never taken for a block.
    key = module if loaded is None else f"slides_block_{module}"
    spec = importlib.util.spec_from_file_location(key, path)
    found = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = found
    spec.loader.exec_module(found)
    return found


def rule_set(name: str) -> str | None:
    """The rule set a block follows: its module's RULES, the first outline's rules without one,
    and None when the block has no module yet."""
    module = module_of(name)
    if module is None:
        return None
    return getattr(module, "RULES", FIRST_OUTLINE)


def load(name: str) -> list[dict]:
    if rule_set(name) == DESIGN_SYSTEM:
        return load_design(name)
    if name.startswith("break") or name == "poll":
        return importlib.import_module("breaks").BLOCKS[name]
    slides = importlib.import_module(name).SLIDES
    return [with_registry_moments(s) if s["kind"] == "demo" else s for s in slides]


def load_module_numbers(name: str) -> list[str]:
    """A section block's "Numbers this section states" list, as the outline prints it."""
    return list(importlib.import_module(name).NUMBERS)


def duplicate_numbers(numbers: list[str]) -> list[str]:
    """Lines that appear more than once in a section's "Numbers this section states" list."""
    seen: set[str] = set()
    repeated: list[str] = []
    for line in numbers:
        key = " ".join(line.split())
        if key in seen and key not in repeated:
            repeated.append(key)
        seen.add(key)
    return repeated


def check_block(name: str, slides: list[dict]) -> list[str]:
    problems = []
    if name in SECTION_META:
        for line in duplicate_numbers(load_module_numbers(name)):
            problems.append(f"{name}: the numbers list repeats {line!r}")
    want = APPROVED[name]
    if [s["minutes"] for s in slides] != want:
        problems.append(
            f"{name}: minutes {[s['minutes'] for s in slides]} differ from approved {want}"
        )
    for i, s in enumerate(slides, 1):
        tag = f"{name}#{i} {s['title']!r}"
        if words(s["title"]) > 10 and s["kind"] != "demo":
            problems.append(f"{tag}: title over 10 words")
        on_lines = [COMMENT.sub("", x) for x in s.get("on_slide", [])]
        links = [x for x in on_lines if x.startswith("Link:")]
        on_lines = [x for x in on_lines if not x.startswith("Link:")]
        on = " ".join(on_lines)
        for x in links:
            m = LINK.match(x)
            if not m or not m.group("url").startswith(GITHUB + "/"):
                problems.append(f"{tag}: a link is 'Link: <label> | {GITHUB}/<path>'")
            elif s["kind"] != "demo":
                problems.append(f"{tag}: only a DEMO slide carries a link")
        if not s.get("container"):
            problems.append(f"{tag}: no container layout label")
        for prefix in REQUIRED.get(s["kind"], ()):
            if not any(x.strip().lstrip("*").startswith(prefix) for x in on_lines + links):
                problems.append(f"{tag}: on_slide needs a line starting {prefix!r}")
        body_rows = 0
        for x in on_lines + [""]:
            if x.startswith("|") and not set(x) <= set("|-: "):
                body_rows += 1
            elif not x.startswith("|"):
                if body_rows - 1 > MAX_TABLE_ROWS:
                    problems.append(
                        f"{tag}: a table has {body_rows - 1} rows, at most {MAX_TABLE_ROWS}"
                    )
                body_rows = 0
        for field, text in (("title", s["title"]), ("says", s["says"]), ("on_slide", on)):
            m = NO_REPO.search(text)
            if m and not s.get("allow_example"):
                problems.append(f"{tag}: {field} holds a repo-style token {m.group(0)!r}")
        rng_on = SLIDE_RANGES.get(s["kind"])
        if rng_on and not rng_on[0] <= words(on) <= rng_on[1]:
            problems.append(f"{tag}: {words(on)} words on the slide, want {rng_on[0]}-{rng_on[1]}")
        rng = NOTE_WORDS.get(s["kind"])
        nw = words(" ".join(s["notes"]))
        if rng and not rng[0] <= nw <= rng[1]:
            problems.append(f"{tag}: notes {nw} words, want {rng[0]}-{rng[1]}")
        if s["kind"] != "demo" and not s.get("allow_commands"):
            m = NOTE_REPO.search(" ".join(s["notes"]))
            if m:
                problems.append(
                    f"{tag}: notes hold a path or command {m.group(0)!r} (DEMO notes only)"
                )
        if re.search(r"\breplay", " ".join(s["notes"]) + on + s["says"], re.I):
            problems.append(f"{tag}: the word 'replay' appears")
        if PROVISIONAL.search(" ".join(s["notes"] + s.get("on_slide", []))):
            problems.append(f"{tag}: a provisional marker is left; resolve it or refresh-mark it")
    return problems


def render_first_outline(out: str) -> None:
    """The outline under the first outline's rules, unchanged until every block is rewritten."""
    order = list(APPROVED)
    blocks = [(n, load(n)) for n in order]
    problems = [p for n, sl in blocks for p in check_block(n, sl)]
    total = sum(len(sl) for _, sl in blocks)
    lines = [
        "# Loop Engineering: deck outline",
        "",
        f"Class length: 240 minutes. Sections: 4. Slides: {total}.",
        "",
        "This outline is the input for the deck, which is built from it. Slides teach "
        "transferable engineering concepts; they carry no file names, repository paths, make "
        'commands, or screenshots. The "Source in the repository" column is reviewer metadata only. The '
        "one fragment of code on a slide is the naive query drawn as an annotated diagram on the "
        "slide of the fiscal year 2025 revenue question; the platform's code appears only in each demo segment, opened live "
        "in the editor, and its paths live in that DEMO slide's speaker notes. Every demo is live: "
        "recovery is reset and run it again, never a recording. Each concept slide gives the "
        "principle, why it matters (the failure it prevents), how it works in DataPilot, the "
        "evidence from this course's live runs, the trade-offs, and how to apply it at work. Each "
        "DEMO slide holds its badge on the laptop picture of the reference deck, what to watch for, "
        "the guaranteed moment of its title demo, and one labelled link to the section's demo page "
        "on GitHub, the one link on any slide.",
        "",
        "Every console control and demo name in the notes comes from the demo registry, and each "
        "demo's guaranteed moment in the DEMO notes is quoted from it at build time; every file and "
        "line range in a code walkthrough comes from that section's demo walkthrough page; every "
        "measured number comes from the calibration report, the paired measurements page "
        "(docs/benefits.md), or the live session of 24 October 2026 on gpt-6-luna, where every core "
        "and optional demo showed its moment, both halves. Values the next live session still "
        "changes carry a refresh marker that says what to refresh.",
        "",
        "Terms spelled out once for the whole outline: application programming interface (API), "
        "Structured Query Language (SQL), Coordinated Universal Time (UTC), JavaScript Object "
        "Notation (JSON), and large language model (LLM).",
        REFRESH.format(
            "trace sampling seen live after the LangSmith limit resets on 1 November; each marker "
            "below names its own value"
        ),
        "",
    ]
    t, n, stats, density = 0, 0, {}, []
    for name, slides in blocks:
        lines += [f"## {BLOCK_NAMES[name]}", ""]
        if name in SECTION_META:
            slug, walk = SECTION_META[name]
            mod = importlib.import_module(name)
            demo_start = t + int(sum(s["minutes"] for s in slides[:8]) * 60)
            first = clock(demo_start)
            if name == "s4":
                first = (
                    "2:50 for the baseline experiment, during the poll; 2:55 for the naive "
                    "analyzer, at the break; the rest at " + first
                )
            lines += [
                f"The failure this section fixes: {mod.FAILURE}",
                "",
                "Measured live: " + mod.MEASURED,
                "",
                "The demo: "
                + ", ".join(f"`make demo NAME={d}`" for d in mod.DEMOS)
                + f", launched at {first} on the DEMO slide, code walked at {walk}, recovery "
                f"`make reset NAME={slug}` and re-run: reset and run it again, live.",
                "",
            ]
        lines += [
            "| # | Slide | Layout | Time (start-end) | Says in one line | Source in the repository |",
            "|---|---|---|---|---|---|",
        ]
        rt = t
        for i, s in enumerate(slides):
            secs = int(round(s["minutes"] * 60))
            lines.append(
                f"| {n + i + 1} | {s['title']} | {s['layout']} | {clock(rt)}-{clock(rt + secs)} "
                f"| {s['says']} | {s['src']} |"
            )
            rt += secs
        lines.append("")
        if name in SECTION_META:
            mod = importlib.import_module(name)
            lines += [
                'Numbers this section states (each gets a "Re-check after live runs" line in its notes):',
                "",
            ]
            lines += [f"- {x}" for x in load_module_numbers(name)] + [""]
        lines += [f"### Slides and speaker notes: {BLOCK_NAMES[name]}", ""]
        for s in slides:
            n += 1
            secs = int(round(s["minutes"] * 60))
            lines += [
                f"**Slide {n}: {s['title']}**",
                "",
                f"Container: {s.get('container', '')}",
                "",
                "On the slide:",
                "",
            ]
            prev_table = False
            for x in s.get("on_slide", []):
                is_table = x.startswith("|")
                if is_table != prev_table and lines[-1] != "":
                    lines.append("")
                lines.append(x)
                prev_table = is_table
            lines.append("")
            image = s.get("image")
            if image:
                lines += [
                    f"Picture read from the repository at build time: `{image['path']}`. "
                    f"Alternative text: {image['alt']}",
                    "",
                ]
            diagram = s.get("diagram")
            if diagram:
                lines += [f"Diagram drawn from shapes: {diagram['describe']}", ""]
                if diagram.get("query"):
                    lines += (
                        ["```sql", f"-- {diagram['origin']}"] + list(diagram["query"]) + ["```", ""]
                    )
            onw = words(" ".join(COMMENT.sub("", x) for x in s.get("on_slide", [])))
            notes_words = words(" ".join(COMMENT.sub("", x) for x in s["notes"]))
            density.append((n, s["title"], onw, notes_words))
            lines.append("Speaker notes:")
            lines.append("")
            note = [time_line(s["minutes"], t)] + list(s["notes"])
            lines += [x + "  " if j < len(note) - 1 else x for j, x in enumerate(note)]
            lines.append("")
            nw = words(" ".join(s["notes"]))
            lo, hi = stats.get(s["kind"], (10**9, 0))
            stats[s["kind"]] = (min(lo, nw), max(hi, nw))
            t += secs
    import sources

    lines += [
        "## Words on each slide",
        "",
        "Words on the slide and words in the speaker notes after the Time line; reviewer comments "
        "are not counted.",
        "",
        "| # | Slide | Words on the slide | Words in the notes |",
        "|---|---|---|---|",
    ]
    lines += [f"| {k} | {title} | {w} | {nw} |" for k, title, w, nw in density] + [""]
    lines += ["## Sources cited in the notes", ""] + [f"- {x}" for x in sources.SOURCES] + [""]
    # Every marker in the outline: the header, the section lines and numbers, and the slides.
    refresh = "\n".join(lines).count("<!-- refresh after the session:")
    demos = {n: sum(s["kind"] == "demo" for s in sl) for n, sl in blocks if n in SECTION_META}
    kinds = [s["kind"] for _n, sl in blocks for s in sl]
    order = list(APPROVED)

    def box(ok: bool) -> str:
        return "[x]" if ok else "[ ]"

    lines += [
        "## Checks before building slides",
        "",
        f"- {box(76 <= total <= 80)} {total} slides, within 76 to 80.",
        f"- {box(all(v == 1 for v in demos.values()))} Every section has exactly one DEMO slide: "
        "its badge, what to watch for, the guaranteed moment, and the link to its demo page; its "
        "demos and code walkthrough are in its notes.",
        f"- {box(t == 240 * 60)} The times add up to {t / 60:g} minutes, breaks and the poll "
        "included.",
        f"- {box(kinds.count('break') == 2 and kinds.count('poll') == 1 and order.index('poll') == order.index('s3') + 1)} "
        "Two breaks and exactly one poll, after Section 3: Event loop.",
        f"- {box(not problems)} No file names, repository paths, make commands, or screenshots on "
        "any slide; the DEMO slide's labelled link is the one exception.",
        "- [x] Names are plain; codes appear only in code spans in the notes.",
        f"- {box(not problems)} Every measured number names its evidence; no provisional marker "
        "is left.",
        f"- [ ] {refresh} refresh markers: their values are updated from the next live session, "
        "then the class run.",
        "",
    ]
    Path(out).write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"slides {total}; minutes {t / 60:g}; refresh markers {refresh}")
    for name, slides in blocks:
        print(f"  {BLOCK_NAMES[name]}: {len(slides)}")
    print("notes words by kind (min, max):")
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")
    print(f"problems: {len(problems)}")
    for p in problems:
        print("  x", p)


# ------------------------------------------------------------------------------------------------
# The design system's rules (slides/design-system.md): the rebuild's block plan, the eighteen slide
# types, and the speaker notes standard.

FIRST_OUTLINE = "first outline"
DESIGN_SYSTEM = "design system"
REPO_ROOT = HERE.parents[1]

# (key, name, minutes, slides at most): the block plan of the rebuild, 26 October 2026. Each
# block's slides add up to its minutes exactly; per-slide minutes are free inside a block.
BLOCK_PLAN = [
    ("opening", "Opening", 10, 10),
    ("design", "Designing text-to-SQL", 15, 6),
    ("s1", "Section 1: Agent loop", 38, 13),
    ("s2", "Section 2: Verification loop", 42, 13),
    ("break1", "Break", 10, 1),
    ("s3", "Section 3: Event loop", 55, 13),
    ("poll", "Poll", 5, 1),
    ("break2", "Break", 10, 1),
    ("s4", "Section 4: Hill-climbing loop", 43, 13),
    ("closing", "Closing", 12, 10),
]
MAX_SLIDES = 85
CLASS_SECONDS = 240 * 60
LOOPS = {
    "s1": "Agent loop",
    "s2": "Verification loop",
    "s3": "Event loop",
    "s4": "Hill-climbing loop",
}


class Kind:
    """One slide type: its name, the words on the slide, the lines it must hold, the most bullet
    lines, the words of its "What to say" note, and whether it takes the short notes form."""

    def __init__(self, name, words, required=(), bullets=4, say=(150, 300), short=False):
        self.name, self.words, self.required = name, words, required
        self.bullets, self.say, self.short = bullets, say, short


FULL = (150, 300)  # "What to say" on a concept-type slide
TRANSITION = (30, 150)  # on a transition: title, agenda, section opener, sources
WRAP_UP = (60, 200)  # on a recap or a closing slide
SHORT = (15, 90)  # on a break or the poll, with the short notes form
KINDS = {
    "title": Kind("title", (0, 30), say=TRANSITION),
    "agenda": Kind("agenda", (3, 45), bullets=0, say=TRANSITION),
    "opener": Kind("section opener", (3, 45), ("Fixes:", "Insight:"), bullets=0, say=TRANSITION),
    "insight": Kind("insight", (15, 60), ("Insight:", "Evidence:")),
    "story": Kind("problem story", (20, 75), ('"', "Footer:")),
    "concept": Kind("concept diagram", (0, 0), bullets=0),
    "mechanism": Kind("mechanism (annotated code)", (15, 75), ("Idea:",)),
    "demo": Kind(
        "demo",
        (20, 80),
        ("Badge:", "What to watch for", "Guaranteed moment:", "Link:"),
        bullets=3,
        say=(80, 300),
    ),
    "evidence": Kind("evidence", (10, 60), ("Sample:",)),
    "comparison": Kind("without-and-with comparison", (15, 80)),
    "design_callout": Kind("design callout", (15, 75), ("Decision:", "DataPilot:")),
    "checklist": Kind("apply-it checklist", (20, 90), bullets=6),
    "pitfalls": Kind("pitfalls", (20, 95), ("| Pitfall",), bullets=0),
    "recap": Kind("recap and question", (10, 60), ("Question:",), bullets=3, say=WRAP_UP),
    "poll": Kind("poll", (0, 30), bullets=0, say=SHORT, short=True),
    "break": Kind("break", (0, 30), bullets=0, say=SHORT, short=True),
    "closing": Kind("closing", (20, 190), bullets=0, say=WRAP_UP),
    "sources": Kind("sources", (20, 260), ("Group:",), bullets=0, say=TRANSITION),
}
# The types whose layout draws an "Insight:" line as the Insight callout; on any other type the
# line would fall to plain text, so the check refuses it.
INSIGHT_KINDS = {"insight", "opener", "evidence", "comparison", "pitfalls"}
# A diagram slide's title stays on one line at 36 points bold across 12.13 inches. Measured on the
# deck's titles, 51 characters fit and 56 do not; the deck builder measures each title exactly and
# reports a second line.
DIAGRAM_TITLE_CHARACTERS = 52
# Body rows in a table (the header not counted), and numbered lines, at most.
DESIGN_TABLE_ROWS = 4
NUMBERED = {"agenda": 8, "closing": 10}
DEFAULT_NUMBERED = 4
# The speaker notes standard, in order. Timing is generated from the minutes, never written.
NOTE_HEAD = ("Purpose:", "What to say:")
NOTE_TAIL = ("The point to land:", "Example:", "Ask the room:", "Misconceptions:", "Transition:")
DEMO_GROUP = (
    "Demo:",
    "Command:",
    "Point at:",
    "Expected output:",
    "While it runs:",
    "If it fails:",
    "Backup screenshot:",
)
SHORT_OPTIONAL = "Do:"  # a break or the poll: an instruction for the instructor, any number
NOTE_LABELS = NOTE_HEAD + NOTE_TAIL + DEMO_GROUP + ("Timing:", "Guaranteed moment:", SHORT_OPTIONAL)
NOTE_LIMITS = {"Purpose:": 30, "The point to land:": 30, "Transition:": 40}
MARKER = re.compile(r"\[\^(\d+)\]")  # a source marker in the slide text: [^3] shows as [3]
GROUP = "Group:"  # a sources slide: the heading of a group of sources
ENTRY = re.compile(r"^\[(\d+)\]\s+.+\shttps://\S+$")  # a sources slide entry with its full URL


def label_of(line: str) -> str | None:
    return next((label for label in NOTE_LABELS if line.startswith(label)), None)


def visible_lines(s: dict) -> list[str]:
    """The lines a slide shows, less reviewer comments; the DEMO slide's link line is the link."""
    return [COMMENT.sub("", x) for x in s.get("on_slide", []) if not x.startswith("Link:")]


def visible_words(s: dict) -> int:
    return words(MARKER.sub("", " ".join(visible_lines(s))))


def timing_line(minutes: float, start: int) -> str:
    """The generated "Timing:" note, such as "Timing: 3 minutes (0:12-0:15)"."""
    return "Timing: " + time_line(minutes, start).removeprefix("Time: ")


def with_timing(notes: list[str], minutes: float, start: int) -> list[str]:
    """The notes with the generated Timing line after the Purpose line, as the standard orders."""
    timing = timing_line(minutes, start)
    if notes and notes[0].startswith("Purpose:"):
        return [notes[0], timing, *notes[1:]]
    return [timing, *notes]


def with_design_moments(slide: dict) -> dict:
    """A DEMO slide's notes with each demo's guaranteed moment from the demo registry inserted
    after the demo's "Expected output:" line, so the notes quote the registry word for word."""
    moments = registry_moments()
    notes, current = [], None
    for line in slide["notes"]:
        m = re.match(r"^Demo: (.+?)\.?$", line)
        if m:
            current = m.group(1)
        notes.append(line)
        if line.startswith("Expected output:") and current is not None:
            moment = moments.get(current.lower())
            if moment is None:
                raise ValueError(f"no demo titled {current!r} in the demo registry")
            notes.append(f"Guaranteed moment: {moment}")
    return {**slide, "notes": notes}


def load_design(name: str) -> list[dict]:
    """A design-system block's slides, each marked with its rule set and its block (a slide of the
    sample module names its own block, for its colour and its progress tracker)."""
    module = module_of(name)
    raw = module.BLOCKS[name] if hasattr(module, "BLOCKS") else module.SLIDES
    out = []
    for s in raw:
        s = {**s, "_rules": DESIGN_SYSTEM, "_block": s.get("block", name)}
        out.append(with_design_moments(s) if s["kind"] == "demo" else s)
    return out


def note_order_problems(kind: str, notes: list[str]) -> list[str]:
    """The labels in the order the standard sets, each line starting with its label. The guaranteed
    moment of a DEMO slide's demo is already inserted from the registry."""
    labels = []
    for line in notes:
        label = label_of(line)
        if label is None:
            return [f"a notes line starts with no label: {line[:40]!r}"]
        if label == "Timing:":
            return ["Timing is generated from the minutes; do not write it"]
        if not line[len(label) :].strip():
            return [f"{label} is empty"]
        if label != "Guaranteed moment:":
            labels.append(label)
    if KINDS[kind].short:
        middle = labels[2:-1]
        if (
            labels[:2] != list(NOTE_HEAD)
            or labels[-1:] != ["Transition:"]
            or any(x != SHORT_OPTIONAL for x in middle)
        ):
            return ["notes need Purpose, What to say, any Do lines, then Transition, in order"]
        return []
    head, tail = list(NOTE_HEAD), list(NOTE_TAIL)
    if labels[:2] != head or labels[-len(tail) :] != tail:
        return ["notes need " + ", ".join(x.rstrip(":") for x in head + tail) + ", in order"]
    middle = labels[2 : -len(tail)]
    if kind != "demo":
        return [f"an unexpected label in the notes: {middle[0]}"] if middle else []
    size = len(DEMO_GROUP)
    if (
        not middle
        or len(middle) % size
        or any(middle[i : i + size] != list(DEMO_GROUP) for i in range(0, len(middle), size))
    ):
        return [
            "a DEMO slide's notes give each demo as "
            + ", ".join(x.rstrip(":") for x in DEMO_GROUP)
            + ", in order, after What to say"
        ]
    return []


def note_words_problems(kind: str, notes: list[str]) -> list[str]:
    problems = []
    lo, hi = KINDS[kind].say
    say = words(" ".join(x.removeprefix("What to say:") for x in notes if x.startswith("What to")))
    if not lo <= say <= hi:
        problems.append(f"What to say has {say} words, want {lo}-{hi}")
    for label, most in NOTE_LIMITS.items():
        for line in notes:
            count = words(line[len(label) :])
            if line.startswith(label) and count > most:
                problems.append(f"{label} has {count} words, at most {most}")
    return problems


def table_rows(lines: list[str]) -> list[list[list[str]]]:
    """The Markdown tables among the lines, each as rows of cells, separator rows left out."""
    tables, current = [], None
    for x in [*lines, ""]:
        if x.startswith("|"):
            cells = [c.strip() for c in x.strip().strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue
            if current is None:
                current = []
                tables.append(current)
            current.append(cells)
        else:
            current = None
    return tables


def field_problems(s: dict, lines: list[str]) -> list[str]:
    """The structured fields: the annotated code, the chart, the diagram, the screenshot."""
    problems = []
    kind = s["kind"]
    numbered = {int(m.group(1)) for x in lines if (m := re.match(r"^(\d+)\.\s", x))}
    code, chart, figure, image = (s.get(k) for k in ("code", "chart", "figure", "image"))
    if kind == "mechanism" and not code:
        problems.append("a mechanism slide needs its code")
    if kind == "story" and not (code or image):
        problems.append("a problem story needs its code or its screenshot")
    if kind == "concept" and not figure:
        problems.append("a concept diagram slide needs its figure")
    if kind == "concept" and lines:
        problems.append(
            "a diagram slide holds its title and the diagram only, with no idea line; the idea "
            "and the diagram's points go into the notes"
        )
    if kind == "concept" and len(s["title"]) > DIAGRAM_TITLE_CHARACTERS:
        problems.append(
            f"a diagram slide's title is one line: at most {DIAGRAM_TITLE_CHARACTERS} "
            f"characters, it has {len(s['title'])}"
        )
    if kind == "insight" and numbered and not (image and image.get("callouts")):
        problems.append(
            "an insight slide's evidence lines are bullets ('- '); numbered lines are for "
            "markers on a screenshot"
        )
    if kind == "evidence" and not (chart or table_rows(lines)):
        problems.append("an evidence slide needs a chart or a table")
    if code:
        marks = {mark[2] for mark in code.get("marks", [])}
        for i, fragment, n, *_disc in code.get("marks", []):
            if not 0 <= i < len(code["lines"]) or fragment not in code["lines"][i]:
                problems.append(f"code mark {n}: {fragment!r} is not on line {i}")
        if not code.get("origin"):
            problems.append("the code names its origin: the file and the lines")
        if marks and marks != numbered:
            problems.append(f"code markers {sorted(marks)} differ from callouts {sorted(numbered)}")
    if chart:
        for key in ("title", "categories", "series", "x_label", "y_label"):
            if not chart.get(key):
                problems.append(f"the chart needs its {key}")
        for name, values in chart.get("series", []):
            if len(values) != len(chart.get("categories", [])):
                problems.append(f"chart series {name!r} needs one value per category")
        if not any(x.startswith("Sample:") for x in lines):
            problems.append("a chart states its sample size on a Sample line")
    if figure and not (figure.get("diagram") and figure.get("alt")):
        problems.append("a figure names its diagram and its alternative text")
    if image:
        if not (REPO_ROOT / image.get("path", "")).is_file():
            problems.append(f"no picture at {image.get('path')!r}")
        if not image.get("alt"):
            problems.append("a screenshot has alternative text")
        marks = {n for _x, _y, n in image.get("callouts", [])}
        if marks and marks != numbered:
            problems.append(f"screenshot callouts {sorted(marks)} differ from {sorted(numbered)}")
    return problems


def _comparison_heads(tables: list[list[list[str]]]) -> bool:
    heads = [c.lower() for t in tables[:1] for c in t[0]]
    return any(h.startswith("without") for h in heads) and any(
        h == "with" or h.startswith("with ") for h in heads
    )


def check_slide_design(tag: str, s: dict, sources_count: int) -> list[str]:
    kind = s["kind"]
    spec = KINDS.get(kind)
    if spec is None:
        return [f"{tag}: unknown slide type {kind!r}; the types are {', '.join(KINDS)}"]
    problems = []
    if s.get("minutes", 0) <= 0:
        problems.append(f"{tag}: every slide has minutes")
    if words(s["title"]) > 10:
        problems.append(f"{tag}: title over 10 words")
    raw = [COMMENT.sub("", x) for x in s.get("on_slide", [])]
    lines = visible_lines(s)
    for x in (x for x in raw if x.startswith("Link:")):
        m = LINK.match(x)
        if not m or not m.group("url").startswith(GITHUB + "/"):
            problems.append(f"{tag}: a link is 'Link: <label> | {GITHUB}/<path>'")
        elif kind != "demo":
            problems.append(f"{tag}: only a DEMO slide carries a link")
    for prefix in spec.required:
        if not any(x.strip().lstrip("*").startswith(prefix) for x in raw):
            problems.append(f"{tag}: on_slide needs a line starting {prefix!r}")
    bullets = sum(x.startswith("- ") for x in lines)
    if bullets > spec.bullets:
        problems.append(f"{tag}: {bullets} bullets, at most {spec.bullets}")
    if kind == "checklist" and bullets < 3:
        problems.append(f"{tag}: a checklist has at least 3 items")
    numbered = sum(bool(re.match(r"^\d+\.\s", x)) for x in lines)
    most = NUMBERED.get(kind, DEFAULT_NUMBERED)
    if numbered > most:
        problems.append(f"{tag}: {numbered} numbered lines, at most {most}")
    if kind in NUMBERED and numbered < 3:
        problems.append(f"{tag}: at least 3 numbered lines")
    tables = table_rows(lines)
    for t in tables:
        if len(t) - 1 > DESIGN_TABLE_ROWS:
            problems.append(f"{tag}: a table has {len(t) - 1} rows, at most {DESIGN_TABLE_ROWS}")
    if kind not in INSIGHT_KINDS and any(x.startswith("Insight:") for x in lines):
        problems.append(
            f"{tag}: an Insight line is drawn as the Insight callout only on "
            + ", ".join(sorted(INSIGHT_KINDS))
        )
    if kind == "comparison" and not _comparison_heads(tables):
        problems.append(f"{tag}: a comparison is a table with a Without and a With column")
    if kind == "sources":
        for x in lines:
            if not (x.startswith(GROUP) or ENTRY.match(x)):
                problems.append(f"{tag}: a sources line is 'Group: <topic>' or '[n] <entry> <URL>'")
    else:
        for field, text in (
            ("title", s["title"]),
            ("says", s["says"]),
            ("on_slide", " ".join(lines)),
        ):
            m = NO_REPO.search(text)
            if m:
                problems.append(f"{tag}: {field} holds a repository-style token {m.group(0)!r}")
    lo, hi = spec.words
    if not lo <= visible_words(s) <= hi:
        problems.append(f"{tag}: {visible_words(s)} words on the slide, want {lo}-{hi}")
    for m in MARKER.finditer(" ".join(lines)):
        if not 1 <= int(m.group(1)) <= sources_count:
            problems.append(f"{tag}: source marker [{m.group(1)}] is not in the sources list")
    problems += [f"{tag}: {p}" for p in field_problems(s, lines)]
    notes = list(s["notes"])
    problems += [f"{tag}: {p}" for p in note_order_problems(kind, notes)]
    problems += [f"{tag}: {p}" for p in note_words_problems(kind, notes)]
    if kind != "demo" and not s.get("allow_commands"):
        m = NOTE_REPO.search(" ".join(notes))
        if m:
            problems.append(f"{tag}: notes hold a path or command {m.group(0)!r} (DEMO notes only)")
    if re.search(r"\breplay", " ".join(notes) + " ".join(lines) + s["says"], re.I):
        problems.append(f"{tag}: the word 'replay' appears")
    if PROVISIONAL.search(" ".join(notes + s.get("on_slide", []))):
        problems.append(f"{tag}: a provisional marker is left; resolve it or refresh-mark it")
    return problems


def sources_count() -> int:
    return len(importlib.import_module("sources").SOURCES)


# "Source 12", "Sources 39 and 43", "Sources 30, 33 and 37" in the speaker notes.
NOTE_CITATION = re.compile(r"\bSources? (\d+(?:(?:, | and )\d+)*)")


def cited_sources(blocks: list[tuple[str, list[dict]]]) -> tuple[list[int], list[int]]:
    """The sources the deck cites (a marker on a slide or "Source N" in the notes), and the sources
    its sources slides list, each in number order."""
    cited: set[int] = set()
    listed: set[int] = set()
    for _name, slides in blocks:
        for s in slides:
            lines = visible_lines(s)
            if s["kind"] == "sources":
                listed |= {int(m.group(1)) for x in lines if (m := ENTRY.match(x))}
                continue
            cited |= {int(n) for n in MARKER.findall(" ".join(lines))}
            for m in NOTE_CITATION.finditer(" ".join(s["notes"])):
                cited |= {int(n) for n in re.findall(r"\d+", m.group(1))}
    return sorted(cited), sorted(listed)


def check_block_design(name: str, slides: list[dict]) -> list[str]:
    """Every slide's rules, and, for a block of the plan, its total minutes and its slide cap."""
    count = sources_count()
    problems = []
    for i, s in enumerate(slides, 1):
        problems += check_slide_design(f"{name}#{i} {s['title']!r}", s, count)
    plan = {key: (minutes, most) for key, _n, minutes, most in BLOCK_PLAN}
    if name in plan:
        minutes, most = plan[name]
        total = sum(s["minutes"] for s in slides)
        if total != minutes:
            problems.append(
                f"{name}: its slides add up to {total:g} minutes, the block has {minutes}"
            )
        if len(slides) > most:
            problems.append(f"{name}: {len(slides)} slides, at most {most}")
        if name in LOOPS and sum(s["kind"] == "demo" for s in slides) != 1:
            problems.append(f"{name}: a section has exactly one DEMO slide")
    return problems


def check(name: str, slides: list[dict]) -> list[str]:
    """A block's problems under its own rule set."""
    if rule_set(name) == DESIGN_SYSTEM:
        return check_block_design(name, slides)
    return check_block(name, slides)


def outline_rules() -> tuple[str | None, dict[str, str | None]]:
    """The rule set the whole outline is built under, and each block's own rule set. None when the
    blocks disagree: some rewritten to the design system, some not yet."""
    first = list(APPROVED)
    plan = [key for key, *_ in BLOCK_PLAN]
    sets = {n: rule_set(n) for n in dict.fromkeys(first + plan)}
    if all(sets[n] == FIRST_OUTLINE for n in first) and sets["design"] is None:
        return FIRST_OUTLINE, sets
    if all(sets[n] == DESIGN_SYSTEM for n in plan):
        return DESIGN_SYSTEM, sets
    return None, sets


def block_order() -> list[str]:
    """The blocks of the outline, in class order, under the rule set it is built with."""
    rules, _sets = outline_rules()
    return [key for key, *_ in BLOCK_PLAN] if rules == DESIGN_SYSTEM else list(APPROVED)


def block_names() -> dict[str, str]:
    """Each block's name under the rule set the outline is built with."""
    rules, _sets = outline_rules()
    if rules == DESIGN_SYSTEM:
        return {key: name for key, name, *_ in BLOCK_PLAN}
    return dict(BLOCK_NAMES)


def show(line: str) -> str:
    """A slide line as the outline prints it: a source marker [^3] as [3]."""
    return MARKER.sub(r"[\1]", line)


def slide_lines_design(n: int, s: dict, start: int) -> list[str]:
    """One slide of the design-system outline: its type, its lines, its fields, its notes."""
    lines = [f"**Slide {n}: {s['title']}**", "", f"Type: {KINDS[s['kind']].name}.", ""]
    lines += ["On the slide:", ""]
    prev_table = False
    for x in s.get("on_slide", []):
        is_table = x.startswith("|")
        if is_table != prev_table and lines[-1] != "":
            lines.append("")
        lines.append(show(x) if is_table else show(x) + "  ")
        prev_table = is_table
    lines[-1] = lines[-1].rstrip()
    lines.append("")
    code = s.get("code")
    if code:
        marks = ", ".join(f"{m[2]} on {m[1]!r}" for m in code.get("marks", []))
        lines += [
            f"Annotated code on the slide, from {code['origin']}; markers {marks}:",
            "",
            f"```{code.get('language', 'text')}",
            *code["lines"],
            "```",
            "",
        ]
    chart = s.get("chart")
    if chart:
        series = "; ".join(
            f"{name}: "
            + ", ".join(f"{c} {v:g}" for c, v in zip(chart["categories"], values, strict=True))
            for name, values in chart["series"]
        )
        lines += [
            f"Native chart, {chart.get('type', 'column')}: {chart['title']}. Horizontal axis: "
            f"{chart['x_label']}. Vertical axis: {chart['y_label']}. {series}.",
            "",
        ]
    figure = s.get("figure")
    if figure:
        lines += [f"Diagram (Excalidraw, {figure['diagram']}): {figure['alt']}", ""]
    image = s.get("image")
    if image:
        lines += [f"Screenshot, cropped, read from `{image['path']}`: {image['alt']}", ""]
    lines += ["Speaker notes:", ""]
    note = with_timing(list(s["notes"]), s["minutes"], start)
    lines += [x + "  " if j < len(note) - 1 else x for j, x in enumerate(note)]
    lines.append("")
    return lines


def render_design(out: str, blocks: list[tuple[str, list[dict]]], samples: bool = False) -> int:
    """The outline under the design system (or the sample slides' outline); every problem is
    printed, and the gate reads the "problems: N" line."""
    problems = [p for n, sl in blocks for p in check_block_design(n, sl)]
    names = {key: name for key, name, *_ in BLOCK_PLAN}
    plan = {key: (minutes, most) for key, _n, minutes, most in BLOCK_PLAN}
    total = sum(len(sl) for _, sl in blocks)
    seconds = sum(int(round(s["minutes"] * 60)) for _, sl in blocks for s in sl)
    head = "sample slides, one of every type" if samples else "deck outline"
    lines = [
        f"# Loop Engineering: {head}",
        "",
        f"Class length: 240 minutes. Blocks: {len(blocks)}. Slides: {total}.",
        "",
        "This outline is the input for the deck, which is built from it under the design system "
        "(slides/design-system.md): one fixed layout per slide type, a progress tracker in the "
        "loop's colour on every slide, and speaker notes under the labels of the notes standard. "
        "Slides carry no file names, repository paths, or make commands; the one link on a slide "
        "is the DEMO slide's labelled link to its demo page on GitHub. Every demo is live: "
        "recovery is reset and run it again, never a recording. A source marker such as [3] "
        "names an entry of the sources list at the end.",
        "",
        "Terms spelled out once for the whole outline: application programming interface (API), "
        "Structured Query Language (SQL), Coordinated Universal Time (UTC), JavaScript Object "
        "Notation (JSON), and large language model (LLM).",
        "",
    ]
    t, n, density = 0, 0, []
    for name, slides in blocks:
        block_seconds = sum(int(round(s["minutes"] * 60)) for s in slides)
        if name in plan:
            minutes, most = plan[name]
            lines += [
                f"## {names[name]}",
                "",
                f"Clock {clock(t)}-{clock(t + block_seconds)}: {minutes} minutes, at most {most} "
                f"slides; {len(slides)} slides.",
                "",
            ]
        else:
            lines += ["## The sample slides", ""]
        lines += [
            "| # | Slide | Type | Time (start-end) | Says in one line | Source in the repository |",
            "|---|---|---|---|---|---|",
        ]
        rt = t
        for i, s in enumerate(slides):
            secs = int(round(s["minutes"] * 60))
            kind = KINDS[s["kind"]].name if s["kind"] in KINDS else s["kind"]
            lines.append(
                f"| {n + i + 1} | {s['title']} | {kind} | {clock(rt)}-{clock(rt + secs)} "
                f"| {s['says']} | {s['src']} |"
            )
            rt += secs
        lines += ["", f"### Slides and speaker notes: {names.get(name, 'the sample slides')}", ""]
        for s in slides:
            n += 1
            if s["kind"] in KINDS:
                lines += slide_lines_design(n, s, t)
            density.append((n, s["title"], visible_words(s), words(" ".join(s["notes"]))))
            t += int(round(s["minutes"] * 60))
    import sources

    lines += [
        "## Words on each slide",
        "",
        "Words on the slide (source markers and reviewer comments not counted) and words in the "
        "speaker notes (the generated Timing line not counted).",
        "",
        "| # | Slide | Words on the slide | Words in the notes |",
        "|---|---|---|---|",
    ]
    lines += [f"| {k} | {title} | {w} | {nw} |" for k, title, w, nw in density] + [""]
    cited, listed = cited_sources(blocks)
    shown = sorted(set(cited) | set(listed))
    lines += ["## Sources cited on the slides and in the notes", ""]
    lines += [
        "The sources slides list these, with the course's own evidence, under the numbers of the "
        "verified source list.",
        "",
    ]
    lines += [f"- {sources.SOURCES[n - 1]}" for n in shown if 1 <= n <= len(sources.SOURCES)]
    lines += [""]
    if not samples:
        if listed:
            missing = [n for n in cited if n not in listed]
            if missing:
                problems.append(
                    "cited but not on the sources slides: " + ", ".join(map(str, missing))
                )
        if total > MAX_SLIDES:
            problems.append(f"{total} slides, at most {MAX_SLIDES}")
        if seconds != CLASS_SECONDS:
            problems.append(f"the slides add up to {seconds / 60:g} minutes, not 240")
        kinds = [s["kind"] for _n, sl in blocks for s in sl]
        if kinds.count("break") != 2 or kinds.count("poll") != 1:
            problems.append("two breaks and one poll")

        def box(ok: bool) -> str:
            return "[x]" if ok else "[ ]"

        lines += [
            "## Checks before building slides",
            "",
            f"- {box(total <= MAX_SLIDES)} {total} slides, at most {MAX_SLIDES}.",
            f"- {box(seconds == CLASS_SECONDS)} The times add up to {seconds / 60:g} minutes; "
            "each block's slides add up to its minutes.",
            f"- {box(not problems)} Every section has exactly one DEMO slide, with its demos in "
            "its notes; two breaks and one poll, after Section 3: Event loop.",
            f"- {box(not problems)} Every slide follows its type's layout rules and the speaker "
            "notes standard.",
            "",
        ]
    Path(out).write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"rules: {DESIGN_SYSTEM}; slides {total}; minutes {seconds / 60:g}")
    for name, slides in blocks:
        print(f"  {names.get(name, name)}: {len(slides)}")
    print(f"problems: {len(problems)}")
    for p in problems:
        print("  x", p)
    return 0


def render(out: str) -> int:
    """The outline under the rule set every block follows; nothing is written when they differ."""
    rules, sets = outline_rules()
    if rules == FIRST_OUTLINE:
        render_first_outline(out)
        return 0
    if rules == DESIGN_SYSTEM:
        return render_design(out, [(key, load(key)) for key, *_ in BLOCK_PLAN])
    print("The block modules follow two rule sets, so the outline is not built:")
    for name, value in sets.items():
        print(f"  {name}: {value or 'no module yet'}")
    print(
        f'Set RULES = "{DESIGN_SYSTEM}" in every block module, and add the design block, to build '
        "under the design system; check one block meanwhile with --check <block>."
    )
    print("problems: 1")
    return 1


def main(argv: list[str]) -> int:
    if argv[:1] == ["--check"]:
        problems = []
        for name in argv[1:]:
            problems += check(name, load(name))
        for p in problems:
            print("x", p)
        print(f"problems: {len(problems)}")
        return 1 if problems else 0
    if argv[:1] == ["--samples"]:
        return render_design(argv[1], [("samples", load_design("samples"))], samples=True)
    return render(argv[0])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
