"""The style tools run on this repository, and the checker's templates match docs/STYLE.md."""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "platform" / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module  # dataclasses look their module up by name
    spec.loader.exec_module(module)
    return module


def test_style_check_has_no_errors() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "check_style.py")],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_prose_lint_is_clean() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "lint_prose.py")],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_templates_match_the_style_guide() -> None:
    check_style = _load("check_style")
    text = (REPO / "docs" / "STYLE.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```markdown skeleton:([a-z-]+)\n(.*?)```", text, re.S)
    found = {kind: re.findall(r"^## (.+)$", body, re.M) for kind, body in blocks}
    assert found == check_style.TEMPLATES


def test_section_names_come_from_the_config() -> None:
    check_style = _load("check_style")
    sections = check_style.CONFIG["sections"]
    assert check_style.NAMES["Section"] == {s["number"]: s["name"] for s in sections}
    for section in sections:
        assert (REPO / f"section-{section['number']}-{section['slug']}").is_dir()
