"""Every name the course shows: sections, autonomy levels, business rules, traps, agents.

The single source for prose names. docs/STYLE.md and platform/config/course.toml mirror the section
list, and a unit test keeps them equal. Demo and planted-item names live in
their registries (platform/demos/registry.yaml, platform/planted/registry.yaml).
"""

from __future__ import annotations

from dataclasses import dataclass

# No number: the module's place in the program is not fixed yet; it follows Harness Engineering.
MODULE_NAME = "Loop Engineering"
MODULE_TITLE = f"Module: {MODULE_NAME}"
PREVIOUS_MODULE = "the Harness Engineering module"


@dataclass(frozen=True)
class Section:
    number: int
    name: str
    slug: str

    @property
    def title(self) -> str:
        return f"Section {self.number}: {self.name}"

    @property
    def assignment_title(self) -> str:
        return f"Assignment {self.number}: {self.name}"

    @property
    def folder(self) -> str:
        return f"section-{self.number}-{self.slug}"


SECTIONS: tuple[Section, ...] = (
    Section(1, "Agent loop", "agent-loop"),
    Section(2, "Verification loop", "verification-loop"),
    Section(3, "Event loop", "event-loop"),
    Section(4, "Hill-climbing loop", "hill-climbing-loop"),
)
SECTIONS_BY_SLUG = {s.slug: s for s in SECTIONS}

# Autonomy level identifier -> the name shown in prose and on the console.
AUTONOMY_LEVEL_NAMES = {
    "report_only": "report-only level",
    "assisted": "assisted level",
    "unattended": "unattended level",
}

BUSINESS_RULES = (
    "Fiscal year",
    "Money in cents",
    "Net revenue",
    "Cancelled orders",
    "Eastern business days",
    "Internal accounts",
)

TRAPS = (
    "Fiscal year",
    "Net revenue",
    "Cancelled orders",
    "Eastern time",
    "Internal accounts",
)

# Agent identifier -> the name in prose. The router is listed because the course names it, and
# it is deliberately not an agent.
AGENT_NAMES = {
    "analyst": "the analyst",
    "schema_scout": "the schema scout",
    "reviewer": "the reviewer",
    "router": "the router",
    "failure_analyst": "the failure analyst",
    "rule_writer": "the rule writer",
    "critic": "the critic",
}


def business_rule_title(number: int) -> str:
    return f"Business rule {number}: {BUSINESS_RULES[number - 1]}"


def trap_title(number: int) -> str:
    return f"Trap {number}: {TRAPS[number - 1]}"
