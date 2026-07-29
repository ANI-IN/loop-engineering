"""Fixture: a view file that renders only through Metric. Must pass.

Exercises the structural uses of 0 and 1 that the rule must keep legal:
indexing, an off-by-one, and an early return.
"""

from loopeng.metric import MetricStore


def render(store: MetricStore, items: list[str]) -> str:
    if not items:
        return "not yet measured"
    first = items[0]
    rest = len(items) - 1
    metric = store.get("l0.loop.haiku.pass_rate")
    return f"{first} and {rest} more: {metric.render()}"
