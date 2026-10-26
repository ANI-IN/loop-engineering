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
read-only role, and a statement timeout each assume the layer above them fails. Graders run
before execution, after execution, and on the final answer, and send their reasons back to the
agent; a retry cap ends the loop. In the diagram, Stage 1 checks each query and Stage 2 checks
the answer. A write the database
refuses is never sent back: the run ends at once as escalated, with no retry. After every grader
passes, an independent reviewer reads the result.

![Two stages of checks. Stage 1: each query passes the parse, statement policy, schema, cost, and personal data graders, then the read-only executor and the execution grader; a block sends feedback to the analyst, personal data goes to a person, and a write the database refuses ends the run at once. Stage 2: the answer envelope's query runs through graders 1 to 6 again, then the final-answer grader, then the reviewer agent; a failure retries, up to 3 attempts. A red band on top: the stop before every model call and every tool call](diagrams/verification-layers.svg)

*Notice the order: the reviewer only ever sees an answer that every grader passed, and the stop before the model call can end the run at any point.*

The section ends with the fiscal year 2025 revenue question passing every grader and failing the
gold check. Graders prove a query is safe and well formed, not that it means what the business
means. The gold check is what
[Section 4: Hill-climbing loop](../section-4-hill-climbing-loop/README.md) measures with. The full
idea is in [concepts.md](concepts.md) (in class, minutes 0 to 24).

## How to work through this section

### How it works in the code

- [`QueryChecker.check`](../platform/src/datapilot/loop2_verification/checker.py) runs the
  graders before execution, then the read-only executor, then the execution grader.
- [`StatementPolicyGrader`](../platform/src/datapilot/loop2_verification/graders/statement_policy.py)
  is the syntax-tree guard; `NaiveGuard` in the same file is the planted first-word check.
- [`Executor`](../platform/src/datapilot/loop2_verification/executor.py) runs every query in a
  read-only transaction, under the agent role and a statement timeout.
- [`VerificationLoop`](../platform/src/datapilot/loop2_verification/loop.py) sends grader reasons
  back to the agent, and `attempt_allowed` in `limits.py` enforces `limits.max_retries`.
- [`Reviewer`](../platform/src/datapilot/loop2_verification/reviewer.py) reads the question, the
  query, and the result once every grader has passed.

The [walkthrough](demo/walkthrough.md) explains these lines (minutes 36 to 42).

### The demo

Three core demos, live, in minutes 24 to 36: malicious SQL (`verify-malicious-sql`) shows which
layer stopped each statement; the retry cap (`verify-retry-cap`) shows the cost counter stop at
the cap; every grader passes, still wrong (`verify-graders-pass-still-wrong`) shows a green
checklist beside a failed gold check. Every result carries a live stamp. Run them with the
[demo page](demo/README.md); the measured runs are on the
[evidence page](../docs/evidence/section-2-verification-loop.md).

### The assignment

[Assignment 2: Verification loop](assignment/README.md) adds two graders: one that asks back when
a question uses a business term the knowledge does not define, and one that blocks an email
address or phone number in an answer nobody approved. It is done when
`make check-assignment NAME=verification-loop` reads PASS on every line. Effort: about 2 hours;
the cost of a check is on the [costs page](../docs/costs.md#assignments).

### Apply it in a real system

- Make the database role the boundary: read-only, with a statement timeout. A parser is a second
  layer, never the only one.
- Cap retries in code, send each grader's reason back, and end a run at once on a refused write.
- Judge meaning with hand-written gold results on more than one database; graders cannot.

### Further reading

The [reading list](post-class-reading/README.md) has three: why one database is not proof, least
privilege and allow-lists, and database error codes as feedback.

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
