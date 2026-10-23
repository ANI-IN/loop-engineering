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

The agent loop gets better tools before it gets more rules. `describe_table` returns types,
sample rows, and distinct values, and `run_query` caps what reaches the model. The answer comes
back as an answer envelope with the SQL it used. One helper, the schema scout, suggests tables
and joins and keeps no state.

![The analyst agent between its prompt and its tools list_tables, describe_table, run_query, and scout_schema; run_query goes through the checker and returns at most 50 rows; scout_schema starts a schema scout agent inside a dashed tool boundary with only list_tables and describe_table; the run ends in an answer envelope; a red box lists the stops: 12 model calls, 16 tool calls, 60,000 tokens](diagrams/agent-loop.svg)

*Notice the schema scout's boundary: it can read the catalog but has no run_query, and every answer arrives as one structured envelope.*

The section ends with the fiscal year 2025 question still answered wrong. Better tools do not
supply the missing rules, which is the case for
[Section 2: Verification loop](../section-2-verification-loop/README.md). Results of the class
runs go on the [evidence page](../docs/evidence/section-1-agent-loop.md).

## How to work through this section

| Part | What it gives you | In class |
|---|---|---|
| [concepts.md](concepts.md) | The loop, its tools, and why tool design decides answers | Minutes 0-23 |
| [demo/](demo/README.md) | The simple question, the confident wrong answer, and unbounded rows, live | Minutes 23-35 |
| [demo/walkthrough.md](demo/walkthrough.md) | The analyst, the tools, and the row cap | Minutes 35-40 |
| [assignment/](assignment/README.md) | Assignment 1: Agent loop, a value-lookup tool | After class |
| [post-class-reading/](post-class-reading/README.md) | Readings on SQL agents and evidence | After class |
| [session-notes.md](session-notes.md) | What class showed, questions, what to try next | After class |

In class, every demo result on the console shows a live stamp: its run's start time in the
viewer's local time and its LangSmith trace link. The `demo/expected/` folder is for you
after class; it is never opened in class.

## Where next

- First time here? Install everything with [setup/](../setup/README.md), then run the
  [demos](demo/README.md).
- Already set up? Start with [concepts.md](concepts.md).
- Next section: [Section 2: Verification loop](../section-2-verification-loop/README.md).

## Sources

- Source 1: Can LLM Already Serve as A Database Interface? A BIg Bench for Large-Scale Database Grounded Text-to-SQLs, <https://arxiv.org/abs/2305.03111>, Jinyang Li et al., 2023-05-04
- Source 2: Spider 2.0: Evaluating Language Models on Real-World Enterprise Text-to-SQL Workflows, <https://arxiv.org/abs/2411.07763>, Fangyu Lei et al., 2024-11-12
- Source 3: LangChain SQL agent, <https://docs.langchain.com/oss/python/langchain/sql-agent>, LangChain, n.d.
