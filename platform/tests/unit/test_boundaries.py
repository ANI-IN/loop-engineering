"""Boundaries the course depends on: no assignment's required change exists in class code, and
the spend ledger and secrets never sit inside the repository or the release tree."""

from __future__ import annotations

import re
import tomllib

import pytest
import yaml
from conftest import scan

from datapilot.observability import spend
from datapilot.settings import PLATFORM, REPO

# Each assignment's new capability, as patterns that must not appear in class code paths.
ASSIGNMENT_CAPABILITIES = {
    "Assignment 1: Agent loop (value lookup)": r"value[_ ]?lookup|lookup_value|resolve_value",
    "Assignment 2: Verification loop (clarify or abstain)": r"clarify[_ ]or[_ ]abstain|abstain",
    "Assignment 2: Verification loop (personal-data leak grader)": r"leak[_ ]grader|LeakGrader",
    "Assignment 3: Event loop (revenue anomaly alert)": r"anomal",
    "Assignment 4: Hill-climbing loop (repeat-customer family)": r"repeat[_ ]customer",
    "Assignment 4: Hill-climbing loop (minimum holdout rule)": r"min(imum)?_holdout",
}
CLASS_CODE = ["platform/src", "platform/packs", "platform/console", "platform/ops"]


def _grep(pattern: str) -> str:
    # Comments that name the assignment which builds the capability are allowed, and so are the
    # assignments' extension-point modules (extension.py in each loop), which
    # test_assignment_boundaries.py proves inert.
    lines = [
        ln
        for ln in scan(pattern, *CLASS_CODE)
        if "Assignment" not in ln and "/extension.py:" not in ln.replace("\\", "/")
    ]
    return "\n".join(lines)


@pytest.mark.parametrize("capability", sorted(ASSIGNMENT_CAPABILITIES))
def test_no_assignment_capability_exists_in_class_code(capability: str) -> None:
    assert _grep(ASSIGNMENT_CAPABILITIES[capability]) == ""


def test_the_class_benchmark_has_no_ambiguous_items() -> None:
    folder = PLATFORM / "packs" / "datapilot_us" / "benchmark"
    statuses = []
    for path in folder.glob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        items = data if isinstance(data, list) else data.get("items", [])
        statuses += [item.get("expected_status", "answered") for item in items]
    assert "needs_clarification" not in statuses


def test_the_spend_ledger_lives_outside_the_repository() -> None:
    assert REPO not in spend.DEFAULT_LEDGER.resolve().parents


def test_secrets_and_ledgers_are_not_in_the_release_allow_list() -> None:
    release = tomllib.loads((PLATFORM / "config" / "release.toml").read_text(encoding="utf-8"))
    included = " ".join(release["include"])
    assert '.env"' not in included and not re.search(r"(^|\s)\.env(\s|$)", included)
    assert "sqlite" not in included
