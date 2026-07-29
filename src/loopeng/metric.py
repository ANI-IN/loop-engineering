"""The only way a measured number enters this project.

Two properties matter. First, a Metric cannot exist without its n — the interval
is computed from counts rather than passed in, so there is no way to assert a
precision you did not observe. Second, MetricStore.get raises rather than
returning a default, so a missing measurement renders as "not yet measured"
instead of as zero.

`source` distinguishes measurement from estimation. Token counts read off a
response are measured. Anything in dollars is estimated, because it is a token
count multiplied by a price table rather than billed usage — that is true of
LangSmith's cost figures and equally true of ours.
"""

import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, Self

# Two-sided 95% critical value. Inlined rather than pulled from scipy: one
# constant is cheaper to trust than a dependency, and the confidence level is
# fixed for the whole workshop, so there is nothing here to configure.
Z_95 = 1.959963984540054

Source = Literal["measured", "estimated"]


def _wilson(p: float, n: int) -> tuple[float, float]:
    """Wilson score interval for a proportion.

    The textbook normal approximation p ± z·sqrt(p(1-p)/n) is wrong in the regime
    this workshop actually runs in: at n=10 with p=0 it returns the degenerate
    interval [0, 0], and at p near the boundary it returns endpoints outside
    [0, 1]. Wilson stays inside the boundary and keeps width at p=0 and p=1,
    which is the difference between "we saw no failures" and "we cannot fail".
    """
    z2 = Z_95**2
    denominator = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denominator
    half = (Z_95 * math.sqrt(p * (1 - p) / n + z2 / (4 * n**2))) / denominator
    # At p=0 and p=1 the endpoints land exactly on the boundary analytically, so
    # the clamp is catching float error rather than a real excursion — but the
    # test asserting [0, 1] runs on floats, not on the algebra.
    return max(0.0, centre - half), min(1.0, centre + half)


def _render_time(moment: datetime) -> str:
    """Time of day, plus enough date to stop a stale number passing as fresh."""
    stamp = moment.strftime("%H:%M")
    if moment.date() == datetime.now().date():
        return f"{stamp} today"
    return f"{stamp} on {moment.date().isoformat()}"


def _render_number(value: float) -> str:
    if math.isfinite(value) and value == int(value):
        return f"{int(value):,}"
    return f"{value:,.2f}"


@dataclass(frozen=True)
class Metric:
    """A number that carries its own evidence: how many observations, computed when.

    Frozen because a metric is a record of something that happened. Mutating one
    after the fact would mean the interval and the value no longer agree, and
    nothing downstream could tell.
    """

    value: float
    n: int
    ci_low: float
    ci_high: float
    computed_at: datetime
    source: Source

    def __post_init__(self) -> None:
        # The factories check this first and say more. This backstop covers the
        # two paths that skip them: direct construction and load() of a results
        # file somebody hand-edited.
        if self.n < 1:
            raise ValueError(f"A metric needs at least one observation; got n={self.n}.")

    @classmethod
    def from_counts(
        cls,
        successes: int,
        n: int,
        *,
        source: Source = "measured",
        computed_at: datetime | None = None,
    ) -> Self:
        """A proportion and the interval implied by the counts behind it.

        The interval is not a parameter. Passing counts is the only way in, so a
        caller who has run three trials cannot report the precision of thirty.
        """
        if n < 1:
            raise ValueError(f"A proportion needs at least one trial; got n={n}.")
        if not 0 <= successes <= n:
            raise ValueError(f"successes must lie in [0, {n}]; got {successes}.")

        p = successes / n
        ci_low, ci_high = _wilson(p, n)
        return cls(
            value=p,
            n=n,
            ci_low=ci_low,
            ci_high=ci_high,
            computed_at=_now_if_none(computed_at),
            source=source,
        )

    @classmethod
    def from_value(
        cls,
        value: float,
        n: int,
        *,
        source: Source,
        computed_at: datetime | None = None,
    ) -> Self:
        """A non-proportion — seconds, bytes, tokens, dollars — with its n attached.

        The interval collapses onto the value. A mean latency does have sampling
        error, but computing it needs the spread of the samples, and this
        constructor is handed a single number; inventing an interval from a
        number that does not contain one would be exactly the unearned precision
        this module exists to prevent. n still travels with it, because "1.4s
        over 3 runs" and "1.4s over 300" are different claims.

        `source` is required here, with no default: everything that reaches this
        constructor has to be classified by hand, and dollars are always
        estimated.
        """
        if n < 1:
            raise ValueError(f"A metric needs at least one observation; got n={n}.")
        return cls(
            value=value,
            n=n,
            ci_low=value,
            ci_high=value,
            computed_at=_now_if_none(computed_at),
            source=source,
        )

    def render(self) -> str:
        """One line, carrying the number and everything needed to discount it."""
        prefix = "est. " if self.source == "estimated" else ""
        when = _render_time(self.computed_at)

        if self.ci_low == self.ci_high:
            # A collapsed interval means this is an observation, not an estimate
            # of a population parameter. Printing "±0.0" would advertise a
            # precision nobody computed.
            return f"{prefix}{_render_number(self.value)} (n={self.n}, computed {when})"

        # Wilson is asymmetric about p, so there is no single ± that is exact.
        # Reporting the wider arm bounds the error on both sides; reporting the
        # narrower one, or the mean of the two, would understate it.
        half = max(self.value - self.ci_low, self.ci_high - self.value)
        return f"{prefix}{self.value * 100:.1f}% (n={self.n}, ±{half * 100:.1f}, computed {when})"


def _now_if_none(computed_at: datetime | None) -> datetime:
    # Local and naive, to match the timestamps callers hand in and the local
    # "today" that render() compares against.
    return datetime.now() if computed_at is None else computed_at


def _as_json(metric: Metric) -> dict[str, object]:
    return {
        "value": metric.value,
        "n": metric.n,
        "ci_low": metric.ci_low,
        "ci_high": metric.ci_high,
        "computed_at": metric.computed_at.isoformat(),
        "source": metric.source,
    }


def _from_json(payload: dict[str, object]) -> Metric:
    return Metric(
        value=float(payload["value"]),
        n=int(payload["n"]),
        ci_low=float(payload["ci_low"]),
        ci_high=float(payload["ci_high"]),
        computed_at=datetime.fromisoformat(str(payload["computed_at"])),
        source=str(payload["source"]),
    )


class MetricStore:
    """Metrics under dotted keys, with no accessor that can invent a number.

    There is deliberately no `get_value(key, default=0.0)` and no `__getitem__`
    that shrugs. A view that asks for a metric which was never recorded gets a
    KeyError and has to decide what to print; the honest answer is "not yet
    measured", and the only way to make that the easy path is to make silence
    impossible.
    """

    def __init__(self, metrics: dict[str, Metric] | None = None) -> None:
        self._metrics: dict[str, Metric] = dict(metrics) if metrics else {}

    def get(self, key: str) -> Metric:
        try:
            return self._metrics[key]
        except KeyError:
            raise KeyError(
                f"No metric recorded for {key!r}. Recorded keys: {self.keys()}. "
                "Render this as 'not yet measured' — do not substitute a zero."
            ) from None

    def put(self, key: str, metric: Metric) -> None:
        self._metrics[key] = metric

    def keys(self) -> list[str]:
        # Sorted rather than insertion-ordered, so a report built from keys() and
        # a results file written by save() list their metrics in the same order.
        return sorted(self._metrics)

    def save(self, path: Path | str) -> None:
        """Write the store as JSON that diffs cleanly between runs.

        sort_keys and a fixed indent mean a re-run of the same experiment produces
        a byte-identical file, so `git diff` on results/ shows what moved and
        nothing else.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {key: _as_json(metric) for key, metric in self._metrics.items()}
        path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path | str) -> Self:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls({key: _from_json(payload) for key, payload in raw.items()})
