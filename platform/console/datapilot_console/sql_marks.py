"""Where each trap shows in a query, for the annotated SQL.

The trap labels come from the run itself (the gold check's labels); this module only finds the
fragment of the SQL text each label points at, so the component can mark it and number its note.
It decides nothing: a query with no labels gets no marks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# label -> (trap name shown on the note, the note, the fragments to mark)
TRAPS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "total_cents_used": (
        "Net revenue",
        "total_cents is what the customer was charged, tax and shipping included; net revenue "
        "is subtotal_cents minus discount_cents.",
        (r"\btotal_cents\b",),
    ),
    "calendar_year_range": (
        "Fiscal year",
        "The fiscal year runs from February 1 to January 31; fiscal year 2025 ends on "
        "31 January 2025, so a calendar-year range reads the wrong twelve months.",
        (
            r"'\d{4}-01-01'",
            r"'\d{4}-12-31'",
            r"(?i)extract\s*\(\s*year\b[^)]*\)",
            r"(?i)date_trunc\s*\(\s*'year'[^)]*\)",
        ),
    ),
    "missing_status_filter": (
        "Cancelled orders",
        "Status 5 means cancelled, and cancelled orders never count; this query keeps them.",
        (r"(?i)(?<=from )(?:warehouse\.)?orders\b", r"(?i)(?<=join )(?:warehouse\.)?orders\b"),
    ),
    "utc_truncation": (
        "Eastern time",
        "order_ts is stored in UTC; read it AT TIME ZONE 'America/New_York' before comparing "
        "it with a date.",
        (r"\border_ts\b",),
    ),
    "missing_internal_filter": (
        "Internal accounts",
        "Customers with an @harborpine.com email are staff and test accounts and are excluded; "
        "this query keeps them.",
        (
            r"(?i)(?<=join )(?:warehouse\.)?customers\b",
            r"(?i)(?<=from )(?:warehouse\.)?customers\b",
            r"(?i)\bwhere\b",
            r"(?i)(?<=from )(?:warehouse\.)?orders\b",
        ),
    ),
}


@dataclass(frozen=True)
class Note:
    trap: str
    text: str
    marks: list[tuple[int, int, int]]  # (line, start, end)


def annotate(lines: list[str], labels: list[str]) -> list[Note]:
    """One note per known label, in label order; each marks the label's fragments that do not
    overlap a fragment an earlier note already marked."""
    taken: list[tuple[int, int, int]] = []
    notes = []
    for label in labels:
        if label not in TRAPS:
            continue
        trap, text, patterns = TRAPS[label]
        marks = []
        for pattern in patterns:
            for number, line in enumerate(lines):
                for found in re.finditer(pattern, line):
                    span = (number, found.start(), found.end())
                    if not any(_overlaps(span, other) for other in taken + marks):
                        marks.append(span)
            if marks:
                break  # the first pattern that matches is the clearest mark
        taken += marks
        notes.append(Note(trap, text, marks))
    return notes


def _overlaps(a: tuple[int, int, int], b: tuple[int, int, int]) -> bool:
    return a[0] == b[0] and a[1] < b[2] and b[1] < a[2]
