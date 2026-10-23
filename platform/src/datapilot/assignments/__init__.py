"""The live checks of the four assignments: `make check-assignment NAME=<slug>`.

Each check brings up the real stack, checks the deterministic requirements against the real
Postgres and services, prints its cost estimate, checks the OpenAI key, and then runs the
done-when scenario live: every step that involves the agent or a model calls the real OpenAI API.
Nothing here stands in for a model's output or reuses an earlier result. The per-assignment
scenario is section-N-<slug>/assignment/check.py; this package is the machinery they share.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from datapilot.names import SECTIONS_BY_SLUG
from datapilot.settings import REPO

VARIANTS = ("reference", "alternative-one", "alternative-two")


@dataclass(frozen=True)
class Assignment:
    slug: str
    title: str  # "Assignment 1: Agent loop"
    folder: Path  # section-1-agent-loop/assignment, inside the tree being checked

    @property
    def check_file(self) -> Path:
        return self.folder / "check.py"

    def solution(self, variant: str) -> Path:
        if variant not in VARIANTS:
            raise KeyError(f"unknown solution {variant!r}; use one of {', '.join(VARIANTS)}")
        return self.folder / "solution" / variant


# The public repository's .gitignore carries this line while the solutions are withheld: they are
# published at the start of the Thursday review.
WITHHELD_LINE = "section-*/assignment/solution/"
WITHHELD_REASON = "the solutions are published at the start of the Thursday review"


def solutions_withheld(tree: Path = REPO) -> bool:
    """True in a public copy made before the Thursday review: its .gitignore withholds the
    solutions and no solution folder is present. The private build never withholds them, so a
    missing solution there still fails every check that needs it."""
    ignore = tree / ".gitignore"
    if not ignore.is_file() or WITHHELD_LINE not in ignore.read_text(encoding="utf-8").split():
        return False
    return not any(
        (tree / s.folder / "assignment" / "solution").exists() for s in SECTIONS_BY_SLUG.values()
    )


def assignment(slug: str, tree: Path = REPO) -> Assignment:
    if slug not in SECTIONS_BY_SLUG:
        raise KeyError(f"unknown assignment {slug!r}; use one of {', '.join(SECTIONS_BY_SLUG)}")
    section = SECTIONS_BY_SLUG[slug]
    return Assignment(slug, section.assignment_title, tree / section.folder / "assignment")
