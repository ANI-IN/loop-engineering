"""A fixed build budget for the tests of the spend mechanism (zero tokens)."""

from __future__ import annotations

import copy

from datapilot.config import pack_config
from datapilot.observability import spend

# A fixed allocation for the tests of the mechanism (lines, reserve, session), so they do not
# change each time the owner moves money between lines; the owner's own allocation is pinned by
# the two tests named "are the owners" in test_budget_lines.py, which read the real pack.
TEST_BUDGET = {
    "lines": {
        "development live checks": 1.50,
        "calibration": 2.20,
        "assignment verification": 2.80,
        "rehearsal": 2.50,
        "reserve": 1.00,
    },
    "session": {
        "total_usd": 2.35,
        "lines": {
            "development live checks": 0.30,
            "calibration": 0.95,
            "assignment verification": 1.10,
        },
    },
}


def with_test_budget(monkeypatch) -> None:  # a pytest MonkeyPatch
    """Point the spend module at the real pack with the build budget set to TEST_BUDGET."""
    real = copy.deepcopy(pack_config())
    budget = real["build_budget"]
    for name, cap in TEST_BUDGET["lines"].items():
        budget["lines"][name]["cap_usd"] = cap
    budget["total_usd"], budget["warn_usd"], budget["stop_usd"] = 10.0, 6.0, 10.0
    budget["session"]["total_usd"] = TEST_BUDGET["session"]["total_usd"]
    budget["session"]["lines"] = dict(TEST_BUDGET["session"]["lines"])
    monkeypatch.setattr(spend, "pack_config", lambda: real)
