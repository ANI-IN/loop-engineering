"""Build a public course repository from an allow-list of a private build repository.

    uv run python tools/release/make_release.py --config release.json            # dry run
    uv run python tools/release/make_release.py --config release.json --build DIR

A reference implementation of the private-to-public release pattern, small on purpose:

1. Only files tracked at `--ref` (default HEAD) are read, straight from git objects, so the
   working tree and untracked files never reach the public tree.
2. A file is public when it matches the allow-list (`allow`, glob patterns where `**` spans
   folders) and is not under a private folder (`private_dirs`) or in `private_files`.
3. Excluded-test detector: a public test whose code (not its docstring or comments) names an
   excluded file would fail in the public tree, so it is dropped and listed.
4. Leak check: no private path in the public list, and no public file holding key-like text,
   a host path, or a `deny` word. The report names the file and the kind, never the text.
5. One commit by the configured author in a fresh repository, then the configured tags on it.
6. Verification: the `verify` command (for example `uv run pytest -q`) runs in the public tree.

The dry run builds in a temporary folder and deletes it; `--build DIR` keeps it for the owner to
inspect and push. Nothing is ever pushed.

Config (JSON): {"allow": ["README.md", "src/**", "tests/**"], "private_dirs": ["research/",
"grader/"], "private_files": [], "deny": ["<internal name>"], "author_name": "<AUTHOR>",
"author_email": "<AUTHOR>@users.noreply.github.com", "commit_message": "<COURSE> release",
"tags": ["release-v1"], "verify": ["uv", "run", "pytest", "-q"]}
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

KEY_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"(?<![A-Za-z0-9])lsv2_[A-Za-z0-9_]{10,}"),
    re.compile(r"(?<![A-Za-z0-9])gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"(?<![A-Za-z0-9])AKIA[0-9A-Z]{16}(?![0-9A-Z])"),
    re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"),
)
HOST_PATHS = (
    re.compile(r"/home/[A-Za-z0-9._-]+/"),
    re.compile(r"/mnt/[a-z]/Users/[^/\s]+", re.IGNORECASE),
    re.compile(r"\b[A-Za-z]:\\Users\\[^\\\s]+", re.IGNORECASE),
)


@dataclass(frozen=True)
class Config:
    allow: list[str]
    private_dirs: list[str] = field(default_factory=list)
    private_files: list[str] = field(default_factory=list)
    deny: list[str] = field(default_factory=list)
    author_name: str = "<AUTHOR>"
    author_email: str = "author@example.com"
    commit_message: str = "Course release"
    tags: list[str] = field(default_factory=list)
    verify: list[str] = field(default_factory=list)
    # Regular expressions for host-path matches that are documented examples (a placeholder name,
    # a fake test user), not a real machine's path; any other host path is still a problem.
    host_path_examples: list[str] = field(default_factory=list)
    # Lines appended to the public tree's .gitignore before the commit.
    gitignore_extra: list[str] = field(default_factory=list)


def load_config(path: Path) -> Config:
    return Config(**json.loads(Path(path).read_text(encoding="utf-8")))


def _glob(path: str, pattern: str) -> bool:
    if pattern.endswith("/**"):
        # everything under the folder; the folder part may itself hold a wildcard (section-*/**)
        return fnmatch.fnmatchcase(path, pattern[:-3] + "/*")
    return fnmatch.fnmatchcase(path, pattern)


def private(path: str, cfg: Config) -> bool:
    return path in cfg.private_files or any(
        path.startswith(d) or f"/{d}" in f"/{path}" for d in cfg.private_dirs
    )


def select(paths: Iterable[str], cfg: Config) -> tuple[list[str], dict[str, str]]:
    """(public paths, {excluded path: reason}) where reason is "private" or "not allowed"."""
    included, excluded = [], {}
    for path in sorted(paths):
        if private(path, cfg):
            excluded[path] = "private"
        elif any(_glob(path, p) for p in cfg.allow):
            included.append(path)
        else:
            excluded[path] = "not allowed"
    return included, excluded


def leaks(paths: Iterable[str], cfg: Config) -> list[str]:
    return [p for p in paths if private(p, cfg)]


def _docstring_nodes(tree: ast.AST) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                ids.add(id(body[0].value))
    return ids


def find_excluded_tests(
    sources: Mapping[str, str], excluded: Iterable[str]
) -> dict[str, list[str]]:
    """Test files whose code names an excluded file: a string constant that is, or ends with,
    an excluded path. Docstrings and comments do not count."""
    excluded = sorted(set(excluded))
    found: dict[str, list[str]] = {}
    for path, text in sorted(sources.items()):
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        docs = _docstring_nodes(tree)
        reasons = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in docs
            ):
                for token in re.findall(r"[\w.\-/]+", node.value):
                    for ex in excluded:
                        if token == ex or token.endswith("/" + ex):
                            reasons.append(f"line {node.lineno}: names {ex}")
        if reasons:
            found[path] = sorted(set(reasons))
    return found


def _real_host_path(text: str, examples: Iterable[str]) -> bool:
    allowed = [re.compile(e) for e in examples]
    return any(
        not any(a.search(m.group(0)) for a in allowed) for p in HOST_PATHS for m in p.finditer(text)
    )


def content_problems(files: Mapping[str, str], cfg: Config) -> list[str]:
    """Key-like text, host paths, and deny words in public files; the text is never shown."""
    out = []
    for path, text in sorted(files.items()):
        if any(p.search(text) for p in KEY_PATTERNS):
            out.append(f"{path}: key-like text")
        if _real_host_path(text, cfg.host_path_examples):
            out.append(f"{path}: host path")
        for word in cfg.deny:
            if word and word.casefold() in text.casefold():
                out.append(f"{path}: deny word #{cfg.deny.index(word) + 1}")
    return out


def _git(repo: Path, *args: str, env: Mapping[str, str] | None = None) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, env=env
    ).stdout


def tracked(repo: Path, ref: str) -> list[str]:
    out = _git(repo, "ls-tree", "-r", "-z", "--name-only", ref)
    return [p for p in out.decode().split("\0") if p]


def blob(repo: Path, ref: str, path: str) -> bytes:
    return _git(repo, "show", f"{ref}:{path}")


def _is_test(path: str) -> bool:
    base = posixpath.basename(path)
    return path.endswith(".py") and (base.startswith("test_") or base == "conftest.py")


@dataclass
class Result:
    public: list[str] = field(default_factory=list)
    dropped_tests: dict[str, list[str]] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)
    verify_rc: int | None = None

    @property
    def ok(self) -> bool:
        return not self.problems and self.verify_rc in (0, None)


def release(repo: Path, cfg: Config, dest: Path, ref: str = "HEAD") -> Result:
    res = Result()
    paths = tracked(repo, ref)
    included, excluded = select(paths, cfg)
    res.problems += [f"{p}: private path in the public list" for p in leaks(included, cfg)]
    blobs = {p: blob(repo, ref, p) for p in included}
    texts = {}
    for p, data in blobs.items():
        try:
            texts[p] = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
    tests = {p: t for p, t in texts.items() if _is_test(p)}
    res.dropped_tests = find_excluded_tests(tests, excluded)
    res.public = [p for p in included if p not in res.dropped_tests]
    res.problems += content_problems({p: texts[p] for p in res.public if p in texts}, cfg)
    if res.problems:
        return res
    if dest.exists() and any(dest.iterdir()):
        raise ValueError(f"{dest} is not empty")
    write_tree(dest, {p: blobs[p] for p in res.public}, cfg)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": cfg.author_name,
        "GIT_AUTHOR_EMAIL": cfg.author_email,
        "GIT_COMMITTER_NAME": cfg.author_name,
        "GIT_COMMITTER_EMAIL": cfg.author_email,
    }
    _git(dest, "init", "-q", "-b", "main")
    _git(dest, "add", "-A")
    _git(dest, "-c", "commit.gpgsign=false", "commit", "-q", "-m", cfg.commit_message, env=env)
    for tag in cfg.tags:
        _git(dest, "-c", "tag.gpgsign=false", "tag", "-a", tag, "-m", tag, env=env)
    if cfg.verify:
        res.verify_rc = subprocess.run(cfg.verify, cwd=dest).returncode
        if res.verify_rc:
            res.problems.append(f"verify failed in the public tree (exit {res.verify_rc})")
    return res


def write_tree(dest: Path, files: Mapping[str, bytes], cfg: Config) -> None:
    """Write the public files into `dest`, then append `gitignore_extra` to its .gitignore."""
    for p, data in files.items():
        target = dest / p
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    if cfg.gitignore_extra:
        ignore = dest / ".gitignore"
        text = ignore.read_text(encoding="utf-8") if ignore.exists() else ""
        lines = "\n".join(cfg.gitignore_extra)
        sep = "" if not text or text.endswith("\n") else "\n"
        ignore.write_text(f"{text}{sep}{lines}\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--build", type=Path, default=None, help="keep the built tree here")
    a = ap.parse_args(argv)
    cfg = load_config(a.config)
    dest = a.build or Path(tempfile.mkdtemp(prefix="release-"))
    try:
        res = release(a.repo, cfg, dest, a.ref)
    finally:
        if a.build is None:
            shutil.rmtree(dest, ignore_errors=True)
    print(f"public files: {len(res.public)}")
    for path, why in res.dropped_tests.items():
        print(f"! test dropped (names an excluded file): {path} ({why[0]})")
    for line in res.problems:
        print(f"x {line}")
    if res.ok:
        print("dry run passed" if a.build is None else f"built {dest} (not pushed)")
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
