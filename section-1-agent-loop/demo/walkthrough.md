# Demo walkthrough for Section 1: Agent loop

The code behind the demos of this section: how the analyst is built, where its knowledge enters,
and how its Structured Query Language (SQL) results reach the model.

> **Terms on this page**
>
> - **Agent loop**: The model calls tools, reads the results, and repeats until it answers.
> - **Knowledge version**: A numbered set of business rules given to the agent in its prompt.
> - **Answer envelope**: The structured result of a run: status, SQL, rows, and answer text.
> - **Planted bug**: A defect switched on by a flag so a demo shows its failure every time.
>
> All terms: [glossary](../../docs/glossary.md).

## What this code does

The analyst is one `create_agent` call. Before every model call, middleware writes the system
prompt: the base prompt, the business date, and the active knowledge version. Two more middleware
end the loop at the call limits in `platform/packs/datapilot_us/pack.yaml`. The model picks a tool;
`run_query` hands the SQL to the checker and caps the rows that go back.
The loop ends when the model returns an answer envelope, the structured output of the run.

```mermaid
sequenceDiagram
    participant Worker
    participant Analyst as Analyst (create_agent)
    participant Model
    participant Tools as Tools and checker
    Worker->>Analyst: question
    loop until an answer envelope or a limit
        Analyst->>Model: prompt with the business date and knowledge v1
        Model-->>Analyst: tool call (list_tables, describe_table, run_query)
        Analyst->>Tools: run the tool; run_query goes through the checker
        Tools-->>Analyst: result, rows capped at limits.row_cap
    end
    Model-->>Analyst: answer envelope
    Analyst-->>Worker: SQL, rows, answer text
```

## The code, explained

### platform/src/datapilot/loop1_agent/analyst.py, lines 56-58

```python
# platform/src/datapilot/loop1_agent/analyst.py (lines 56-58)
    @dynamic_prompt
    def inject_knowledge(request: ModelRequest) -> str:
        return f"{base}\n{business_date.prompt_line()}\n\n{knowledge.prompt_block()}"
```

The knowledge reaches the model here, on every call, not once at build time. Under knowledge
version v1 the block holds only the money rule, so the confident wrong answer shows what the
model does with the traps left out. A new version changes this block and nothing else.

### platform/src/datapilot/loop1_agent/analyst.py, lines 72-86

```python
# platform/src/datapilot/loop1_agent/analyst.py (lines 72-86)
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
```

The loop's stops are middleware, read from `limits` in `pack.yaml`. The model call limit ends the
run; the tool call limit answers extra calls with an error so the model can still answer.
`*middleware` is where later loops add the run guard, the kill switch, and approvals.
`ToolStrategy(AnswerEnvelope)` makes the answer a typed object the graders can read.

### platform/src/datapilot/loop1_agent/tools.py, lines 33-54

```python
# platform/src/datapilot/loop1_agent/tools.py (lines 33-54)
def cap_rows(rows: list[tuple[Any, ...]], limit: int) -> tuple[list[tuple[Any, ...]], bool]:
    if planted("BUG_UNBOUNDED_ROWS"):
        return rows, False  # planted: every row goes back to the model
    return rows[:limit], len(rows) > limit


def format_result(result: QueryResult, row_cap: int) -> str:
    rows, truncated = cap_rows(list(result.rows), row_cap)
    rows, values_cut = cap_values(rows)
    payload: dict[str, Any] = {
        "columns": result.columns,
        "rows": [list(r) for r in rows],
        "total_row_count": result.total_row_count,
        "truncated": truncated,
    }
    notices = [f"Showing {len(rows)} of {result.total_row_count} rows."] if truncated else []
    if values_cut:
        payload["values_cut"] = values_cut
        notices.append(f"{values_cut} value(s) were cut to {VALUE_CHARACTER_CAP} characters.")
    if notices:
        payload["notice"] = " ".join([*notices, ONE_ROW_PER_ROW])
    return json.dumps(payload, default=str)
```

This is the unbounded rows demo. The cap lives in the tool, so no prompt wording can lift it. The
model still learns the total row count. `cap_values`, just below in the same file, cuts each value
longer than 2,000 characters, because one row can hold an array of every address. The notice keeps
the agent at one row per result row instead of inviting it to gather every row into one value.
With the unbounded rows bug (`BUG_UNBOUNDED_ROWS`) on, the planted branch returns every row, and
the token counter shows the cost.

## If you copy this into your repository

- Keep the cap in the tool result, with the total count and a notice. A cap that only the prompt
  asks for is a request, not a limit.
- Keep the knowledge in a `dynamic_prompt` middleware, so a new rule set needs no rebuild and each
  run records which version it used.
- Keep both call limits as middleware, with the exit behaviours shown here.
- Change the row cap and the call limits to fit your data, in one settings file, not in code.
- Change the tools to your schema: a description with types, sample rows, and distinct values helps
  the model more than a list of names.
- Check it with a query that returns more rows than the cap: the tool must return at most the cap,
  the total count, and the notice.
