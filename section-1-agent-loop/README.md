# Module: Loop Engineering - Section 1: Agent loop

What the agent does on its own: pick tools, write Structured Query Language (SQL), and answer,
with nothing checking it yet.

## The problem

**Illustrative scenario.** A finance manager at Harbor & Pine Outfitters asks the analytics agent
for last fiscal year's net revenue. The agent lists the tables, finds a column named
`total_cents`, and sums it over the calendar year. The sum keeps cancelled orders, which hide
behind an undocumented status code. It also keeps the staff test accounts on the
`@harborpine.com` email domain. The agent answers in one confident sentence. The number goes into
a board deck, and nobody can say where it came from.

> **Terms on this page**
>
> - **Agent loop**: The model calls tools, reads the results, and repeats until it answers.
> - **Trap**: A business rule the schema does not reveal, so a plausible query gets it wrong.
> - **Gold SQL**: The query an analyst wrote by hand that gives the right answer.
> - **Answer envelope**: The structured result of a run: status, SQL, rows, and answer text.
> - **Schema scout**: A stateless helper agent that suggests tables and joins for a question.
> - **Planted bug**: A defect switched on by a flag so a demo shows its failure every time.
>
> All terms: [glossary](../docs/glossary.md).

## Why it happens

- The rules that define "net revenue" and "fiscal year" live in people's heads, not in the
  schema. [BIRD](https://arxiv.org/abs/2305.03111) calls this external knowledge and gives
  models the missing rules as evidence.
- Enterprise schemas are larger and messier than benchmark schemas, and large language model
  (LLM) agents do much worse on them ([Spider 2.0](https://arxiv.org/abs/2411.07763)).
- A tool that returns too much, or describes too little, shapes every later step of the loop.
  The [LangChain SQL agent](https://docs.langchain.com/oss/python/langchain/sql-agent) tutorial
  gives the agent four tools and trusts what they return.

## How this section fixes it

![The four-loop map with the agent loop highlighted: the analyst and the schema scout inside the verification, event, and hill-climbing loops, which are shown muted](../docs/diagrams/four-loops-agent-loop.svg)

*Where this section sits: the agent loop is highlighted; the other three loops stay in view.*

The agent loop gets better tools before it gets more rules. `describe_table` returns types,
sample rows, and distinct values, and `run_query` caps what reaches the model. The answer comes
back as an answer envelope with the SQL it used. One helper, the schema scout, suggests tables
and joins and keeps no state.

![The analyst agent between its prompt, which carries the business date and the active knowledge version, and its tools list_tables, describe_table, run_query, and scout_schema; run_query goes through the checker and returns at most 50 rows; scout_schema starts a schema scout agent inside a dashed tool boundary with only list_tables and describe_table; the run ends in an answer envelope; a stop box lists the limits of every run: 12 model calls, 16 tool calls, 60,000 tokens](diagrams/agent-loop.svg)

*Notice the schema scout's boundary: it can read the catalog but has no run_query, and every answer arrives as one structured envelope.*

The section ends with the fiscal year 2025 question still answered wrong. Better tools do not
supply the missing rules. That is why
[Section 2: Verification loop](../section-2-verification-loop/README.md) adds checks, and why only
the rules learned in Section 4: Hill-climbing loop fix the number. The full idea is in
[concepts.md](concepts.md) (in class, minutes 0 to 23).

## How to work through this section

### How it works in the code

- [`build_analyst`](../platform/src/datapilot/loop1_agent/analyst.py) builds the agent with the
  knowledge prompt, the model and tool call limits, and the answer envelope as its result.
- [`analyst_tools`](../platform/src/datapilot/loop1_agent/tools.py) defines `list_tables`,
  `describe_table`, and `run_query`; `format_result` cuts rows at `limits.row_cap` in `pack.yaml`.
- [`scout_tool`](../platform/src/datapilot/loop1_agent/scout.py) runs the schema scout with the
  two catalog tools only.
- [`GuardMiddleware`](../platform/src/datapilot/loop1_agent/guard.py) checks the run's token
  budget before every model call and every tool call.

The [walkthrough](demo/walkthrough.md) explains these lines (minutes 35 to 40).

### The demo

Three core demos, live, in minutes 23 to 35: the simple question
(`agent-simple-question`) shows the tool timeline; the confident wrong answer
(`agent-confident-wrong-answer`) shows the mismatch against gold; unbounded rows
(`agent-unbounded-rows`) shows the token counter with the row cap off and on. Every result
carries a live stamp: its start time and its LangSmith trace link. Run them with the
[demo page](demo/README.md); `demo/expected/` is for comparison after class only. The measured
runs are on the [evidence page](../docs/evidence/section-1-agent-loop.md).

### The assignment

[Assignment 1: Agent loop](assignment/README.md) adds a value-lookup tool that maps informal or
misspelled names to stored values, and asks when two are equally close. It is done when
`make check-assignment NAME=agent-loop` reads PASS on every line. Effort: about 1.5 hours; the
cost of a check is on the [costs page](../docs/costs.md#assignments).

### Apply it in a real system

- Bound every tool result in code: a row cap, the total count, and a truncation notice.
- Return the query with every answer, in a structured result a person or a check can re-run.
- Put the stops for model calls, tool calls, and tokens outside the prompt, where the model
  cannot talk past them.

### Further reading

The [reading list](post-class-reading/README.md) has three: business knowledge as evidence, how
far enterprise schemas are from benchmarks, and how to design what a tool returns.

## Where next

- First time here? Install everything with [setup/](../setup/README.md), then run the
  [demos](demo/README.md).
- Already set up? Start with [concepts.md](concepts.md).
- Next section: [Section 2: Verification loop](../section-2-verification-loop/README.md).

## Sources

- Source 1: Can LLM Already Serve as A Database Interface? A BIg Bench for Large-Scale Database Grounded Text-to-SQLs, <https://arxiv.org/abs/2305.03111>, Jinyang Li et al., 2023-05-04
- Source 2: Spider 2.0: Evaluating Language Models on Real-World Enterprise Text-to-SQL Workflows, <https://arxiv.org/abs/2411.07763>, Fangyu Lei et al., 2024-11-12
- Source 3: LangChain SQL agent, <https://docs.langchain.com/oss/python/langchain/sql-agent>, LangChain, n.d.
