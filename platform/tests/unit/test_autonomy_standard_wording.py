"""The autonomy policy describes eligibility as the hill-climbing loop decides it: a family is
cleared on the gate's confirmed standard (eligibility.confirmed_clearance), never on one pass of
every holdout item in one experiment."""

from __future__ import annotations

from datapilot.loop3_events import autonomy

STANDARD = "confirmed standard"
WHERE = "eligibility.confirmed_clearance"


def _flat(text: str | None) -> str:
    return " ".join((text or "").split())


def test_the_module_docstring_names_the_confirmed_standard() -> None:
    doc = _flat(autonomy.__doc__)
    assert STANDARD in doc and WHERE in doc
    assert "passes 2 of 3 runs" in doc and "2 of 3 more runs" in doc
    assert "every benchmark item of the family passed on holdout" not in doc


def test_mark_eligible_names_the_confirmed_standard() -> None:
    doc = _flat(autonomy.mark_eligible.__doc__)
    assert STANDARD in doc and WHERE in doc
    assert "when every holdout item of a family passes." not in doc
