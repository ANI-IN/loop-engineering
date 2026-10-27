"""Link check for every Markdown file the release ships: each relative link and anchor resolves.

Usage:
    uv run python platform/scripts/check_links.py           # every shipped Markdown file
    uv run python platform/scripts/check_links.py --list    # print the files it reads, and exit

The files are the Markdown files platform/config/release.toml ships (`include` less `exclude`,
the internal files, and the build-only files), so a file the release leaves out is never read and
a run on the private repository checks what a run on the public copy checks. Each relative link,
reference definition and HTML href must name a file or folder that exists, and its `#anchor` a
heading or HTML id of the Markdown file it names (GitHub's slug rule), by the style checker's
own functions (`check_style.link_problems`). Two more rules:

- a relative link may not name a file the release leaves out: it would resolve here and point at
  nothing in the public copy;
- a link to the course's own GitHub repository (`<repository>/tree/main/<path>` or
  `<repository>/blob/main/<path>`, the address in slides/source/build.py), such as the demo links
  of slides/outline.md, must name a shipped file or folder, and its anchor a heading of that file,
  or of the folder's README.md.

The files an agent reads (a demo's files, the kit templates; `check_style.gets_link_check`) point
into the repository the agent or the learner works in, not this one: they are listed as skipped.

Output: one line per problem, `x <path>:<line>: <message>`, then `<files> files checked,
<problems> problems, <skipped> skipped`. Exit code: 1 when there is a problem, else 0.
"""

from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from urllib.parse import unquote

REPO = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_style  # noqa: E402

RELEASE_FILE = Path("platform") / "config" / "release.toml"
DECK_BUILDER = REPO / "slides" / "source" / "build.py"
# Folders a walk never enters: git data, environments, caches, build output.
SKIPPED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".import_linter_cache",
    "node_modules",
    "build",
    "dist",
    "test-results",
    "playwright-report",
}


def release_list(root: Path) -> dict:
    """The release list of the tree at `root`."""
    return tomllib.loads((root / RELEASE_FILE).read_text(encoding="utf-8"))


def ships(rel: str, release: dict) -> bool:
    """The release build's rule for one path (a folder ends with "/"): included, not excluded, not
    an internal or build-only file."""
    if rel.rstrip("/").rsplit("/", 1)[-1] in release["internal_files"]:
        return False
    if rel in release.get("build_only", []):
        return False
    if any(fnmatch.fnmatchcase(rel, e + "*") or rel.startswith(e) for e in release["exclude"]):
        return False
    return any(
        fnmatch.fnmatchcase(rel, e + "*") if e.endswith("/") else rel == e
        for e in release["include"]
    )


def _tree(root: Path) -> list[str]:
    """Every file git tracks or would track under `root` (git's own list, so ignored output is left
    out); where git cannot read the tree, every file outside the skipped folders."""
    if (root / ".git").exists():
        done = subprocess.run(
            ["git", "ls-files", "-co", "--exclude-standard", "-z"],
            cwd=root,
            capture_output=True,
            check=False,
        )
        if done.returncode == 0:
            return sorted(p for p in done.stdout.decode("utf-8").split("\0") if p)
    found = []
    for top, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIPPED_DIRS]
        found += [(Path(top) / f).relative_to(root).as_posix() for f in files]
    return sorted(found)


def shipped_markdown(root: Path) -> list[str]:
    """The Markdown files the release ships from `root`, as POSIX paths relative to it."""
    release = release_list(root)
    return [
        rel
        for rel in _tree(root)
        if rel.endswith(".md") and ships(rel, release) and (root / rel).is_file()
    ]


def repository_address() -> str:
    """The course's GitHub address, as the deck builder names it."""
    spec = importlib.util.spec_from_file_location("deck_build_for_links", DECK_BUILDER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return str(module.GITHUB).rstrip("/")


def _repository_link(address: str) -> re.Pattern[str]:
    return re.compile(
        re.escape(address)
        + r"/(?:tree|blob)/main/(?P<path>[^\s)>#\"'`|]*)(?:#(?P<anchor>[^\s)>\"'`|]*))?"
    )


def _key(root: Path, file: Path) -> str | None:
    try:
        return file.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def _left_out(root: Path, rel: str, page: check_style.Page, release: dict) -> list[tuple[int, str]]:
    """Relative links from `rel` to a file or folder that exists here but does not ship."""
    out = []
    here = (root / rel).parent
    for no, target in check_style._link_targets(page):
        target = target.strip("<>").strip()
        if not target or check_style._SCHEME.match(target):
            continue
        path = unquote(target.partition("#")[0])
        if not path:
            continue
        file = root / path.lstrip("/") if path.startswith("/") else here / path
        key = _key(root, file)
        if key is None or not file.exists() or key in check_style._GENERATED:
            continue
        if not ships(key + "/" if file.is_dir() else key, release):
            out.append((no, f"link target {target}: the release leaves out {key}"))
    return out


def _anchor_file(file: Path) -> Path | None:
    if file.is_file() and file.suffix.lower() == ".md":
        return file
    if file.is_dir() and (file / "README.md").is_file():
        return file / "README.md"
    return None


def _repository_links(
    root: Path,
    page: check_style.Page,
    release: dict,
    pattern: re.Pattern[str],
    cache: dict[Path, set[str]],
) -> list[tuple[int, str]]:
    """Links to the course's GitHub repository whose path or anchor is not in this tree."""
    out = []
    for ln in page.lines:
        if ln.kind != "prose":
            continue
        for match in pattern.finditer(ln.prose):
            path = unquote(match.group("path")).rstrip("/")
            anchor = match.group("anchor")
            shown = match.group(0)
            file = root / path
            key = _key(root, file)
            if key is None or not file.exists():
                out.append((ln.no, f"repository link {shown}: {path or '/'} does not exist"))
                continue
            if path and not ships(key + "/" if file.is_dir() else key, release):
                out.append((ln.no, f"repository link {shown}: the release leaves out {key}"))
                continue
            if anchor:
                page_file = _anchor_file(file)
                if page_file is None:
                    out.append((ln.no, f"repository link {shown}: {path} has no headings"))
                    continue
                resolved = page_file.resolve()
                if resolved not in cache:
                    cache[resolved] = check_style.anchors(page_file.read_text(encoding="utf-8"))
                if unquote(anchor) not in cache[resolved]:
                    out.append(
                        (
                            ln.no,
                            f"repository link {shown}: no heading or id '{anchor}' in "
                            f"{_key(root, page_file)}",
                        )
                    )
    return out


def file_problems(
    root: Path,
    rel: str,
    release: dict,
    pattern: re.Pattern[str],
    cache: dict[Path, set[str]],
) -> list[tuple[int, str]]:
    """(line, message) for each link in `rel` that does not resolve in the tree at `root`."""
    page = check_style.parse_page((root / rel).read_text(encoding="utf-8"))
    found = check_style.link_problems(page, root, rel, cache)
    found += _left_out(root, rel, page, release)
    found += _repository_links(root, page, release, pattern, cache)
    return sorted(set(found))


def run(root: Path) -> tuple[list[str], list[str], list[str]]:
    """The files checked, the files skipped, and one `path:line: message` line per problem."""
    release = release_list(root)
    pattern = _repository_link(repository_address())
    cache: dict[Path, set[str]] = {}
    checked, skipped, problems = [], [], []
    for rel in shipped_markdown(root):
        if not check_style.gets_link_check(rel):
            skipped.append(rel)
            continue
        checked.append(rel)
        for no, message in file_problems(root, rel, release, pattern, cache):
            problems.append(f"{rel}:{no}: {message}")
    return checked, skipped, problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--list", action="store_true", help="print the shipped Markdown files")
    parser.add_argument("--root", type=Path, default=REPO, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.list:
        print("\n".join(shipped_markdown(root)))
        return 0
    checked, skipped, problems = run(root)
    for rel in skipped:
        print(f"- {rel}: skipped (an agent file; its links point into another repository)")
    for line in problems:
        print(f"x {line}")
    print(f"{len(checked)} files checked, {len(problems)} problems, {len(skipped)} skipped")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
