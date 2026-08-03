"""The documentation, checked rather than trusted.

Three failure modes this guards against, all of which have already happened here:

  - a relative link that stopped resolving after a file moved
  - a command in a README that no longer parses
  - a diagram copied into two places and then edited in one of them
"""

import ast
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"
CHECKLIST = REPO_ROOT / "PRE-DELIVERY-CHECKLIST.md"

def _is_ours(path: Path) -> bool:
    """Skip anything under a dot-directory.

    `.pytest_cache/README.md` was being collected, which made the number of tests
    depend on whether a previous run had left a cache behind — a suite whose size
    changes with its own side effects is not reproducible, and this module exists
    to check reproducibility claims.
    """
    return not any(part.startswith(".") for part in path.relative_to(REPO_ROOT).parts)


MARKDOWN = sorted(path for path in REPO_ROOT.rglob("*.md") if _is_ours(path))

# The per-level diagrams live in two places on purpose: a GitHub visitor reading
# the architecture section should not have to click four times, and a presenter
# opening a stage runbook should not have to scroll back to the root README. The
# duplication is safe only because this module refuses to let them diverge.
SHARED_DIAGRAMS = {
    "demos/01_agent_loop/README.md": "Level 1",
    "demos/02_verification_loop/README.md": "Level 2",
    "demos/03_event_driven_loop/README.md": "Level 3",
    "demos/04_hill_climbing_loop/README.md": "Level 4",
}


def mermaid_blocks(path: Path) -> list[str]:
    return re.findall(r"^```mermaid\n(.*?)^```$", path.read_text(encoding="utf-8"),
                      re.DOTALL | re.MULTILINE)


# ---- links ------------------------------------------------------------------


def _prose_only(body: str) -> str:
    """Everything outside a fenced block or an inline code span.

    A link is a claim about a file. Code is a quotation, and a quotation of code
    that happens to contain brackets-then-parentheses is not a claim about
    anything — `{"agent": lambda: build_agent_app(...)}` is Python, not a link to
    a file called `name`.

    This is not hypothetical tidying. The audit's own report was the first
    document in this repository to quote a Python dict dispatch, and it turned
    the suite red: `docs/audit/agent-b-build-runtime.md links to name, which does
    not exist`. The test was reading source code as documentation.

    Fences are replaced by blank lines rather than deleted so that anything
    reported by line number still lines up with the file.
    """
    without_fences = re.sub(
        r"^(```|~~~).*?^\1",
        lambda m: "\n" * m.group(0).count("\n"),
        body,
        flags=re.DOTALL | re.MULTILINE,
    )
    return re.sub(r"`[^`\n]*`", "", without_fences)


def _links_in(body: str) -> list[str]:
    """Relative link and image targets in one document's prose.

    Split out from `_relative_links` so the extraction can be tested against a
    string. Reading a file to test a regex made the regex untestable, which is
    why the fenced-code defect survived until a document happened to trip it.
    """
    prose = _prose_only(body)
    targets = re.findall(r"(?<!\!)\[[^\]]*\]\(([^)]+)\)", prose)
    targets += re.findall(r"!\[[^\]]*\]\(([^)]+)\)", prose)
    return [
        target for target in targets
        if not target.startswith(("http://", "https://", "mailto:", "#"))
    ]


def _relative_links(path: Path) -> list[str]:
    return _links_in(path.read_text(encoding="utf-8"))


def test_a_link_in_prose_is_still_found_when_code_is_skipped():
    """The fence fix must not be a way of turning the link check off.

    Half of this test is the bug that prompted it — a Python dict dispatch, which
    read as a link to a file called `name` — and half is an ordinary link in
    prose, which must still be found. A fix that made both disappear would leave
    every document unchecked and every test still green.
    """
    body = (
        "See [the inventory](docs/audit/00-inventory.md).\n"
        "\n"
        "```python\n"
        'app = {"agent": lambda: build_agent_app(warehouse)}[args.view]()\n'
        "```\n"
        "\n"
        "Inline `{\"trap\": lambda: build_trap_app(items)}[key]` too.\n"
    )
    assert _links_in(body) == ["docs/audit/00-inventory.md"]


def test_an_image_in_prose_is_still_found():
    assert _links_in("![dial](assets/dial.png)\n") == ["assets/dial.png"]


def test_a_fenced_block_does_not_swallow_the_document_after_it():
    """An unbalanced count would blank the rest of the file and check nothing."""
    body = "```\ncode\n```\n\nThen [a link](README.md).\n"
    assert _links_in(body) == ["README.md"]


@pytest.mark.parametrize("path", MARKDOWN, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_every_relative_link_resolves(path):
    for target in _relative_links(path):
        resolved = (path.parent / target.split("#")[0]).resolve()
        assert resolved.exists(), (
            f"{path.relative_to(REPO_ROOT)} links to {target}, which does not exist"
        )


# ---- documented commands must be runnable ------------------------------------
#
# `README.md` told the room to run `charts.py --with-reference` for the whole life
# of the Stage 4 runbook. There is no such flag — the real one is `--reference` —
# so the single most-repeated command of the most expensive stage exited 2 every
# time, while a paid sweep was in flight.
#
# Every other check in this module reads prose. This one reads the commands, which
# is the part of a document a reader actually executes.

# `[^\S\n]` is horizontal whitespace only. `\s+` here matched newlines, so one
# command's flag list ran on into every line below it and the checker blamed
# `enqueue.py` for `worker.py --drain`. A checker that reports the wrong file is
# worse than none: it teaches the reader to distrust it and then be right to.
_COMMAND = re.compile(r"^[^\S\n]*uv run python[^\S\n]+(\S+\.py)([^\n]*)", re.MULTILINE)


def _documented_commands(body: str) -> list[tuple[str, list[str]]]:
    """(script, long flags) for every `uv run python …` in a fenced block.

    Line continuations are joined first, so a command split over several lines is
    read as one. Only `--flags` are collected: values, paths and quoted questions
    vary legitimately between documents and prove nothing.
    """
    joined = re.sub(r"\\\n\s*", " ", body)
    commands = []
    for script, tail in _COMMAND.findall(joined):
        flags = [
            token.split("=")[0]
            for token in tail.split()
            if token.startswith("--")
        ]
        commands.append((script, flags))
    return commands


def _declared_flags(script: Path) -> set[str]:
    """Every option string the script's argparse declares, read from the AST.

    Static rather than `--help`, deliberately: importing thirteen entry points in
    a subprocess apiece is slow, and a script whose parser cannot be built without
    a credential would make this test need one.
    """
    tree = ast.parse(script.read_text(encoding="utf-8"))
    flags = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if getattr(node.func, "attr", None) != "add_argument":
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if arg.value.startswith("-"):
                    flags.add(arg.value)
    return flags


# The audit record quotes broken commands on purpose — that is what a finding IS.
# `docs/audit/agent-d-docs-links.md` contains `charts.py --with-reference` as the
# evidence for the defect this checker was written to catch, so running the checker
# over it would forbid the repository from describing its own bugs.
#
# Scoped to `docs/audit/` rather than all of `docs/`, so ordinary documentation
# added there later is still checked.
INSTRUCTIONAL = [p for p in MARKDOWN if "docs/audit/" not in p.as_posix()]


@pytest.mark.parametrize(
    "path", INSTRUCTIONAL, ids=lambda p: str(p.relative_to(REPO_ROOT))
)
def test_every_documented_command_names_a_script_that_exists(path):
    for script, _ in _documented_commands(path.read_text(encoding="utf-8")):
        assert (REPO_ROOT / script).is_file(), (
            f"{path.relative_to(REPO_ROOT)} runs {script}, which does not exist"
        )


@pytest.mark.parametrize(
    "path", INSTRUCTIONAL, ids=lambda p: str(p.relative_to(REPO_ROOT))
)
def test_every_documented_flag_is_accepted_by_the_script(path):
    for script, flags in _documented_commands(path.read_text(encoding="utf-8")):
        target = REPO_ROOT / script
        if not target.is_file():
            continue  # the test above owns that failure
        declared = _declared_flags(target)
        if not declared:
            continue  # no argparse: nothing to contradict
        for flag in flags:
            assert flag in declared, (
                f"{path.relative_to(REPO_ROOT)} runs `{script} {flag}`, but "
                f"{script} declares no such option. It accepts: {sorted(declared)}"
            )


def test_the_command_reader_would_have_caught_the_flag_that_shipped():
    """The regression guard, against the exact text that was wrong.

    A parser that silently found no commands would make both tests above vacuous
    and green, which is the failure mode this whole module exists to prevent.
    """
    found = _documented_commands(
        "```bash\nuv run python demos/04_hill_climbing_loop/charts.py --with-reference\n```\n"
    )
    assert found == [("demos/04_hill_climbing_loop/charts.py", ["--with-reference"])]
    assert "--with-reference" not in _declared_flags(
        REPO_ROOT / "demos" / "04_hill_climbing_loop" / "charts.py"
    )
    assert "--reference" in _declared_flags(
        REPO_ROOT / "demos" / "04_hill_climbing_loop" / "charts.py"
    )


def test_the_command_reader_joins_a_continued_line():
    body = (
        "```bash\n"
        "uv run python demos/03_event_driven_loop/enqueue.py \\\n"
        '  --question "what share of beauty orders ended up with a refund?"\n'
        "```\n"
    )
    assert _documented_commands(body) == [
        ("demos/03_event_driven_loop/enqueue.py", ["--question"])
    ]


def test_no_markdown_points_at_a_file_in_a_deleted_directory():
    """`scripts/` and `app/` are gone.

    Aimed at *paths*, not at the words: `demos/README.md` says there is no such
    directory, and that sentence is true and should stay. What must not survive is
    a reference to a file inside one of them.

    `docs/` used to be listed here and no longer is, because it exists again — it
    holds the audit record. A blanket ban would now be a rule that outlived its
    reason, which is the failure this repository is about. The check that replaced
    it is stricter, not weaker: see the test below, which requires every `docs/`
    path in prose to resolve rather than requiring it to be absent.
    """
    stale = re.compile(r"`(?:scripts|app)/[\w./-]+\.\w+`")
    for path in MARKDOWN:
        found = stale.findall(path.read_text(encoding="utf-8"))
        assert not found, (
            f"{path.relative_to(REPO_ROOT)} points at {found}, in a removed directory"
        )


def test_every_docs_path_named_in_prose_resolves():
    """A backticked `docs/…` path is a citation, and a citation must resolve.

    The audit record is cited by path from several documents. A link would be
    caught by `test_every_relative_link_resolves`; a bare backticked path would
    not have been caught by anything, which is how a stale citation survives.
    """
    cited = re.compile(r"`(docs/[\w./-]+\.\w+)`")
    for path in MARKDOWN:
        for target in cited.findall(path.read_text(encoding="utf-8")):
            assert (REPO_ROOT / target).exists(), (
                f"{path.relative_to(REPO_ROOT)} cites {target}, which does not exist"
            )


def test_the_clone_instructions_are_real():
    """`git clone <repo>` was a placeholder in two files, and `cd \"Loop Eng\"` was
    never the directory a clone produces."""
    for path in (README, CHECKLIST):
        body = path.read_text(encoding="utf-8")
        if "git clone" not in body:
            continue
        assert "<repo>" not in body, f"{path.name} still has a placeholder clone URL"
        assert 'cd "Loop Eng"' not in body, f"{path.name} cds to the wrong directory"
        assert "github.com/ANI-IN/loop-engineering" in body
        assert "cd loop-engineering" in body


def test_the_readme_links_to_the_checklist_and_it_resolves():
    assert "PRE-DELIVERY-CHECKLIST.md" in README.read_text(encoding="utf-8")
    assert CHECKLIST.is_file()


# ---- diagrams ---------------------------------------------------------------


def test_the_readme_carries_the_system_overview_and_every_level():
    """One nesting overview plus one diagram per loop level."""
    assert len(mermaid_blocks(README)) == 1 + len(SHARED_DIAGRAMS)


@pytest.mark.parametrize("stage", sorted(SHARED_DIAGRAMS), ids=lambda s: s.split("/")[1])
def test_each_stage_diagram_is_byte_identical_in_the_readme(stage):
    """A diagram duplicated by hand is a diagram that drifts. This is the
    enforcement that makes the duplication safe."""
    stage_blocks = mermaid_blocks(REPO_ROOT / stage)
    assert len(stage_blocks) == 1, f"{stage} should carry exactly one diagram"
    assert stage_blocks[0] in mermaid_blocks(README), (
        f"the {SHARED_DIAGRAMS[stage]} diagram in {stage} differs from the one in "
        f"README.md. They are duplicated deliberately and must stay identical."
    )


@pytest.mark.parametrize("path", MARKDOWN, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_no_diagram_carries_a_measured_number(path):
    """No numbers in any diagram. Level names and hex colours are not numbers."""
    for block in mermaid_blocks(path):
        stripped = re.sub(r"#[0-9a-fA-F]{3,8}", "", block)              # colours
        stripped = re.sub(r"stroke-dasharray:[\d\s]+", "", stripped)    # dash patterns
        # Identifiers, not measurements: prompt levels (L0/L3), loop levels
        # (Level 2, LEVEL 4), and verifier versions (V1, V2).
        stripped = re.sub(r"\bL[0-4]\b", "", stripped)
        stripped = re.sub(r"\blevel [0-4]\b", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\bV[12]\b", "", stripped)
        assert not re.search(r"\d", stripped), (
            f"{path.relative_to(REPO_ROOT)} has a number in a diagram: "
            f"{re.findall(r'.{0,40}[0-9].{0,40}', stripped)[:3]}"
        )


# ---- commands ---------------------------------------------------------------


def _fenced_bash(path: Path) -> list[str]:
    return re.findall(r"^```bash\n(.*?)^```$", path.read_text(encoding="utf-8"),
                      re.DOTALL | re.MULTILINE)


@pytest.mark.parametrize("path", MARKDOWN, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_documented_python_entry_points_exist(path):
    """Every `demos/...py` or `tools/...py` named in a shell block must be a file.

    This is what catches a runbook naming a script that was renamed or removed —
    the failure mode that makes a runbook lie at minute forty of a live session.
    """
    for block in _fenced_bash(path):
        for script in re.findall(r"(?:demos|tools)/[\w/]+\.py", block):
            assert (REPO_ROOT / script).is_file(), (
                f"{path.relative_to(REPO_ROOT)} documents {script}, which does not exist"
            )


def test_every_documented_view_is_a_real_choice():
    """`--view` names in the docs must match what demos/views.py accepts."""
    from demos_views_choices import VIEWS  # noqa: F401  (see the fixture below)


@pytest.fixture(autouse=True, scope="module")
def _install_views_shim():
    """demos/ is not a package, so the view list is read from the source."""
    source = (REPO_ROOT / "demos" / "views.py").read_text(encoding="utf-8")
    match = re.search(r"^VIEWS = \(([^)]*)\)", source, re.MULTILINE)
    views = tuple(re.findall(r'"([a-z]+)"', match.group(1)))
    module = type(sys)("demos_views_choices")
    module.VIEWS = views
    sys.modules["demos_views_choices"] = module
    yield
    del sys.modules["demos_views_choices"]


def test_documented_views_match_the_entry_point():
    from demos_views_choices import VIEWS

    body = README.read_text(encoding="utf-8")
    documented = re.search(r"--view \{([a-z,]+)\}", body)
    assert documented, "the README does not document the view choices"
    assert set(documented.group(1).split(",")) == set(VIEWS)


def test_the_lint_rule_and_chart_renderer_are_documented():
    """Both are invoked in CI or by the checklist; a reader must be able to find
    them from the README alone."""
    body = README.read_text(encoding="utf-8")
    assert "tools/lint_no_numbers.py" in body
    assert "tools/render_readme_charts.py" in body
    assert "tools/sync_hf.py" in body


def test_the_readme_prose_names_no_measurement():
    """Numbers live inside the self-labelling images, not in prose.

    Dates, version numbers, section numbers and table rows are structure rather
    than findings, so the check is aimed at what a finding actually looks like:
    a percentage, a p-value, or a dollar figure.
    """
    body = README.read_text(encoding="utf-8")
    body = re.sub(r"^\s*\|.*\|\s*$", "", body, flags=re.MULTILINE)   # tables
    body = re.sub(r"```.*?```", "", body, flags=re.DOTALL)           # code
    body = re.sub(r"\[[^\]]*\]\([^)]*\)", "", body)                  # links
    offenders = re.findall(r"\d+(?:\.\d+)?\s?%|\bp\s?[=<]\s?0?\.\d+|\$\s?\d", body)
    assert not offenders, f"README prose states a measurement: {offenders}"


def test_the_offline_suite_command_is_what_ci_runs():
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for command in ("uv run ruff check .", "uv run pytest -q",
                    "uv run python tools/lint_no_numbers.py"):
        assert command in ci, f"CI does not run {command!r}"
        assert command in README.read_text(encoding="utf-8"), (
            f"the README does not document {command!r}, which CI runs"
        )


def test_git_tracks_no_file_under_a_removed_directory():
    """`scripts/` and `app/` are removed and must stay that way.

    `docs/` was on this list and has been taken off it deliberately: the
    directory exists again and holds the audit record, which is tracked on
    purpose. Leaving it here would have been a rule kept past its reason —
    and this suite would then be asserting the absence of files that other
    tests in it require to be present.
    """
    tracked = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, cwd=REPO_ROOT,
    ).stdout.split()
    for path in tracked:
        assert not path.startswith(("scripts/", "app/")), (
            f"{path} is still tracked but its directory was removed"
        )


# ---- a citation printed as provenance must resolve ---------------------------
#
# `sweep/orchestrator.py` printed "a 16.2% floor (results/noise_floor_*.json)" to the
# room before the first cell ran, and no such file existed in the repo — the artifact
# was on the author's machine and .gitignore dropped it. A citation that resolves to
# nothing is the same defect class as the lint rule that pointed at a moved path and
# scanned nothing: it looks like evidence and cannot be checked.
#
# Extends the link-checking pattern above rather than starting a new one.

CITING_MODULES = (
    "src/loopeng/sweep/orchestrator.py",
    "src/loopeng/sweep/reference.py",
)

# Paths these modules WRITE rather than cite. A chart directory that does not exist yet
# is not a broken citation; it is an output. Enumerated, so adding one is deliberate.
WRITTEN_NOT_CITED = frozenset({
    "results/sweep",       # live cell output, gitignored by design — a fresh clone has none
    "results/charts",      # where the chart PNGs are written
})


def _repo_paths_in_strings(path: Path) -> set[str]:
    """Every `results/...`-shaped string constant in a module, docstrings included.

    Docstrings count here, unlike in the numeric-literal rule: a path named in a
    docstring is still a citation a reader will try to follow.
    """
    import ast

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            found.update(re.findall(r"results/[\w./*-]*[\w*]", node.value))
    return found


@pytest.mark.parametrize("module", CITING_MODULES)
def test_every_repo_path_named_in_the_sweep_modules_resolves(module):
    import glob

    path = REPO_ROOT / module
    for cited in sorted(_repo_paths_in_strings(path)):
        if cited in WRITTEN_NOT_CITED:
            continue
        matches = glob.glob(str(REPO_ROOT / cited))
        assert matches, (
            f"{module} names {cited!r}, which resolves to nothing. A citation printed "
            f"as provenance that does not exist looks like evidence and is not."
        )


def test_the_noise_floor_the_pre_registration_cites_is_committed():
    """It was gitignored, so every clone printed a citation to a missing file."""
    from loopeng.sweep.orchestrator import NOISE_FLOOR_PATH

    assert (REPO_ROOT / NOISE_FLOOR_PATH).is_file()
    tracked = subprocess.run(
        ["git", "ls-files", str(NOISE_FLOOR_PATH)],
        capture_output=True, text=True, cwd=REPO_ROOT,
    ).stdout.strip()
    assert tracked, f"{NOISE_FLOOR_PATH} exists locally but is not tracked"


def test_the_pre_registration_reads_the_floor_out_of_the_file_it_cites():
    """A number typed next to its own citation is the failure the section warns about."""
    import json

    from loopeng.sweep.orchestrator import NOISE_FLOOR_PATH, pre_registration

    body = json.loads((REPO_ROOT / NOISE_FLOOR_PATH).read_text())
    printed = pre_registration(50)

    assert str(NOISE_FLOOR_PATH) in printed
    assert str(body["n_disagreed"]) in printed
    assert str(body["n_items_identical_path"]) in printed
    # And the citation must not claim it was computed just now.
    assert "computed" not in printed.split("Measured justification")[1].split("\n\n")[0]


def test_an_absent_citation_says_so_rather_than_quoting_a_figure(monkeypatch):
    """If the file goes missing the line reports that, instead of a number nothing on
    disk supports."""
    from loopeng.sweep import orchestrator

    monkeypatch.setattr(orchestrator, "NOISE_FLOOR_PATH", Path("results/gone.json"))
    assert "NOT ON DISK" in orchestrator._noise_floor_reading()


def test_the_noise_floors_are_derived_from_committed_replicates():
    """They were typed as 3.3 and 18.8. Both are exactly what the committed data yields,
    so nothing measured changed — but they can no longer drift from their evidence."""
    from loopeng.sweep.reference import NOISE_FLOORS, noise_floors

    assert NOISE_FLOORS == noise_floors()
    for model, floor in NOISE_FLOORS.items():
        assert (REPO_ROOT / floor["derived_from"]).parent.is_dir()
        assert floor["n_replicates"] >= 2, f"{model} cannot measure variance from one run"


def test_a_single_replicate_reports_no_floor_rather_than_zero(tmp_path):
    """One replicate cannot measure run-to-run variance, and a zero would read as
    "this model is deterministic"."""
    import shutil

    from loopeng.sweep.reference import noise_floors

    source = REPO_ROOT / "results" / "prefix_v1" / "sweep"
    shutil.copy(source / "worker_L0_loop_r0.json", tmp_path / "worker_L0_loop_r0.json")

    assert noise_floors(tmp_path) == {}


# ---- committed probe output carries no credentials or identifiers ------------


def test_the_resume_probe_log_publishes_no_uuids():
    """It published a LangSmith organisation UUID, a dataset UUID and a session UUID in
    a public repository. Redacted in place rather than deleted, because results/gate0.json
    cites this path by name and must not change — a citation that stops resolving is the
    defect the lint rule and the pre-registration were both just fixed for."""
    uuid_shaped = re.compile(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
    )
    for name in ("_resume_first.log", "_resume_marker.txt"):
        body = (REPO_ROOT / "results" / name).read_text(encoding="utf-8")
        assert not uuid_shaped.findall(body), f"results/{name} still carries a UUID"


def test_the_redaction_says_what_was_removed_and_why():
    """A redacted artifact with no note is indistinguishable from a truncated one."""
    body = (REPO_ROOT / "results" / "_resume_first.log").read_text(encoding="utf-8")
    assert "REDACTED" in body
    assert "gate0.json" in body, "the note must say why the file stays at this path"


def test_the_finding_survives_the_redaction():
    """The evidence is what the target invocations show, not where the run was hosted."""
    body = (REPO_ROOT / "results" / "_resume_first.log").read_text(encoding="utf-8")
    assert "[target] invoked" in body
    assert "resume-probe-a" in body


def test_gate0_still_cites_files_that_exist():
    """It names the two probe artifacts, and it is committed evidence that must not be
    edited — so they have to keep resolving."""
    import json

    gate0 = json.loads((REPO_ROOT / "results" / "gate0.json").read_text(encoding="utf-8"))
    # Trailing punctuation is prose, not path. `[\w./-]+` swallowed the full stop
    # on a sentence ending in `results/_resume_first.log.` and reported a missing
    # file that was right there — a checker failing on grammar rather than on the
    # thing it checks.
    cited = [
        path.rstrip(".,;:")
        for path in re.findall(r"results/[\w./-]+", json.dumps(gate0))
    ]
    for path in sorted(set(cited)):
        assert (REPO_ROOT / path).exists(), f"results/gate0.json cites {path}, which is gone"


def test_no_committed_file_carries_an_api_key_shape():
    """A key in a public repo is unbounded spend by strangers."""
    import subprocess

    tracked = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, cwd=REPO_ROOT,
    ).stdout.split()
    key_shaped = re.compile(r"\b(?:sk-ant-|lsv2_)[A-Za-z0-9_-]{12,}")
    for name in tracked:
        path = REPO_ROOT / name
        if not path.is_file() or path.suffix in {".png", ".duckdb", ".lock"}:
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        assert not key_shaped.findall(body), f"{name} looks like it carries a credential"


def test_ci_asserts_the_single_key_journey():
    """F4: the check whose absence let a required LANGSMITH_API_KEY ship green. It has to
    live in the OFFLINE job — the property is that no network and no real key are needed."""
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "only ANTHROPIC_API_KEY can start" in ci
    assert "langsmith_api_key is None" in ci
    # And it must not have introduced a secret into a job that had none.
    assert "secrets." not in ci, "the offline job must need no secret"


def test_the_readme_documents_the_cloners_journey():
    """§11 was written for the author delivering a workshop. §11.0 is for someone who
    just cloned."""
    body = README.read_text(encoding="utf-8")
    assert "Run it on your own key" in body
    assert "--profile smoke" in body
    assert "--reference=compare" in body
    assert "LangSmith is optional" in body


def test_the_readme_states_that_no_chart_appears_without_live_calls():
    """The property is true and enforced and was never said to the reader."""
    body = README.read_text(encoding="utf-8")
    assert "without live Claude API calls" in body
    assert "--view exhibit" in body


def test_the_readme_quotes_the_real_deselected_count():
    """The README shows expected pytest output. Only part of it is worth pinning.

    The `passed` count moves every time a test is added — including when this test
    was added, which made the first version of it fail against the number it had
    just changed. Pinning it would force a README edit on every commit that adds a
    test, and the README already says the count moves.

    `deselected` is different. It is the five live-marked tests, it is stable, and
    the README makes a CLAIM about it — "5 deselected is correct, not a problem" —
    which would be wrong if the live suite grew and nobody noticed. That is the
    part a reader could be misled by, so that is the part asserted.
    """
    quoted = re.search(r"^(\d+) passed, (\d+) deselected$",
                       README.read_text(encoding="utf-8"), re.MULTILINE)
    assert quoted, "the README no longer shows an expected pytest summary line"

    collected = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-m", "live"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    ).stdout
    tally = re.search(r"(\d+)/(\d+) tests collected", collected)
    assert tally, f"could not read a collection tally from:\n{collected[-400:]}"

    live = int(tally.group(1))
    assert int(quoted.group(2)) == live, (
        f"README says {quoted.group(2)} deselected; there are {live} live tests"
    )
def test_no_identifier_shaped_uuid_survives_anywhere_in_history():
    """The check that was missing, and whose absence is the point.

    `.gitignore` states the identifiers in `results/_resume_first.log` were
    "REDACTED IN PLACE". They were — at HEAD. The redaction landed as an ordinary
    content edit, not a history rewrite, so three UUIDs stayed live in ten commits
    reachable from `main`, and the only test guarding the policy looked at the
    working tree. A rule enforced against HEAD alone is a rule that cannot see the
    thing it was written to prevent.

    This walks every blob in every reachable commit. It is the whole history, not
    a sample, and it costs about a second.

    If this fails after a rewrite, the rewrite did not take. If it fails on a new
    commit, something published an identifier — find it before pushing anywhere.
    """
    uuid_shaped = re.compile(
        rb"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    )

    blobs = subprocess.run(
        ["git", "rev-list", "--objects", "--all"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    ).stdout.splitlines()
    names = {}
    for entry in blobs:
        sha, _, path = entry.partition(" ")
        names[sha] = path

    kinds = subprocess.run(
        ["git", "cat-file", "--batch-check=%(objectname) %(objecttype)"],
        input="\n".join(names), capture_output=True, text=True, cwd=REPO_ROOT,
    ).stdout.split()

    offenders = []
    for sha, kind in zip(kinds[::2], kinds[1::2], strict=True):
        if kind != "blob":
            continue
        content = subprocess.run(
            ["git", "cat-file", "blob", sha],
            capture_output=True, cwd=REPO_ROOT,
        ).stdout
        if uuid_shaped.search(content):
            offenders.append(f"{names.get(sha, '?')} ({sha[:8]})")

    assert not offenders, (
        f"identifier-shaped UUIDs survive in history: {sorted(set(offenders))[:10]}"
    )

