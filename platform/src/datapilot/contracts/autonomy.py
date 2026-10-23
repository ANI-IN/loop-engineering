"""Autonomy levels and the policy that applies them per metric family."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from datapilot.names import AUTONOMY_LEVEL_NAMES


class AutonomyLevel(StrEnum):
    REPORT_ONLY = "report_only"  # answers posted labelled unverified; no exports
    ASSISTED = "assisted"  # answers posted; personal data and exports need human approval
    UNATTENDED = "unattended"  # unattended posting for eligible metric families only

    @property
    def label(self) -> str:
        return AUTONOMY_LEVEL_NAMES[self.value]


class DemotionReason(StrEnum):
    HOLDOUT_REGRESSION = "holdout_regression"
    BUDGET_EXHAUSTED = "budget_exhausted"
    CONSECUTIVE_ESCALATIONS = "consecutive_escalations"
    KILL_SWITCH = "kill_switch"


class AutonomyPolicy(Protocol):
    def level_for(self, metric_family: str | None) -> AutonomyLevel:
        """The level that applies to one run, after the global level and family eligibility."""
        ...

    def needs_approval(self, metric_family: str | None, *, personal_data: bool) -> bool: ...
