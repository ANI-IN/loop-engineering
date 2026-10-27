"""The outline check: the slide outline builds with no problems and equals the committed copy."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_outline.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_outline", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["check_outline"] = module
    spec.loader.exec_module(module)
    return module


check_outline = _load()

# A stand-in for slides/source/build.py: writes the outline it holds and prints its report.
FAKE_BUILD = """import sys
from pathlib import Path
Path(sys.argv[1]).write_bytes({outline!r})
print("slides: 1")
print("problems: {problems}")
raise SystemExit({code})
"""


def _tree(tmp_path: Path, built: bytes, committed: bytes | None, problems: int = 0) -> Path:
    build = tmp_path / "slides" / "source" / "build.py"
    build.parent.mkdir(parents=True)
    build.write_text(
        FAKE_BUILD.format(outline=built, problems=problems, code=1 if problems else 0),
        encoding="utf-8",
    )
    if committed is not None:
        (tmp_path / "slides" / "outline.md").write_bytes(committed)
    return tmp_path


def test_a_current_outline_passes() -> None:
    assert check_outline.outline_problems("x\nproblems: 0\n", "# Outline\n", "# Outline\n") == []


def test_a_build_with_problems_fails() -> None:
    found = check_outline.outline_problems("problems: 2\n", "# Outline\n", "# Outline\n")
    assert found == [
        "slides/source/build.py reports problems: fix the block modules, then run make outline"
    ]


def test_a_stale_outline_fails_and_shows_the_difference() -> None:
    found = check_outline.outline_problems(
        "problems: 0\n", "# Outline\nnew line\n", "# Outline\nold line\n"
    )
    assert len(found) == 1
    assert found[0].startswith("slides/outline.md is out of date: run make outline and commit it")
    assert "-old line" in found[0] and "+new line" in found[0]


def test_a_missing_outline_fails() -> None:
    found = check_outline.outline_problems("problems: 0\n", "# Outline\n", None)
    assert found == ["slides/outline.md is missing: run make outline and commit it"]


@pytest.mark.parametrize(
    ("built", "committed", "problems", "code"),
    [
        (b"# Outline\n", b"# Outline\n", 0, 0),
        (b"# Outline\n", b"# Outline\r\n", 0, 1),  # byte for byte: line endings count
        (b"# Outline\nnew\n", b"# Outline\nold\n", 0, 1),
        (b"# Outline\n", b"# Outline\n", 3, 1),
    ],
)
def test_main_builds_the_trees_own_outline(
    tmp_path: Path, built: bytes, committed: bytes, problems: int, code: int
) -> None:
    root = _tree(tmp_path, built, committed, problems)
    assert check_outline.main(["--root", str(root)]) == code
