"""The price table, in one place, with the date it was taken.

Every dollar figure this project produces is an **estimate**, and the label never
gets upgraded. Tokens are measured — they come off the response. Dollars are those
tokens multiplied by numbers typed in by hand from a pricing page on a particular
day. Only a billing export makes cost a measurement, and this project does not read
one. That is equally true of LangSmith's cost column, which is the same arithmetic
against its own table.

Prices are per million tokens, per model, per token class. The four classes bill
differently and the difference is not small:

    class                        rate vs base input
    input                        1.00x
    cache_write                  vendor-specific — see below
    cache_read                   0.10x on both vendors
    output                       varies by model

Summing `input_tokens` alone is therefore wrong on exactly the cells where caching
fires — which, under the current model policy, is every agent cell, because the
schema-plus-rules prefix is byte-identical across every call in a run.

WHY `cache_write` IS NOT ONE NUMBER ACROSS VENDORS
--------------------------------------------------

Anthropic charges a **premium** to populate the cache: a 5-minute write bills at
1.25x base input. OpenAI charges **nothing extra** — a cache write bills at the
ordinary input rate and only reads are discounted. Modelling that as one field
with a per-model value keeps `cost_usd` a single expression, and the alternative
— a vendor branch inside the cost function — would put a provider conditional in
the one place every reported dollar passes through.

So for the OpenAI rows below, `cache_write` equals `input`. That is not a
placeholder and it is not a rounding: it is the actual rate.

WHY THE ANTHROPIC ROWS MOVED
----------------------------

`claude-sonnet-5` was priced here at $3.00 / $15.00. The published rate is
$2.00 / $10.00, and had been for the life of the file. Every dollar figure this
project ever printed for a Sonnet cell was overstated by 50% — including the
committed reference measurements and the tables in README §12.

That is worth stating plainly rather than fixing quietly. It is the exact failure
this module's own docstring warns about: a hand-entered table is a measurement of
nothing, and nothing in the build compared it to the source. `PRICES_TAKEN_ON`
existed to make the staleness visible and did not, because a date only helps a
reader who goes and checks. `scripts/check_prices.py` is the check that was
missing.
"""

from dataclasses import dataclass

# Taken from the two vendors' published pricing pages on this date. Update it
# whenever a rate below changes, and re-run `scripts/check_prices.py`.
PRICES_TAKEN_ON = "2026-09-07"
PRICES_SOURCES = (
    "https://developers.openai.com/api/docs/pricing",
    "https://claude.com/pricing",
)


@dataclass(frozen=True)
class ModelPrices:
    """USD per million tokens, per token class."""

    input: float
    output: float
    cache_write: float
    cache_read: float

    def cost_usd(
        self,
        *,
        input_tokens: int,
        output_tokens: int,
        cache_creation_input_tokens: int = 0,
        cache_read_input_tokens: int = 0,
    ) -> float:
        """Estimated dollars for one call, counting every token class separately."""
        return (
            input_tokens * self.input
            + output_tokens * self.output
            + cache_creation_input_tokens * self.cache_write
            + cache_read_input_tokens * self.cache_read
        ) / 1_000_000


PRICES: dict[str, ModelPrices] = {
    # ---- OpenAI -----------------------------------------------------------
    # The agent. Every loop, every retry, every sweep cell runs here.
    #
    # The 90% cache-read discount is the reason this model and not a legacy
    # budget tier: the schema-plus-rules prefix is identical on every call, so
    # the discount applies to the great majority of input tokens the agent ever
    # sends. `gpt-4o-mini` discounts cache reads by 50% ($0.15 -> $0.075), which
    # is half the saving on the token class that dominates this workload.
    "gpt-5.6-luna": ModelPrices(
        input=0.20,
        output=1.20,
        # No write premium on OpenAI. See the module docstring.
        cache_write=0.20,
        cache_read=0.02,
    ),
    # The reference bar. One condition, no loops, held-out set only.
    "gpt-6-astra": ModelPrices(
        input=10.00,
        output=50.00,
        cache_write=10.00,
        cache_read=1.00,
    ),
    # ---- Anthropic --------------------------------------------------------
    # The judge. Triage and failure sorting only, and it never blocks, so its
    # volume is a fraction of the agent's and its price barely reaches a chart.
    # It is here because a model with no price entry raises rather than costing
    # nothing, and a judge silently free would understate the session's spend.
    "claude-haiku-4-5": ModelPrices(
        input=1.00,
        output=5.00,
        # Anthropic's 5-minute cache write bills at 1.25x base input.
        cache_write=1.25,
        cache_read=0.10,
    ),
}


class UnknownModelPrice(KeyError):
    """Raised rather than defaulting to zero.

    A model with no price entry silently costing nothing would make a sweep look
    free, which is the single most misleading way this table could fail.
    """


def prices_for(model_id: str) -> ModelPrices:
    try:
        return PRICES[model_id]
    except KeyError as exc:
        raise UnknownModelPrice(
            f"no price entry for {model_id!r}; add one to loopeng.pricing.PRICES "
            f"(rates last taken {PRICES_TAKEN_ON})"
        ) from exc
