"""Whether a hosted instance may make live model calls, and what bounds it.

**Off unless three things are all true**, because the failure mode is somebody else's
money and it is silent until the bill arrives:

  1. `LOOPENG_LIVE=1` is set explicitly. Not inferred from a key being present, since
     a key can arrive for a dozen reasons that are not "please spend it".
  2. `ANTHROPIC_API_KEY` is set to something real.
  3. A spend ceiling is configured. Live with no ceiling is not a configuration this
     accepts; it refuses rather than defaulting to a number nobody chose.

Even then, the bounds below are enforced per process rather than advertised. The
exhibit's guarantee is structural — no client is ever constructed — and this is the
weaker, quantitative version of the same idea: a client may be constructed, and the
ledger stops it after a fixed amount.

**A public host with a working key is unbounded spend by strangers.** The ceiling here
turns "unbounded" into "capped", which is not the same as safe. Password-gate it or keep
it private; the cap is a backstop, not a door.
"""

import os
from dataclasses import dataclass, field

from loopeng.usage import CallUsage, UsageLedger


class LiveRefused(RuntimeError):
    """Live was asked for and the configuration does not permit it."""


class BudgetExhausted(RuntimeError):
    """The session ceiling is spent. Raised instead of quietly continuing."""


@dataclass
class LiveConfig:
    enabled: bool
    ceiling_usd: float
    max_calls: int
    reason: str

    @property
    def summary(self) -> str:
        if not self.enabled:
            return f"**Live calls are off.** {self.reason}"
        return (
            f"**Live calls are on**, capped at est. ${self.ceiling_usd:.2f} and "
            f"{self.max_calls} calls for this process. When either runs out the app "
            f"keeps working and stops calling."
        )


def read_config(env: dict | None = None) -> LiveConfig:
    env = os.environ if env is None else env

    if env.get("LOOPENG_LIVE", "").strip() not in ("1", "true", "True", "yes"):
        return LiveConfig(False, 0.0, 0, "LOOPENG_LIVE is not set, so nothing calls a model.")

    key = env.get("ANTHROPIC_API_KEY", "").strip()
    if not key or key.startswith("exhibit-"):
        return LiveConfig(
            False, 0.0, 0,
            "LOOPENG_LIVE is set but ANTHROPIC_API_KEY is missing, so live is refused "
            "rather than half enabled.",
        )

    raw_ceiling = env.get("LOOPENG_LIVE_CEILING_USD", "").strip()
    if not raw_ceiling:
        return LiveConfig(
            False, 0.0, 0,
            "LOOPENG_LIVE is set but LOOPENG_LIVE_CEILING_USD is not. Live with no "
            "ceiling is not a configuration this accepts, and defaulting to a number "
            "nobody chose would be worse than refusing.",
        )
    try:
        ceiling = float(raw_ceiling)
    except ValueError:
        return LiveConfig(
            False, 0.0, 0,
            f"LOOPENG_LIVE_CEILING_USD={raw_ceiling!r} is not a number.",
        )
    if ceiling <= 0:
        return LiveConfig(False, 0.0, 0, "LOOPENG_LIVE_CEILING_USD must be greater than zero.")

    max_calls = int(env.get("LOOPENG_LIVE_MAX_CALLS", "60"))
    return LiveConfig(True, ceiling, max_calls, "")


@dataclass
class LiveBudget:
    """The running total, checked BEFORE each call rather than after."""

    config: LiveConfig
    ledger: UsageLedger = field(default_factory=UsageLedger)

    def check(self) -> None:
        if not self.config.enabled:
            raise LiveRefused(self.config.reason)
        if len(self.ledger) >= self.config.max_calls:
            raise BudgetExhausted(
                f"the {self.config.max_calls}-call ceiling for this process is spent. "
                "Restart it to reset, or raise LOOPENG_LIVE_MAX_CALLS."
            )
        if self.ledger.cost_usd() >= self.config.ceiling_usd:
            raise BudgetExhausted(
                f"the est. ${self.config.ceiling_usd:.2f} ceiling for this process is "
                f"spent (est. ${self.ledger.cost_usd():.4f} used). Restart it to reset."
            )

    def record(self, call: CallUsage) -> CallUsage:
        return self.ledger.record(call)

    def render(self) -> str:
        if not self.config.enabled:
            return self.config.summary
        spent, calls = self.ledger.cost_usd(), len(self.ledger)
        return (
            f"est. ${spent:.4f} of ${self.config.ceiling_usd:.2f} · "
            f"{calls} of {self.config.max_calls} calls"
        )
