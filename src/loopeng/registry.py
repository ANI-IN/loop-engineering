"""Role to model mapping.

The spec asks for a registry so swapping a model is one edit. It cannot be a
dict of strings, because the two models do not accept the same request:

    parameter                  claude-haiku-4-5       claude-sonnet-5
    output_config.effort       errors                 supported (default "high")
    temperature (non-default)  allowed                400
    thinking                   {type:"enabled",...}   adaptive, on by default

So a role maps to a model id *plus* the kwargs that are legal for it. Swapping a
model is still one edit; the edit is just larger than a string.

Sonnet 5 sends no `thinking` key, which means adaptive thinking runs. That is
deliberate: it is how the frontier model would actually be deployed, and it is
what makes the cost gap in the TRAP demo real. max_tokens is sized with headroom
for thinking plus the SQL, not sized to the SQL — max_tokens caps both together.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    request_kwargs: Mapping[str, Any]


REGISTRY: Mapping[str, ModelSpec] = MappingProxyType(
    {
        "worker": ModelSpec(
            model_id="claude-haiku-4-5",
            # No effort (errors on this model), no thinking. SQL is short.
            #
            # temperature=0 is pinned here and NOT on the frontier role, because Haiku
            # accepts it and Sonnet 5 rejects any non-default sampling parameter with a
            # 400. That asymmetry is not cosmetic: measured 2026-07-29, two runs of the
            # same 50 items at default temperature disagreed on 6 of the 45 items where
            # the loop never intervened — a 13.3% run-to-run disagreement floor, large
            # enough to swamp the effect the sweep is looking for.
            #
            # The consequence is that the two models' error bars mean different things.
            # Haiku's carry sampling noise only; Sonnet's carry sampling noise plus
            # run-to-run variance. Any cross-model comparison inherits that asymmetry
            # on top of already being underpowered, and has to say so on screen.
            request_kwargs=MappingProxyType({"max_tokens": 2048, "temperature": 0}),
        ),
        "frontier": ModelSpec(
            model_id="claude-sonnet-5",
            # No thinking key: adaptive runs by default. Headroom for it.
            # No effort key: the model's own default is what ships.
            request_kwargs=MappingProxyType({"max_tokens": 8192}),
        ),
    }
)


def spec_for(role: str) -> ModelSpec:
    return REGISTRY[role]
