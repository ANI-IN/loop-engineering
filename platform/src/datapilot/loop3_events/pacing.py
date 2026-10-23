"""Demo pacing (a labelled demo aid): a pause between lifecycle stages and before each model and
tool call, so a run visibly moves across the board and the kill switch can catch it in flight.
It only waits; it never changes what a run does or returns."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware

from datapilot.planted import planted
from datapilot.settings import get_settings


def seconds() -> float:
    return get_settings().demo_pacing_seconds if planted("DEMO_PACING") else 0.0


async def pause() -> None:
    if (wait := seconds()) > 0:
        await asyncio.sleep(wait)


class PacingMiddleware(AgentMiddleware):
    def before_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        time.sleep(seconds())
        return None

    async def abefore_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        await pause()
        return None

    def wrap_tool_call(self, request: Any, handler: Callable[[Any], Any]) -> Any:
        time.sleep(seconds())
        return handler(request)

    async def awrap_tool_call(self, request: Any, handler: Callable[[Any], Awaitable[Any]]) -> Any:
        await pause()
        return await handler(request)
