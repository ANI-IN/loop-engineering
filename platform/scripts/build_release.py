"""Build the public course tree from the release list (platform/config/release.toml).

    uv run python platform/scripts/build_release.py                    # dry run of HEAD
    uv run python platform/scripts/build_release.py --build DIR        # a new one-commit repository
    uv run python platform/scripts/build_release.py --into CLONE       # update a clone of main
    uv run python platform/scripts/build_release.py --with-solutions --into CLONE
                                                   # the Thursday review: publish the solutions

The release list is turned into the configuration of the release kit
(platform/scripts/kit/release/make_release.py), which reads only git objects, so untracked and
uncommitted files never ship. `--build` makes the first release: a fresh repository with one
commit. `--into` updates an existing clone of the public main branch for a later release: it
writes the public files, removes tracked files that are no longer public, and stages the result,
leaving the commit (a normal commit, never a rewrite) to the person publishing. Words that must
never appear in a public file are passed with `--deny`, so the words themselves are not published.

The four assignment solutions are withheld until the Thursday review: the release list excludes
them and the public .gitignore ignores them. At the start of the review the course owner runs the
release with `--with-solutions`, which ships the solution folders and leaves that .gitignore block
out. Every later release keeps `--with-solutions`: an `--into` release without it refuses a clone
that already publishes the solutions, so a release never unpublishes them by accident.

Every mode then runs the public tree's own checks in the built tree: the strict style check of the
course text, the release gate, which fails on any warning; and the unit tests (`uv run pytest`, no
database, no model), which fail on a failing test or on a skip that the withheld solutions do not
explain. `--without-public-tests` leaves both out, for a quick look at the file list only.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
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
# The unit suite of the public tree: the same selection as `make test`.
PUBLIC_TESTS = ["uv", "run", "--frozen", "pytest", "-q", "-p", "no:cacheprovider", "-rs"]
PUBLIC_TESTS += ["-m", "not integration and not live"]
# The style checker of the course text; strict style is the release gate.
STYLE_CHECKER = "platform/scripts/check_style.py"
# The skip reason of every check that needs the withheld solutions (datapilot.assignments).
WITHHELD_SKIP = "the assignment solutions are published at the start of the Thursday review"


def _allow(entry: str) -> str:
    return entry + "**" if entry.endswith("/") else entry


def _listed(repo: Path, ref: str) -> dict:
    return tomllib.loads(make_release.blob(repo, ref, RELEASE_LIST).decode("utf-8"))


def config(
    repo: Path, ref: str, deny: list[str], message: str, *, with_solutions: bool = False
) -> make_release.Config:
    """The release kit's configuration from the release list at `ref`. With `with_solutions`, the
    solution folders ship and the public .gitignore no longer withholds them."""
    listed = _listed(repo, ref)
    solutions = listed.get("solutions")
    tracked = make_release.tracked(repo, ref)
    private_dirs: list[str] = []
    for entry in listed["exclude"]:
        if with_solutions and entry == solutions:
            continue
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
        deny_patterns=listed.get("deny_patterns", []),
        gitignore_extra=[] if with_solutions else listed.get("public_gitignore", []),
        gitignore_drop=listed.get("build_only_gitignore", []),
    )


def _solution_files(paths: list[str], solutions: str | None) -> list[str]:
    if not solutions:
        return []
    return [p for p in paths if fnmatch.fnmatchcase(p, solutions + "*")]


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


def update_clone(
    repo: Path,
    cfg: make_release.Config,
    clone: Path,
    ref: str,
    *,
    with_solutions: bool = False,
) -> make_release.Result:
    """Write the public files of `ref` into an existing clone of main and stage the change."""
    res = make_release.Result()
    solutions = _listed(repo, ref).get("solutions")
    published = _solution_files(_git(clone, "ls-files").splitlines(), solutions)
    if published and not with_solutions:
        res.problems.append(
            f"{clone} already publishes the solutions ({len(published)} files): add "
            "--with-solutions, or this release would delete them"
        )
        return res
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


def skip_problems(output: str) -> list[str]:
    """Skips in the public tests' summary (`-rs`) that the withheld solutions do not explain."""
    problems = []
    for line in output.splitlines():
        found = re.match(r"^SKIPPED \[(\d+)\] (\S+?:\d+):\s*(.*)$", line.strip())
        if found and WITHHELD_SKIP not in found.group(3):
            problems.append(f"{found.group(1)} skipped in {found.group(2)}: {found.group(3)}")
    return problems


def public_test_problems(tree: Path) -> list[str]:
    """Run the public tree's unit suite in its own environment and report what fails."""
    env = {k: v for k, v in os.environ.items() if k != "UV_PROJECT_ENVIRONMENT"}
    env.pop("VIRTUAL_ENV", None)  # the built tree gets its own .venv, never this checkout's
    done = subprocess.run(PUBLIC_TESTS, cwd=tree, env=env, capture_output=True, text=True)
    print(f"public tests: {(done.stdout.strip().splitlines() or ['no output'])[-1]}")
    problems = [
        f"skip not explained by the withheld solutions: {p}" for p in skip_problems(done.stdout)
    ]
    if done.returncode != 0:
        tail = "\n".join((done.stdout + done.stderr).strip().splitlines()[-15:])
        problems.append(f"the public tree's unit tests failed (exit {done.returncode}):\n{tail}")
    return problems


def public_style_problems(tree: Path) -> list[str]:
    """The release gate on the course text: the public tree's own style checker, strict, so a
    warning fails the release as an error does (the checker needs only the standard library)."""
    checker = tree / STYLE_CHECKER
    if not checker.is_file():
        return [f"the public tree has no {STYLE_CHECKER}: the strict style check cannot run"]
    done = subprocess.run(
        [sys.executable, str(checker), "--strict"], cwd=tree, capture_output=True, text=True
    )
    print(f"public style: {(done.stdout.strip().splitlines() or ['no output'])[-1]}")
    if done.returncode == 0:
        return []
    tail = "\n".join((done.stdout + done.stderr).strip().splitlines()[-15:])
    return [f"the strict style check failed (exit {done.returncode}):\n{tail}"]


def public_checks(tree: Path) -> list[str]:
    """The public tree's own checks: the strict style check and the unit tests."""
    return public_style_problems(tree) + public_test_problems(tree)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--deny", action="append", default=[], help="a word no public file may hold")
    ap.add_argument("--message", default="Loop Engineering: the course and the DataPilot platform")
    ap.add_argument(
        "--with-solutions",
        action="store_true",
        help="ship the four solution folders (the Thursday review and every release after it)",
    )
    ap.add_argument(
        "--without-public-tests",
        action="store_true",
        help="leave out the public tree's strict style check and unit tests (a quick look)",
    )
    where = ap.add_mutually_exclusive_group()
    where.add_argument("--build", type=Path, help="a new one-commit repository in this folder")
    where.add_argument("--into", type=Path, help="an existing clone of the public main branch")
    a = ap.parse_args(argv)
    cfg = config(a.repo, a.ref, a.deny, a.message, with_solutions=a.with_solutions)
    solutions = _solution_files(
        make_release.tracked(a.repo, a.ref), _listed(a.repo, a.ref).get("solutions")
    )
    if a.with_solutions and not solutions:
        print(f"x --with-solutions: no solution files at {a.ref}")
        return 1
    if a.into:
        res = update_clone(a.repo, cfg, a.into, a.ref, with_solutions=a.with_solutions)
        if res.ok and not a.without_public_tests:
            res.problems += public_checks(a.into)
    else:
        dest = a.build or Path(tempfile.mkdtemp(prefix="release-"))
        try:
            res = make_release.release(a.repo, cfg, dest, a.ref)
            if res.ok and not a.without_public_tests:
                res.problems += public_checks(dest)
        finally:
            if a.build is None:
                shutil.rmtree(dest, ignore_errors=True)
    print(f"public files: {len(res.public)}")
    if a.with_solutions:
        chosen = set(solutions)
        print(f"solutions published: {sum(p in chosen for p in res.public)} files")
    for path, why in res.dropped_tests.items():
        print(f"! test dropped (names an excluded file): {path} ({why[0]})")
    for line in res.problems:
        print(f"x {line}")
    if res.ok:
        if a.into:
            print(
                f"staged in {a.into}; commit as a normal commit, run "
                f"`make ci-local REPO={a.into}` in Linux, and push without force only if it passes"
            )
        elif a.build:
            print(f"built {a.build} (not pushed)")
        else:
            print("dry run passed")
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
