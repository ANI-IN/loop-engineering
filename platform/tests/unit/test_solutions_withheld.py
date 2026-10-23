"""A public copy made before the Thursday review withholds the solutions, and its checks say so
instead of failing; the private build never withholds them (zero tokens; temporary trees only)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from datapilot.assignments import WITHHELD_LINE, solutions_withheld
from datapilot.names import SECTIONS_BY_SLUG

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


def _check_style():
    spec = importlib.util.spec_from_file_location("check_style", SCRIPTS / "check_style.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["check_style"] = module
    spec.loader.exec_module(module)
    return module


def _tree(root: Path, *, ignore_line: bool, solutions: bool) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / ".gitignore").write_text(
        ".env\n" + (WITHHELD_LINE + "\n" if ignore_line else ""), encoding="utf-8"
    )
    for section in SECTIONS_BY_SLUG.values():
        folder = root / section.folder / "assignment"
        folder.mkdir(parents=True)
        if solutions:
            (folder / "solution").mkdir()
            (folder / "solution" / "SOLUTION.md").write_text("# Solution\n", encoding="utf-8")
    return root


@pytest.mark.parametrize(
    ("ignore_line", "solutions", "withheld"),
    [(True, False, True), (False, False, False), (True, True, False), (False, True, False)],
)
def test_only_a_public_copy_without_solutions_withholds_them(
    tmp_path: Path, ignore_line: bool, solutions: bool, withheld: bool
) -> None:
    tree = _tree(tmp_path, ignore_line=ignore_line, solutions=solutions)
    assert solutions_withheld(tree) is withheld


def test_the_page_check_requires_solutions_unless_they_are_withheld(tmp_path: Path) -> None:
    check_style = _check_style()
    private = _tree(tmp_path / "private", ignore_line=False, solutions=False)
    public = _tree(tmp_path / "public", ignore_line=True, solutions=False)

    def needs_solution(root: Path) -> bool:
        return any("SOLUTION.md" in p.message for p in check_style.section_problems(root))

    assert needs_solution(private), "the private build still requires every SOLUTION.md"
    assert not needs_solution(public), "the public copy withholds them until the Thursday review"
