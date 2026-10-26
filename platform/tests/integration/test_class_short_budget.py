"""The class morning with less than one class pass left of the day's tokens, on the tests' own
database (zero tokens): the refusal keeps the day-before rehearsal session open; the knowing start
(ACCEPT_TOKENS_LEFT, the exact count left) starts the class session and ends the rehearsal one; the
worker's cap is unchanged, so the day's count still blocks every run once it is reached."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta

import pytest

from datapilot import db
from datapilot.config import pack_config
from datapilot.contracts.live import SessionPurpose
from datapilot.loop3_events import budget, sessions
from datapilot.loop4_hill_climbing import preflight as checks
from datapilot.settings import get_settings

pytest_plugins = ["loops_fixtures"]
pytestmark = [pytest.mark.integration]

LEFT = 300_000  # less than budgets.class_pass_tokens (521,000)


@pytest.fixture
def rehearsed_today(clean_ops: None) -> Iterator[None]:
    """The day-before rehearsal session still open, and the Eastern time day's count at the cap
    minus LEFT, as after a rehearsal on the class's own Eastern time day. It needs clean_ops
    first, since clean_ops empties ops.budgets and ops.live_sessions."""
    sessions.start_session(SessionPurpose.REHEARSAL, "rehearsal", "UTC")
    cap = int(pack_config()["budgets"]["tokens_per_day"])
    with db.connect(db.Role.APP) as conn:
        budget.add_usage(conn, cap - LEFT)
        conn.commit()
    yield
    with db.connect(db.Role.APP) as conn:
        conn.execute("UPDATE ops.live_sessions SET ended_at = now() WHERE ended_at IS NULL")
        conn.commit()


def class_preflight(accepted_left: int | None) -> checks.Preflight:
    def tokens() -> tuple[checks.Check, str | None]:
        with db.connect(db.Role.APP) as conn:
            day = budget.today(conn)
        per_pass = int(pack_config()["budgets"]["class_pass_tokens"])
        return checks.budget_check(
            SessionPurpose.CLASS, day, per_pass, timedelta(hours=2), accepted_left
        )

    return checks.preflight(
        SessionPurpose.CLASS,
        get_settings(),
        canary=lambda: [checks.CanaryRun("product-count", "easy", True, "", None)],
        start_session=sessions.start_session,
        services=lambda: [checks.Check("postgres", True, "migrations applied")],
        budget=tokens,
        key=lambda: checks.Check("openai key", True, "stub-model"),
        install=lambda: [],
    )


def open_purpose() -> str | None:
    with db.connect(db.Role.APP) as conn:
        found = sessions.open_session(conn)
    return found.purpose.value if found else None


@pytest.mark.usefixtures("rehearsed_today")
def test_the_refusal_leaves_the_rehearsal_session_open_and_names_the_knowing_start() -> None:
    report = class_preflight(None)
    assert report.session is None and report.stopped is not None
    assert f"ACCEPT_TOKENS_LEFT={LEFT}" in report.stopped
    assert open_purpose() == "rehearsal"
    # a count other than the one left, such as one set on an earlier day, is refused the same way
    assert class_preflight(LEFT + 1).session is None and open_purpose() == "rehearsal"


@pytest.mark.usefixtures("rehearsed_today")
def test_the_knowing_start_opens_the_class_session_and_keeps_the_cap() -> None:
    report = class_preflight(LEFT)
    assert report.stopped is None and report.session is not None
    assert open_purpose() == "class"
    with db.connect(db.Role.APP) as conn:
        ended = conn.execute(
            "SELECT count(*) AS n FROM ops.live_sessions "
            "WHERE purpose = 'rehearsal' AND ended_at IS NOT NULL"
        ).fetchone()["n"]
        day = budget.today(conn)
        # the cap is the pack's: the knowing start changes no count and no limit
        assert (day.left, day.cap) == (LEFT, int(pack_config()["budgets"]["tokens_per_day"]))
        budget.add_usage(conn, LEFT)
        assert budget.exhausted(conn)  # the worker blocks every run from here on
        conn.rollback()
    assert ended == 1
