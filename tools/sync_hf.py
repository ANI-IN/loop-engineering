"""Push the frozen exhibit to a Hugging Face Space, in one step.

Replaces a shell script that filtered by copying only what it wanted. Copying the
right things is not the same as refusing the wrong ones: a filter that misses is
silent, and what it would leak here is either a credential or a stored sweep cell
that makes a chart look computed.

So this **asserts** rather than trusts. Every file staged for the push is checked
against the forbidden set, and a single match aborts before anything is pushed.

WHAT MUST NEVER REACH THE SPACE
-------------------------------

  .env                 credentials. The Space needs none and gets none.
  results/sweep/       live cell output. A stored cell on a public page renders as
  results/ablation/    though it had just been computed, which is the one thing
                       this project refuses.
  *.duckdb             generated data. The Space rebuilds the warehouse from the
                       seed at startup and asserts its checksum.

WHY THE SPACE IS SAFE WITHOUT A KEY
-----------------------------------

It runs the EXHIBIT profile: no roles, no cells, a zero spend cap. The guarantee
is structural rather than quantitative — `tests/test_exhibit.py` spies on the
`anthropic.Anthropic` constructor and asserts none is ever built. That test is the
security boundary, and it is why a public Space here cannot spend anyone's money.

REQUIREMENTS
------------

Spaces do not use uv. `deploy/hf/requirements.txt` is generated from `uv.lock` by
`--write-requirements`, pinned, and restricted to what the exhibit actually
imports — the first attempt exported all of the lock and failed to build, because
the Space's interpreter is older than the one uv resolved against.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# There is deliberately NO default remote.
#
# It carried one — built from the GitHub owner's name — and that namespace does
# not exist on Hugging Face, so the tool confidently pushed at a 404. A default
# that names a place nobody verified is the same defect this project is about, so
# --remote is required and the operator has to say where.


# Copied in. Anything not listed does not reach the Space.
PAYLOAD_DIRS = (
    ("deploy/hf", "."),
    ("src/loopeng", "src/loopeng"),
    ("results/reference", "results/reference"),
)
PAYLOAD_FILES = (
    ("results/gate0.json", "results/gate0.json"),
)

# Checked for after staging. Assertions, not filters.
FORBIDDEN_NAMES = (".env",)
FORBIDDEN_DIRS = ("results/sweep", "results/ablation", "results/charts")
FORBIDDEN_SUFFIXES = (".duckdb", ".duckdb.wal")

# The exhibit's real import surface. Floors rather than exact pins: the Space's
# interpreter is not the one uv resolved against, and an exact pin from the wrong
# Python is how this failed the first time.
SPACE_PACKAGES = (
    "gradio",
    "duckdb",
    "sqlglot",
    "pyyaml",
    "pydantic",
    "pydantic-settings",
    "structlog",
    # Never used to construct a client on the Space, but imported at module scope
    # by the agent loop, so it has to install.
    "anthropic",
)

def required_frontmatter() -> dict[str, str]:
    """The Space's frontmatter, with the SDK version read from the lock.

    `sdk_version` was the string "6.20.0", typed here. That made THREE uncoupled
    sources of truth for the gradio version — `pyproject.toml`, this file, and
    `deploy/hf/requirements.txt` — and this one is the one that decides what the
    hosted Space actually runs.

    So bumping gradio in pyproject.toml and regenerating requirements.txt left the
    deployed Space pinned to 6.20.0, with nothing failing and nothing to notice.
    A version the tests never exercise, running the page the public sees.

    Read from `uv.lock` so the Space runs the gradio the suite was green against.
    """
    return {
        "sdk": "gradio",
        "sdk_version": locked_versions()["gradio"],
        "app_file": "app.py",
    }


class SyncRefused(RuntimeError):
    """Something forbidden reached the staging directory. Nothing was pushed."""


# ---------------------------------------------------------------------------
# staging
# ---------------------------------------------------------------------------


def _ignore(_directory, names):
    return [
        name for name in names
        if name == "__pycache__"
        or name.endswith((".pyc", ".duckdb", ".duckdb.wal"))
    ]


def stage(destination: Path) -> Path:
    """Copy the payload into `destination`. Copies nothing else."""
    destination.mkdir(parents=True, exist_ok=True)

    for source, target in PAYLOAD_DIRS:
        src = REPO_ROOT / source
        if not src.is_dir():
            raise SyncRefused(f"{source} is missing; the Space would be incomplete")
        shutil.copytree(src, destination / target, dirs_exist_ok=True, ignore=_ignore)

    for source, target in PAYLOAD_FILES:
        src = REPO_ROOT / source
        if src.is_file():
            (destination / target).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, destination / target)

    return destination


# ---------------------------------------------------------------------------
# the refusals
# ---------------------------------------------------------------------------


def assert_nothing_forbidden(staged: Path) -> list[Path]:
    """Walk everything staged and refuse on the first forbidden thing.

    Returns the file list so the caller can report what IS being pushed — a sync
    that says only what it blocked tells you nothing about what it sent.
    """
    files = sorted(p for p in staged.rglob("*") if p.is_file())
    offences: list[str] = []

    for path in files:
        relative = path.relative_to(staged)
        posix = relative.as_posix()

        if path.name in FORBIDDEN_NAMES:
            offences.append(f"{posix} — a credentials file must never reach a Space")
        if path.suffix in FORBIDDEN_SUFFIXES:
            offences.append(
                f"{posix} — generated data; the Space rebuilds it from the seed"
            )
        for directory in FORBIDDEN_DIRS:
            if posix == directory or posix.startswith(f"{directory}/"):
                offences.append(
                    f"{posix} — live cell output would render on a public page as "
                    f"though it had just been computed"
                )

    if offences:
        raise SyncRefused(
            "REFUSING TO PUSH. Nothing was sent.\n  " + "\n  ".join(offences)
        )
    return files


def assert_frontmatter(staged: Path) -> dict[str, str]:
    """The Space README's frontmatter decides whether it builds at all."""
    readme = staged / "README.md"
    if not readme.is_file():
        raise SyncRefused("the Space has no README.md, so it has no frontmatter")

    lines = readme.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise SyncRefused("the Space README does not open with a frontmatter block")

    frontmatter: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            key, _, value = line.partition(":")
            frontmatter[key.strip()] = value.strip().strip('"').strip("'")

    for key, expected in required_frontmatter().items():
        actual = frontmatter.get(key)
        if actual != expected:
            raise SyncRefused(
                f"Space frontmatter {key}={actual!r}, expected {expected!r}. "
                f"The Space will not build."
            )
    return frontmatter


def assert_no_secrets_referenced(staged: Path) -> None:
    """The Space entry point must not set a credential at all.

    This check used to REQUIRE the placeholder `exhibit-no-live-calls`, because
    settings validated a mandatory key at import and the Space would otherwise die
    on startup. That placeholder was a config contradiction wearing a disguise: the
    exhibit makes no model call, so it should never have needed a key, fake or real.

    `load_settings(require_credential=False)` removed the reason, so the rule
    inverts and gets stricter. The Space must set NO ANTHROPIC_API_KEY — not a real
    one, which would make a public page able to spend, and not a fake one, which
    would turn a genuine misconfiguration into a confusing model error instead of a
    named missing variable.
    """
    app = (staged / "app.py").read_text(encoding="utf-8")
    for line in app.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "ANTHROPIC_API_KEY" in stripped:
            raise SyncRefused(
                f"app.py sets or reads ANTHROPIC_API_KEY: {stripped!r}. The exhibit "
                f"makes no model call and must ask for no credential — a real key "
                f"would make a public page able to spend, and a fake one hides a "
                f"real misconfiguration behind a model error."
            )


# ---------------------------------------------------------------------------
# requirements, generated from the lock
# ---------------------------------------------------------------------------


def locked_versions() -> dict[str, str]:
    """Package to version, read from uv.lock.

    Parsed rather than shelled out to, so this works without uv on PATH and cannot
    be affected by whatever environment happens to be active.
    """
    versions: dict[str, str] = {}
    name: str | None = None
    for line in (REPO_ROOT / "uv.lock").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("name = "):
            name = stripped.split("=", 1)[1].strip().strip('"')
        elif stripped.startswith("version = ") and name:
            versions[name] = stripped.split("=", 1)[1].strip().strip('"')
            name = None
    return versions


def render_requirements() -> str:
    versions = locked_versions()
    missing = [p for p in SPACE_PACKAGES if p not in versions]
    if missing:
        raise SyncRefused(f"not in uv.lock: {missing}")

    lines = [
        "# GENERATED by tools/sync_hf.py from uv.lock. Do not edit by hand.",
        "#",
        "# Spaces do not use uv, so the lock has to be exported. Only the exhibit's",
        "# real import surface is listed: the first attempt exported the whole lock",
        "# and the build failed, because the Space's interpreter is older than the one",
        "# uv resolved against and a transitive dependency required the newer one.",
        "#",
        "# Floors rather than exact pins, for the same reason. The version after each",
        "# `>=` is what uv.lock currently resolves, so this file changes when the lock",
        "# changes and a reviewer can see it move.",
        "",
    ]
    lines += [f"{package}>={versions[package]}" for package in SPACE_PACKAGES]
    return "\n".join(lines) + "\n"


def write_requirements() -> Path:
    path = REPO_ROOT / "deploy" / "hf" / "requirements.txt"
    path.write_text(render_requirements(), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# the push
# ---------------------------------------------------------------------------


def push(staged: Path, remote: str) -> None:
    """A fresh single-commit history, force-pushed. The Space is a mirror."""
    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=staged, check=True,
                       capture_output=True, text=True)

    git("init", "-q", "-b", "main")
    git("add", "-A")
    git("-c", "user.name=ANI-IN",
        "-c", "user.email=44803072+ANI-IN@users.noreply.github.com",
        "commit", "-q", "-m", "Loop Engineering exhibit")
    git("push", "-f", remote, "HEAD:main")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync the exhibit to a HF Space.")
    parser.add_argument("--remote",
                        help="Space git remote, e.g. "
                             "https://huggingface.co/spaces/<user>/<name>. Required "
                             "unless --dry-run: the Space must exist first, and this "
                             "tool will not guess where it is.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Stage and run every check, push nothing.")
    parser.add_argument("--write-requirements", action="store_true",
                        help="Regenerate deploy/hf/requirements.txt from uv.lock and exit.")
    parser.add_argument("--keep", help="Keep the staging directory at this path.")
    args = parser.parse_args(argv)

    if args.write_requirements:
        print(f"wrote {write_requirements().relative_to(REPO_ROOT)}")
        return 0

    holder = Path(args.keep) if args.keep else Path(tempfile.mkdtemp(prefix="loopeng-hf-"))
    staged = holder / "space"

    try:
        stage(staged)
        files = assert_nothing_forbidden(staged)
        frontmatter = assert_frontmatter(staged)
        assert_no_secrets_referenced(staged)
    except SyncRefused as refusal:
        print(f"\n{refusal}", file=sys.stderr)
        return 1

    expected = render_requirements()
    actual = (REPO_ROOT / "deploy" / "hf" / "requirements.txt").read_text(encoding="utf-8")
    if expected != actual:
        print("deploy/hf/requirements.txt is out of date with uv.lock.", file=sys.stderr)
        print("Run: uv run python tools/sync_hf.py --write-requirements", file=sys.stderr)
        return 1

    total = sum(path.stat().st_size for path in files)
    print(f"staged {len(files)} file(s), {total:,} bytes, in {staged}")
    print(f"  sdk {frontmatter['sdk']} {frontmatter['sdk_version']}, "
          f"app_file {frontmatter['app_file']}")
    print("  refused: .env, results/sweep, results/ablation, *.duckdb — none present")

    if args.dry_run:
        print("\ndry run: nothing pushed.")
        return 0

    if not args.remote:
        print("\n--remote is required to push. Create the Space first, then pass its "
              "git URL. Nothing was pushed.", file=sys.stderr)
        return 1

    print(f"\npushing to {args.remote}")
    try:
        push(staged, args.remote)
    except subprocess.CalledProcessError as failure:
        print(f"git failed:\n{failure.stderr}", file=sys.stderr)
        return 1
    print(f"pushed to {args.remote}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
