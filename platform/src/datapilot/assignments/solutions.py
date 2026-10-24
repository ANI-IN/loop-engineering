"""Solutions onto a copy of the starter, and the build's verification passes.

`make apply-solution NAME=<slug> VARIANT=<variant>` copies the tree (the complete class system with
its extension points) to a scratch folder outside the repository, copies the variant's files/ over
it, and applies its changes.patch when it has one. Learner work in the repository is never
touched, and an existing copy is replaced only when asked (FORCE=1, or --force). In a public copy
made before the Thursday review the solutions are withheld, and apply stops and says so. The copy
links to the repository's .env rather than copying it.

`make verify-assignments` runs, for each assignment, the starter once (it must FAIL) and each of
the three solutions twice in a row (each must PASS), under the spend activity "assignment
verification", and writes what each run printed into solution/captured/, with a terminal image
and a console screenshot. Captures are evidence for people; no check ever reads them.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from datapilot.assignments import VARIANTS, assignment, solutions_withheld
from datapilot.assignments.cost import VERIFICATION
from datapilot.assignments.report import Stop
from datapilot.assignments.stack import CLASS_PROJECT, DEFAULTS, running_stack
from datapilot.names import SECTIONS
from datapilot.settings import PLATFORM, REPO

SKIP = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".import_linter_cache",
    "node_modules",
    ".runs",
    "exports",
    "test-results",
    "playwright-report",
    ".claude",
}
NOTE = "Your output will differ: run times, ids, and the agent's wording change on every run."
# A LangSmith run link names the organization it belongs to. The build's traces are private, so a
# capture keeps each trace id in words and never the build's organization (it ships with the
# solutions at the Thursday review).
TRACE_LINK = re.compile(
    r"https://(?:[\w.-]+\.)?smith\.langchain\.com/o/[0-9a-f-]+/projects/p/[0-9a-f-]+/r/"
    r"(?P<trace>[0-9a-f-]+)(?:\?\S*)?"
)
PRIVATE_TRACE = "trace id {trace}, in the build's private LangSmith project"
# The console page each assignment's runs show on, and an element that means it has loaded.
CONSOLE_PAGES = {
    "agent-loop": ("events", ".sl"),
    "verification-loop": ("events", ".sl"),
    "event-loop": ("events", ".sl"),
    "hill-climbing-loop": ("improve", ".sl"),
}


def work_root() -> Path:
    default = Path.home() / ".datapilot" / "assignment-work"
    return Path(os.environ.get("DATAPILOT_ASSIGNMENT_WORK", default))


def _tracked(tree: Path) -> list[Path] | None:
    """Tracked and new, not ignored, files; None when git cannot list them (not a checkout, or an
    agent worktree under WSL whose .git file names a Windows path)."""
    if shutil.which("git") is None or not (tree / ".git").exists():
        return None
    done = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=tree, capture_output=True
    )
    if done.returncode != 0:
        return None
    return [Path(p) for p in done.stdout.decode().split("\0") if p]


def _solution_folder(rel: Path) -> bool:
    parts = rel.parts
    return len(parts) > 2 and parts[1] == "assignment" and parts[2] == "solution"


def copy_tree(source: Path, dest: Path) -> None:
    """The starter: the tree without any assignment's solution folder, so a copy holds only the
    one variant applied to it."""
    if dest.exists():
        shutil.rmtree(dest)
    files = _tracked(source)
    if files is None:
        shutil.copytree(source, dest, ignore=shutil.ignore_patterns(*SKIP, ".env", "solution"))
        return
    for rel in files:
        skipped = rel.parts and rel.parts[0] in SKIP or _solution_folder(rel)
        if skipped or not (source / rel).is_file():
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / rel, target)


WITHHELD = (
    "The solutions are withheld until the Thursday review: this copy has no solution/ folder, so "
    "there is no {variant} to apply. They are published at the start of the review. To check your "
    "own work now, run make check-assignment NAME={slug}."
)
EXISTS = (
    "{dest} already exists, and apply never replaces a folder unasked: it may hold your own "
    "changes. Replace it with FORCE=1 on the make command (or --force), or remove it yourself."
)


def solution_files(slug: str, variant: str, source: Path) -> tuple[Path | None, Path | None]:
    """The variant's files/ folder and changes.patch, each None when absent; a Stop when the copy
    withholds the solutions, or when the variant has neither, so nothing reports a solution applied
    that was never there."""
    if solutions_withheld(source):
        raise Stop(WITHHELD.format(variant=variant, slug=slug))
    solution = assignment(slug, source).solution(variant)
    files = solution / "files"
    patch = solution / "changes.patch"
    found = (files if files.is_dir() else None, patch if patch.is_file() else None)
    if found == (None, None):
        raise Stop(f"{solution} has no files/ folder and no changes.patch: nothing to apply.")
    return found


def apply(
    slug: str,
    variant: str,
    *,
    source: Path = REPO,
    dest: Path | None = None,
    force: bool = False,
) -> Path:
    """A scratch copy of `source` with the solution applied ("starter" applies nothing). An
    existing destination is replaced only with `force`."""
    dest = dest or work_root() / f"{slug}-{variant}"
    files, patch = solution_files(slug, variant, source) if variant != "starter" else (None, None)
    if dest.exists() and not force:
        raise Stop(EXISTS.format(dest=dest))
    copy_tree(source, dest)
    if variant != "starter":
        if files is not None:
            shutil.copytree(files, dest, dirs_exist_ok=True)
        if patch is not None:
            subprocess.run(
                ["git", "apply", "--whitespace=nowarn", str(patch)], cwd=dest, check=True
            )
    env_file = source / ".env"
    if env_file.is_file() and not (dest / ".env").exists():
        try:
            (dest / ".env").symlink_to(env_file)
        except OSError:
            print("note: could not link .env; export OPENAI_API_KEY before the check")
    return dest


@dataclass(frozen=True)
class Capture:
    name: str  # such as "reference-run-1"
    code: int
    text: str


def _run_captured(slug: str, tree: Path) -> tuple[int, str]:
    env = {
        **os.environ,
        "DATAPILOT_SPEND_ACTIVITY": VERIFICATION,
        "PYTHONPATH": str(tree / "platform" / "src"),
    }
    process = subprocess.Popen(
        [sys.executable, "-m", "datapilot.assignments", "check", slug],
        cwd=tree,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    lines = []
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="", flush=True)
        lines.append(line)
    return process.wait(), "".join(lines)


def _kit() -> None:
    kit = str(PLATFORM / "scripts" / "kit" / "capture")
    if kit not in sys.path:
        sys.path.insert(0, kit)


def masked(text: str) -> str:
    """Every LangSmith run link becomes its trace id in words: no organization is named."""
    return TRACE_LINK.sub(lambda hit: PRIVATE_TRACE.format(trace=hit.group("trace")), text)


def _redacted(text: str) -> str:
    """Host home folders become ~, as in every capture of the course kit, and every LangSmith
    run link becomes its trace id (masked)."""
    _kit()
    from capturelib import redact_paths

    return masked(redact_paths(text))


def _terminal_image(text: str, out: Path, command: str) -> str | None:
    """None when written, else why not."""
    _kit()
    try:
        from term_render import render  # the course kit's renderer: it refuses key-like text

        render(text, out, command=command, ranges="-60", title="Terminal")
    except Exception as error:  # a missing image is reported on the page, never invented
        return f"{type(error).__name__}: {error}"
    return None


def _console_image(slug: str, out: Path) -> str | None:
    """None when written, else why not."""
    path, ready = CONSOLE_PAGES[slug]
    url = f"http://localhost:{os.environ.get('CONSOLE_PORT', DEFAULTS['CONSOLE_PORT'])}/{path}"
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 720})
            page.goto(url)
            page.locator(ready).first.wait_for(timeout=60_000)
            page.wait_for_timeout(2500)  # two fragment ticks, so every component has its data
            page.screenshot(path=str(out))
            browser.close()
    except Exception as error:  # a missing screenshot is reported on the page, never invented
        return f"{type(error).__name__}: {str(error).splitlines()[0][:200]}"
    return None


def _write_capture(slug: str, folder: Path, capture: Capture) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    text = _redacted(capture.text)
    (folder / f"{capture.name}.txt").write_text(text, encoding="utf-8")
    command = f"make check-assignment NAME={slug}"
    terminal_problem = _terminal_image(text, folder / f"{capture.name}-terminal.png", command)
    console_problem = _console_image(slug, folder / f"{capture.name}-console.png")
    verdict = "PASS" if capture.code == 0 else "FAIL" if capture.code == 1 else "stopped"
    title = assignment(slug).title
    when = datetime.now(UTC).strftime("%d %B %Y, %H:%M")
    lines = [
        f"# Module: Loop Engineering - {title}, {capture.name}",
        "",
        f"A verification pass of the live check, run on {when} Coordinated Universal Time. "
        f"The check ended {verdict}. The full output is in "
        f"[{capture.name}.txt]({capture.name}.txt).",
        "",
        NOTE,  # before the first image or captured block, as the style guide asks
        "",
    ]
    if terminal_problem is None:
        lines += [
            f"![The terminal after {command} finished: the last lines of its output, with the "
            f"result line reading {verdict}.]({capture.name}-terminal.png)",
            "",
            "*The end of the check's output, with each live run's trace id and live stamp.*",
            "",
        ]
    else:
        lines += [f"No terminal image was made ({terminal_problem}).", ""]
    if console_problem is None:
        lines += [
            f"![The DataPilot console at 1280 by 720 pixels, on the page that shows this "
            f"assignment's runs, just after the check.]({capture.name}-console.png)",
            "",
            "*The console right after the check, showing the runs of the open live session.*",
            "",
        ]
    else:
        lines += [f"No console screenshot was made ({console_problem}).", ""]
    traces = [
        hit.group(1) for hit in re.finditer(r"trace: trace id ([0-9a-f-]+), in the build's", text)
    ]
    if traces:
        lines += [
            "Trace ids of the live runs, in order (the build's LangSmith project is private, so "
            "no link is given):",
            "",
        ]
        lines += [f"- {trace}" for trace in traces]
        lines.append("")
    while lines and lines[-1] == "":
        lines.pop()
    (folder / f"{capture.name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify(only: list[str] | None = None) -> int:
    """Every assignment: the starter once, each solution twice. Returns 0 when all came out as
    expected (the starter FAIL, every solution PASS). The verification makes its own copies, so it
    replaces them; in a public copy it stops before any check, as apply does."""
    if solutions_withheld():
        raise Stop(WITHHELD.format(variant="solution", slug="<slug>"))
    problems = []
    for section in SECTIONS:
        slug = section.slug
        if only and slug not in only:
            continue
        folder = assignment(slug).folder / "solution" / "captured"
        plan = [("starter", 1), *[(variant, 2) for variant in VARIANTS]]
        for variant, times in plan:
            tree = apply(slug, variant, force=True)
            for n in range(1, times + 1):
                code, text = _run_captured(slug, tree)
                name = f"{variant}-run-{n}" if times > 1 else variant
                _write_capture(slug, folder, Capture(name, code, text))
                expected = 1 if variant == "starter" else 0
                if code != expected:
                    problems.append(f"{slug} {name}: exit {code}, expected {expected}")
    stop_stack()
    for problem in problems:
        print(f"x {problem}")
    return 1 if problems else 0


def stop_stack() -> None:
    """Stop the check's own Compose project, keeping its volume (the seeded data and the session's
    baseline). It never names the class project."""
    if running_stack() or shutil.which("docker") is None:
        return
    project = os.environ.get("COMPOSE_PROJECT_NAME") or DEFAULTS["COMPOSE_PROJECT_NAME"]
    if project != CLASS_PROJECT:
        subprocess.run(["docker", "compose", "-p", project, "down"], check=False)
