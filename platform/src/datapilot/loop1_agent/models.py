"""Chat model construction. Every agent gets its model from a factory, so the event loop and the
tests decide which model a run uses; the live factory is the only one in the package."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from datapilot.config import pack_config
from datapilot.observability.spend import SpendCallback
from datapilot.settings import Settings, get_settings

# component ("analyst", "schema_scout", "reviewer") -> chat model
ModelFactory = Callable[[str], BaseChatModel]


def openai_factory(
    *,
    run_id: str | None = None,
    activity: str | None = None,
    settings: Settings | None = None,
    pack: dict[str, Any] | None = None,
) -> ModelFactory:
    """The live models: the Responses API, the reasoning effort and the output-token cap from
    pack.yaml, no temperature, and the spend ledger on every call, under `activity` when the job
    names one (else this process's DATAPILOT_SPEND_ACTIVITY)."""
    from langchain_openai import ChatOpenAI

    settings = settings or get_settings()
    pack = pack or pack_config()

    def build(component: str) -> BaseChatModel:
        model = settings.agent_model
        call = pack["models"][component]
        return ChatOpenAI(
            model=model,
            api_key=settings.openai_api_key,
            use_responses_api=bool(pack["models"].get("use_responses_api", True)),
            reasoning={"effort": call["reasoning_effort"]},
            # sent to the Responses API as max_output_tokens
            max_tokens=int(call["max_output_tokens"]),
            callbacks=[
                SpendCallback(component=component, model=model, run_id=run_id, activity=activity)
            ],
        )

    return build
