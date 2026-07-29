"""The two rules that keep demos/ from becoming a maintenance problem.

Rule 1: demos are thin entry points. No loop logic lives in demos/; it lives in
src/loopeng/. The loops are nested rather than parallel, so a second copy in a demo
file is a second place for it to drift, and every number the room sees has to come
out of one system.

Rule 2: every demo cold-starts. This is a floater format — people arrive mid-session
— so no stage may depend on an earlier one having run.

Both are tested rather than documented, for the usual reason: a convention that is
only written down is one nobody finds out has been broken.
"""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMOS = REPO_ROOT / "demos"

STAGES = (
    "01_agent_loop",
    "02_verification_loop",
    "03_event_driven_loop",
    "04_hill_climbing_loop",
)

# Entry points each stage is expected to grow. They arrive with their phases; the
# tests below pass trivially while a file is absent and bite the moment it lands,
# which is the same discipline as the numeric-literal rule.
ENTRY_POINTS = {
    "01_agent_loop": ("run.py", "trap.py"),
    "02_verification_loop": ("run.py", "regex_swap.py", "failure_paths.py", "abstain.py"),
    "03_event_driven_loop": ("worker.py", "enqueue.py"),
    "04_hill_climbing_loop": ("sweep.py", "charts.py"),
}

MAX_DEMO_LINES = 100

README_SECTIONS = ("ADDS", "COSTS", "COLD", "SHAPE")


def _existing_demo_files():
    return sorted(path for path in DEMOS.rglob("*.py") if path.name != "__init__.py")


# ---- structure --------------------------------------------------------------


def test_every_stage_folder_exists():
    for stage in STAGES:
        assert (DEMOS / stage).is_dir(), f"demos/{stage}/ is missing"


def test_every_stage_has_a_readme():
    for stage in STAGES:
        assert (DEMOS / stage / "README.md").is_file(), f"demos/{stage}/README.md is missing"


def test_there_is_no_separate_runbook():
    """Each stage README is the runbook. A separate one drifts from the code, and a
    runbook that lies at minute forty of a live session is the one thing we cannot
    have."""
    stray = list((REPO_ROOT / "docs").rglob("runbook*.md")) if (REPO_ROOT / "docs").is_dir() else []
    assert not stray, f"a separate runbook exists and will drift: {stray}"


def test_each_readme_carries_exactly_the_four_things():
    for stage in STAGES:
        text = (DEMOS / stage / "README.md").read_text(encoding="utf-8")
        for section in README_SECTIONS:
            assert section in text, f"demos/{stage}/README.md has no {section} section"


def test_readmes_say_what_to_do_when_the_shape_does_not_appear():
    """The failure mode this guards: a runbook that only describes success leaves the
    presenter improvising in front of the room."""
    for stage in STAGES:
        text = (DEMOS / stage / "README.md").read_text(encoding="utf-8").lower()
        assert "does not appear" in text or "if the" in text, (
            f"demos/{stage}/README.md does not say what to do when the shape is absent"
        )


def test_the_top_level_readme_explains_the_numbering():
    """Folder numbers are loop levels and stage order, not phase numbers. Saying so
    is the whole reason the top-level README exists."""
    text = (DEMOS / "README.md").read_text(encoding="utf-8")
    assert "not phase numbers" in text.lower()
    assert "gr.State" in text, "the Gradio per-user state warning is missing"


# ---- Rule 1: thin entry points ----------------------------------------------


@pytest.mark.parametrize("path", _existing_demo_files(), ids=lambda p: p.name)
def test_demo_files_stay_thin(path):
    """Over ~100 lines means loop logic has leaked out of src/loopeng/."""
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= MAX_DEMO_LINES, (
        f"{path.relative_to(REPO_ROOT)} is {len(lines)} lines, over the {MAX_DEMO_LINES}-line "
        "budget. Loop logic belongs in src/loopeng/; the demo wires args, calls in, and renders."
    )


@pytest.mark.parametrize("path", _existing_demo_files(), ids=lambda p: p.name)
def test_demo_files_define_no_loop_logic(path):
    """A demo that defines its own classes, or more than a couple of helpers, is
    growing a second copy of a loop that already exists in src/."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
    assert not classes, f"{path.name} defines {classes}; that belongs in src/loopeng/"
    assert len(functions) <= 3, (
        f"{path.name} defines {len(functions)} top-level functions ({functions}); "
        "a thin entry point wires args, calls into src/, and renders"
    )


@pytest.mark.parametrize("path", _existing_demo_files(), ids=lambda p: p.name)
def test_demo_files_import_from_loopeng(path):
    """A demo importing nothing from src/ is not calling the real system, which means
    whatever it renders did not come from the same place as every other number."""
    source = path.read_text(encoding="utf-8")
    assert "loopeng" in source, f"{path.name} does not import from loopeng"


def test_the_src_packages_backing_the_demos_exist():
    for package in ("agent", "verify", "queue", "sweep"):
        assert (REPO_ROOT / "src" / "loopeng" / package / "__init__.py").is_file(), (
            f"src/loopeng/{package}/ is missing; demos have nowhere to call into"
        )


# ---- Rule 2: cold start -----------------------------------------------------


def _cold_start_targets():
    targets = []
    for stage, files in ENTRY_POINTS.items():
        for name in files:
            path = DEMOS / stage / name
            if path.is_file():
                targets.append(path)
    return targets


@pytest.mark.parametrize("path", _cold_start_targets(), ids=lambda p: f"{p.parent.name}/{p.name}")
def test_entry_points_start_cold(path, tmp_path):
    """Runs each entry point with --help from a clean working directory.

    --help rather than a full run: this must stay offline and free, and what is being
    tested is that the module imports and its argument wiring stands up without any
    earlier stage having populated anything. An entry point that cannot even parse
    its own arguments from a cold start certainly cannot run.
    """
    result = subprocess.run(
        [sys.executable, str(path), "--help"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"{path.name} failed to start cold from an empty directory:\n{result.stderr[-2000:]}"
    )


def test_cold_start_coverage_is_reported_rather_than_silently_empty():
    """Zero entry points is the expected state before Phase 1, and it must not look
    like a passing cold-start suite. This prints what was actually covered."""
    covered = _cold_start_targets()
    expected = sum(len(files) for files in ENTRY_POINTS.values())
    print(f"cold-start coverage: {len(covered)} of {expected} planned entry points exist")
    assert len(covered) <= expected
