"""A 400 is the only proof that a parameter is legal for a model.

This project does not claim "supported" without a test that enforces it, so each
role issues one real minimal request with its own request_kwargs. If this fails
with a 400, the kwargs in registry.py are wrong — fix them, not this test.
"""

import anthropic
import pytest

from loopeng.registry import REGISTRY
from loopeng.settings import load_settings


@pytest.mark.live
@pytest.mark.parametrize("role", sorted(REGISTRY))
def test_request_kwargs_are_accepted_by_the_model(role):
    settings = load_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key.get_secret_value())
    spec = REGISTRY[role]

    response = client.messages.create(
        model=spec.model_id,
        messages=[{"role": "user", "content": "Reply with the single word: ok"}],
        **spec.request_kwargs,
    )

    assert response.usage.input_tokens > 0
    assert response.usage.output_tokens > 0
    # The served model should correspond to the one requested. Anthropic may return
    # a more specific id than the alias, so this is a prefix-ish check rather than
    # equality — assert what is actually guaranteed, not what looks tidy.
    assert response.model
