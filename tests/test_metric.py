from datetime import datetime

import pytest

from loopeng.metric import Metric, MetricStore


def test_wilson_interval_brackets_the_point_estimate():
    m = Metric.from_counts(successes=12, n=25)
    assert m.ci_low < m.value < m.ci_high


def test_wilson_interval_narrows_as_n_grows():
    """The noise floor shrinking with n is the thing the room watches happen live."""
    narrow = Metric.from_counts(successes=500, n=1000)
    wide = Metric.from_counts(successes=5, n=10)
    assert (narrow.ci_high - narrow.ci_low) < (wide.ci_high - wide.ci_low)


def test_wilson_interval_stays_inside_zero_and_one():
    """The normal approximation goes out of bounds at the small n this workshop
    actually runs. Wilson is chosen for exactly that reason."""
    for successes, n in ((0, 10), (10, 10), (1, 3), (0, 1), (1, 1)):
        m = Metric.from_counts(successes=successes, n=n)
        assert 0.0 <= m.ci_low <= m.ci_high <= 1.0


def test_zero_n_is_rejected():
    """A metric with no observations is not a metric."""
    with pytest.raises(ValueError):
        Metric.from_counts(successes=0, n=0)


def test_successes_outside_n_is_rejected():
    with pytest.raises(ValueError):
        Metric.from_counts(successes=11, n=10)
    with pytest.raises(ValueError):
        Metric.from_counts(successes=-1, n=10)


def test_metric_is_frozen():
    m = Metric.from_counts(successes=1, n=4)
    with pytest.raises(Exception):  # noqa: B017
        m.value = 0.9


def test_render_carries_n_and_time():
    m = Metric.from_counts(successes=3, n=25, computed_at=datetime(2026, 7, 29, 14, 22))
    rendered = m.render()
    assert "n=25" in rendered
    assert "14:22" in rendered
    assert "±" in rendered


def test_estimated_renders_with_a_visible_prefix():
    """An estimate that renders like a measurement is the specific dishonesty this
    field exists to prevent."""
    assert Metric.from_value(0.42, n=8, source="estimated").render().startswith("est. ")
    assert not Metric.from_value(0.42, n=8, source="measured").render().startswith("est. ")


def test_from_value_collapses_the_interval():
    """Seconds and byte counts are observations, not estimates of a population
    parameter. Inventing an interval here would be unearned precision."""
    m = Metric.from_value(1.5, n=3, source="measured")
    assert m.ci_low == m.ci_high == m.value


def test_from_value_rejects_zero_n():
    with pytest.raises(ValueError):
        Metric.from_value(1.0, n=0, source="measured")


def test_store_raises_on_missing_key():
    """There is no bare-value accessor and no default, so a view cannot silently
    render a zero where a measurement is absent."""
    store = MetricStore()
    with pytest.raises(KeyError):
        store.get("l0.loop.haiku.silent_error_rate")


def test_store_round_trips(tmp_path):
    store = MetricStore()
    store.put("a.b", Metric.from_counts(successes=1, n=4))
    store.put("c.d", Metric.from_value(2.5, n=9, source="estimated"))
    path = tmp_path / "m.json"
    store.save(path)

    reloaded = MetricStore.load(path)
    assert reloaded.get("a.b").n == 4
    assert reloaded.get("c.d").source == "estimated"
    assert reloaded.get("c.d").value == 2.5
    assert reloaded.keys() == ["a.b", "c.d"]


def test_store_save_creates_parent_directories(tmp_path):
    store = MetricStore()
    store.put("a", Metric.from_counts(successes=1, n=2))
    store.save(tmp_path / "nested" / "deep" / "m.json")
    assert (tmp_path / "nested" / "deep" / "m.json").exists()


def test_the_interval_always_contains_its_own_value():
    """It did not, at the boundaries, and the failure was invisible until something
    drew it.

    At 60/60 the Wilson arithmetic returned ci_high = 0.9999999999999998 — two ulps
    below a value of 1.0 — so the interval excluded its own point estimate. Both
    round to the same percentage, so nothing that rendered a string could see it.
    `ci_high - value` went negative, and matplotlib refuses a negative error bar, so
    the first chart to draw one on a boundary observation was the first thing to
    notice.
    """
    for n in (1, 8, 60, 137, 1000):
        for successes in (0, 1, n - 1, n):
            if not 0 <= successes <= n:
                continue
            metric = Metric.from_counts(successes, n)
            assert metric.ci_low <= metric.value <= metric.ci_high, (
                f"{successes}/{n}: interval "
                f"[{metric.ci_low!r}, {metric.ci_high!r}] excludes {metric.value!r}"
            )


def test_error_bar_arms_are_never_negative():
    """The consumer's form of the property above, written the way a chart writes it.

    Asserting the ordering is not quite the same as asserting the subtraction, and it
    is the subtraction that matplotlib rejects.
    """
    for n in (1, 12, 60, 500):
        for successes in (0, n):
            metric = Metric.from_counts(successes, n)
            assert metric.value - metric.ci_low >= 0
            assert metric.ci_high - metric.value >= 0
