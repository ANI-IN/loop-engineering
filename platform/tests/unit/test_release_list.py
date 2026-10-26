"""The release list covers every top-level folder; the checkers scan every public page folder; every
shipped Markdown file is a course page or holds the naming rule as other shipped Markdown."""

from __future__ import annotations

import fnmatch
import importlib.util
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
RELEASE = tomllib.loads((REPO / "platform/config/release.toml").read_text(encoding="utf-8"))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "platform/scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _listed(name: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(name + "/", p) or fnmatch.fnmatch(name, p) for p in patterns)


def _ignored_by_gitignore(root: Path, name: str) -> bool:
    """A top-level folder the root .gitignore names (`name/`, `/name/`, or a pattern such as
    `*.egg-info/`); read only when git cannot list the checkout."""
    ignore = root / ".gitignore"
    if not ignore.is_file():
        return False
    for raw in ignore.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "!")):
            continue
        pattern = line.strip("/")
        if "/" not in pattern and fnmatch.fnmatch(name, pattern):
            return True
    return False


def _top_level_folders(root: Path) -> list[str]:
    """The top-level folders that hold a file git tracks or would track: folders git ignores
    (`.vscode/`, `test-results/`, `node_modules/`, an environment, a cache) can never ship, so a
    learner's tools may create them freely. Git lists them; where git cannot read the checkout
    (an agent worktree under WSL, whose .git file names a Windows path), the root .gitignore
    decides."""
    done = None
    if shutil.which("git") and (root / ".git").exists():
        done = subprocess.run(
            ["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=root, capture_output=True
        )
    if done is not None and done.returncode == 0:
        paths = [p for p in done.stdout.decode("utf-8").split("\0") if "/" in p]
        return sorted({p.split("/", 1)[0] for p in paths})
    return sorted(
        p.name
        for p in root.iterdir()
        if p.is_dir() and p.name != ".git" and not _ignored_by_gitignore(root, p.name)
    )


@pytest.mark.parametrize("with_git", [True, False])
def test_a_folder_git_ignores_is_not_a_top_level_folder(tmp_path: Path, with_git: bool) -> None:
    (tmp_path / ".gitignore").write_text(
        ".vscode/\n/test-results/\nnode_modules/\n*.egg-info/\n", encoding="utf-8"
    )
    for folder in ["docs", "new-folder", ".vscode", "test-results", "node_modules", "x.egg-info"]:
        (tmp_path / folder).mkdir()
        (tmp_path / folder / "file.txt").write_text("text\n", encoding="utf-8")
    if with_git and shutil.which("git"):
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(["git", "add", "docs"], cwd=tmp_path, check=True)
    assert _top_level_folders(tmp_path) == ["docs", "new-folder"]


def test_every_top_level_folder_is_included_or_excluded() -> None:
    unknown = [
        name
        for name in _top_level_folders(REPO)
        if not _listed(name, RELEASE["include"] + RELEASE["exclude"])
    ]
    assert unknown == [], "add each to `include` or `exclude` in platform/config/release.toml"


def test_the_checkers_scan_every_public_page_folder() -> None:
    check_style = _load("check_style")
    lint_prose = _load("lint_prose")
    for folder in RELEASE["pages"]:
        if folder == "section-*":
            continue  # both tools find the section folders by name
        assert folder in check_style._DEFAULT_DIRS, folder
        assert folder in lint_prose.DEFAULT_TARGETS, folder
        assert _listed(folder, RELEASE["include"]), folder


def _ships(rel: str) -> bool:
    """The release build's rule for one working-tree path: included, not excluded, not internal."""
    if rel.rsplit("/", 1)[-1] in RELEASE["internal_files"] or rel in RELEASE["build_only"]:
        return False
    if any(fnmatch.fnmatchcase(rel, e + "*") or rel.startswith(e) for e in RELEASE["exclude"]):
        return False
    return any(
        fnmatch.fnmatchcase(rel, e + "*") if e.endswith("/") else rel == e
        for e in RELEASE["include"]
    )


def _shipped_markdown() -> list[str]:
    from conftest import SKIPPED_DIRS

    found = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in SKIPPED_DIRS]
        for name in files:
            rel = (Path(root) / name).relative_to(REPO).as_posix()
            if name.endswith(".md") and _ships(rel):
                found.append(rel)
    return sorted(found)


def test_every_shipped_markdown_file_is_read_by_a_checker() -> None:
    check_style = _load("check_style")
    pages = {p.relative_to(REPO).as_posix() for p in check_style.default_files(REPO)}
    shipped = _shipped_markdown()
    assert "README.md" in shipped and "SECURITY.md" in shipped
    unread = [
        rel
        for rel in shipped
        if rel not in pages
        and rel not in check_style._NOT_PUBLIC
        and not any(fnmatch.fnmatchcase(rel, p) for p in RELEASE["other_markdown"])
    ]
    assert unread == [], "add each to a page folder or to other_markdown in release.toml"


def test_shipped_markdown_that_is_not_a_page_holds_the_naming_rule() -> None:
    short_forms = _load("short_forms")
    others = [
        rel
        for rel in _shipped_markdown()
        if any(fnmatch.fnmatchcase(rel, p) for p in RELEASE["other_markdown"])
    ]
    assert "SECURITY.md" in others and "platform/console/DESIGN.md" in others
    problems = []
    for rel in others:
        text = (REPO / rel).read_text(encoding="utf-8")
        for number, form, _advice in short_forms.check_short_forms(text, markdown=True):
            problems.append(f"{rel}:{number}: short form {form}")
        for number, word, _advice in short_forms.check_shorthand(text, markdown=True):
            problems.append(f"{rel}:{number}: shorthand {word}")
    assert problems == []


def _shipped_files() -> list[str]:
    from conftest import SKIPPED_DIRS

    found = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in SKIPPED_DIRS]
        for name in files:
            rel = (Path(root) / name).relative_to(REPO).as_posix()
            if _ships(rel):
                found.append(rel)
    return sorted(found)


def _excluded_inside_shipped_folders() -> list[str]:
    """What the release leaves out of a folder that ships (the deck's build files in slides/, the
    guide kit's template): a shipped file that names one points a learner at nothing. The
    solutions are left out too, but only until the Thursday review, so pages name them; so are
    the files withheld until they are written (`withheld_until_later`: the session notes, written
    after the class run), which the instructor guide and the style guide name, but no page links."""
    folders = [e for e in RELEASE["include"] if e.endswith("/")]
    later = [RELEASE["solutions"], *RELEASE.get("withheld_until_later", [])]
    return [
        e
        for e in RELEASE["exclude"]
        if e not in later and any(fnmatch.fnmatchcase(e, f + "?*") for f in folders)
    ]


def test_no_shipped_file_names_a_file_the_release_leaves_out() -> None:
    excluded = _excluded_inside_shipped_folders()
    assert any(e.startswith("slides/") for e in excluded), "the deck's build files are listed"
    # A folder is named by its path; a file also by its name alone, as a page beside it writes it.
    needles = [e if e.endswith("/") else e.rsplit("/", 1)[-1] for e in excluded]
    problems = []
    for rel in _shipped_files():
        if rel == "platform/config/release.toml":
            continue  # the release list itself names what it leaves out
        try:
            text = (REPO / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            problems += [f"{rel}:{number}: names {n}" for n in needles if n in line]
    assert problems == [], "the release does not ship what these lines name:\n" + "\n".join(
        problems
    )


_LINK_TARGET = re.compile(r"\]\(([^)\s#]+)")


def test_no_shipped_page_links_to_a_file_withheld_until_later() -> None:
    """A file the release withholds until it is written (the session notes) is excluded, and no
    shipped Markdown links to it: the link would point a learner at nothing until it ships."""
    later = RELEASE.get("withheld_until_later", [])
    assert "section-*/session-notes.md" in later
    assert all(entry in RELEASE["exclude"] for entry in later), "each one is excluded too"
    problems = []
    for rel in _shipped_markdown():
        text = (REPO / rel).read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), 1):
            for target in _LINK_TARGET.findall(line):
                if "://" in target:
                    continue
                path = posixpath.normpath(posixpath.join(posixpath.dirname(rel), target))
                if any(fnmatch.fnmatchcase(path, pattern) for pattern in later):
                    problems.append(f"{rel}:{number}: links {path}")
    assert problems == []


def _shipped_texts() -> dict[str, str]:
    """The text of every file the release would ship from the working tree, less the tests the
    release drops because they name a file it leaves out (as platform/scripts/build_release.py
    does), so a dropped test's fixtures are not read."""
    from conftest import SKIPPED_DIRS

    texts, left_out = {}, []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in SKIPPED_DIRS]
        for name in files:
            rel = (Path(root) / name).relative_to(REPO).as_posix()
            if not _ships(rel):
                left_out.append(rel)
                continue
            try:
                texts[rel] = (REPO / rel).read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
    make_release = _load("build_release").make_release
    tests = {p: t for p, t in texts.items() if make_release._is_test(p)}
    dropped = make_release.find_excluded_tests(tests, left_out)
    return {p: t for p, t in texts.items() if p not in dropped}


def test_no_shipped_file_holds_placeholder_text() -> None:
    """The release build's placeholder check (platform/scripts/build_release.py) on the working
    tree's shipped files, with the release list's allow entries: what a release would refuse."""
    build_release = _load("build_release")
    allow = RELEASE.get("placeholder_allow", [])
    problems = build_release.placeholder_problems(_shipped_texts(), allow)
    assert problems == [], "write the content, or withhold the page:\n" + "\n".join(problems)


def test_every_placeholder_allow_entry_is_still_needed() -> None:
    """Each allow entry names a reason and rules the check knows, and each of its rules still
    allows a finding in a shipped file: an entry that no longer matches anything goes."""
    build_release = _load("build_release")
    known = {name for name, _, _ in build_release.PLACEHOLDER_RULES} | {build_release.EMPTY_HEADING}
    texts = _shipped_texts()
    findings = {
        (path, rule)
        for path, text in texts.items()
        for _, rule in build_release.placeholder_findings(path, text)
    }
    stale = []
    for entry in RELEASE.get("placeholder_allow", []):
        assert entry.get("why"), entry
        for rule in entry["rules"]:
            assert rule in known, rule
            if not any(r == rule and fnmatch.fnmatchcase(p, entry["path"]) for p, r in findings):
                stale.append(f"{entry['path']}: {rule}")
    assert stale == [], "remove these from placeholder_allow in release.toml:\n" + "\n".join(stale)
