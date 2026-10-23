"""Every folder the tool writes in a learner's copy is git-ignored, so `git status` stays clean."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
# Keep equal to the tool-output block of .gitignore; add a folder here when the tool starts
# writing one.
TOOL_OUTPUT_DIRS = [".runs/", "exports/", "guide/build/"]


def test_every_tool_output_folder_is_ignored() -> None:
    lines = {
        line.strip() for line in (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
    }
    missing = [folder for folder in TOOL_OUTPUT_DIRS if folder not in lines]
    assert missing == []
