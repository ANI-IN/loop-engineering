# Module: Loop Engineering - Section 2: Verification loop

What checks every query and answer before anyone sees it, and what those checks cannot prove.

## The problem

**Illustrative scenario.** A product name in the Harbor & Pine Outfitters catalogue carries a
line of text telling the agent to delete old orders. The agent reads it in a sample row and
stacks a second Structured Query Language (SQL) statement after its SELECT. A guard that only checks the query starts with
"select" lets it through, and only the read-only role refuses it. In another run a check keeps
failing, the agent keeps retrying, and the bill climbs. Then the fiscal year revenue answer
passes every check and is still wrong.

> **Terms on this page**
>
> - **Verification loop**: Graders check each query and answer, and send failures back to the agent.
> - **Grader**: A check that passes or fails one stage of a run and says why.
> - **Reviewer**: An independent agent that reads the question, SQL, and result after the graders pass.
> - **Planted bug**: A defect switched on by a flag so a demo shows its failure every time.
> - **Human approval**: A person approves or rejects a held action before it runs.
>
> All terms: [glossary](../docs/glossary.md).

## Why it happens

- A prompt rule or a model-based query checker is not a boundary. The
  [LangChain SQL agent](https://docs.langchain.com/oss/python/langchain/sql-agent) tutorial
  checks queries with a model and forbids data changes by instruction.
- A syntax tree cannot see SQL inside string literals, and some statements parse to an opaque
  command. Only a read-only transaction refuses every write, with the error class listed in
  [PostgreSQL Error Codes](https://www.postgresql.org/docs/current/errcodes-appendix.html).
- A result that matches on one database can still be wrong.
  [Semantic Evaluation for Text-to-SQL with Distilled Test Suites](https://arxiv.org/abs/2010.02840)
  measures how often single-database execution match gives false positives.

## How this section fixes it

The verification loop wraps the agent loop in layers. A syntax-tree guard, a schema allowlist, a
read-only role, and a statement timeout each assume the layer above them fails. Graders at three
stages send their reasons back to the agent, and a retry cap ends the loop. A write the database
refuses is never sent back: the run ends at once as escalated, with no retry. After every grader
passes, an independent reviewer reads the result.

![Two stages of checks. Stage 1: each query passes the parse, statement policy, schema, cost, and personal data graders, then the read-only executor and the execution grader; a block sends feedback to the analyst, personal data goes to a person, and a write the database refuses ends the run at once. Stage 2: the answer envelope's query runs through graders 1 to 6 again, then the final-answer grader, then the reviewer agent; a failure retries, up to 3 attempts. A red band on top: the stop before every model call and every tool call](diagrams/verification-layers.svg)

*Notice the order: the reviewer only ever sees an answer that every grader passed, and the stop before the model call can end the run at any point.*

The section ends with the spine question passing every grader and failing the gold check. Graders
prove a query is safe and well formed, not that it means what the business means. The gold check
is what [Section 4: Hill-climbing loop](../section-4-hill-climbing-loop/README.md) measures with.
Results of the class runs go on the [evidence page](../docs/evidence/section-2-verification-loop.md).

## How to work through this section

| Part | What it gives you | In class |
|---|---|---|
| [concepts.md](concepts.md) | Defense layers, graders, caps, and the reviewer | Minutes 0-24 |
| [demo/](demo/README.md) | Malicious SQL, the retry cap, and every grader passes, still wrong, live | Minutes 24-36 |
| [demo/walkthrough.md](demo/walkthrough.md) | The guard, the executor, the cap, and the reviewer | Minutes 36-42 |
| [assignment/](assignment/README.md) | Assignment 2: Verification loop, two new graders | After class |
| [post-class-reading/](post-class-reading/README.md) | Readings on SQL safety and evaluation | After class |
| [session-notes.md](session-notes.md) | What class showed, questions, what to try next | After class |

In class, every demo result on the console shows a live stamp: its run's start time in the
viewer's local time and its LangSmith trace link. The `demo/expected/` folder is for you
after class; it is never opened in class.

## Where next

- First time here? Install everything with [setup/](../setup/README.md), then run the
  [demos](demo/README.md).
- Already set up? Start with [concepts.md](concepts.md).
- Previous section: [Section 1: Agent loop](../section-1-agent-loop/README.md).
- Next section: [Section 3: Event loop](../section-3-event-loop/README.md). Answers are now safe,
  but someone still has to decide who asks, when, and who may approve.

## Sources

- Source 1: LangChain SQL agent, <https://docs.langchain.com/oss/python/langchain/sql-agent>, LangChain, n.d.
- Source 2: PostgreSQL Error Codes, <https://www.postgresql.org/docs/current/errcodes-appendix.html>, PostgreSQL Global Development Group, n.d.
- Source 3: Semantic Evaluation for Text-to-SQL with Distilled Test Suites, <https://arxiv.org/abs/2010.02840>, Ruiqi Zhong et al., 2020-10-06
