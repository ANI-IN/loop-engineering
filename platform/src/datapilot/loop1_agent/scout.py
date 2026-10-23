"""The schema scout: a stateless subagent behind the tool scout_schema(question).

Each call is a fresh agent with only the catalog tools and no memory; it returns a SchemaBrief the
analyst may use or ignore.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, ModelCallLimitMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool, StructuredTool

from datapilot.contracts import SchemaBrief
from datapilot.loop1_agent import prompts
from datapilot.loop1_agent.models import ModelFactory
from datapilot.loop1_agent.tools import Warehouse

NO_BRIEF = "The schema scout returned no brief; use list_tables and describe_table."


def _catalog_tools(warehouse: Warehouse) -> list[BaseTool]:
    def list_tables() -> str:
        """List the warehouse tables and views, each with a one-line description."""
        return warehouse.list_tables()

    def describe_table(name: str) -> str:
        """Describe one table: column types, comments, sample rows, and few distinct values."""
        return warehouse.describe_table(name)

    return [StructuredTool.from_function(list_tables), StructuredTool.from_function(describe_table)]


def scout_tool(
    models: ModelFactory,
    warehouse: Warehouse,
    *,
    middleware: Sequence[AgentMiddleware] = (),
    model_call_limit: int = 6,
) -> BaseTool:
    def build() -> Any:
        return create_agent(
            models("schema_scout"),
            _catalog_tools(warehouse),
            system_prompt=prompts.SCHEMA_SCOUT,
            middleware=[
                *middleware,
                ModelCallLimitMiddleware(run_limit=model_call_limit, exit_behavior="end"),
            ],
            response_format=ToolStrategy(SchemaBrief),
            name="schema_scout",
        )

    def brief(result: dict[str, Any]) -> str:
        found = result.get("structured_response")
        return found.model_dump_json() if isinstance(found, SchemaBrief) else NO_BRIEF

    def scout_schema(question: str) -> str:
        """Ask the schema scout which tables, columns, and joins could answer a question."""
        return brief(build().invoke({"messages": [HumanMessage(question)]}))

    async def ascout_schema(question: str) -> str:
        return brief(await build().ainvoke({"messages": [HumanMessage(question)]}))

    return StructuredTool.from_function(
        func=scout_schema, coroutine=ascout_schema, name="scout_schema"
    )
