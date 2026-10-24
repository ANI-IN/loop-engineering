"""Where each trap shows in a query, for the annotated SQL.

The trap labels come from the run itself (the gold check's labels); this module only finds the
fragment of the SQL text each label points at, so the component can mark it and number its note.
It decides nothing: a query with no labels gets no marks. A label whose fragment cannot be found
in the text still gets its note, and the note then says plainly that no line is marked for it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# A calendar-year bound as the analyst writes it: a bare string or a typed DATE, TIMESTAMP, or
# TIMESTAMPTZ literal, with or without a time and an offset, and an optional cast. It is the
# literal the trap detector reads (a string starting with a year's 1 January or 31 December);
# the mark takes in the type keyword and the cast, so the whole bound is marked.
_TYPED = r"(?:\b(?:date|timestamptz|timestamp(?:\s+with(?:out)?\s+time\s+zone)?)\s+)?"
_CAST = r"(?:::\s*(?:date|timestamptz|timestamp)\b)?"
CALENDAR_BOUND = rf"(?i){_TYPED}'\d{{4}}-(?:01-01|12-31)\b[^']*'{_CAST}"


def _after(word: str, table: str) -> str:
    """A table named after FROM or JOIN, with or without its schema; only the table is marked."""
    return rf"(?i)\b{word}\s+(?P<m>(?:\w+\.)?{table})\b"


NO_MARK = "No line of this query is marked for this trap: its fragment was not found in the text."

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
            CALENDAR_BOUND,
            r"(?i)\bextract\s*\(\s*year\b[^)]*\)",
            r"(?i)\bdate_(?:trunc|part)\s*\(\s*'year'[^)]*\)",
            r"(?i)\byear\s*\([^)]*\)",
        ),
    ),
    "missing_status_filter": (
        "Cancelled orders",
        "Status 5 means cancelled, and cancelled orders never count; this query keeps them.",
        (_after("from", "orders"), _after("join", "orders")),
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
            _after("join", "customers"),
            _after("from", "customers"),
            r"(?i)\bwhere\b",
            _after("from", "orders"),
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
    overlap a fragment an earlier note already marked. A note with no fragment to mark says so
    (NO_MARK), so a numbered note never points at nothing."""
    taken: list[tuple[int, int, int]] = []
    notes = []
    for label in labels:
        if label not in TRAPS:
            continue
        trap, text, patterns = TRAPS[label]
        marks: list[tuple[int, int, int]] = []
        for pattern in patterns:
            for number, line in enumerate(lines):
                for found in re.finditer(pattern, line):
                    start, end = found.span("m" if "m" in found.re.groupindex else 0)
                    span = (number, start, end)
                    if not any(_overlaps(span, other) for other in taken + marks):
                        marks.append(span)
            if marks:
                break  # the first pattern that matches is the clearest mark
        taken += marks
        notes.append(Note(trap, text if marks else f"{text} {NO_MARK}", marks))
    return notes


def _overlaps(a: tuple[int, int, int], b: tuple[int, int, int]) -> bool:
    return a[0] == b[0] and a[1] < b[2] and b[1] < a[2]
