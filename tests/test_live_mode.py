"""Live mode is off unless three things are true, and bounded even then."""

import pytest

from loopeng.usage import CallUsage
from loopeng.views.live_mode import (
    BudgetExhausted,
    LiveBudget,
    LiveRefused,
    read_config,
)

FULL = {
    "LOOPENG_LIVE": "1",
    "ANTHROPIC_API_KEY": "sk-ant-real",
    "LOOPENG_LIVE_CEILING_USD": "0.50",
}


def test_off_by_default():
    assert not read_config({}).enabled


def test_a_key_alone_does_not_enable_it():
    """A key can arrive for a dozen reasons that are not 'please spend it'."""
    assert not read_config({"ANTHROPIC_API_KEY": "sk-ant-real"}).enabled


def test_the_flag_alone_does_not_enable_it():
    assert not read_config({"LOOPENG_LIVE": "1"}).enabled


def test_it_refuses_rather_than_defaulting_the_ceiling():
    """Live with no ceiling is not a configuration this accepts. Defaulting to a
    number nobody chose would be worse than refusing."""
    config = read_config({"LOOPENG_LIVE": "1", "ANTHROPIC_API_KEY": "sk-ant-real"})
    assert not config.enabled
    assert "ceiling" in config.reason.lower()


def test_the_exhibit_placeholder_key_does_not_count():
    """The Space sets a placeholder so settings validate. It must not read as real."""
    config = read_config({**FULL, "ANTHROPIC_API_KEY": "exhibit-no-live-calls"})
    assert not config.enabled


def test_a_nonsense_or_negative_ceiling_refuses():
    assert not read_config({**FULL, "LOOPENG_LIVE_CEILING_USD": "lots"}).enabled
    assert not read_config({**FULL, "LOOPENG_LIVE_CEILING_USD": "0"}).enabled
    assert not read_config({**FULL, "LOOPENG_LIVE_CEILING_USD": "-1"}).enabled


def test_all_three_together_enable_it():
    config = read_config(FULL)
    assert config.enabled
    assert config.ceiling_usd == 0.50


# ---- the bound is checked BEFORE spending ----------------------------------


def test_a_disabled_budget_refuses_every_call():
    budget = LiveBudget(read_config({}))
    with pytest.raises(LiveRefused):
        budget.check()


def test_the_call_ceiling_stops_it():
    budget = LiveBudget(read_config({**FULL, "LOOPENG_LIVE_MAX_CALLS": "2"}))
    budget.check()
    for _ in range(2):
        budget.record(CallUsage("claude-haiku-4-5", "ok", input_tokens=1, output_tokens=1))
    with pytest.raises(BudgetExhausted) as exc:
        budget.check()
    assert "call ceiling" in str(exc.value)


def test_the_spend_ceiling_stops_it():
    budget = LiveBudget(read_config({**FULL, "LOOPENG_LIVE_CEILING_USD": "0.001"}))
    budget.check()
    budget.record(CallUsage("claude-sonnet-5", "ok", input_tokens=100_000, output_tokens=100_000))
    with pytest.raises(BudgetExhausted):
        budget.check()


def test_a_failed_call_still_counts_against_the_ceiling():
    """Tokens bill whether or not the answer shipped, so an errored call must not be
    a free retry."""
    budget = LiveBudget(read_config({**FULL, "LOOPENG_LIVE_MAX_CALLS": "1"}))
    budget.record(CallUsage("claude-haiku-4-5", "error", input_tokens=500, output_tokens=200))
    with pytest.raises(BudgetExhausted):
        budget.check()


def test_the_meter_renders_both_bounds():
    budget = LiveBudget(read_config(FULL))
    budget.record(CallUsage("claude-haiku-4-5", "ok", input_tokens=1000, output_tokens=500))
    rendered = budget.render()
    assert "est. $" in rendered and "of $0.50" in rendered and "1 of" in rendered


def test_the_summary_says_plainly_when_live_is_off():
    assert "Live calls are off" in read_config({}).summary


# ---- the docs say this is not wired; that must stay true or stop being said ---


def test_no_entry_point_calls_the_live_mode_guard():
    """SECURITY.md, README.md, ONBOARDING.md and demos/ONBOARDING-views.md all now
    state plainly that this module is not wired to anything and that its three
    environment variables are inert.

    That is a security claim, so it is checked rather than trusted. If live mode is
    ever wired up, this fails and every one of those four documents must be
    corrected in the same change — which is the point. A security claim that
    silently becomes false is worse than no claim.
    """
    import pathlib

    root = pathlib.Path(__file__).resolve().parent.parent
    callers = []
    for directory in ("src", "demos", "tools", "deploy"):
        for path in (root / directory).rglob("*.py"):
            if path.name == "live_mode.py":
                continue
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if line.lstrip().startswith("#"):
                    continue
                if "read_config(" in line or "LiveBudget(" in line:
                    callers.append(f"{path.relative_to(root)}:{n}")
    assert not callers, (
        f"live_mode is now wired at {callers}. Update SECURITY.md, README.md's env "
        f"table, ONBOARDING.md's env table and demos/ONBOARDING-views.md — all four "
        f"currently tell readers the guard is inert."
    )


def test_security_md_does_not_present_the_guard_as_an_active_control():
    import pathlib

    body = (pathlib.Path(__file__).resolve().parent.parent / "SECURITY.md").read_text(
        encoding="utf-8"
    )
    assert "There is no spend guard in this build" in body
    assert "Do not rely on one" in body
