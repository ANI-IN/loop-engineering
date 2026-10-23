"""The OpenAI key gate before the first model call of a live check.

A missing or rejected key stops the check with exactly MISSING_KEY. The check never falls back to
anything offline. The gate itself costs no tokens: it lists the account's models.
"""

from __future__ import annotations

import os
import re
from typing import Any

import httpx

from datapilot.assignments.report import Stop
from datapilot.settings import Settings, get_settings

MISSING_KEY = "Live checks need your OpenAI key from the operations team"
# How a rejected key shows up in a run that failed mid-check.
_REJECTED = re.compile(r"invalid_api_key|incorrect api key|authenticationerror|\b401\b", re.I)


def require_openai_key(settings: Settings | None = None, *, http: Any = None) -> None:
    settings = settings or get_settings()
    key = settings.openai_api_key.get_secret_value().strip()
    if not key:
        raise Stop(MISSING_KEY)
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    client = http or httpx.Client(timeout=20)
    try:
        response = client.get(f"{base}/models", headers={"Authorization": f"Bearer {key}"})
    except httpx.HTTPError as error:
        raise Stop(f"Could not reach OpenAI to check the key ({type(error).__name__}).") from None
    finally:
        if http is None:
            client.close()
    if response.status_code in (401, 403):
        raise Stop(MISSING_KEY)
    if response.status_code >= 400:
        raise Stop(f"OpenAI answered {response.status_code} to the key check; try again later.")


NO_CREDITS = (
    "The OpenAI account behind your key has no credits left, so the live runs failed. Ask the "
    "operations team to add credits, then run the check again."
)
_NO_CREDITS = re.compile(r"insufficient_quota|credit_balance_exhausted", re.I)


def out_of_credits(text: str) -> bool:
    """True when a failed run's error says the account has no credits left."""
    return bool(_NO_CREDITS.search(text))


def rejected(text: str) -> bool:
    """True when a failed run's error says the key was rejected."""
    return bool(_REJECTED.search(text))
