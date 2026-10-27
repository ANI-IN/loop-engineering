"""Markdown lint for every Markdown file the release ships: pymarkdown (pymarkdownlnt, pinned in the
dev group of pyproject.toml) with the repository's configuration, .pymarkdown.yaml.

Usage:
    uv run python platform/scripts/lint_markdown.py            # every shipped Markdown file
    uv run python platform/scripts/lint_markdown.py PATH ...   # these files only

The files are the ones platform/scripts/check_links.py lists (platform/config/release.toml decides
what ships), so a file the release leaves out is never read, and a run on the private repository
lints what a run on the public copy lints. pymarkdown runs in the repository root, where it reads
.pymarkdown.yaml by its standard name; --strict-config makes a mistake in that file an error.

A rule one file breaks by design is turned off for that file alone, in PER_FILE_ALLOW, with the
reason; every other file keeps it. platform/tests/unit/test_lint_markdown.py fails when an entry
no longer matches a file, or its rule no longer fires there, so the list never outlives its reason.

Output: pymarkdown's own lines, `<path>:<line>:<column>: <rule id>: <message>`, then a count.
Exit code: 1 when there is a problem, 2 when the configuration file is missing, else 0.
"""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_links  # noqa: E402

CONFIG_NAME = ".pymarkdown.yaml"

# A shipped file (a glob) and the rules it may break, each with its reason.
PER_FILE_ALLOW: dict[str, dict[str, str]] = {
    "slides/outline.md": {
        "md024": "the outline names each part of the agenda, and the class has two parts "
        "named Break",
        "md032": "a slide's lines follow the deck builder's line grammar "
        "(slides/design-system.md): a bullet comes straight after its Lead: or Body line",
        "md034": "a demo slide's 'Link: <label> | <address>' line and the sources list hold plain "
        "addresses the deck builder reads",
    },
    "guide/chapters/*.md": {
        "md001": "a chapter's steps are '### Step N:' headings straight under its title, as the "
        "style check (SC28) and the guide's PDF builder read them",
    },
}


def allowed_rules(rel: str) -> list[str]:
    """The rules turned off for one file (POSIX path relative to the repository root)."""
    rules: set[str] = set()
    for pattern, entries in PER_FILE_ALLOW.items():
        if fnmatch.fnmatchcase(rel, pattern):
            rules.update(entries)
    return sorted(rules)


def command(files: list[str], disabled: list[str] | None = None) -> list[str]:
    """The pymarkdown command line for `files` (paths relative to the repository root)."""
    off = ["--disable-rules", ",".join(disabled)] if disabled else []
    return [sys.executable, "-m", "pymarkdown", "--strict-config", *off, "scan", *files]


def groups(files: list[str]) -> dict[tuple[str, ...], list[str]]:
    """The files grouped by the rules turned off for them, so each group is one pymarkdown run."""
    found: dict[tuple[str, ...], list[str]] = {}
    for rel in files:
        found.setdefault(tuple(allowed_rules(rel)), []).append(rel)
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("paths", nargs="*", help="files (default: every shipped Markdown file)")
    parser.add_argument("--root", type=Path, default=check_links.REPO, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not (root / CONFIG_NAME).is_file():
        print(f"x {CONFIG_NAME} is missing in {root}")
        return 2
    files = [Path(p).as_posix() for p in args.paths] or check_links.shipped_markdown(root)
    failed = False
    for disabled, members in sorted(groups(files).items()):
        done = subprocess.run(command(members, list(disabled)), cwd=root, check=False)
        failed = failed or done.returncode != 0
    print(f"{len(files)} Markdown files linted, {'problems found' if failed else 'no problems'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
