"""The event loop names the starting knowledge itself, since it never imports the hill-climbing
loop; the two names must agree (zero tokens)."""

from datapilot.loop3_events import commands
from datapilot.loop4_hill_climbing import versions


def test_the_event_loop_and_the_hill_climbing_loop_start_from_the_same_version() -> None:
    assert commands.STARTING_VERSION == versions.STARTING_VERSION
