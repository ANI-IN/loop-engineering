"""Token accounting for every call, including the ones that failed.

Two things here exist to stop the loop looking cheaper than it is, because that
bias runs in one direction: it flatters Haiku-plus-a-loop against Sonnet one-shot,
which is precisely the comparison the workshop is built to make.

**Every call is counted.** A call that errored, timed out, or was cut off by the
budget still generated tokens and still bills. Recording only the calls that
produced a usable answer would drop exactly the retries a loop exists to make.

**Every token class is recorded.** Cache writes bill above base input and cache
reads well below it, so `input_tokens` alone is wrong on any cell where caching
fires. The four fields are kept separately all the way to the report.

Dollars carry `source="estimated"` forever — see loopeng.pricing.
"""

from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from loopeng.pricing import prices_for

Outcome = Literal["ok", "error", "timeout", "budget_exhausted"]


class UsageReconciliationError(RuntimeError):
    """A cell's totals do not equal the sum of its calls.

    Asserted rather than eyeballed: a per-call record that quietly fails to reach
    the cell total is how a sweep under-reports its own spend.
    """


@dataclass(frozen=True)
class CallUsage:
    """One request to one model. Recorded whether or not it produced an answer."""

    model_id: str
    outcome: Outcome
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    @classmethod
    def from_response(cls, model_id: str, response: Any, outcome: Outcome = "ok") -> "CallUsage":
        """Read all four fields off an Anthropic response.

        The cache fields are absent on responses where caching was not in play, and
        the SDK reports them as None rather than 0, so both are normalised here.
        """
        usage = getattr(response, "usage", None)

        def field_value(name: str) -> int:
            return int(getattr(usage, name, 0) or 0)

        return cls(
            model_id=model_id,
            outcome=outcome,
            input_tokens=field_value("input_tokens"),
            output_tokens=field_value("output_tokens"),
            cache_creation_input_tokens=field_value("cache_creation_input_tokens"),
            cache_read_input_tokens=field_value("cache_read_input_tokens"),
        )

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_creation_input_tokens
            + self.cache_read_input_tokens
        )

    def cost_usd(self) -> float:
        """Estimated. Never measured — see loopeng.pricing."""
        return prices_for(self.model_id).cost_usd(
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            cache_creation_input_tokens=self.cache_creation_input_tokens,
            cache_read_input_tokens=self.cache_read_input_tokens,
        )


@dataclass
class UsageLedger:
    """Every call made, in order. The unit of truth for spend."""

    calls: list[CallUsage] = field(default_factory=list)

    def record(self, call: CallUsage) -> CallUsage:
        self.calls.append(call)
        return call

    def __len__(self) -> int:
        return len(self.calls)

    def totals(self) -> dict[str, int]:
        return {
            "n_calls": len(self.calls),
            "input_tokens": sum(c.input_tokens for c in self.calls),
            "output_tokens": sum(c.output_tokens for c in self.calls),
            "cache_creation_input_tokens": sum(c.cache_creation_input_tokens for c in self.calls),
            "cache_read_input_tokens": sum(c.cache_read_input_tokens for c in self.calls),
            "total_tokens": sum(c.total_tokens for c in self.calls),
        }

    def cost_usd(self) -> float:
        """Estimated total. Counts failed and timed-out calls, which also bill."""
        return sum(call.cost_usd() for call in self.calls)

    def by_outcome(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for call in self.calls:
            counts[call.outcome] = counts.get(call.outcome, 0) + 1
        return counts

    def by_model(self) -> dict[str, dict[str, int | float]]:
        models: dict[str, dict[str, int | float]] = {}
        for call in self.calls:
            entry = models.setdefault(
                call.model_id,
                {"n_calls": 0, "total_tokens": 0, "cost_usd_estimated": 0.0},
            )
            entry["n_calls"] += 1
            entry["total_tokens"] += call.total_tokens
            entry["cost_usd_estimated"] += call.cost_usd()
        return models

    def as_dict(self) -> dict:
        return {
            "totals": self.totals(),
            "by_outcome": self.by_outcome(),
            "by_model": self.by_model(),
            "cost_usd_estimated": self.cost_usd(),
            "calls": [asdict(call) for call in self.calls],
        }


def reconcile(ledger: UsageLedger, cell_totals: dict[str, int]) -> None:
    """Assert the per-call records sum to the cell's reported totals.

    Raises rather than warning. A reconciliation gap means either a call was made
    without being recorded, or a total was computed from something other than the
    calls — and both make the reported spend wrong in the direction of too low.
    """
    computed = ledger.totals()
    mismatches = {
        key: (computed.get(key), cell_totals[key])
        for key in cell_totals
        if computed.get(key) != cell_totals[key]
    }
    if mismatches:
        detail = ", ".join(
            f"{key}: calls sum to {got}, cell reports {want}"
            for key, (got, want) in sorted(mismatches.items())
        )
        raise UsageReconciliationError(detail)


def merge(ledgers: Iterable[UsageLedger]) -> UsageLedger:
    merged = UsageLedger()
    for ledger in ledgers:
        merged.calls.extend(ledger.calls)
    return merged
