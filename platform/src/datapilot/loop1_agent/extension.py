"""Extension points of Assignment 1: Agent loop, the value lookup.

The class system calls every hook below on every run. Each hook is inert here, so class runs are
unchanged; the assignment fills them in (section-1-agent-loop/assignment/starter/README.md). The
course build's boundary test keeps this file in this state on the class branch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from langchain_core.tools import BaseTool

from datapilot.contracts import AnswerEnvelope
from datapilot.loop1_agent.tools import Warehouse

Kind = Literal["product", "category"]
# The tool name the analyst sees and the check looks for in each run's tool calls.
LOOKUP_TOOL_NAME = "find_exact_values"
# The most candidates one lookup may return: the result goes to the model, so it stays short.
MAX_CANDIDATES = 5


@dataclass(frozen=True)
class Candidate:
    value: str  # an exact value stored in the warehouse
    score: float  # closeness to the wording, from 0 (unrelated) to 1 (the same)


@dataclass(frozen=True)
class Lookup:
    """One lookup: the wording asked about, the closest exact values, and whether to ask."""

    kind: Kind
    wording: str
    candidates: list[Candidate] = field(default_factory=list)
    ambiguous: bool = False  # the top two candidates are equally close: ask, do not guess

    @property
    def best(self) -> str | None:
        return self.candidates[0].value if self.candidates and not self.ambiguous else None


@dataclass
class LookupLog:
    """Every lookup of one run, in order. The verification loop makes one per run."""

    lookups: list[Lookup] = field(default_factory=list)


# EXTENSION POINT, TODO 1 (agent-loop-1): the lookup itself.
def lookup_values(warehouse: Warehouse, kind: Kind, wording: str) -> Lookup:
    raise NotImplementedError(
        "agent-loop-1: return the exact product names or category names closest to the wording, "
        "at most MAX_CANDIDATES, read through warehouse.url (the read-only agent role)"
    )


# EXTENSION POINT, TODO 2 (agent-loop-2): the tools this assignment adds to the analyst.
def lookup_tools(warehouse: Warehouse, log: LookupLog) -> list[BaseTool]:
    # The class analyst has no lookup tool; return a tool named LOOKUP_TOOL_NAME that calls
    # lookup_values and appends each Lookup to log.lookups.
    return []


# EXTENSION POINT, TODO 3 (agent-loop-3): one more working-method step for the analyst's prompt.
WORKING_METHOD = ""


# EXTENSION POINT, TODO 4 (agent-loop-4): what the run records about the lookups it used.
def with_matches(envelope: AnswerEnvelope, log: LookupLog) -> AnswerEnvelope:
    # The class envelope is returned unchanged; record each match in envelope.assumptions.
    return envelope
