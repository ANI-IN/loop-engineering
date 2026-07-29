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
