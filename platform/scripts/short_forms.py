"""The naming rule (docs/STYLE.md, "Names"): what never appears in prose, and what is spelled out.

Three lists live in platform/config/course.toml:

- [[short_forms]]: codes and short forms for the course's own things (S1, A2, FY2025, PII). An
  error everywhere. check_style.py reports a match on a Markdown page as "Short form in prose".
- [[shorthand]]: shorthand words ("e.g.", "repo", "DB", "config", "docs", "vs"). check_style.py
  reports a match as "Shorthand in prose". A warning while pages are written, an error with
  --strict; an error at once in a commit message (--commit-messages).
- [[technical_terms]]: terms that are fine as words (SQL, API, JSON) but are spelled out on their
  first use on every page, as "Structured Query Language (SQL)" or "SQL (Structured Query
  Language)". check_style.py reports a first use without it as "Term not spelled out on first use".
  A warning, an error with --strict. Commit messages are not held to this part.

None of the lists reads code: inline code spans, fenced code, HTML comments, front matter, link
targets, URLs, paths, file names (.env, config.toml), and identifiers (max_retries) are skipped.

check_style.py checks the course pages. This script checks any other text: commit messages, the
slide outline, the text extracted from the deck, or console labels. A file ending in .md is read as
Markdown (headings are prose); any other text skips lines that start with '#' (the comments of a
commit message template).

Usage:
    uv run python platform/scripts/short_forms.py [--strict | --warn-only] FILE...
    git log --format=%B | uv run python platform/scripts/short_forms.py --commit-messages -

Exit code: 1 on a short form; 1 on shorthand in a commit message; with --strict, 1 on any finding;
with --warn-only, 0 always; 2 when no input is given.
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONFIG_FILE = REPO / "platform" / "config" / "course.toml"
_CODE_SPAN = re.compile(r"(`+)(.+?)\1")

# A shorthand word or a technical term is a whole word: nothing that makes it part of a path, a
# file name, an identifier, a make target, or a variable is joined to it.
_WORD_BEFORE = r"(?<![-\w./\\@$])"
_WORD_AFTER = r"(?![-\w/\\]|\.\w)"
# A term may be joined by a hyphen ("JSON-formatted", "text-to-SQL"): that is still prose.
_TERM_BEFORE = r"(?<![\w./\\@$])"
_TERM_AFTER = r"(?![\w/\\]|\.\w)"


@dataclass(frozen=True)
class ShortForm:
    pattern: re.Pattern[str]
    write: str
    covered_by_codes: bool


@dataclass(frozen=True)
class Shorthand:
    word: str
    pattern: re.Pattern[str]
    write: str


@dataclass(frozen=True)
class Term:
    term: str
    expansion: str
    pattern: re.Pattern[str]
    before: re.Pattern[str]  # "<expansion> (" right before the term
    after: re.Pattern[str]  # " (<expansion>)" right after the term

    @property
    def spelled_out(self) -> str:
        return f"{self.expansion} ({self.term})"


def _config(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load(path: Path = CONFIG_FILE) -> list[ShortForm]:
    return [
        ShortForm(re.compile(e["pattern"]), e["write"], bool(e.get("covered_by_codes", False)))
        for e in _config(path).get("short_forms", [])
    ]


def load_shorthand(path: Path = CONFIG_FILE) -> list[Shorthand]:
    out = []
    for e in _config(path).get("shorthand", []):
        flags = re.IGNORECASE if e.get("ignore_case", True) else 0
        pattern = re.compile(f"{_WORD_BEFORE}(?:{e['match']}){_WORD_AFTER}", flags)
        out.append(Shorthand(e["word"], pattern, e["write"]))
    return out


def _expansion_regex(expansion: str) -> str:
    """The expansion's words, any case, any run of spaces or a line break between them."""
    return r"\s+".join(re.escape(word) for word in expansion.split())


def load_terms(path: Path = CONFIG_FILE) -> list[Term]:
    out = []
    for e in _config(path).get("technical_terms", []):
        term, words = e["term"], _expansion_regex(e["expansion"])
        emphasis = r"[*_]*"
        out.append(
            Term(
                term,
                e["expansion"],
                re.compile(f"{_TERM_BEFORE}{re.escape(term)}s?{_TERM_AFTER}"),
                re.compile(rf"(?i:{words})s?{emphasis}\s*\(\s*{emphasis}$"),
                re.compile(rf"{emphasis}\s*\(\s*{emphasis}(?i:{words})s?{emphasis}\s*\)"),
            )
        )
    return out


SHORT_FORMS = load()
SHORTHAND = load_shorthand()
TERMS = load_terms()

# -- masking: what is not prose --------------------------------------------------------------------

_LINK_TARGET = re.compile(r"\]\(([^)]*)\)")
_URL = re.compile(r"<?\b(?:https?|ftp|file)://[^\s<>]*[^\s<>.,;:!?)\]'\"]>?|<?\bwww\.[^\s<>]+>?")
_REFERENCE = re.compile(r"^(\s*\[[^\]]+\]:\s*)(\S+.*)$")
_HTML_CODE = re.compile(r"<(code|kbd|samp|pre)\b[^>]*>.*?</\1>", re.IGNORECASE)
# A conventional commit's type and scope: "docs(research):" or "build(config)!:".
_COMMIT_PREFIX = re.compile(r"^[a-z]+(?:\([^)\n]*\))?!?:(?=\s|$)")


def _blank(match: re.Match[str]) -> str:
    return " " * len(match.group(0))


def mask_code_spans(text: str) -> str:
    """Inline code is an identifier, not prose: blank it out, keeping offsets."""
    return _CODE_SPAN.sub(_blank, text)


def mask_prose(text: str) -> str:
    """One line with code spans, inline HTML code, link targets, reference link targets, and URLs
    blanked out, keeping offsets."""
    text = mask_code_spans(text)
    text = _HTML_CODE.sub(_blank, text)
    text = _LINK_TARGET.sub(lambda m: "](" + " " * len(m.group(1)) + ")", text)
    reference = _REFERENCE.match(text)
    if reference:
        text = reference.group(1) + " " * len(reference.group(2))
    return _URL.sub(_blank, text)


_FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")


def _strip_comments(text: str, in_comment: bool) -> tuple[str, bool]:
    """`text` with HTML comments blanked out, and whether a comment is still open at its end."""
    out = ""
    while text:
        if in_comment:
            end = text.find("-->")
            if end < 0:
                return out + " " * len(text), True
            out += " " * (end + 3)
            text, in_comment = text[end + 3 :], False
            continue
        start = text.find("<!--")
        if start < 0:
            return out + text, False
        out += text[:start] + "    "
        text, in_comment = text[start + 4 :], True
    return out, in_comment


def prose(text: str) -> list[tuple[int, str]]:
    """(line number, prose) for every line of a Markdown page that holds prose. Front matter,
    fenced code, and HTML comments are left out; code spans (also one that runs on to the next
    line), link targets, and URLs are blanked out, keeping offsets. Headings, lists, tables, and
    quotes are prose."""
    out: list[tuple[int, str]] = []
    lines = text.splitlines()
    start = 0
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() in ("---", "...")), None)
        if end is not None:
            start = end + 1
    fence = ""
    tick = ""  # a code span still open from the line before
    in_comment = False
    for index in range(start, len(lines)):
        raw = lines[index]
        if fence:
            close = _FENCE.match(raw)
            if (
                close
                and close.group(1)[0] == fence[0]
                and len(close.group(1)) >= len(fence)
                and not close.group(2).strip()
            ):
                fence = ""
            continue
        if not in_comment:
            opening = _FENCE.match(raw)
            if opening and not (opening.group(1)[0] == "`" and "`" in opening.group(2)):
                fence, tick = opening.group(1), ""
                continue
        if not raw.strip():
            tick = ""
        line, in_comment = _strip_comments(raw, in_comment)
        if tick:
            end = line.find(tick)
            if end < 0:
                continue
            line = " " * (end + len(tick)) + line[end + len(tick) :]
            tick = ""
        line = mask_prose(line)
        stray = re.search(r"`+", line)
        if stray:
            tick = stray.group(0)
            line = line[: stray.start()] + " " * (len(line) - stray.start())
        if line.strip():
            out.append((index + 1, line))
    return out


def plain_lines(text: str, *, commit_messages: bool = False) -> list[tuple[int, str]]:
    """(line number, prose) for plain text: fenced blocks and lines that start with '#' (the
    comments of a commit message template) are left out; code spans and URLs are blanked out.
    In a commit message, the type and scope of the subject ("docs(research):") are not prose."""
    out = []
    in_fence = False
    for no, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence or line.startswith("#"):
            continue
        if commit_messages:
            line = _COMMIT_PREFIX.sub(_blank, line)
        out.append((no, mask_prose(line)))
    return out


# -- the three rules -------------------------------------------------------------------------------


def find(text: str, *, include_codes: bool = True) -> list[tuple[str, str]]:
    """Every (short form, what to write instead) in one line of prose."""
    masked = mask_code_spans(text)
    found = []
    for form in SHORT_FORMS:
        if form.covered_by_codes and not include_codes:
            continue
        found += [(m.group(0), form.write) for m in form.pattern.finditer(masked)]
    return found


def find_shorthand(text: str) -> list[tuple[str, str]]:
    """Every (shorthand word, what to write instead) in one line of prose, in order."""
    masked = mask_prose(text)
    hits = [
        (m.start(), entry.word, entry.write)
        for entry in SHORTHAND
        for m in entry.pattern.finditer(masked)
    ]
    return [(word, write) for _, word, write in sorted(hits)]


def first_use_problems(lines: list[tuple[int, str]]) -> list[tuple[int, str, str]]:
    """(line number, term, what to write) for each technical term whose first use in `lines` (the
    prose of one page, in order) is not spelled out. Only the first use of a term is read."""
    text, starts = "", []
    for no, line in lines:
        starts.append((len(text), no))
        text += line + "\n"
    problems = []
    for term in TERMS:
        match = term.pattern.search(text)
        if match is None:
            continue
        if term.before.search(text[: match.start()]) and re.match(r"\s*\)", text[match.end() :]):
            continue
        if term.after.match(text[match.end() :]):
            continue
        line = [no for start, no in starts if start <= match.start()][-1]
        problems.append((line, term.term, term.spelled_out))
    return sorted(problems)


def check_text(text: str) -> list[tuple[int, str, str]]:
    """(line number, short form, advice) for plain text; fenced blocks and '#' comment lines
    (as in a commit message template) are skipped."""
    problems = []
    in_fence = False
    for no, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence or line.startswith("#"):
            continue
        problems += [(no, form, advice) for form, advice in find(line)]
    return problems


def _lines(text: str, *, markdown: bool, commit_messages: bool) -> list[tuple[int, str]]:
    return prose(text) if markdown else plain_lines(text, commit_messages=commit_messages)


def check_short_forms(text: str, *, markdown: bool) -> list[tuple[int, str, str]]:
    """(line number, short form, advice). Markdown is read as a page (headings are prose); plain
    text as `check_text` reads it."""
    if not markdown:
        return check_text(text)
    return [(no, form, advice) for no, line in prose(text) for form, advice in find(line)]


def check_shorthand(
    text: str, *, markdown: bool, commit_messages: bool = False
) -> list[tuple[int, str, str]]:
    """(line number, shorthand word, advice)."""
    lines = _lines(text, markdown=markdown, commit_messages=commit_messages)
    return [(no, word, advice) for no, line in lines for word, advice in find_shorthand(line)]


def check_first_use(text: str, *, markdown: bool) -> list[tuple[int, str, str]]:
    """(line number, term, its spelled-out form): the whole text is one page."""
    return first_use_problems(_lines(text, markdown=markdown, commit_messages=False))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("inputs", nargs="*", help="files, or '-' for standard input")
    parser.add_argument(
        "--commit-messages",
        action="store_true",
        help="the text is commit messages: shorthand is an error, the first-use rule is not read",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--strict", action="store_true", help="every finding is an error")
    mode.add_argument("--warn-only", action="store_true", help="report only; exit 0")
    args = parser.parse_args(argv)
    if not args.inputs:
        print(__doc__)
        return 2
    shorthand_is_error = args.commit_messages or args.strict
    counts = {"short forms": 0, "shorthand": 0, "first use": 0}
    for arg in args.inputs:
        name, text = (
            ("stdin", sys.stdin.read()) if arg == "-" else (arg, Path(arg).read_text("utf-8"))
        )
        markdown = arg != "-" and arg.endswith(".md") and not args.commit_messages
        for no, form, advice in check_short_forms(text, markdown=markdown):
            print(f"{name}:{no}: short form '{form}': write {advice}")
            counts["short forms"] += 1
        mark = "" if shorthand_is_error else "warning: "
        for no, word, advice in check_shorthand(
            text, markdown=markdown, commit_messages=args.commit_messages
        ):
            print(f"{mark}{name}:{no}: shorthand '{word}': write {advice}")
            counts["shorthand"] += 1
        if args.commit_messages:
            continue
        mark = "" if args.strict else "warning: "
        for no, term, spelled_out in check_first_use(text, markdown=markdown):
            print(f"{mark}{name}:{no}: first use of '{term}' on the page: write '{spelled_out}'")
            counts["first use"] += 1
    print(
        f"short forms: {counts['short forms']} found; shorthand: {counts['shorthand']} found; "
        f"terms not spelled out on first use: {counts['first use']} found"
    )
    if args.warn_only:
        return 0
    failed = counts["short forms"] or (shorthand_is_error and counts["shorthand"])
    return 1 if failed or (args.strict and counts["first use"]) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
