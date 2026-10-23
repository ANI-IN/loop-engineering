"""Scan a git repository for keys and host paths: the tracked tree and the full history.

    uv run python tools/scan/scan_secrets.py [--repo .] [--paths]

Key patterns use word boundaries (`sk-` inside `task-...` is not a key). Host paths are user
home folders on Linux, macOS, WSL, and Windows. The output is booleans per check plus, for keys,
a masked prefix (the first 4 characters and the length): a key is never printed. Exit 1 when
any key is found in the tree or the history, or (with --paths) any host path in the tree.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

KEYS = (
    ("openai-style", re.compile(r"(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{16,}")),
    ("lsv2", re.compile(r"(?<![A-Za-z0-9_])lsv2_[A-Za-z0-9_]{10,}")),
    ("github", re.compile(r"(?<![A-Za-z0-9_])gh[pousr]_[A-Za-z0-9]{30,}")),
    ("aws", re.compile(r"(?<![A-Za-z0-9])AKIA[0-9A-Z]{16}(?![0-9A-Z])")),
    ("slack", re.compile(r"(?<![A-Za-z0-9])xox[abpr]-[A-Za-z0-9-]{10,}")),
    ("private-key", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")),
    ("bearer", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{20,}")),
)
HOST_PATHS = (
    re.compile(r"/home/(?!runner\b|user\b)[A-Za-z0-9._-]+/"),
    re.compile(r"(?<![\w/])/Users/[A-Za-z0-9._-]+/"),
    re.compile(r"/mnt/[a-z]/Users/[^/\s]+", re.IGNORECASE),
    re.compile(r"\b[A-Za-z]:\\Users\\[^\\\s]+", re.IGNORECASE),
)


@dataclass(frozen=True)
class Hit:
    kind: str
    masked: str  # first 4 characters and the length; never the key


def mask(value: str) -> str:
    return f"{value[:4]}… ({len(value)} chars)"


def find_keys(text: str) -> list[Hit]:
    return [Hit(kind, mask(m.group(0))) for kind, p in KEYS for m in p.finditer(text)]


def find_host_paths(text: str) -> list[str]:
    return [m.group(0) for p in HOST_PATHS for m in p.finditer(text)]


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
    return out.stdout.decode("utf-8", "replace")


def scan_repo(repo: Path) -> dict[str, object]:
    """Booleans per check, and masked key prefixes (tree and history)."""
    tree_keys: list[Hit] = []
    tree_paths: list[str] = []
    for path in _git(repo, "ls-files", "-z").split("\0"):
        if not path or not (repo / path).is_file():
            continue
        try:
            text = (repo / path).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        tree_keys += find_keys(text)
        tree_paths += [f"{path}" for _ in find_host_paths(text)]
    history = _git(repo, "log", "--all", "-p", "--no-color", "--no-ext-diff")
    added = "\n".join(line[1:] for line in history.splitlines() if line.startswith("+"))
    history_keys = find_keys(added) + find_keys(_git(repo, "log", "--all", "--format=%B"))
    return {
        "tree_keys": bool(tree_keys),
        "history_keys": bool(history_keys),
        "tree_host_paths": bool(tree_paths),
        "masked": sorted({f"{h.kind}: {h.masked}" for h in tree_keys + history_keys}),
        "host_path_files": sorted(set(tree_paths)),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--paths", action="store_true", help="fail on host paths in the tree too")
    a = ap.parse_args(argv)
    r = scan_repo(a.repo)
    print(f"keys in tree: {r['tree_keys']}")
    print(f"keys in history: {r['history_keys']}")
    print(f"host paths in tree: {r['tree_host_paths']}")
    for line in r["masked"]:
        print(f"  {line}")
    for path in r["host_path_files"]:
        print(f"  host path in {path}")
    bad = r["tree_keys"] or r["history_keys"] or (a.paths and r["tree_host_paths"])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
