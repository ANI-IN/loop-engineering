"""The content checksum the seeded warehouse must produce.

Asserted at startup on any ephemeral host. A Space whose filesystem was wiped
regenerates the warehouse from the seed in a fraction of a second, which is free — but
silently serving DIFFERENT data than the session would undermine every figure on the
page, and nothing about the failure would be visible. So it is checked rather than
assumed.

Regenerate this value only when the generator changes on purpose:

    uv run python -c "from loopeng.warehouse.generate import content_checksum; \
        print(content_checksum('warehouse.duckdb'))"
"""

from pathlib import Path

EXPECTED_CONTENT_CHECKSUM = "fde8f8fcb6fef7cccbaa94504064ca1e62e4ba809de53c647d4cc2a46de829d0"


class WarehouseMismatch(RuntimeError):
    """The regenerated warehouse does not match the one the measurements came from."""


def assert_matches(path: Path) -> str:
    from loopeng.warehouse.generate import content_checksum

    actual = content_checksum(path)
    if actual != EXPECTED_CONTENT_CHECKSUM:
        raise WarehouseMismatch(
            "the regenerated warehouse does not match the one these measurements were "
            f"taken against.\n  expected {EXPECTED_CONTENT_CHECKSUM}\n  actual   {actual}\n"
            "Every figure on this page was measured against the expected contents, so "
            "serving this one would make them wrong in a way nobody could see."
        )
    return actual
