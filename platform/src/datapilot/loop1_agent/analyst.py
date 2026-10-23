"""The analyst: create_agent with the knowledge injected by dynamic_prompt, call limits from the
pack, structured output, and LangSmith metadata. The schema scout is one more tool when enabled."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    ModelCallLimitMiddleware,
    ModelRequest,
    ToolCallLimitMiddleware,
    dynamic_prompt,
)
from langchain.agents.structured_output import ToolStrategy
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.types import Checkpointer

from datapilot import business_date
from datapilot.config import pack_config
from datapilot.contracts import AnswerEnvelope, KnowledgeVersion
from datapilot.loop1_agent import prompts


@dataclass(frozen=True)
class AgentLimits:
    row_cap: int
    model_call_limit: int
    tool_call_limit: int
    tokens_per_run: int
    scout_enabled: bool
    reviewer_enabled: bool

    @classmethod
    def from_pack(cls, cfg: dict[str, Any] | None = None) -> AgentLimits:
        cfg = cfg or pack_config()
        limits, agents = cfg["limits"], cfg["agents"]
        return cls(
            row_cap=int(limits["row_cap"]),
            model_call_limit=int(limits["model_call_limit"]),
            tool_call_limit=int(limits["tool_call_limit"]),
            tokens_per_run=int(cfg["budgets"]["tokens_per_run"]),
            scout_enabled=bool(agents["schema_scout"]["enabled"]),
            reviewer_enabled=bool(agents["reviewer"]["enabled"]),
        )


def knowledge_prompt(base: str, knowledge: KnowledgeVersion) -> AgentMiddleware:
    """The system prompt on every model call: the base prompt, the business date, and the active
    knowledge."""

    @dynamic_prompt
    def inject_knowledge(request: ModelRequest) -> str:
        return f"{base}\n{business_date.prompt_line()}\n\n{knowledge.prompt_block()}"

    return inject_knowledge


def build_analyst(
    *,
    model: BaseChatModel,
    tools: Sequence[BaseTool],
    knowledge: KnowledgeVersion,
    limits: AgentLimits,
    middleware: Sequence[AgentMiddleware] = (),
    checkpointer: Checkpointer | None = None,
) -> Any:
    return create_agent(
        model,
        list(tools),
        system_prompt=prompts.ANALYST,
        middleware=[
            knowledge_prompt(prompts.ANALYST, knowledge),
            *middleware,
            ModelCallLimitMiddleware(run_limit=limits.model_call_limit, exit_behavior="end"),
            # "end" works only for a single tool; "continue" answers extra calls with an error.
            ToolCallLimitMiddleware(run_limit=limits.tool_call_limit, exit_behavior="continue"),
        ],
        response_format=ToolStrategy(AnswerEnvelope),
        checkpointer=checkpointer,
        name="analyst",
    )


@dataclass(frozen=True)
class RunMetadata:
    """LangSmith metadata on every trace of a run; child runs inherit it."""

    run_id: str
    event_id: str | None
    demo_name: str | None
    pack: str
    knowledge_version: str
    autonomy_level: str
    planted_active: list[str] = field(default_factory=list)
    model: str = ""

    def as_metadata(self, attempt: int) -> dict[str, Any]:
        # LangGraph reads a metadata key named run_id as its own and then ignores new input on the
        # thread, so the run id is published as datapilot_run_id (the trace id is the run id too).
        data = asdict(self)
        data["datapilot_run_id"] = data.pop("run_id")
        return {**data, "attempt": attempt}

    def config(self, *, thread_id: str, trace_id: str, attempt: int) -> dict[str, Any]:
        tags = [f"pack:{self.pack}", f"knowledge:{self.knowledge_version}", self.autonomy_level]
        tags += [f"demo:{self.demo_name}"] if self.demo_name else []
        tags += [f"planted:{flag}" for flag in self.planted_active]
        return {
            "configurable": {"thread_id": thread_id},
            "run_id": trace_id,
            "run_name": "datapilot-run",
            "tags": tags,
            "metadata": self.as_metadata(attempt),
            "recursion_limit": 100,
        }
