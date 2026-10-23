"""The naming check, part 2: shorthand words in prose, and technical terms spelled out on their
first use on every page (docs/STYLE.md, "Names"). Each rule has cases that must be found and cases
that must not: code spans, fenced code, paths, URLs, file names, identifiers, and longer words."""

from __future__ import annotations

import importlib.util
import io
import sys
import tomllib
from pathlib import Path

import pytest

from datapilot.settings import PLATFORM

SCRIPTS = PLATFORM / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses look their module up by name
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def short_forms():
    return _load("short_forms")


@pytest.fixture(scope="module")
def check_style(short_forms):
    return _load("check_style")


# -- the lists in course.toml ---------------------------------------------------------------------


def test_the_lists_live_in_the_course_config() -> None:
    config = tomllib.loads((PLATFORM / "config" / "course.toml").read_text("utf-8"))
    words = {entry["word"] for entry in config["shorthand"]}
    assert words == {
        "e.g.", "i.e.", "etc.", "repo", "DB", "env", "config", "info", "docs", "max", "min",
        "approx", "vs",
    }  # fmt: skip
    terms = {entry["term"]: entry["expansion"] for entry in config["technical_terms"]}
    assert terms == {
        "SQL": "Structured Query Language",
        "API": "application programming interface",
        "JSON": "JavaScript Object Notation",
        "CSV": "comma-separated values",
        "LLM": "large language model",
        "HTTP": "Hypertext Transfer Protocol",
        "URL": "Uniform Resource Locator",
        "UTC": "Coordinated Universal Time",
    }


# -- shorthand: found in prose --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "word"),
    [
        ("Use a cache, e.g. a dictionary.", "e.g."),
        ("E.g. the first run.", "e.g."),
        ("Use a cache (e.g., a dictionary).", "e.g."),
        ("The fast path, i.e. no review.", "i.e."),
        ("I.e. the fast path.", "i.e."),
        ("Apples, pears, etc.", "etc."),
        ("Apples, pears, etc, and more.", "etc."),
        ("Clone the repo first.", "repo"),
        ("Two repos and one branch.", "repo"),
        ("The Repo is public.", "repo"),
        ("The DB is down.", "DB"),
        ("Query the db again.", "DB"),
        ("Set the key in your env first.", "env"),
        ("Edit the config and run again.", "config"),
        ("Two configs differ.", "config"),
        ("More info is on the next page.", "info"),
        ("See the docs for the full list.", "docs"),
        ("Docs: the full list.", "docs"),
        ("Read [the docs](docs/README.md) first.", "docs"),
        ("The max is 5 runs.", "max"),
        ("Max 5 runs per day.", "max"),
        ("The min is 1 run.", "min"),
        ("The class is 240 min long.", "min"),
        ("Wait 5 mins.", "min"),
        ("Time: 0.5 min (0:00-0:00:30)", "min"),
        ("It takes approx 10 seconds.", "approx"),
        ("It takes approx. 10 seconds.", "approx"),
        ("The agent vs the reviewer.", "vs"),
        ("The agent vs. the reviewer.", "vs"),
        ("Vs. the old run, it is faster.", "vs"),
    ],
)
def test_shorthand_in_prose_is_found(short_forms, text: str, word: str) -> None:
    assert [w for w, _ in short_forms.find_shorthand(text)] == [word]


def test_every_shorthand_word_gives_its_full_word(short_forms) -> None:
    advice = dict(short_forms.find_shorthand("See the docs, the repo, and the DB, e.g. today."))
    assert set(advice) == {"docs", "repo", "DB", "e.g."}
    assert "documentation" in advice["docs"]
    assert "repository" in advice["repo"]
    assert "database" in advice["DB"]
    assert "for example" in advice["e.g."]


# -- shorthand: not found -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        # inline code spans
        "Run `make docs` now.",
        "Set `max_retries` to 3.",
        "Copy `.env.example` to `.env` first.",
        "Use ``repo`` in code only.",
        # paths and file names
        "Read docs/STYLE.md first.",
        "Open docs/ in the editor.",
        "Edit platform/config/course.toml and run again.",
        "The settings live in config.toml.",
        "Copy .env.example to .env first.",
        "The file .env holds the keys.",
        "The hosts file is /etc/hosts.",
        "The cache lives in ~/.cache/repo/.",
        # identifiers and make targets
        "The setting max_retries is 3.",
        "The flag DB_URL is read at start.",
        "Run make docs-check before you commit.",
        "The env-file flag reads it.",
        "The column min_date holds it.",
        # URLs and link targets
        "See https://example.org/repo/docs for details.",
        "See <https://example.org/docs/etc> for details.",
        "Read the [style guide](docs/STYLE.md).",
        "Read the [style guide](https://example.org/docs).",
        # longer words and full words
        "The Maximum value and the minimum value.",
        "The environment, the repository, the database, and the configuration.",
        "More information and documentation, at most about 10 versus 12.",
        "Minutes, minimal, maximise, environments, configured, informed.",
        "The class takes 240 minutes.",
        "Open VS Code.",
        "The log level is INFO.",
        "Etcetera is not a word we use either, but it is not shorthand.",
        "Use MAX() and min() in the query.",
    ],
)
def test_code_paths_urls_and_full_words_are_not_shorthand(short_forms, text: str) -> None:
    assert short_forms.find_shorthand(text) == []


# -- technical terms: first use on a page ---------------------------------------------------------


def _first_use(short_forms, text: str) -> list[tuple[int, str]]:
    return [(no, term) for no, term, _ in short_forms.first_use_problems(short_forms.prose(text))]


@pytest.mark.parametrize(
    ("term", "expansion"),
    [
        ("SQL", "Structured Query Language"),
        ("API", "application programming interface"),
        ("JSON", "JavaScript Object Notation"),
        ("CSV", "comma-separated values"),
        ("LLM", "large language model"),
        ("HTTP", "Hypertext Transfer Protocol"),
        ("URL", "Uniform Resource Locator"),
        ("UTC", "Coordinated Universal Time"),
    ],
)
def test_each_term_needs_its_expansion_on_first_use(short_forms, term, expansion) -> None:
    assert _first_use(short_forms, f"The agent writes {term} for you.") == [(1, term)]
    assert _first_use(short_forms, f"The agent writes {expansion} ({term}). Then {term}.") == []
    assert _first_use(short_forms, f"The agent writes {term} ({expansion}). Then {term}.") == []


def test_the_expansion_may_come_in_either_order_and_any_case(short_forms) -> None:
    assert _first_use(short_forms, "Structured Query Language (SQL) first.\n\nThen SQL.") == []
    assert _first_use(short_forms, "SQL (Structured Query Language) first.\n\nThen SQL.") == []
    assert _first_use(short_forms, "Application programming interface (API) calls.") == []
    assert _first_use(short_forms, "An API (Application Programming Interface) call.") == []
    assert _first_use(short_forms, "**Structured Query Language** (SQL) in bold.") == []


def test_the_expansion_may_wrap_onto_the_next_line(short_forms) -> None:
    assert _first_use(short_forms, "It writes Structured Query\nLanguage (SQL) for you.") == []


def test_plurals_count_as_a_use(short_forms) -> None:
    assert _first_use(short_forms, "Two APIs are called.") == [(1, "API")]
    assert _first_use(short_forms, "Two application programming interfaces (APIs).") == []


def test_only_the_first_use_counts_and_is_reported_once(short_forms) -> None:
    text = "It writes SQL.\n\nStructured Query Language (SQL) is late.\n\nMore SQL."
    assert _first_use(short_forms, text) == [(1, "SQL")]


def test_a_later_use_needs_no_expansion(short_forms) -> None:
    text = "Structured Query Language (SQL) here.\n\nSQL again, and SQL once more."
    assert _first_use(short_forms, text) == []


def test_the_expansion_alone_is_not_the_first_use(short_forms) -> None:
    # Spelled out without the term, then the bare term: the term's first use still lacks it.
    text = "Structured Query Language is old.\n\nThe agent writes SQL."
    assert _first_use(short_forms, text) == [(3, "SQL")]


@pytest.mark.parametrize(
    "text",
    [
        "Run `SELECT 1` as `SQL`.",
        "```sql\n-- SQL in a fenced block\nSELECT 1;\n```",
        "~~~\nGET the API\n~~~",
        "<!-- SQL in a comment -->",
        "<!--\nAPI in a comment\nover two lines\n-->",
        "---\ntitle: the SQL page\n---\nNo term here.",
        "The key is OPENAI_API_KEY in the file.",
        "Open https://example.org/API/SQL for details.",
        "Read [the guide](docs/SQL.md).",
        "The file platform/api/JSON/x.py holds it.",
        "The file is report.JSON.md here.",
    ],
)
def test_code_comments_front_matter_urls_and_identifiers_are_not_a_first_use(
    short_forms, text: str
) -> None:
    assert _first_use(short_forms, text) == []


def test_the_term_counts_once_per_page(check_style, tmp_path: Path) -> None:
    page = "Structured Query Language (SQL) here, then SQL.\n"
    assert _naming(check_style, tmp_path, page, "docs/one.md") == []
    assert _naming(check_style, tmp_path, "And SQL here.\n", "docs/two.md") == [("SC33", 1)]


# -- check_style.py on a Markdown page ------------------------------------------------------------


def _naming(check_style, root: Path, text: str, rel: str = "docs/naming-page.md"):
    problems = check_style.check_text(rel, text, root)
    return [(p.check, p.line) for p in problems if p.check in ("SC32", "SC33")]


def test_the_page_check_reports_shorthand_and_first_use(check_style, tmp_path: Path) -> None:
    page = "# Title\n\nClone the repo, e.g. with git.\n\nThe agent writes SQL.\n"
    assert _naming(check_style, tmp_path, page) == [("SC32", 3), ("SC32", 3), ("SC33", 5)]


def test_the_page_check_skips_fences_code_comments_and_front_matter(check_style, tmp_path) -> None:
    page = (
        "---\n"
        "name: repo-tool\n"
        "description: the repo docs, e.g. SQL\n"
        "---\n"
        "# Title\n"
        "\n"
        "Run `make docs` and set `max_retries`.\n"
        "<!-- check-style: allow SC08 the repo output, e.g. SQL -->\n"
        "<!-- guide: the docs, the repo, and the API -->\n"
        "\n"
        "```bash\n"
        "cp .env.example .env  # the repo env, e.g. SQL\n"
        "```\n"
        "\n"
        "Read docs/STYLE.md and the [style guide](docs/STYLE.md), then the Maximum.\n"
    )
    assert _naming(check_style, tmp_path, page) == []


def test_a_multi_line_code_span_is_not_prose(check_style, tmp_path: Path) -> None:
    page = "# Title\n\nRun `make\ndocs` now.\n"
    assert _naming(check_style, tmp_path, page) == []


def test_the_new_rules_are_warnings(check_style) -> None:
    assert check_style.CHECKS["SC32"][1] == check_style.WARNING
    assert check_style.CHECKS["SC33"][1] == check_style.WARNING
    # The short forms stay errors: the new rules weaken nothing.
    assert check_style.CHECKS["SC31"][1] == check_style.ERROR


def test_an_allow_marker_skips_the_line(check_style, tmp_path: Path) -> None:
    page = "# Title\n\nThe repo, quoted. <!-- check-style: allow SC32 a quoted console label -->\n"
    assert _naming(check_style, tmp_path, page) == []


def _main(check_style, root: Path, text: str, *flags: str) -> tuple[int, str]:
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "page.md").write_text(text, encoding="utf-8")
    out = io.StringIO()
    old, sys.stdout = sys.stdout, out
    try:
        code = check_style.main(["--root", str(root), "--names-only", *flags, "docs/page.md"])
    finally:
        sys.stdout = old
    return code, out.getvalue()


def test_warnings_by_default_errors_under_strict(check_style, tmp_path: Path) -> None:
    page = "# Title\n\nClone the repo.\n\nThe agent writes SQL.\n"
    code, out = _main(check_style, tmp_path, page)
    assert code == 0
    assert "! docs/page.md:3: Shorthand in prose: 'repo': write 'repository'" in out
    assert "! docs/page.md:5: Term not spelled out on first use: 'SQL': write " in out
    assert "Structured Query Language (SQL)" in out
    code, _ = _main(check_style, tmp_path, page, "--strict")
    assert code == 1


def test_the_message_shown_holds_no_check_code(check_style, tmp_path: Path) -> None:
    _, out = _main(check_style, tmp_path, "# Title\n\nClone the repo. Track MRR.\n")
    lines = [line for line in out.splitlines() if line.startswith(("x ", "! "))]
    assert len(lines) == 2
    assert not any("SC3" in line for line in lines)
    assert any(line.startswith("x ") and "Short form in prose" in line for line in lines)


def test_names_only_reports_only_the_naming_checks(check_style, tmp_path: Path) -> None:
    # A leftover marker (an error of another check) is not part of the naming check.
    code, out = _main(check_style, tmp_path, "# Title\n\nFIXME: the repo.\n")
    assert code == 0
    lines = [line for line in out.splitlines() if line.startswith(("x ", "! "))]
    assert lines == [
        "! docs/page.md:3: Shorthand in prose: 'repo': write 'repository' (plural 'repositories')"
    ]


def test_the_template_headings_hold_no_shorthand(check_style, short_forms) -> None:
    for kind, headings in check_style.TEMPLATES.items():
        for heading in headings:
            assert short_forms.find_shorthand(heading) == [], (kind, heading)


# -- short_forms.py on other text -----------------------------------------------------------------


def _cli(short_forms, text: str, *flags: str, monkeypatch, capsys) -> tuple[int, str]:
    monkeypatch.setattr(sys, "stdin", io.StringIO(text))
    code = short_forms.main([*flags, "-"])
    return code, capsys.readouterr().out


def test_commit_messages_fail_on_shorthand(short_forms, monkeypatch, capsys) -> None:
    code, out = _cli(
        short_forms, "fix: the repo guard\n", "--commit-messages", monkeypatch=monkeypatch,
        capsys=capsys,
    )  # fmt: skip
    assert code == 1
    assert "shorthand 'repo': write 'repository'" in out


def test_commit_messages_skip_the_type_prefix_and_the_first_use_rule(
    short_forms, monkeypatch, capsys
) -> None:
    text = "docs(research): the SQL notes\n\nbuild(config): the API settings\n"
    code, out = _cli(short_forms, text, "--commit-messages", monkeypatch=monkeypatch, capsys=capsys)
    assert code == 0, out


def test_commit_messages_still_fail_on_short_forms(short_forms, monkeypatch, capsys) -> None:
    code, _ = _cli(
        short_forms, "feat: FY2025 revenue\n", "--commit-messages", monkeypatch=monkeypatch,
        capsys=capsys,
    )  # fmt: skip
    assert code == 1


def test_commit_messages_skip_comment_lines_fences_and_code(short_forms) -> None:
    text = "feat: the reviewer\n# the repo in a comment line\n```\nthe repo\n```\nSet `max`.\n"
    assert short_forms.check_shorthand(text, markdown=False, commit_messages=True) == []


def test_other_text_warns_by_default_and_fails_under_strict(
    short_forms, monkeypatch, capsys
) -> None:
    text = "# Outline\n\nSource in the repo. The agent writes SQL.\n"
    code, out = _cli(short_forms, text, monkeypatch=monkeypatch, capsys=capsys)
    assert code == 0
    assert "warning: stdin:3: shorthand 'repo'" in out
    assert "warning: stdin:3: first use of 'SQL'" in out
    code, _ = _cli(short_forms, text, "--strict", monkeypatch=monkeypatch, capsys=capsys)
    assert code == 1


def test_a_markdown_file_skips_code_comments_and_links(short_forms, tmp_path: Path, capsys) -> None:
    outline = tmp_path / "outline.md"
    outline.write_text(
        "# Outline\n\n<!-- the repo -->\n\n```text\nthe repo, SQL\n```\n\n"
        "Read [the guide](docs/STYLE.md) and run `make docs`.\n",
        encoding="utf-8",
    )
    assert short_forms.main(["--strict", str(outline)]) == 0, capsys.readouterr().out


def test_a_markdown_heading_is_prose(short_forms, tmp_path: Path, capsys) -> None:
    outline = tmp_path / "outline.md"
    outline.write_text("# Outline\n\n## Source in the repo\n", encoding="utf-8")
    assert short_forms.main(["--strict", str(outline)]) == 1
    assert "outline.md:3: shorthand 'repo'" in capsys.readouterr().out


def test_find_keeps_to_the_short_forms(short_forms) -> None:
    # find() is the short-forms list only (the benchmark and registry tests use it).
    assert short_forms.find("Clone the repo, e.g. now.") == []
    assert short_forms.find("Track MRR.")
