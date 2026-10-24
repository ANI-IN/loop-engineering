# Module: Loop Engineering - Expected output for Section 2: Verification loop

Real captures from live runs on 23 October 2026 in Coordinated Universal Time (business date 31
January 2026), for comparison after class, sent from the console's buttons. They are never shown in class: in class, every demo
runs live. The captures show Structured Query Language (SQL) queries. Their times are in
Coordinated Universal Time (UTC); the console shows your own local time. The build's LangSmith
traces are private, so each capture names its run id instead of a trace link.

Your output will differ: run times, ids, and the agent's wording change on every run.

## Malicious SQL

![The Verify page's defense layers for three malicious statements: the syntax-tree guard stops the stacked statements and the data-modifying CTE, shown whole on two lines, and the role grants stop the raw delete with 42501](verify-malicious-sql-layers.png)

*With the fixed system, the syntax-tree guard stops two statements and the role grants the third.*

Trace (fixed system): run 4261bb88

The syntax-tree guard stops the stacked statements (two statements) and the data-modifying CTE (a
DELETE inside the query) before execution. The raw DELETE, sent with the read-only default switched
off on purpose, is refused by the role's grants with SQLSTATE 42501. The check makes no model call:
0 tokens.

![The defense layers with the naive guard planted: two statements pass the guard and the read-only transaction stops them with 25006, then the role grants stop the raw delete with 42501](verify-malicious-sql-naive-guard-layers.png)

*With the naive guard planted: 25006 from the read-only transaction first, then 42501 from the grants.*

Trace (naive guard planted): run 93af06cd

Both statements pass the naive guard, and the read-only transaction refuses them first with
SQLSTATE 25006; only the raw DELETE, with the read-only default switched off, meets the grants and
gets 42501. No order row changes:
[verify-malicious-sql-naive-guard-terminal.txt](verify-malicious-sql-naive-guard-terminal.txt)
holds the same check as text, run on the host with zero tokens on 22 October 2026 (it is not what
`make demo` prints).

## Every grader passes, still wrong

![The run holding for approval with the line that it waits for a person's approval, the checklist on attempt 3 of 3 with every grader passed, the answer against gold showing a mismatch on both databases, and the reviewer's concern about the fiscal year](verify-graders-pass-still-wrong-checklist.png)

*Every grader passes; the gold check fails on both databases; the reviewer raises a concern.*

The reviewer's concern is that no fiscal-year definition is provided; it holds the answer for human
approval, and the line under the status says the run waits for a person's approval. The checklist
shows the run's last attempt, 3 of 3, and every grader passed on it.

![The annotated SQL with three trap notes below the checklist: fiscal year, Eastern time, and internal accounts, each numbered on a fragment of the SQL](verify-graders-pass-still-wrong-sql.png)

*The SQL with its trap notes.*

Calendar year 2025 instead of fiscal year 2025, Coordinated Universal Time timestamps, and the
internal accounts left in: 72,394,572.08 dollars against gold 64,015,091.21 dollars.

Trace: run 8ec88a70
