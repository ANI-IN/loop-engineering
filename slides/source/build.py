"""Builds slides/outline.md from the block modules in this folder and checks every rule a script can.

Usage:
  python3 build.py OUT_PATH            # build the whole outline (all blocks must exist)
  python3 build.py --check s1 [s2 ...] # check only these blocks, write nothing
  python3 build.py --samples OUT_PATH  # the sample block module: one slide of every type
  python3 build.py --samples OUT_PATH samples3  # design system 3's sample module

Three rule sets. A block module that sets RULES = "design system" follows the design system and
the slide schema in slides/design-system.md: the block plan of the first rebuild (BLOCK_PLAN, with
a block total in minutes instead of fixed minutes per position), the slide types, and the speaker
notes standard. A module that sets RULES = "design system 2" follows the same design system under
the second rebuild's block plan (BLOCK_PLAN_2: the problem statement and foundations blocks) and
its added checks: the evidence diet, at most two code slides per section, one insight per section
on its opener, the scoreboard on each section's recap, and Structured Query Language spelled out
once in the deck, on the title slide. A module that sets RULES = "design system 3" follows the
third rebuild (slides/design-system.md, "The third rebuild"): the previous module's deck as the
model, its own types (the copied slides among them), line grammar, notes ranges, section rhythm,
block plan (BLOCK_PLAN_3, no foundations block), and the sources numbered in the order the deck
first cites them. A module without RULES follows the first outline's rules,
described below. The whole outline is built under one rule set: when the blocks disagree, the build
names each block and its rule set and writes nothing.

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
    if rule_set(name) in DESIGNED:
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
# The second rebuild (27 October 2026): the same design system under its own block plan and checks.
DESIGN_SYSTEM_2 = "design system 2"
# The third rebuild (27 October 2026): the previous module's deck as the model (slides/design-system.md,
# "The third rebuild"), its own types, block plan, line grammar and checks.
DESIGN_SYSTEM_3 = "design system 3"
DESIGNED = (DESIGN_SYSTEM, DESIGN_SYSTEM_2, DESIGN_SYSTEM_3)
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
# The second rebuild's block plan, 27 October 2026 (.dev/review/deck2-brief.md): 78 slides plus at
# most 7 sources slides, so the closing's cap is its 7 slides and 7 sources slides.
BLOCK_PLAN_2 = [
    ("opening", "Opening", 5, 3),
    ("problem", "The problem", 12, 4),
    ("foundations", "Foundations", 13, 5),
    ("design", "Designing text-to-SQL", 10, 4),
    ("s1", "Section 1: Agent loop", 35, 13),
    ("s2", "Section 2: Verification loop", 35, 13),
    ("break1", "Break", 10, 1),
    ("s3", "Section 3: Event loop", 48, 13),
    ("poll", "Poll", 5, 1),
    ("break2", "Break", 10, 1),
    ("s4", "Section 4: Hill-climbing loop", 42, 13),
    ("closing", "Closing", 15, 14),
]
# The third rebuild's block plan, 27 October 2026 (.dev/review/deck3-brief.md): 89 slides, at most
# 90; the foundations block does not exist under it.
BLOCK_PLAN_3 = [
    ("opening", "Opening", 13, 13),
    ("problem", "The problem", 24, 9),
    ("design", "Designing text-to-SQL", 10, 5),
    ("s1", "Section 1: Agent loop", 35, 12),
    ("s2", "Section 2: Verification loop", 33, 12),
    ("break1", "Break", 10, 1),
    ("s3", "Section 3: Event loop", 43, 12),
    ("poll", "Poll", 5, 1),
    ("break2", "Break", 10, 1),
    ("s4", "Section 4: Hill-climbing loop", 35, 12),
    ("closing", "Closing", 22, 12),
]
PLANS = {DESIGN_SYSTEM: BLOCK_PLAN, DESIGN_SYSTEM_2: BLOCK_PLAN_2, DESIGN_SYSTEM_3: BLOCK_PLAN_3}
MAX_SLIDES = 85
MAX_SLIDES_3 = 90
CLASS_SECONDS = 240 * 60
LOOPS = {
    "s1": "Agent loop",
    "s2": "Verification loop",
    "s3": "Event loop",
    "s4": "Hill-climbing loop",
}
# The scoreboard: the fiscal year 2025 revenue question's state after each section, as the owner's
# specification of 27 October 2026 words it (section 4, item 8). A recap slide names its section in
# its `scoreboard` field; the payoff slide shows the scoreboard complete.
SCOREBOARD = {
    1: "The agent sees enough, but the answer is still wrong.",
    2: "The wrong answer is caught and flagged, but only while someone is watching.",
    3: "It runs safely unattended, but it is still wrong.",
    4: "Correct: $64,015,091.21, posted at the level its family has earned.",
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
PROBLEM = (300, 400)  # on a problem statement slide: the owner's specification, section 3
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
    # The second rebuild's types (27 October 2026).
    "pattern": Kind("pattern", (12, 60), ("Definition:", "Use when:", "Avoid when:"), bullets=0),
    "problem": Kind("problem statement", (20, 90), ("Lead:",), bullets=6, say=PROBLEM),
    "payoff": Kind(
        "payoff", (40, 130), ("Before:", "After:", "Level:", "Loop:"), bullets=6, say=FULL
    ),
}
# The lines a pattern slide may hold, each at most once; a payoff slide's lines besides its
# requirement checks ("- ") and its optional sample line.
PATTERN_LINES = ("Definition:", "Use when:", "Avoid when:", "Elsewhere:")
PAYOFF_LINES = ("Before:", "After:", "Level:", "Loop:", "Sample:")
# A pattern slide's lines are one line each: characters at most, measured on Fira Sans at 20 points
# (bold label included) for the full width (Definition, Elsewhere) and for one of two columns (Use
# when, Avoid when); the deck builder measures each line exactly and reports a second line.
PATTERN_CHARACTERS = {"Definition:": 90, "Use when:": 44, "Avoid when:": 44, "Elsewhere:": 90}
PATTERN_DIAGRAM = "pattern-"  # a pattern slide's diagram: a pattern diagram's deck export
# The kinds whose slides may show a run id, a date, or a Sample line (the evidence diet), and the
# sources slides, whose entries are a bibliography.
EVIDENCE_KINDS = {"evidence", "demo", "payoff", "sources"}
CODE_PANELS = ("Pattern", "DataPilot")  # the label of a code panel, under design system 2
CODE_SLIDES_PER_SECTION = 2
SPELLED_SQL = "Structured Query Language"
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
    rules = getattr(module, "RULES", DESIGN_SYSTEM)
    rules = rules if rules in DESIGNED else DESIGN_SYSTEM
    out = []
    for s in raw:
        s = {**s, "_rules": rules, "_block": s.get("block", name)}
        out.append(with_design_moments(s) if s["kind"] == "demo" else s)
    return out


def note_order_problems(kind: str, notes: list[str]) -> list[str]:
    """The labels in the order the standard sets, each line starting with its label. The guaranteed
    moment of a DEMO slide's demo is already inserted from the registry. A "Do:" line, an
    instruction for the instructor and not spoken, may stand anywhere in the full form (round 1's
    ruling 23), a DEMO slide's run sheet before its demo groups among them; the label order is
    read without it, as it is without the guaranteed moment."""
    labels = []
    short = KINDS[kind].short
    for line in notes:
        label = label_of(line)
        if label is None:
            return [f"a notes line starts with no label: {line[:40]!r}"]
        if label == "Timing:":
            return ["Timing is generated from the minutes; do not write it"]
        if not line[len(label) :].strip():
            return [f"{label} is empty"]
        if label == SHORT_OPTIONAL and not short:
            continue
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
    if kind == "pattern" and not figure:
        problems.append("a pattern slide needs its figure, a pattern diagram")
    if (
        kind == "pattern"
        and figure
        and not str(figure.get("diagram", "")).startswith(PATTERN_DIAGRAM)
    ):
        problems.append(
            f"a pattern slide shows a pattern diagram, named {PATTERN_DIAGRAM}<name>; "
            f"{figure.get('diagram')!r} is not one"
        )
    if kind != "pattern" and figure and str(figure.get("diagram", "")).startswith(PATTERN_DIAGRAM):
        problems.append(
            "a pattern diagram is drawn for the pattern slide's compact panel; show it on a "
            "pattern slide"
        )
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


LOOP_LABEL = re.compile(r"^Section ([1-4])(?::\s*(.+))?$")


def loop_tag(tag: str) -> str | None:
    """The block key a tag names: a loop's name ("Agent loop"), or "Section 1" with or without its
    loop's name; None when it names no loop."""
    tag = tag.strip()
    m = LOOP_LABEL.match(tag)
    if m:
        key = f"s{m.group(1)}"
        return key if not m.group(2) or m.group(2).lower() == LOOPS[key].lower() else None
    return next((k for k, name in LOOPS.items() if name.lower() == tag.lower()), None)


def pattern_problems(s: dict, lines: list[str]) -> list[str]:
    """A pattern slide: a definition, the use-when and avoid-when lines, an optional elsewhere line
    with its source marker, and nothing else, each line short enough for one line."""
    problems = []
    for x in lines:
        label = next((p for p in PATTERN_LINES if x.startswith(p)), None)
        if label is None:
            problems.append(
                f"a pattern slide holds only {', '.join(PATTERN_LINES)} lines, not {x[:40]!r}"
            )
            continue
        if sum(y.startswith(label) for y in lines) > 1:
            problems.append(f"a pattern slide holds one {label} line")
        shown = len(MARKER.sub("", x))
        if shown > PATTERN_CHARACTERS[label]:
            problems.append(
                f"the {label} line is one line: at most {PATTERN_CHARACTERS[label]} characters, "
                f"it has {shown}"
            )
        if label == "Elsewhere:" and not MARKER.search(x):
            problems.append("an Elsewhere line names the other stack only where sourced: a marker")
    return sorted(set(problems), key=problems.index)


def problem_problems(s: dict, lines: list[str]) -> list[str]:
    """A problem statement slide: one lead line and 3 to 6 short items, each item optionally
    tagged "| <loop>" with the loop it maps to."""
    problems = []
    items = [x for x in lines if x.startswith("- ")]
    if sum(x.startswith("Lead:") for x in lines) != 1:
        problems.append("a problem slide holds one Lead line")
    if not 3 <= len(items) <= 6:
        problems.append(f"a problem slide holds 3 to 6 items, it has {len(items)}")
    for x in lines:
        if not x.startswith(("Lead:", "- ")):
            problems.append(f"a problem slide holds a Lead line and items only, not {x[:40]!r}")
    for x in items:
        _text, bar, tag = x.partition("|")
        if bar and loop_tag(tag) is None:
            problems.append(f"an item's tag names a loop or a section: {tag.strip()!r}")
    return problems


def payoff_problems(s: dict, lines: list[str]) -> list[str]:
    """The payoff slide: the wrong answer and the right one, the level it posted at, what each loop
    contributed (one Loop line per section, in order), and the requirement groups checked."""
    problems = []
    for label in ("Before:", "After:", "Level:"):
        found = [x for x in lines if x.startswith(label)]
        if len(found) != 1:
            problems.append(f"a payoff slide holds one {label} line")
        elif label != "Level:" and "|" not in found[0]:
            problems.append(f"a {label} line is '{label} <label> | <value>'")
    loops = [x for x in lines if x.startswith("Loop:")]
    named = [loop_tag(x.removeprefix("Loop:").split("|", 1)[0]) for x in loops]
    if named != list(LOOPS) or not all("|" in x for x in loops):
        problems.append(
            "a payoff slide holds four Loop lines, 'Loop: Section 1 | <what it contributed>' to "
            "Section 4, in order"
        )
    checks = [x for x in lines if x.startswith("- ")]
    if not 3 <= len(checks) <= 6:
        problems.append(f"a payoff slide checks 3 to 6 requirement groups, it has {len(checks)}")
    if sum(x.startswith("Sample:") for x in lines) > 1:
        problems.append("a payoff slide holds at most one Sample line")
    for x in lines:
        if not x.startswith((*PAYOFF_LINES, "- ")):
            problems.append(f"a payoff slide holds no other line: {x[:40]!r}")
    return problems


# The evidence diet of the second rebuild: a run id is a word of 8 or more hexadecimal characters
# with a digit in it; a date is a day and a month, a month and a day or a year, or a numeric date.
RUN_ID = re.compile(r"\b(?=[0-9a-f]*\d)[0-9a-f]{8,}\b", re.I)
MONTH = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
DATE = re.compile(
    rf"\b(?:\d{{1,2}}(?:st|nd|rd|th)? {MONTH}\b|{MONTH} \d{{1,4}}\b|\d{{4}}-\d{{2}}-\d{{2}}\b"
    rf"|\d{{1,2}}/\d{{1,2}}/\d{{2,4}}\b)"
)
URL_TEXT = re.compile(r"https?://\S+")


def evidence_diet_problems(s: dict, lines: list[str]) -> list[str]:
    """No run id, no date, and no Sample line on a slide, except the evidence, demo and payoff
    slides (and the sources slides' entries): they go into the speaker notes."""
    if s["kind"] in EVIDENCE_KINDS:
        return []
    problems = []
    text = URL_TEXT.sub("", " ".join([s["title"], *lines]))
    m = RUN_ID.search(text)
    if m:
        problems.append(f"a run id {m.group(0)!r} on the slide: run ids go into the notes")
    m = DATE.search(text)
    if m:
        problems.append(f"a date {m.group(0)!r} on the slide: dates go into the notes")
    if any(x.startswith("Sample:") for x in lines):
        problems.append(
            "a Sample line on the slide: only the evidence, demo and payoff slides state a sample "
            "size; it goes into the notes"
        )
    return problems


def code_panel_problems(s: dict) -> list[str]:
    """Design system 2: a mechanism slide labels its code panel "Pattern" (generic code, no
    DataPilot names) or "DataPilot" (its real code)."""
    code = s.get("code")
    if not code or s["kind"] != "mechanism":
        return []  # a problem story's code is the agent's query, shown as evidence
    panel = code.get("panel")
    if panel not in CODE_PANELS:
        return [f"the code names its panel: 'panel': 'Pattern' or 'DataPilot', not {panel!r}"]
    if panel == "Pattern":
        text = " ".join([*code.get("lines", []), code.get("origin", "")])
        if re.search(r"datapilot", text, re.I):
            return ["a Pattern panel is generic code: no DataPilot names in its lines or origin"]
    return []


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
    # The sources slides are a bibliography, not presented: the owner's specification of 27
    # October 2026 gives them zero minutes. Every other slide has time.
    if s.get("minutes", 0) <= 0 and not (kind == "sources" and s.get("minutes") == 0):
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
    checks = {"pattern": pattern_problems, "problem": problem_problems, "payoff": payoff_problems}
    if kind in checks:
        problems += [f"{tag}: {p}" for p in checks[kind](s, lines)]
    board = s.get("scoreboard")
    if board is not None and (kind != "recap" or board not in SCOREBOARD):
        problems.append(f"{tag}: a scoreboard is a recap slide's section number, 1 to 4")
    if s.get("_rules") == DESIGN_SYSTEM_2:
        problems += [f"{tag}: {p}" for p in evidence_diet_problems(s, lines)]
        problems += [f"{tag}: {p}" for p in code_panel_problems(s)]
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


def rules_of(slides: list[dict]) -> str:
    """The rule set a block's slides were loaded under (the design system when unmarked)."""
    return next((s["_rules"] for s in slides if s.get("_rules") in DESIGNED), DESIGN_SYSTEM)


def section_problems(name: str, slides: list[dict]) -> list[str]:
    """Design system 2, a section: at most two code slides; one insight, on its opener; its recap
    carries the scoreboard of this section."""
    problems = []
    number = int(name[1])
    code = [s for s in slides if s.get("code") or s["kind"] == "mechanism"]
    if len(code) > CODE_SLIDES_PER_SECTION:
        problems.append(
            f"{name}: {len(code)} code slides, at most {CODE_SLIDES_PER_SECTION} (the pattern in "
            "code, then DataPilot's version)"
        )
    openers = [s for s in slides if s["kind"] == "opener"]
    insights = [(s, x) for s in slides for x in visible_lines(s) if x.startswith("Insight:")]
    if len(openers) != 1:
        problems.append(f"{name}: a section has one opener, it has {len(openers)}")
    if len(insights) != 1 or (openers and insights and insights[0][0] is not openers[0]):
        problems.append(
            f"{name}: one insight per section, on its opener; it has {len(insights)}"
            + (
                " and one off the opener"
                if any(s["kind"] != "opener" for s, _x in insights)
                else ""
            )
        )
    recaps = [s for s in slides if s["kind"] == "recap"]
    if not recaps or any(s.get("scoreboard") != number for s in recaps):
        problems.append(
            f"{name}: its recap carries the scoreboard of Section {number}: scoreboard={number}"
        )
    return problems


def spelled_out_problems(name: str, slides: list[dict]) -> list[str]:
    """Design system 2: Structured Query Language is spelled out once in the deck, on the title
    slide (the opening's first slide, or the sample module's), and on no other slide."""
    problems = []
    for i, s in enumerate(slides):
        shown = SPELLED_SQL in " ".join([s["title"], *visible_lines(s)])
        first = name in ("opening", "samples", "samples3") and i == 0
        if first and (s["kind"] != "title" or not shown):
            problems.append(
                f"{name}#1: the title slide spells out {SPELLED_SQL}, the one place in the deck"
            )
        elif shown and not first:
            problems.append(
                f"{name}#{i + 1} {s['title']!r}: {SPELLED_SQL} is spelled out once in the deck, "
                "on the title slide; write SQL here"
            )
    return problems


def check_block_design(name: str, slides: list[dict], rules: str | None = None) -> list[str]:
    """Every slide's rules, and, for a block of the plan, its total minutes and its slide cap;
    under design system 2 also the section checks and the one spelling out of SQL; under design
    system 3 its own types and checks."""
    rules = rules or rules_of(slides)
    if rules == DESIGN_SYSTEM_3:
        return check_block_design_3(name, slides)
    count = sources_count()
    problems = []
    for i, s in enumerate(slides, 1):
        problems += check_slide_design(f"{name}#{i} {s['title']!r}", s, count)
    if rules == DESIGN_SYSTEM_2:
        problems += spelled_out_problems(name, slides)
        if name in LOOPS:
            problems += section_problems(name, slides)
    plan = {key: (minutes, most) for key, _n, minutes, most in PLANS[rules]}
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
    if rule_set(name) in DESIGNED:
        return check_block_design(name, slides)
    return check_block(name, slides)


def outline_rules() -> tuple[str | None, dict[str, str | None]]:
    """The rule set the whole outline is built under, and each block's own rule set. None when the
    blocks disagree: some rewritten, some not yet. A plan's rule set is chosen when every block of
    its plan follows it and no other block's module follows another rule set."""
    first = list(APPROVED)
    keys = list(dict.fromkeys(first + [key for plan in PLANS.values() for key, *_ in plan]))
    sets = {n: rule_set(n) for n in keys}
    if all(sets[n] == FIRST_OUTLINE for n in first) and all(
        sets[n] is None for n in keys if n not in first
    ):
        return FIRST_OUTLINE, sets
    for rules, plan in PLANS.items():
        own = [key for key, *_ in plan]
        others = [n for n in keys if n not in own]
        if rules == DESIGN_SYSTEM_3:
            # The third rebuild has no foundations block: a module left from the second rebuild's
            # plan is not part of its outline.
            others = [n for n in others if n not in RETIRED_3]
        if all(sets[n] == rules for n in own) and all(sets[n] in (None, rules) for n in others):
            return rules, sets
    return None, sets


def block_order() -> list[str]:
    """The blocks of the outline, in class order, under the rule set it is built with."""
    rules, _sets = outline_rules()
    return [key for key, *_ in PLANS[rules]] if rules in PLANS else list(APPROVED)


def block_names() -> dict[str, str]:
    """Each block's name under the rule set the outline is built with."""
    rules, _sets = outline_rules()
    if rules in PLANS:
        return {key: name for key, name, *_ in PLANS[rules]}
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
        panel = f", labelled {code['panel']}" if code.get("panel") else ""
        lines += [
            f"Annotated code on the slide{panel}, from {code['origin']}; markers {marks}:",
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
    board = s.get("scoreboard")
    if board in SCOREBOARD:
        lines += [f"Scoreboard after Section {board}:", ""]
        for n, state in SCOREBOARD.items():
            name = f"- Section {n}: {LOOPS[f's{n}']}"
            if n > board:
                lines.append(f"{name} (to come)")
            else:
                lines.append(f"{name} ({'now' if n == board else 'done'}): {state}")
        lines.append("")
    lines += ["Speaker notes:", ""]
    note = with_timing(list(s["notes"]), s["minutes"], start)
    lines += [x + "  " if j < len(note) - 1 else x for j, x in enumerate(note)]
    lines.append("")
    return lines


def render_design(
    out: str,
    blocks: list[tuple[str, list[dict]]],
    samples: bool = False,
    rules: str = DESIGN_SYSTEM,
) -> int:
    """The outline under a design-system rule set (or the sample slides' outline); every problem
    is printed, and the gate reads the "problems: N" line."""
    problems = [p for n, sl in blocks for p in check_block_design(n, sl, rules)]
    names = {key: name for key, name, *_ in PLANS[rules]}
    plan = {key: (minutes, most) for key, _n, minutes, most in PLANS[rules]}
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
        "The sources slides list these under the numbers of the verified source list.",
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
            uncited = [n for n in listed if n not in cited]
            if uncited:
                problems.append(
                    "on the sources slides but cited nowhere: " + ", ".join(map(str, uncited))
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
        ]
        if rules == DESIGN_SYSTEM_2:
            lines += [
                f"- {box(not problems)} The evidence diet: run ids, dates and sample-size lines "
                "only on the evidence, demo and payoff slides; one insight per section, on its "
                "opener; at most two code slides per section, labelled Pattern or DataPilot; each "
                "section's recap carries its scoreboard.",
                f"- {box(not problems)} {SPELLED_SQL} is spelled out once in the deck, on the title "
                "slide.",
            ]
        lines.append("")
    Path(out).write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"rules: {rules}; slides {total}; minutes {seconds / 60:g}")
    for name, slides in blocks:
        print(f"  {names.get(name, name)}: {len(slides)}")
    print(f"problems: {len(problems)}")
    for p in problems:
        print("  x", p)
    return 0


# ------------------------------------------------------------------------------------------------
# The third rebuild (design system 3): the previous module's deck as the model. Its types, line
# grammar, notes ranges, the sources numbered by first citation, and the section rhythm
# (slides/design-system.md, "The third rebuild (design system 3)").

RETIRED_3 = ("foundations",)  # blocks of an earlier plan that design system 3 does not have
WHOLE = (250, 400)  # the whole speaker notes, every label included, on a teaching slide


class Kind3(Kind):
    """A type of design system 3: like Kind, with `whole`, the range of the whole notes' words
    (every label included) that replaces the "What to say" range on a teaching slide."""

    def __init__(self, name, words, required=(), bullets=6, say=FULL, short=False, whole=None):
        super().__init__(name, words, required, bullets, say, short)
        self.whole = whole


KINDS_3 = {
    "title": Kind3("title", (0, 30), short=True, say=SHORT),
    "intro": Kind3("introduction (copied)", (0, 120), short=True, say=SHORT),
    "profile": Kind3("instructor profile (copied)", (0, 120), short=True, say=SHORT),
    "logistics": Kind3("course logistics (copied)", (0, 120), short=True, say=SHORT),
    "qa": Kind3("ask about anything (copied)", (0, 120), short=True, say=SHORT),
    "break": Kind3("break (copied)", (0, 120), short=True, say=SHORT),
    "poll": Kind3("poll (copied)", (0, 120), short=True, say=SHORT),
    "agenda": Kind3("today's agenda", (8, 45), bullets=0, say=TRANSITION),
    "problem": Kind3("problem statement rows", (30, 120), ("Lead:",), bullets=5, whole=WHOLE),
    "quotes": Kind3("the challenge: quotes", (25, 100), ("Lead:", "Quote:"), 0, whole=WHOLE),
    "costs": Kind3("two cost panels", (25, 90), ("Lead:", "Panel:"), bullets=8, whole=WHOLE),
    "concept": Kind3("concept diagram", (10, 45), ("Lead:", "Key idea:"), 0, whole=WHOLE),
    "table": Kind3("table", (20, 200), ("Lead:",), bullets=0),
    "failure": Kind3("failure story", (50, 110), ("Lead:",), bullets=0, whole=WHOLE),
    "question": Kind3("question", (25, 80), ("Lead:", "Key idea:"), bullets=0, whole=WHOLE),
    "technique": Kind3("numbered technique", (70, 120), ("Key idea:",), bullets=5, whole=WHOLE),
    "references": Kind3("references", (0, 400), bullets=0, short=True, say=SHORT),
}
# The types kept as in design system 2: their lines, words and notes ranges.
for _key in ("design_callout", "evidence", "payoff", "closing", "demo"):
    _kind = KINDS[_key]
    KINDS_3[_key] = Kind3(_kind.name, _kind.words, _kind.required, _kind.bullets, _kind.say)

# The copied types: the reference deck's slide, its visible text filled from the module's lines in
# this fixed order (the shape's id in the reference slide, the paragraph in that shape). A slot
# ("card", 0) is the API key slide's placeholder card in place of the email picture. `required`
# and `optional` lines are drawn on the copied slide besides its slots: the poll's question and a
# note under the LangSmith link (the free plan's traces, with its source marker).
COPIED_KINDS = ("intro", "profile", "logistics", "qa", "break", "poll")
COPIED = {
    "intro": {"slide": 2, "slots": ((458, 0),)},
    "profile": {
        "slide": 3,
        "slots": ((483, 0), (483, 1), (464, 0), (480, 0), (481, 0), (482, 0)),
    },
    "logistics:structure": {"slide": 4, "slots": ((488, 0), (489, 0), (489, 1))},
    "logistics:optimise": {
        "slide": 5,
        "slots": ((500, 0), (498, 0), (498, 1), (499, 0), (499, 1)),
    },
    "logistics:support_team": {"slide": 6, "slots": ((505, 0), (505, 1), (505, 2))},
    "logistics:support_features": {
        "slide": 7,
        "slots": ((511, 0), *((512, k) for k in range(6))),
    },
    "logistics:success": {
        "slide": 8,
        "slots": ((517, 0), *((518, k) for k in range(7)), (518, 8)),
    },
    "logistics:api_key": {
        "slide": 9,
        "slots": ((523, 0), *((524, k) for k in range(5)), ("card", 0)),
    },
    "logistics:langsmith": {"slide": 10, "slots": ((531, 0), (530, 0)), "optional": ("Note:",)},
    "qa": {"slide": 31, "slots": ((755, 0), *((754, k) for k in range(10)))},
    "break:10": {"slide": 32, "slots": ((763, 0), (761, 0))},
    "break:5": {"slide": 54, "slots": ((999, 0), (998, 0))},
    "poll": {"slide": 53, "slots": ((991, 0), (993, 0)), "required": ("Question:",)},
}
VARIANTS = tuple(key.split(":", 1)[1] for key in COPIED if key.startswith("logistics:"))


def copied_key(s: dict) -> str:
    """The copied slide a copied type takes: a logistics slide by its variant, a break by its
    minutes (the reference's 10-minute and 5-minute breaks)."""
    kind = s["kind"]
    if kind == "logistics":
        return f"logistics:{s.get('variant')}"
    if kind == "break":
        return "break:5" if s.get("minutes") == 5 else "break:10"
    return kind


def copied_parts(s: dict) -> tuple[list[str], list[str]]:
    """A copied slide's lines: the slot lines, in the fill order, and its labelled extra lines."""
    spec = COPIED.get(copied_key(s), {})
    labels = tuple(spec.get("required", ())) + tuple(spec.get("optional", ()))
    lines = [COMMENT.sub("", x) for x in s.get("on_slide", [])]
    extra = [x for x in lines if labels and x.startswith(labels)]
    return [x for x in lines if x not in extra], extra


# The icons a problem row may name; the deck builder draws each as the picture of that name.
ICONS = ("warning", "swap", "copy", "pause", "branch", "check", "search", "chart", "lock", "clock")
PROBLEM_ROW = re.compile(r"^- \*\*(?P<label>[^*]+?:)\*\*\s+(?P<text>.+?)\s*\|\s*(?P<icon>[\w-]+)$")
QUOTE = re.compile(r"^Quote:\s*(?P<text>.+?)\s*\|\s*(?P<n>\d+)\s*$")
NOW = re.compile(r"^Now:\s*(?P<n>\d+)\s*$")
TITLE_CHARACTERS_3 = 60  # one line at 30 points bold on the 12.13-inch title
DEMO_TITLE_CHARACTERS_3 = 80  # one line at 25 points bold
KEY_IDEA_KINDS = ("concept", "technique", "question", "table", "problem", "costs")
LEAD_KINDS = (
    "problem",
    "quotes",
    "costs",
    "concept",
    "table",
    "failure",
    "question",
    "design_callout",
    "evidence",
    "payoff",
    "closing",
    "references",
)
EVIDENCE_KINDS_3 = {"evidence", "demo", "payoff", "references", "title", *COPIED_KINDS}
TABLE_ROWS_3 = 10
REFERENCE_ROWS = 12  # a references table, at most
MAX_SOURCES_3 = 24  # two references tables
FAILURE_STEP_WORDS = 16
TECHNIQUE_WORDS = (60, 100)  # the technique's lines of explanation, in all
SECTION_RHYTHM = (
    "agenda",
    "failure",
    "question",
    "technique",
    "technique",
    "technique",
    "technique",
    "design_callout",
    "table",
    "demo",
    "evidence",
    "qa",
)
CHEAT_SHEET_HEADER = ["Technique", "What it does", "How to apply it in your system"]
BARE_NOTE_CITATION = re.compile(r"\bSources? \d")


def visible_lines_3(s: dict) -> list[str]:
    """The lines a slide shows under design system 3: the DEMO link, the agenda's star line and
    a quote's or a problem row's trailing reference left out of the words."""
    out = []
    for x in visible_lines(s):
        if NOW.match(x):
            continue
        m = QUOTE.match(x)
        if m:
            x = "Quote: " + m.group("text")
        m = PROBLEM_ROW.match(x)
        if m:
            x = f"- **{m.group('label')}** {m.group('text')}"
        out.append(x)
    return out


def visible_words_3(s: dict) -> int:
    return words(MARKER.sub("", " ".join(visible_lines_3(s))))


def citations_of(s: dict) -> list[int]:
    """The sources a slide cites, in order: its markers and quotes on the slide, then the markers
    in its notes. A references slide cites none: it lists them."""
    if s["kind"] == "references":
        return []
    out: list[int] = []
    for x in visible_lines(s):
        m = QUOTE.match(x)
        out += [int(n) for n in MARKER.findall(x)]
        if m:
            out.append(int(m.group("n")))
    for x in s.get("notes", []):
        out += [int(n) for n in MARKER.findall(x)]
    return out


def citation_order(slides: list[dict]) -> dict[int, int]:
    """Stable source number -> its number in the deck, in order of first citation: on the slide,
    then in the notes, slide by slide."""
    order: dict[int, int] = {}
    for s in slides:
        for n in citations_of(s):
            order.setdefault(n, len(order) + 1)
    return order


def cite(text: str, order: dict[int, int], marker: str = "[{}]") -> str:
    """Markers [^n] as the deck shows them: "[k]" on a slide, `marker` "{}" for "Source k" in the
    notes."""
    return MARKER.sub(lambda m: marker.format(order.get(int(m.group(1)), "?")), text)


REFERENCE_LINE = 90  # characters of "title, author, date" a references row holds on one line


MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def reference_date(number: int) -> str:
    """A source's date as the references tables print it: "29 September 2025" from its exact date
    (no hyphen for a line to break at), else its year, or "undated"."""
    import sources

    exact = sources.DATES.get(number)
    if exact:
        year, month, day = (int(x) for x in exact.split("-"))
        return f"{day} {MONTHS[month - 1]} {year}"
    return sources.ENTRIES[number - 1][5]


def reference_weight(number: int) -> int:
    """The lines a source's row takes in a references table, estimated from its length."""
    import math

    import sources

    _n, _topic, title, _short, who, year, _url = sources.ENTRIES[number - 1]
    who = sources.SLIDE_WHO.get(number, who)  # the references tables' short author form
    text = f"{title}, {who}, {reference_date(number)}"
    return max(1, math.ceil(len(text) / REFERENCE_LINE))


def reference_split(order: dict[int, int]) -> int:
    """How many sources part 1 lists: the split, in order of first citation, that balances the two
    tables' heights (their rows' lines), each at most 12 rows; on a tie, the more on part 1."""
    ranked = [n for _k, n in sorted((k, n) for n, k in order.items())]
    if len(ranked) <= REFERENCE_ROWS:
        return len(ranked)
    weights = [reference_weight(n) for n in ranked]
    choices = range(len(ranked) - REFERENCE_ROWS, REFERENCE_ROWS + 1)
    return min(choices, key=lambda k: (max(sum(weights[:k]), sum(weights[k:])), -k))


def reference_rows(order: dict[int, int], part: int) -> list[tuple[int, int]]:
    """(deck number, stable number) of the sources a references table lists, in order of first
    citation: part 1 the first ones, part 2 the rest, split so the two tables are about as tall
    (at most 12 rows each)."""
    ranked = sorted((k, n) for n, k in order.items())
    split = reference_split(order)
    return ranked[:split] if part == 1 else ranked[split:]


def failure_problems(s: dict, lines: list[str]) -> list[str]:
    problems = []
    lead = [x for x in lines if x.startswith("Lead:")]
    if lead and not strip_lead(lead[0]).startswith("An illustrative"):
        problems.append('a failure story\'s lead starts "An illustrative ..."')
    steps = [x for x in lines if re.match(r"^\d+\.\s", x)]
    if [x.split(".", 1)[0] for x in steps] != ["1", "2", "3", "4", "5"]:
        problems.append("a failure story holds five numbered steps, 1. to 5., in order")
    for x in steps:
        text = x.split(".", 1)[1].strip()
        if words(text) > FAILURE_STEP_WORDS:
            problems.append(f"step {x[:2]} has {words(text)} words, at most {FAILURE_STEP_WORDS}")
        if not (text[:1].isupper() and text.rstrip().endswith((".", "!", "?"))):
            problems.append(f"step {x[:2]} is a full sentence: a capital, then a full stop")
    if not s["title"].startswith("Failure story:"):
        problems.append('a failure story\'s title starts "Failure story:"')
    for x in lines:
        if not (x.startswith("Lead:") or re.match(r"^\d+\.\s", x)):
            problems.append(f"a failure story holds its lead and five steps only, not {x[:40]!r}")
    return problems


def strip_lead(line: str) -> str:
    return line.removeprefix("Lead:").strip()


def question_problems(s: dict, lines: list[str]) -> list[str]:
    problems = []
    reasons = [x for x in lines if re.match(r"^\d+\.\s", x)]
    if not 2 <= len(reasons) <= 3:
        problems.append(f"a question slide gives 2 or 3 numbered reasons, it has {len(reasons)}")
    if not re.search(r":\s+Why not .+\?$", s["title"]):
        problems.append('a question slide\'s title is "<Loop name>: Why not ...?"')
    for x in lines:
        if not (x.startswith(("Lead:", "Key idea:")) or re.match(r"^\d+\.\s", x)):
            problems.append(
                f"a question slide holds a lead, a key idea and reasons, not {x[:40]!r}"
            )
    return problems


def technique_problems(s: dict, lines: list[str]) -> list[str]:
    problems = []
    explained = [x for x in lines if x.startswith("- ")]
    if not 3 <= len(explained) <= 5:
        problems.append(f"a technique slide holds 3 to 5 lines, it has {len(explained)}")
    count = words(MARKER.sub("", " ".join(x[2:] for x in explained)))
    lo, hi = TECHNIQUE_WORDS
    if not lo <= count <= hi:
        problems.append(f"a technique's lines hold {count} words, want {lo}-{hi}")
    if not re.match(r"^[1-4]\) \S", s["title"]):
        problems.append('a technique slide\'s title is "N) Name" or "N) Name: claim"')
    for x in lines:
        if not x.startswith(("- ", "Key idea:")):
            problems.append(f"a technique slide holds its lines and its key idea, not {x[:40]!r}")
    return problems


def problem_rows_problems(s: dict, lines: list[str]) -> list[str]:
    problems = []
    rows = [x for x in lines if x.startswith("- ")]
    if not 3 <= len(rows) <= 5:
        problems.append(f"a problem slide holds 3 to 5 rows, it has {len(rows)}")
    for x in rows:
        m = PROBLEM_ROW.match(x)
        if not m:
            problems.append(f"a problem row is '- **Label:** text | icon', not {x[:40]!r}")
        elif m.group("icon") not in ICONS:
            problems.append(f"the icon {m.group('icon')!r} is not one of {', '.join(ICONS)}")
    for x in lines:
        if not x.startswith(("Lead:", "- ", "Footer:", "Key idea:")):
            problems.append(
                f"a problem slide holds a lead, rows, a footer or a key idea, not {x!r}"
            )
    if any(x.startswith("Footer:") for x in lines) and any(
        x.startswith("Key idea:") for x in lines
    ):
        problems.append("a problem slide ends with a footer or a key idea, not both")
    return problems


def quotes_problems(s: dict, lines: list[str], count: int) -> list[str]:
    problems = []
    quotes = [x for x in lines if x.startswith("Quote:")]
    if not 2 <= len(quotes) <= 4:
        problems.append(f"a quotes slide holds 2 to 4 quotes, it has {len(quotes)}")
    for x in quotes:
        m = QUOTE.match(x)
        if not m:
            problems.append(f"a quote is 'Quote: text | n', not {x[:40]!r}")
        elif not 1 <= int(m.group("n")) <= count:
            problems.append(f"the quote's source {m.group('n')} is not in the sources list")
    for x in lines:
        if not x.startswith(("Lead:", "Quote:")):
            problems.append(f"a quotes slide holds its lead and its quotes, not {x[:40]!r}")
    return problems


def costs_problems(s: dict, lines: list[str]) -> list[str]:
    problems = []
    panels: list[int] = []
    for x in lines:
        if x.startswith("Panel:"):
            panels.append(0)
        elif x.startswith("- "):
            if not panels:
                problems.append("a cost point comes after its Panel line")
            else:
                panels[-1] += 1
        elif not x.startswith(("Lead:", "Key idea:")):
            problems.append(f"a costs slide holds a lead, two panels and points, not {x[:40]!r}")
    if len(panels) != 2:
        problems.append(f"a costs slide holds two Panel lines, it has {len(panels)}")
    if any(not 2 <= n <= 4 for n in panels):
        problems.append(f"each cost panel holds 2 to 4 points, they hold {panels}")
    return problems


def table_problems_3(s: dict, lines: list[str]) -> list[str]:
    problems = []
    tables = table_rows(lines)
    if len(tables) != 1:
        problems.append(f"a table slide holds one table, it has {len(tables)}")
    for t in tables:
        if len(t) - 1 > TABLE_ROWS_3:
            problems.append(f"a table has {len(t) - 1} body rows, at most {TABLE_ROWS_3}")
        head = t[0]
        if len(head) == 4 and (head[0] != head[2] or head[1] != head[3]):
            problems.append(
                "a table of four columns is two term-meaning pairs: the same header twice"
            )
        if any(len(row) != len(head) for row in t):
            problems.append("every row of a table has as many cells as its header")
    for x in lines:
        if not (x.startswith(("Lead:", "Key idea:", "|"))):
            problems.append(f"a table slide holds a lead, a table and a key idea, not {x[:40]!r}")
    return problems


def agenda_problems(s: dict, lines: list[str]) -> list[str]:
    problems = []
    rows = [x for x in lines if re.match(r"^\d+\.\s", x)]
    if [x.split(".", 1)[0] for x in rows] != ["1", "2", "3", "4"]:
        problems.append("the agenda holds the four loops, 1. to 4., in order")
    now = [x for x in lines if x.startswith("Now:")]
    if len(now) > 1 or (now and not NOW.match(now[0])):
        problems.append("the agenda's star is one 'Now: N' line")
    elif now and not 1 <= int(NOW.match(now[0]).group("n")) <= 4:
        problems.append("the agenda's star is over a loop, 'Now: 1' to 'Now: 4'")
    for x in lines:
        if not (re.match(r"^\d+\.\s", x) or x.startswith("Now:")):
            problems.append(f"the agenda holds its four rows and a Now line, not {x[:40]!r}")
    return problems


def copied_problems(s: dict) -> list[str]:
    problems = []
    key = copied_key(s)
    spec = COPIED.get(key)
    if spec is None:
        if s["kind"] == "logistics":
            return [f"a logistics slide names its variant, one of {', '.join(VARIANTS)}"]
        return [f"no copied slide for {key!r}"]
    slots, extra = copied_parts(s)
    if len(slots) != len(spec["slots"]):
        problems.append(
            f"the copied slide fills {len(spec['slots'])} text slots in a fixed order; "
            f"{len(slots)} lines given"
        )
    for label in spec.get("required", ()):
        if sum(x.startswith(label) for x in extra) != 1:
            problems.append(f"the copied slide holds one {label} line")
    for label in spec.get("optional", ()):
        if sum(x.startswith(label) for x in extra) > 1:
            problems.append(f"the copied slide holds at most one {label} line")
    return problems


def field_problems_3(s: dict, lines: list[str]) -> list[str]:
    problems = []
    kind = s["kind"]
    figure, chart, image = (s.get(k) for k in ("figure", "chart", "image"))
    if kind in ("concept", "technique") and not figure:
        problems.append(f"a {kind} slide needs its figure")
    if figure:
        if not (figure.get("diagram") and figure.get("alt")):
            problems.append("a figure names its diagram and its alternative text")
        pattern = str(figure.get("diagram", "")).startswith(PATTERN_DIAGRAM)
        if kind == "technique" and not pattern:
            problems.append(f"a technique slide shows a pattern diagram, {PATTERN_DIAGRAM}<name>")
        if kind != "technique" and pattern:
            problems.append("a pattern diagram is drawn for the technique slide's pattern panel")
        if kind not in ("concept", "technique"):
            problems.append("a figure belongs to a concept or a technique slide")
    if s.get("code"):
        problems.append("design system 3 has no code slide: code goes into the DEMO notes")
    if kind == "evidence" and not (chart or table_rows(lines)):
        problems.append("an evidence slide needs a chart or a table")
    if chart:
        for key in ("title", "categories", "series", "x_label", "y_label"):
            if not chart.get(key):
                problems.append(f"the chart needs its {key}")
        for name, values in chart.get("series", []):
            if len(values) != len(chart.get("categories", [])):
                problems.append(f"chart series {name!r} needs one value per category")
        if not any(x.startswith("Sample:") for x in lines):
            problems.append("a chart states its sample size on a Sample line")
    if image:
        problems.append("design system 3 shows no screenshot on a slide: it goes into the notes")
    return problems


def notes_problems_3(kind: str, notes: list[str], block: str) -> list[str]:
    """The notes standard under design system 3: the eight labels (the short form on the title,
    the copied types and the references), and the whole notes' words on a teaching slide."""
    spec = KINDS_3[kind]
    order_kind = "demo" if kind == "demo" else ("break" if spec.short else "concept")
    problems = note_order_problems(order_kind, notes)
    whole = spec.whole or (WHOLE if kind == "table" and block == "problem" else None)
    if whole:
        # The whole notes' words are the spoken ones: an instructor's "Do:" line is not counted.
        count = words(" ".join(x for x in notes if not x.startswith(SHORT_OPTIONAL)))
        if not whole[0] <= count <= whole[1]:
            problems.append(f"the notes have {count} words, want {whole[0]}-{whole[1]}")
        for label, most in NOTE_LIMITS.items():
            for line in notes:
                if line.startswith(label) and words(line[len(label) :]) > most:
                    problems.append(
                        f"{label} has {words(line[len(label) :])} words, at most {most}"
                    )
    else:
        lo, hi = spec.say
        say = words(
            " ".join(x.removeprefix("What to say:") for x in notes if x.startswith("What to"))
        )
        if not lo <= say <= hi:
            problems.append(f"What to say has {say} words, want {lo}-{hi}")
        for label, most in NOTE_LIMITS.items():
            for line in notes:
                if line.startswith(label) and words(line[len(label) :]) > most:
                    problems.append(
                        f"{label} has {words(line[len(label) :])} words, at most {most}"
                    )
    m = BARE_NOTE_CITATION.search(" ".join(notes))
    if m:
        problems.append(f"cite a source in the notes as 'Source [^n]', not {m.group(0)!r}")
    return problems


def check_slide_design_3(tag: str, s: dict, count: int, block: str = "") -> list[str]:
    kind = s["kind"]
    spec = KINDS_3.get(kind)
    if spec is None:
        return [f"{tag}: unknown slide type {kind!r}; the types are {', '.join(KINDS_3)}"]
    problems = []
    if s.get("minutes", 0) <= 0 and not (kind == "references" and s.get("minutes") == 0):
        problems.append(f"{tag}: every slide has minutes (the references slides 0)")
    most = DEMO_TITLE_CHARACTERS_3 if kind == "demo" else TITLE_CHARACTERS_3
    if kind not in ("title", *COPIED_KINDS) and len(s["title"]) > most:
        problems.append(f"{tag}: a title is one line of at most {most} characters")
    raw = [COMMENT.sub("", x) for x in s.get("on_slide", [])]
    lines = visible_lines(s)
    problems += [f"{tag}: {p}" for p in field_problems_3(s, lines)]
    if kind in COPIED_KINDS:
        problems += [f"{tag}: {p}" for p in copied_problems(s)]
    for x in (x for x in raw if x.startswith("Link:")):
        m = LINK.match(x)
        if not m or not m.group("url").startswith(GITHUB + "/"):
            problems.append(f"{tag}: a link is 'Link: <label> | {GITHUB}/<path>'")
        elif kind != "demo":
            problems.append(f"{tag}: only a DEMO slide carries a link line")
    if kind not in COPIED_KINDS:
        for prefix in spec.required:
            if not any(x.strip().lstrip("*").startswith(prefix) for x in raw):
                problems.append(f"{tag}: on_slide needs a line starting {prefix!r}")
        if any(x.startswith("Insight:") for x in lines):
            problems.append(f"{tag}: design system 3 has no Insight callout; write a Key idea")
        keys = [x for x in lines if x.startswith("Key idea:")]
        if keys and kind not in KEY_IDEA_KINDS:
            problems.append(f"{tag}: a Key idea is drawn on {', '.join(KEY_IDEA_KINDS)} only")
        if len(keys) > 1:
            problems.append(f"{tag}: one Key idea line")
        leads = [x for x in lines if x.startswith("Lead:")]
        if len(leads) > 1 or (leads and kind not in LEAD_KINDS):
            problems.append(f"{tag}: at most one Lead line, on {', '.join(LEAD_KINDS)}")
        bullets = sum(x.startswith("- ") for x in lines)
        if bullets > spec.bullets and kind not in ("costs",):
            problems.append(f"{tag}: {bullets} bullets, at most {spec.bullets}")
        numbered = sum(bool(re.match(r"^\d+\.\s", x)) for x in lines)
        most_numbered = {"agenda": 4, "failure": 5, "question": 3, "closing": 10}.get(kind, 4)
        if numbered > most_numbered:
            problems.append(f"{tag}: {numbered} numbered lines, at most {most_numbered}")
        for field, text in (
            ("title", s["title"]),
            ("says", s["says"]),
            ("on_slide", " ".join(lines)),
        ):
            m = NO_REPO.search(text)
            if m:
                problems.append(f"{tag}: {field} holds a repository-style token {m.group(0)!r}")
    checks = {
        "failure": failure_problems,
        "question": question_problems,
        "technique": technique_problems,
        "problem": problem_rows_problems,
        "costs": costs_problems,
        "table": table_problems_3,
        "agenda": agenda_problems,
    }
    if kind in checks:
        problems += [f"{tag}: {p}" for p in checks[kind](s, lines)]
    if kind == "quotes":
        problems += [f"{tag}: {p}" for p in quotes_problems(s, lines, count)]
    if kind == "payoff":
        body = [x for x in lines if not x.startswith("Lead:")]  # a lead line is allowed here
        problems += [f"{tag}: {p}" for p in payoff_problems(s, body)]
    if kind == "concept":
        for x in lines:
            if not x.startswith(("Lead:", "Key idea:")):
                problems.append(
                    f"{tag}: a concept slide holds its lead and its key idea, not {x!r}"
                )
    if kind == "references":
        if s.get("part") not in (1, 2):
            problems.append(f"{tag}: a references slide names its part, 1 or 2")
        if any(not x.startswith("Lead:") for x in lines):
            problems.append(f"{tag}: a references slide's rows come from the citations")
    if kind == "demo" and not re.match(
        r"^Section [1-4]: .+ - Implementation Notes: \S", s["title"]
    ):
        problems.append(
            f"{tag}: a DEMO slide's title is 'Section N: <Loop name> - Implementation Notes: ...'"
        )
    if kind == "design_callout" and not s["title"].startswith("Text-to-SQL design:"):
        problems.append(f"{tag}: a design callout's title starts 'Text-to-SQL design:'")
    lo, hi = spec.words
    if not lo <= visible_words_3(s) <= hi:
        problems.append(f"{tag}: {visible_words_3(s)} words on the slide, want {lo}-{hi}")
    for m in MARKER.finditer(" ".join(lines)):
        if not 1 <= int(m.group(1)) <= count:
            problems.append(f"{tag}: source marker [{m.group(1)}] is not in the sources list")
    for x in s.get("notes", []):
        for m in MARKER.finditer(x):
            if not 1 <= int(m.group(1)) <= count:
                problems.append(f"{tag}: notes cite [^{m.group(1)}], not in the sources list")
    board = s.get("scoreboard")
    if board is not None and (kind != "evidence" or board not in SCOREBOARD):
        problems.append(f"{tag}: a scoreboard is an evidence slide's section number, 1 to 4")
    if kind not in EVIDENCE_KINDS_3:
        problems += [f"{tag}: {p}" for p in evidence_diet_problems({**s, "kind": "-"}, lines)]
    notes = list(s.get("notes", []))
    problems += [f"{tag}: {p}" for p in notes_problems_3(kind, notes, block)]
    if kind != "demo" and not s.get("allow_commands"):
        m = NOTE_REPO.search(" ".join(notes))
        if m:
            problems.append(f"{tag}: notes hold a path or command {m.group(0)!r} (DEMO notes only)")
    if re.search(r"\breplay", " ".join(notes) + " ".join(lines) + s["says"], re.I):
        problems.append(f"{tag}: the word 'replay' appears")
    if PROVISIONAL.search(" ".join(notes + s.get("on_slide", []))):
        problems.append(f"{tag}: a provisional marker is left; resolve it or refresh-mark it")
    return problems


def section_problems_3(name: str, slides: list[dict]) -> list[str]:
    """A section in the reference's rhythm: 12 slides in order, the star on its loop, the four
    techniques numbered 1) to 4), the cheat sheet's three columns, the DEMO slide's title, and the
    scoreboard on its Measured slide."""
    problems = []
    number = int(name[1])
    loop = LOOPS[name]
    kinds = [s["kind"] for s in slides]
    if kinds != list(SECTION_RHYTHM):
        problems.append(
            f"{name}: a section's 12 slides run {', '.join(SECTION_RHYTHM)}; got {kinds}"
        )
        return problems
    agenda, failure, question, *techniques = slides[:7]
    design, cheat, demo, evidence, _qa = slides[7:]
    now = [NOW.match(x) for x in visible_lines(agenda)]
    if [int(m.group("n")) for m in now if m] != [number]:
        problems.append(f"{name}: its agenda's star is over its loop: 'Now: {number}'")
    if not question["title"].lower().startswith(loop.lower() + ":"):
        problems.append(f"{name}: the question slide's title starts '{loop}:'")
    for i, s in enumerate(techniques, 1):
        if not s["title"].startswith(f"{i}) "):
            problems.append(f"{name}: technique {i}'s title starts '{i}) '")
    tables = table_rows(visible_lines(cheat))
    if (
        not cheat["title"].startswith("Cheat Sheet:")
        or not tables
        or tables[0][0] != CHEAT_SHEET_HEADER
    ):
        problems.append(
            f"{name}: the cheat sheet is titled 'Cheat Sheet: ...' with the columns "
            + " | ".join(CHEAT_SHEET_HEADER)
        )
    if tables and len(tables[0]) - 1 != 4:
        problems.append(f"{name}: the cheat sheet has one row per technique, four rows")
    if not demo["title"].startswith(f"Section {number}: {loop} - Implementation Notes:"):
        problems.append(
            f"{name}: the DEMO slide's title starts 'Section {number}: {loop} - Implementation Notes:'"
        )
    if not evidence["title"].startswith("Measured:"):
        problems.append(f"{name}: the evidence slide's title starts 'Measured:'")
    if evidence.get("scoreboard") != number:
        problems.append(f"{name}: its Measured slide carries the scoreboard: scoreboard={number}")
    del failure, design
    return problems


def check_block_design_3(name: str, slides: list[dict]) -> list[str]:
    count = sources_count()
    problems = []
    for i, s in enumerate(slides, 1):
        block = s.get("_block", name)
        problems += check_slide_design_3(f"{name}#{i} {s['title']!r}", s, count, block)
    problems += spelled_out_problems(name, slides)
    plan = {key: (minutes, most) for key, _n, minutes, most in BLOCK_PLAN_3}
    if name in plan:
        minutes, most = plan[name]
        total = sum(s["minutes"] for s in slides)
        if total != minutes:
            problems.append(
                f"{name}: its slides add up to {total:g} minutes, the block has {minutes}"
            )
        if len(slides) > most:
            problems.append(f"{name}: {len(slides)} slides, at most {most}")
    if name in LOOPS:
        problems += section_problems_3(name, slides)
    elif name in plan:
        for s in slides:
            if s["kind"] == "agenda" and any(NOW.match(x) for x in visible_lines(s)):
                problems.append(f"{name}: only a section's agenda carries the star")
    return problems


def deck_problems_3(blocks: list[tuple[str, list[dict]]]) -> list[str]:
    """The whole deck under design system 3: slides, minutes, breaks and poll, and the sources."""
    slides = [s for _n, sl in blocks for s in sl]
    problems = []
    if len(slides) > MAX_SLIDES_3:
        problems.append(f"{len(slides)} slides, at most {MAX_SLIDES_3}")
    seconds = sum(int(round(s["minutes"] * 60)) for s in slides)
    if seconds != CLASS_SECONDS:
        problems.append(f"the slides add up to {seconds / 60:g} minutes, not 240")
    kinds = [s["kind"] for s in slides]
    if kinds.count("break") != 2 or kinds.count("poll") != 1:
        problems.append("two breaks and one poll")
    order = citation_order(slides)
    if len(order) > MAX_SOURCES_3:
        problems.append(f"the deck cites {len(order)} sources, at most {MAX_SOURCES_3}")
    parts = sorted(s.get("part") for s in slides if s["kind"] == "references")
    if parts != [1, 2]:
        problems.append("the closing holds the two references slides, parts 1 and 2")
    return problems


def slide_lines_3(n: int, s: dict, start: int, order: dict[int, int]) -> list[str]:
    """One slide of the outline under design system 3: sources shown by their deck numbers, a
    quote with its attribution, a references slide with its generated rows."""
    import sources

    kind = KINDS_3[s["kind"]].name if s["kind"] in KINDS_3 else s["kind"]
    extra = f" ({s['variant']})" if s.get("variant") else ""
    lines = [f"**Slide {n}: {s['title']}**", "", f"Type: {kind}{extra}.", ""]
    lines += ["On the slide:", ""]
    shown = list(s.get("on_slide", []))
    if s["kind"] == "references":
        shown += ["| Source | Title, author, date |", "|---|---|"]
        for k, number in reference_rows(order, s.get("part", 1)):
            _n, _t, title, _short, who, year, url = sources.ENTRIES[number - 1]
            when = reference_date(number)
            who = sources.SLIDE_WHO.get(number, who)
            shown.append(f"| Source {k} | [{title}]({url}), {who}, {when} |")
    prev_table = False
    for x in shown:
        m = QUOTE.match(x)
        if m:
            number = int(m.group("n"))
            short = sources.ENTRIES[number - 1][3] if 1 <= number <= len(sources.ENTRIES) else "?"
            x = f"Quote: {m.group('text')} — Source {order.get(number, '?')}: {short}"
        is_table = x.startswith("|")
        if is_table != prev_table and lines[-1] != "":
            lines.append("")
        text = cite(x, order)
        lines.append(text if is_table else text + "  ")
        prev_table = is_table
    lines[-1] = lines[-1].rstrip()
    lines.append("")
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
    board = s.get("scoreboard")
    if board in SCOREBOARD:
        lines += [f"Scoreboard after Section {board}:", ""]
        for k, state in SCOREBOARD.items():
            name = f"- Section {k}: {LOOPS[f's{k}']}"
            if k > board:
                lines.append(f"{name} (to come)")
            else:
                lines.append(f"{name} ({'now' if k == board else 'done'}): {state}")
        lines.append("")
    lines += ["Speaker notes:", ""]
    note = [cite(x, order, "{}") for x in with_timing(list(s["notes"]), s["minutes"], start)]
    lines += [x + "  " if j < len(note) - 1 else x for j, x in enumerate(note)]
    lines.append("")
    return lines


def render_design_3(out: str, blocks: list[tuple[str, list[dict]]], samples: bool = False) -> int:
    """The outline under design system 3 (or the sample slides' outline); every problem is
    printed, and the gate reads the "problems: N" line."""
    import sources

    problems = [p for n, sl in blocks for p in check_block_design_3(n, sl)]
    names = {key: name for key, name, *_ in BLOCK_PLAN_3}
    plan = {key: (minutes, most) for key, _n, minutes, most in BLOCK_PLAN_3}
    slides = [s for _n, sl in blocks for s in sl]
    order = citation_order(slides)
    total = len(slides)
    seconds = sum(int(round(s["minutes"] * 60)) for s in slides)
    head = "sample slides, one of every type" if samples else "deck outline"
    lines = [
        f"# Loop Engineering: {head}",
        "",
        f"Class length: 240 minutes. Blocks: {len(blocks)}. Slides: {total}.",
        "",
        "This outline is the input for the deck, which is built from it in the format of the "
        "previous module's deck (slides/design-system.md, design system 3): one fixed layout per "
        "slide type, the agenda before each section, and speaker notes under the labels of the "
        "notes standard. Slides carry no file names, repository paths, or make commands; the "
        "link lines on a slide are the DEMO slide's demo page and the sources. Every demo is "
        "live: recovery is reset and run it again, never a recording. Sources are numbered in "
        "the order the deck first cites them; a marker such as [3] names Source 3 of the "
        "references tables at the end.",
        "",
        "Terms spelled out once for the whole outline: application programming interface (API), "
        "Structured Query Language (SQL), Coordinated Universal Time (UTC), JavaScript Object "
        "Notation (JSON), and large language model (LLM).",
        "",
    ]
    t, n, density = 0, 0, []
    for name, block_slides in blocks:
        block_seconds = sum(int(round(s["minutes"] * 60)) for s in block_slides)
        if name in plan:
            minutes, most = plan[name]
            lines += [
                f"## {names[name]}",
                "",
                f"Clock {clock(t)}-{clock(t + block_seconds)}: {minutes} minutes, at most {most} "
                f"slides; {len(block_slides)} slides.",
                "",
            ]
        else:
            lines += ["## The sample slides", ""]
        lines += [
            "| # | Slide | Type | Time (start-end) | Says in one line | Source in the repository |",
            "|---|---|---|---|---|---|",
        ]
        rt = t
        for i, s in enumerate(block_slides):
            secs = int(round(s["minutes"] * 60))
            kind = KINDS_3[s["kind"]].name if s["kind"] in KINDS_3 else s["kind"]
            lines.append(
                f"| {n + i + 1} | {s['title']} | {kind} | {clock(rt)}-{clock(rt + secs)} "
                f"| {cite(s['says'], order)} | {s['src']} |"
            )
            rt += secs
        lines += ["", f"### Slides and speaker notes: {names.get(name, 'the sample slides')}", ""]
        for s in block_slides:
            n += 1
            if s["kind"] in KINDS_3:
                lines += slide_lines_3(n, s, t, order)
            density.append((n, s["title"], visible_words_3(s), words(" ".join(s["notes"]))))
            t += int(round(s["minutes"] * 60))
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
    lines += ["## Sources in the order cited", ""]
    lines += [
        "The deck's numbers, in order of first citation, with the number of the verified source "
        "list (slides/source/sources.py) each one is.",
        "",
    ]
    for number, k in sorted(order.items(), key=lambda item: item[1]):
        if 1 <= number <= len(sources.SOURCES):
            lines.append(
                f"- Source {k} (list entry {number}): {sources.SOURCES[number - 1][len(f'[{number}] ') :]}"
            )
    lines.append("")
    if not samples:
        problems += deck_problems_3(blocks)

        def box(ok: bool) -> str:
            return "[x]" if ok else "[ ]"

        lines += [
            "## Checks before building slides",
            "",
            f"- {box(total <= MAX_SLIDES_3)} {total} slides, at most {MAX_SLIDES_3}.",
            f"- {box(seconds == CLASS_SECONDS)} The times add up to {seconds / 60:g} minutes; "
            "each block's slides add up to its minutes.",
            f"- {box(not problems)} Each section runs in the reference's rhythm, with exactly one "
            "DEMO slide whose demos are in its notes; two breaks and one poll, after Section 3: "
            "Event loop.",
            f"- {box(len(order) <= MAX_SOURCES_3)} {len(order)} sources, at most "
            f"{MAX_SOURCES_3}, numbered in the order first cited, on two references tables.",
            f"- {box(not problems)} Every slide follows its type's layout rules and the speaker "
            "notes standard.",
            "",
        ]
    Path(out).write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(
        f"rules: {DESIGN_SYSTEM_3}; slides {total}; minutes {seconds / 60:g}; sources {len(order)}"
    )
    for name, block_slides in blocks:
        print(f"  {names.get(name, name)}: {len(block_slides)}")
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
    if rules == DESIGN_SYSTEM_3:
        return render_design_3(out, [(key, load(key)) for key, *_ in BLOCK_PLAN_3])
    if rules in PLANS:
        return render_design(out, [(key, load(key)) for key, *_ in PLANS[rules]], rules=rules)
    print("The block modules follow different rule sets, so the outline is not built:")
    for name, value in sets.items():
        print(f"  {name}: {value or 'no module yet'}")
    print(
        f'Set RULES = "{DESIGN_SYSTEM_2}" in every block module of the second rebuild\'s plan '
        "(with the problem and foundations blocks) to build under it; check one block meanwhile "
        "with --check <block>."
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
        # --samples OUT [MODULE]: the sample module of design system 2 (samples) or of design
        # system 3 (samples3).
        module = argv[2] if len(argv) > 2 else "samples"
        slides = load_design(module)
        if rules_of(slides) == DESIGN_SYSTEM_3:
            return render_design_3(argv[1], [(module, slides)], samples=True)
        return render_design(argv[1], [(module, slides)], samples=True, rules=rules_of(slides))
    return render(argv[0])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
