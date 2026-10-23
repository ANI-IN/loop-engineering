"""The release list covers every top-level folder; the checkers scan every public page folder."""

from __future__ import annotations

import fnmatch
import importlib.util
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RELEASE = tomllib.loads((REPO / "platform/config/release.toml").read_text(encoding="utf-8"))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "platform/scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _listed(name: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(name + "/", p) or fnmatch.fnmatch(name, p) for p in patterns)


def test_every_top_level_folder_is_included_or_excluded() -> None:
    unknown = [
        p.name
        for p in REPO.iterdir()
        if p.is_dir()
        and p.name not in {".git", ".venv", ".pytest_cache", ".ruff_cache", ".import_linter_cache"}
        and not _listed(p.name, RELEASE["include"] + RELEASE["exclude"])
    ]
    assert unknown == []


def test_the_checkers_scan_every_public_page_folder() -> None:
    check_style = _load("check_style")
    lint_prose = _load("lint_prose")
    for folder in RELEASE["pages"]:
        if folder == "section-*":
            continue  # both tools find the section folders by name
        assert folder in check_style._DEFAULT_DIRS, folder
        assert folder in lint_prose.DEFAULT_TARGETS, folder
        assert _listed(folder, RELEASE["include"]), folder
