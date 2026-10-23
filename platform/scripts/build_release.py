"""Build the public course tree from the release list (platform/config/release.toml).

    uv run python platform/scripts/build_release.py                    # dry run of HEAD
    uv run python platform/scripts/build_release.py --build DIR        # a new one-commit repository
    uv run python platform/scripts/build_release.py --into CLONE       # update a clone of main

The release list is turned into the configuration of the release kit
(platform/scripts/kit/release/make_release.py), which reads only git objects, so untracked and
uncommitted files never ship. `--build` makes the first release: a fresh repository with one
commit. `--into` updates an existing clone of the public main branch for a later release: it
writes the public files, removes tracked files that are no longer public, and stages the result,
leaving the commit (a normal commit, never a rewrite) to the person publishing. Words that must
never appear in a public file are passed with `--deny`, so the words themselves are not published.
"""

from __future__ import annotations

import argparse
import fnmatch
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "kit" / "release"))
import make_release  # noqa: E402

AUTHOR_NAME = "ANI-IN"
AUTHOR_EMAIL = "44803072+ANI-IN@users.noreply.github.com"
RELEASE_LIST = "platform/config/release.toml"


def _allow(entry: str) -> str:
    return entry + "**" if entry.endswith("/") else entry


def config(repo: Path, ref: str, deny: list[str], message: str) -> make_release.Config:
    """The release kit's configuration from the release list at `ref`."""
    listed = tomllib.loads(make_release.blob(repo, ref, RELEASE_LIST).decode("utf-8"))
    tracked = make_release.tracked(repo, ref)
    private_dirs: list[str] = []
    for entry in listed["exclude"]:
        if "*" not in entry:
            private_dirs.append(entry)
            continue
        depth = entry.rstrip("/").count("/") + 1
        prefixes = {"/".join(p.split("/")[:depth]) + "/" for p in tracked if p.count("/") >= depth}
        private_dirs += sorted(p for p in prefixes if fnmatch.fnmatchcase(p, entry))
    internal = set(listed.get("internal_files", []))
    private_files = sorted(
        {p for p in tracked if p.rsplit("/", 1)[-1] in internal} | set(listed.get("build_only", []))
    )
    return make_release.Config(
        allow=[_allow(e) for e in listed["include"]],
        private_dirs=private_dirs,
        private_files=private_files,
        deny=deny,
        author_name=AUTHOR_NAME,
        author_email=AUTHOR_EMAIL,
        commit_message=message,
        host_path_examples=listed.get("host_path_examples", []),
        gitignore_extra=listed.get("public_gitignore", []),
    )


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


def update_clone(
    repo: Path, cfg: make_release.Config, clone: Path, ref: str
) -> make_release.Result:
    """Write the public files of `ref` into an existing clone of main and stage the change."""
    res = make_release.Result()
    included, excluded = make_release.select(make_release.tracked(repo, ref), cfg)
    blobs = {p: make_release.blob(repo, ref, p) for p in included}
    texts = {}
    for p, data in blobs.items():
        try:
            texts[p] = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
    tests = {p: t for p, t in texts.items() if make_release._is_test(p)}
    res.dropped_tests = make_release.find_excluded_tests(tests, excluded)
    res.public = [p for p in included if p not in res.dropped_tests]
    res.problems += [
        f"{p}: private path in the public list" for p in make_release.leaks(res.public, cfg)
    ]
    res.problems += make_release.content_problems(
        {p: texts[p] for p in res.public if p in texts}, cfg
    )
    if res.problems:
        return res
    keep = set(res.public)
    for old in _git(clone, "ls-files").splitlines():
        if old not in keep:
            _git(clone, "rm", "-q", "--", old)
    make_release.write_tree(clone, {p: blobs[p] for p in res.public}, cfg)
    _git(clone, "add", "-A")
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--deny", action="append", default=[], help="a word no public file may hold")
    ap.add_argument("--message", default="Loop Engineering: the course and the DataPilot platform")
    where = ap.add_mutually_exclusive_group()
    where.add_argument("--build", type=Path, help="a new one-commit repository in this folder")
    where.add_argument("--into", type=Path, help="an existing clone of the public main branch")
    a = ap.parse_args(argv)
    cfg = config(a.repo, a.ref, a.deny, a.message)
    if a.into:
        res = update_clone(a.repo, cfg, a.into, a.ref)
    else:
        dest = a.build or Path(tempfile.mkdtemp(prefix="release-"))
        try:
            res = make_release.release(a.repo, cfg, dest, a.ref)
        finally:
            if a.build is None:
                shutil.rmtree(dest, ignore_errors=True)
    print(f"public files: {len(res.public)}")
    for path, why in res.dropped_tests.items():
        print(f"! test dropped (names an excluded file): {path} ({why[0]})")
    for line in res.problems:
        print(f"x {line}")
    if res.ok:
        if a.into:
            print(f"staged in {a.into}; commit as a normal commit, then push without force")
        elif a.build:
            print(f"built {a.build} (not pushed)")
        else:
            print("dry run passed")
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
