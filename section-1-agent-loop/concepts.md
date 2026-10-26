# Section 1: Agent loop. Concepts

Reading time: about 8 minutes.

## The problem

**Illustrative scenario.** Take the finance manager's question from the
[section page](README.md#the-problem), one tool call at a time. The analyst calls `list_tables`, then
`describe_table` on `warehouse.orders`, and sees `total_cents`. It sums that column from January
to December and answers in one confident sentence. The total includes tax, shipping, cancelled
orders, and the staff test accounts. The number goes into the board deck.

Nothing in the run was broken. Every tool call worked, and the Structured Query Language (SQL)
query ran. The answer was wrong
because the rules that define the number are not in the schema.

> **Terms on this page**
>
> - **Agent loop**: The model calls tools, reads the results, and repeats until it answers.
> - **Trap**: A business rule the schema does not reveal, so a plausible query gets it wrong.
> - **Answer envelope**: The structured result of a run: status, SQL, rows, and answer text.
> - **Schema scout**: A stateless helper agent that suggests tables and joins for a question.
> - **Knowledge version**: A numbered set of business rules given to the agent in its prompt.
> - **Planted bug**: A defect switched on by a flag so a demo shows its failure every time.
>
> All terms: [glossary](../docs/glossary.md).

## The idea in one sentence

The agent loop can only be as right as its tools let it see, so you design what each tool shows,
cap what it returns, and make the answer a structure you can check.

## How it works

The tempting question is: will a stronger model fix it? No. The fiscal year starts in February,
net revenue is not `total_cents`, cancelled orders are `status = 5`, and internal accounts sit on
one email domain. None of that is in the schema. [BIRD](https://arxiv.org/abs/2305.03111) names
this gap external knowledge and supplies it to models as evidence. A stronger large language model
(LLM) guesses more fluently, but it still guesses.

![The analyst agent between its prompt and its tools list_tables, describe_table, run_query, and scout_schema; run_query goes through the checker and returns at most 50 rows; scout_schema starts a schema scout agent inside a dashed tool boundary with only list_tables and describe_table; the run ends in an answer envelope; a red box lists the stops: 12 model calls, 16 tool calls, 60,000 tokens](diagrams/agent-loop.svg)

*Notice the schema scout's boundary: it can read the catalog but has no run_query, and every answer arrives as one structured envelope.*

### 1) Tools are the agent's eyes

`describe_table` returns column types, nullability, neutral comments, three sample rows, and the
distinct values of low-cardinality columns. With the names-only schema
(`BUG_NAMES_ONLY_SCHEMA`) it returns column names alone, and the analyst misreads columns.
What the tools show decides what the agent can know.

### 2) Cap what reaches the model

`run_query` returns at most the row cap, the total row count, and a truncation notice. The cap is
`limits.row_cap` in `platform/packs/datapilot_us/pack.yaml`, set to 50. A row can still be large, so
each value longer than 2,000 characters is cut too (`VALUE_CHARACTER_CAP` in the same tools file). With the unbounded rows
bug (`BUG_UNBOUNDED_ROWS`), every row reaches the model and the token count spikes. The tool, not
the prompt, bounds the context.

### 3) The answer envelope

The analyst returns an `AnswerEnvelope` (`platform/src/datapilot/contracts/answer.py`): a
status, the final SQL, columns, a rows preview, the row count, the answer text, its assumptions,
and a clarifying question when one is needed. The status is one of answered, needs
clarification, refused, or escalated. A structured answer can be checked; a sentence cannot.

### 4) One scout, not a crowd

The analyst is the only agent that answers. The schema scout is a stateless subagent behind one
tool, `scout_schema(question)`, which returns a `SchemaBrief` of candidate tables, columns, joins,
and caveats. It is advisory and keeps no memory between calls. You switch it with
`agents.schema_scout.enabled` in `pack.yaml`. Add an agent only where judgement is needed, and
keep it stateless.

### Before and after

Before: the analyst sees column names only, runs a query that returns thousands of rows, and
answers in free text with no SQL attached. You cannot tell which rule it applied.

After: the analyst sees types and sample values, gets at most the row cap back with the total
count, and returns an envelope with its SQL and assumptions. The answer can still be wrong, but
now you can see exactly how, and a grader can check it.

## How DataPilot does it

The analyst is built in `platform/src/datapilot/loop1_agent/analyst.py` with `create_agent`. Its
knowledge arrives through a `dynamic_prompt` middleware that injects the active knowledge version.
The tools live in `platform/src/datapilot/loop1_agent/tools.py`. These lines apply the row cap
and the value cap, and return the total count and the notice:

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

The planted bug is one guarded branch, never a fake model output. Version 1 of the knowledge (the
starting version) is near-empty on purpose: `platform/packs/datapilot_us/knowledge/v1.yaml` states only the money rule.
The system prompt in `platform/src/datapilot/loop1_agent/prompts.py` states the role, the method,
and the output contract, and nothing about the business.

## What we measured

| Setting, reviewer on | Tokens per question | Latency per question |
|---|---|---|
| Analyst with the schema scout | 8,648 | 24.2 seconds |
| Analyst without the schema scout | 3,853 | 12.8 seconds |

Each figure is the mean of 4 benchmark questions under version 1, one run each, so it is a small
sample. The gold check gave the same result in both settings: the 2 easy questions passed it, the 2
trap questions failed it. The runs are on the
[Section 1 evidence page](../docs/evidence/section-1-agent-loop.md).

## When it helps, and when it does not

It helps when:

- The question names tables and columns the agent can find, such as order counts by state.
- Sample rows and distinct values reveal a coding, such as a status column with few values.
- A result is large, and the row cap keeps the context small enough to reason over.

It does not help when:

- The rule lives only in people's heads, such as the February fiscal year.
- A tempting column fits the question's words, such as `total_cents` for "revenue".
- Two product names are nearly identical, so the question itself is ambiguous.

## Key takeaways

- Tool design decides what the agent can know: describe columns well and cap what returns.
- Return an answer envelope with SQL and assumptions, so every answer can be checked.
- A stronger model does not supply business rules that are missing from the schema.

## Check your understanding

1. Why does a stronger model not fix the fiscal year 2025 revenue answer?

   <details><summary>Answer</summary>

   The rules that define the number are not in the schema. The model can only guess at the
   fiscal year, the net revenue formula, the cancelled status, and the internal accounts.

   </details>

2. Why does the row cap live in `run_query` and not in the system prompt?

   <details><summary>Answer</summary>

   A prompt asks the model to behave; a tool enforces it. The cap holds even when the model writes
   a query that returns every row.

   </details>

3. What does the schema scout return, and why is it stateless?

   <details><summary>Answer</summary>

   It returns a `SchemaBrief` of candidate tables, columns, joins, and caveats. Keeping it stateless
   means each call depends only on the question, so its advice is easy to test and switch off.

   </details>

4. What does the answer envelope give you that a sentence does not?

   <details><summary>Answer</summary>

   The final SQL, the rows preview, the row count, the assumptions, and a status. Each of those
   can be checked by a grader in Section 2: Verification loop.

   </details>

## Further reading

- [Section 1 reading list](post-class-reading/README.md)
- [The art of loop engineering](https://www.langchain.com/blog/the-art-of-loop-engineering), the
  post that names the four loops this course builds.

## Sources

- Source 1: Can LLM Already Serve as A Database Interface? A BIg Bench for Large-Scale Database Grounded Text-to-SQLs, <https://arxiv.org/abs/2305.03111>, Jinyang Li et al., 2023-05-04
- Source 2: The art of loop engineering, <https://www.langchain.com/blog/the-art-of-loop-engineering>, Sydney Runkle (LangChain), 2026-06-16
