"""Cost honesty: the estimate printed before any model call, and the actual spend at the end.

The estimate is computed, never a constant: each planned model run is priced as a run that uses
its whole token budget (pack.yaml budgets.tokens_per_run), at the model's input rate for the
"about" figure and at its output rate for the ceiling, with the prices in pack.yaml. Both are upper
readings, so each check also prints what a check of a working solution typically spent, measured
in the build's verification. The actual figures come from the build-wide spend ledger, which
records every model call's usage.

Each check also has its own spend cap (assignments.check_cap_usd in pack.yaml), counted from the
ledger rows of this check alone, so it holds with the build budget on or off. The check starts no
new run once its spend, plus the most the runs already under way can still add (the headroom: as
many runs as can be under way at once, each at its whole token budget at the output rate), would
pass the cap; so no check spends more than its cap, and no printed ceiling exceeds it.

Spend activity: each check run records under its own name (check_activity), the base followed by
the assignment's slug and a short id of the run, such as "assignment-agent-loop-1a2b3c4d". The base
is "assignment" for a learner's check, and "assignment verification" when the build runs the check
with DATAPILOT_SPEND_ACTIVITY set to that value (make verify-assignments does). So two checks that
run at the same time, such as the Assignment 4 check beside the others at the Thursday review, never
count each other's calls in their spend line or their cap; and every such name still counts under
the assignment verification line of the build budget (spend.line_for).
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any

from datapilot.assignments.report import Stop
from datapilot.config import pack_config
from datapilot.observability import spend

LEARNER = "assignment"
VERIFICATION = "assignment verification"


def activity() -> str:
    """Read like every budget switch: the environment, else .env."""
    flag = spend.budget_setting("DATAPILOT_SPEND_ACTIVITY")
    return VERIFICATION if flag == VERIFICATION else LEARNER


def check_activity(slug: str, base: str | None = None) -> str:
    """This check run's own activity name: the base, the slug, and a short id of the run."""
    return f"{base or activity()}-{slug}-{uuid.uuid4().hex[:8]}"


@dataclass(frozen=True)
class Planned:
    """Model runs a check is about to start."""

    what: str  # such as "analyst runs (4 questions, 2 runs each)"
    runs: int  # the runs the check always makes
    model: str
    extra: int = 0  # runs it makes only when needed, such as a third run when two disagree


def _price(model: str, pack: dict[str, Any]) -> dict[str, float]:
    if model not in pack["prices"]:
        raise KeyError(f"no price for {model} in pack.yaml: add it before running a live check")
    return pack["prices"][model]


def cents(
    planned: list[Planned], rate: str, pack: dict[str, Any] | None = None, *, extra: bool = False
) -> float:
    pack = pack or pack_config()
    budget = int(pack["budgets"]["tokens_per_run"])
    runs = [(p.runs + (p.extra if extra else 0), p.model) for p in planned]
    dollars = sum(n * budget * _price(model, pack)[rate] for n, model in runs) / 1_000_000
    return dollars * 100


def dollars(usd: float) -> str:
    """1.00 dollar, 1.50 dollars: as the course text writes money."""
    return f"{usd:.2f} dollar" + ("" if f"{usd:.2f}" == "1.00" else "s")


def check_cap_usd(pack: dict[str, Any] | None = None) -> float:
    """The spend cap of one assignment check, from pack.yaml."""
    pack = pack or pack_config()
    try:
        return float(pack["assignments"]["check_cap_usd"])
    except KeyError:
        raise Stop(
            "pack.yaml has no assignments.check_cap_usd, the spend cap of one assignment check: "
            "add it before running a live check"
        ) from None


# As many runs as a check can have under way at once: two_of_three runs its cases on this many
# threads (gold.in_parallel), and the benchmark on evaluation.concurrency threads.
def runs_at_once(pack: dict[str, Any] | None = None) -> int:
    from datapilot.assignments.gold import WORKERS

    pack = pack or pack_config()
    return max(WORKERS, int(pack["evaluation"]["concurrency"]))


def headroom_usd(planned: list[Planned], pack: dict[str, Any] | None = None) -> float:
    """The most the runs already under way can still add: every run that can be under way at once,
    at its whole token budget at the output rate of the dearest planned model."""
    pack = pack or pack_config()
    dearest = max((cents([Planned("", 1, p.model)], "output", pack) for p in planned), default=0)
    return runs_at_once(pack) * dearest / 100


def estimate_lines(
    planned: list[Planned],
    pack: dict[str, Any] | None = None,
    *,
    cap_usd: float | None = None,
    typical: str = "",
    typical_estimated: bool = False,
) -> list[str]:
    pack = pack or pack_config()
    budget = int(pack["budgets"]["tokens_per_run"])
    about = cents(planned, "input", pack)
    ceiling = cents(planned, "output", pack, extra=True)
    first = f"This check makes live model calls, about {about:.1f} cents"
    lines = [first if cap_usd is None else f"{first}, and stops at {dollars(cap_usd)}"]
    for p in planned:
        part = cents([p], "input", pack)
        more = f", plus at most {p.extra} more only if needed" if p.extra else ""
        lines.append(f"  {p.runs} {p.what} on {p.model}{more}: about {part:.1f} cents")
    if cap_usd is not None and ceiling > cap_usd * 100:
        top = (
            f"{cap_usd * 100:.1f} cents, because the spend cap stops the check first (without "
            f"the cap, {ceiling:.1f} cents)"
        )
    else:
        top = f"{ceiling:.1f} cents"
    lines.append(
        f"  Estimate: each run priced as one that uses its whole token budget "
        f"(budgets.tokens_per_run, {budget:,} tokens) at the input rate in pack.yaml; with every "
        f"extra run, at the output rate, the ceiling is {top}. Most runs use far less."
    )
    if typical and typical_estimated:
        lines.append(
            f"  Typical: a check of a working solution is estimated at {typical}, from the "
            "build's verification (docs/costs.md), far below the figure above."
        )
    elif typical:
        lines.append(
            f"  Typical: a check of a working solution has spent {typical} in the build's "
            "verification (docs/costs.md), far below the figure above."
        )
    if cap_usd is not None:
        lines.append(
            f"  Spend cap: {dollars(cap_usd)} for this check (assignments.check_cap_usd in "
            "pack.yaml), counted from this check's own calls in the spend ledger; it starts no "
            "new run once the runs already under way could take it past the cap."
        )
    return lines


def ledger_mark() -> int:
    """The last ledger row before the check's first model call."""
    with spend._connect() as conn:
        return int(conn.execute("SELECT COALESCE(MAX(id), 0) FROM spend_ledger").fetchone()[0])


@dataclass(frozen=True)
class Spent:
    calls: int
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    cost_usd: float

    def line(self, activity_name: str) -> str:
        return (
            f"Spend: {self.calls} model calls, {self.input_tokens:,} input tokens "
            f"({self.cached_input_tokens:,} cached), {self.output_tokens:,} output tokens, "
            f"${self.cost_usd:.4f} ({self.cost_usd * 100:.2f} cents), recorded in the spend "
            f'ledger under the activity "{activity_name}"'
        )


def spent_since(mark: int, activity_name: str) -> Spent:
    with spend._connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(input_tokens), 0), "
            "COALESCE(SUM(cached_input_tokens), 0),"
            " COALESCE(SUM(output_tokens), 0), COALESCE(SUM(cost_usd), 0) FROM spend_ledger "
            "WHERE id > ? AND activity = ?",
            (mark, activity_name),
        ).fetchone()
    return Spent(int(row[0]), int(row[1]), int(row[2]), int(row[3]), float(row[4]))


class CapReached(Stop):
    """The check reached its spend cap: it starts no new run, and the runner winds it down."""


@dataclass
class Cap:
    """One check's spend cap, counted from the ledger rows after `mark` under `activity`: the rows
    of this check, whichever process recorded them (the workers, or the check itself)."""

    usd: float
    mark: int
    activity: str
    headroom_usd: float  # the most the runs already under way can still add
    reached: bool = False
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def spent(self) -> float:
        return spent_since(self.mark, self.activity).cost_usd

    def check(self) -> None:
        """Before each new run and while waiting for one: raise CapReached once this check's
        spend, plus the headroom, would pass the cap. Once reached, it stays reached."""
        with self._lock:
            if not self.reached:
                self.reached = self.spent() + self.headroom_usd >= self.usd
            if self.reached:
                raise CapReached(f"the spend cap of {dollars(self.usd)} was reached")
