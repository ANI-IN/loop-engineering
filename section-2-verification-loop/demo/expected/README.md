# Module: Loop Engineering - Expected output for Section 2: Verification loop

Real captures from live runs on 22 October 2026 (business date 31 January 2026), for comparison
after class. They are never shown in class: in class, every demo runs live. The captures show
Structured Query Language (SQL) queries, with times in Coordinated Universal Time (UTC).

Your output will differ: run times, ids, and the agent's wording change on every run.

## Malicious SQL

![The Verify page's defense layers for three malicious statements: the syntax-tree guard stops the stacked statements and the data-modifying CTE, and the role grants stop the raw delete](verify-malicious-sql-layers.png)

*With the fixed system, the syntax-tree guard stops two statements and the role grants the third.*

The syntax-tree guard stops the stacked statements (two statements) and the data-modifying CTE (a
DELETE inside the query) before execution. The raw DELETE, sent with the read-only default switched
off on purpose, is refused by the role's grants with SQLSTATE 42501.

![The defense layers with the naive guard planted: two statements pass the guard and the read-only transaction stops them with 25006, then the role grants stop the raw delete with 42501](verify-malicious-sql-naive-guard-layers.png)

*With the naive guard planted: 25006 from the read-only transaction first, then 42501 from the grants.*

Both statements pass the naive guard, and the read-only transaction refuses them first with
SQLSTATE 25006; only the raw DELETE, with the read-only default switched off, meets the grants and
gets 42501. No order row changes:
[verify-malicious-sql-naive-guard-terminal.txt](verify-malicious-sql-naive-guard-terminal.txt).
Trace: [run 57b7a363](https://smith.langchain.com/o/10fe45d9-7a3d-4f39-92ad-8c5dc97653d4/projects/p/7ce7a82b-8edc-4fb1-b6bc-d13fe6070f5e/r/57b7a363-d682-4516-a713-f7f8e8fd7874?poll=true)

Trace: [run a3908620](https://smith.langchain.com/o/10fe45d9-7a3d-4f39-92ad-8c5dc97653d4/projects/p/7ce7a82b-8edc-4fb1-b6bc-d13fe6070f5e/r/a3908620-d2f8-4135-bf1e-2f69c5f7cae2?poll=true)

## Every grader passes, still wrong

![The checklist with every grader passed, the answer against gold showing a mismatch on both databases, and the reviewer's concern about the fiscal year](verify-graders-pass-still-wrong-checklist.png)

*Every grader passes; the gold check fails on both databases; the reviewer raises a concern.*

The reviewer's concern is that no fiscal-year definition is provided; it holds the answer for human
approval.

![The annotated SQL with its trap notes below the checklist](verify-graders-pass-still-wrong-sql.png)

*The SQL with its trap notes.*

Calendar year 2025 instead of fiscal year 2025, UTC timestamps, and cancelled orders and internal
accounts left in.

Trace: [run dc6dfa84](https://smith.langchain.com/o/10fe45d9-7a3d-4f39-92ad-8c5dc97653d4/projects/p/7ce7a82b-8edc-4fb1-b6bc-d13fe6070f5e/r/dc6dfa84-c787-45d3-af1e-a523d91b30f5?poll=true)
