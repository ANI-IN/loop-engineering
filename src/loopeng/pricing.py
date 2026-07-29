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
    cache_creation (5m write)    1.25x
    cache_read                   0.10x
    output                       varies by model

Summing `input_tokens` alone is therefore wrong on exactly the cells where caching
fires — which is the L3 sweep, the cells the whole cost comparison rests on.
"""

from dataclasses import dataclass

# Taken from https://claude.com/pricing and the Anthropic API docs pricing page.
# Update this date whenever a rate below changes.
PRICES_TAKEN_ON = "2026-07-29"
PRICES_SOURCE = "https://claude.com/pricing (per million tokens)"


@dataclass(frozen=True)
class ModelPrices:
    """USD per million tokens."""

    input: float
    output: float
    cache_write_5m: float
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
            + cache_creation_input_tokens * self.cache_write_5m
            + cache_read_input_tokens * self.cache_read
        ) / 1_000_000


PRICES: dict[str, ModelPrices] = {
    "claude-haiku-4-5": ModelPrices(
        input=1.00,
        output=5.00,
        cache_write_5m=1.25,
        cache_read=0.10,
    ),
    "claude-sonnet-5": ModelPrices(
        input=3.00,
        output=15.00,
        cache_write_5m=3.75,
        cache_read=0.30,
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
