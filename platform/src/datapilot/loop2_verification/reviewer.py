"""The reviewer: an independent agent that runs only after every deterministic grader passed.

It sees the question, the final SQL, a preview of the result, and the active knowledge, and nothing
else (not the analyst's reasoning or tool calls). Its verdict can hold an answer for human approval;
it can never pass a query or answer that a grader failed, because it is never asked.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, ModelCallLimitMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain_core.messages import HumanMessage

from datapilot import business_date
from datapilot.contracts import KnowledgeVersion, QueryResult, ReviewVerdict
from datapilot.loop1_agent import prompts, tools
from datapilot.loop1_agent.models import ModelFactory


def review_request(
    question: str, sql: str, result: QueryResult, knowledge: KnowledgeVersion, *, preview_rows: int
) -> str:
    preview = {
        "columns": result.columns,
        "rows": [list(r) for r in tools.cap_values(list(result.rows[:preview_rows]))[0]],
        "total_row_count": result.total_row_count,
    }
    return (
        f"{business_date.prompt_line()}\n\n"
        f"Question: {question}\n\nFinal SQL:\n{sql}\n\n"
        f"Result preview:\n{json.dumps(preview, default=str)}\n\n{knowledge.prompt_block()}"
    )


class Reviewer:
    def __init__(self, models: ModelFactory, *, middleware: Sequence[AgentMiddleware] = ()) -> None:
        self.models = models
        self.middleware = list(middleware)

    async def review(
        self,
        question: str,
        sql: str,
        result: QueryResult,
        knowledge: KnowledgeVersion,
        *,
        preview_rows: int,
    ) -> ReviewVerdict | None:
        agent = create_agent(
            self.models("reviewer"),
            [],
            system_prompt=prompts.REVIEWER,
            middleware=[
                *self.middleware,
                ModelCallLimitMiddleware(run_limit=3, exit_behavior="end"),
            ],
            response_format=ToolStrategy(ReviewVerdict),
            name="reviewer",
        )
        text = review_request(question, sql, result, knowledge, preview_rows=preview_rows)
        state = await agent.ainvoke({"messages": [HumanMessage(text)]})
        verdict = state.get("structured_response")
        return verdict if isinstance(verdict, ReviewVerdict) else None
