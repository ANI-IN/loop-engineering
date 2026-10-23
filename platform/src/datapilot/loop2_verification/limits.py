"""The retry cap: how many attempts a run gets before it ends escalated."""

from __future__ import annotations

from datapilot.planted import planted


def attempt_allowed(attempt: int, max_retries: int) -> bool:
    """Whether attempt number `attempt` (1-based) may start. limits.max_retries attempts in all."""
    if planted("BUG_NO_RETRY_CAP"):
        return True  # planted: no cap, so a failing grader loops until something else stops it
    return attempt <= max_retries
