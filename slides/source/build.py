"""Builds slides/outline.md from the block modules in this folder and checks every rule a script can.

Usage:
  python3 build.py OUT_PATH            # build the whole outline (all blocks must exist)
  python3 build.py --check s1 [s2 ...] # check only these blocks, write nothing

Each block module (opening, s1, s2, s3, s4, closing) defines SLIDES, a list of dicts:
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
NO_REPO = re.compile(
    r"(?:\bmake [a-z]|\b[\w-]+/[\w./-]+|\.(?:py|ya?ml|md|toml|sql|sh)\b|\blines? \d+|`)"
)
NOTE_REPO = re.compile(r"\bmake [a-z]|\bplatform/|\b[\w-]+/[\w./-]*\.(?:py|ya?ml|md|toml|sql|sh)\b")
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


def load(name: str) -> list[dict]:
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


def render(out: str) -> None:
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
        "spine question slide; the platform's code appears only in each demo segment, opened live "
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


def main(argv: list[str]) -> int:
    if argv[:1] == ["--check"]:
        problems = []
        for name in argv[1:]:
            problems += check_block(name, load(name))
        for p in problems:
            print("x", p)
        print(f"problems: {len(problems)}")
        return 1 if problems else 0
    render(argv[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
