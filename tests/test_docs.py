"""The documentation, checked rather than trusted.

Three failure modes this guards against, all of which have already happened here:

  - a relative link that stopped resolving after a file moved
  - a command in a README that no longer parses
  - a diagram copied into two places and then edited in one of them
"""

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


def _relative_links(path: Path) -> list[str]:
    body = path.read_text(encoding="utf-8")
    targets = re.findall(r"(?<!\!)\[[^\]]*\]\(([^)]+)\)", body)
    targets += re.findall(r"!\[[^\]]*\]\(([^)]+)\)", body)
    return [
        target for target in targets
        if not target.startswith(("http://", "https://", "mailto:", "#"))
    ]


@pytest.mark.parametrize("path", MARKDOWN, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_every_relative_link_resolves(path):
    for target in _relative_links(path):
        resolved = (path.parent / target.split("#")[0]).resolve()
        assert resolved.exists(), (
            f"{path.relative_to(REPO_ROOT)} links to {target}, which does not exist"
        )


def test_no_markdown_points_at_a_file_in_a_deleted_directory():
    """`docs/`, `scripts/` and `app/` are gone.

    Aimed at *paths*, not at the words: `demos/README.md` says there is no `docs/`
    directory, and that sentence is true and should stay. What must not survive is
    a reference to a file inside one of them.
    """
    stale = re.compile(r"`(?:docs|scripts|app)/[\w./-]+\.\w+`")
    for path in MARKDOWN:
        found = stale.findall(path.read_text(encoding="utf-8"))
        assert not found, (
            f"{path.relative_to(REPO_ROOT)} points at {found}, in a removed directory"
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
        assert "github.com/ANI-IN/loop-engineering-workshop" in body
        assert "cd loop-engineering-workshop" in body


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
    tracked = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, cwd=REPO_ROOT,
    ).stdout.split()
    for path in tracked:
        assert not path.startswith(("docs/", "scripts/", "app/")), (
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
    cited = re.findall(r"results/[\w./-]+", json.dumps(gate0))
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
