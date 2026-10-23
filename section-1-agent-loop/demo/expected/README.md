# Module: Loop Engineering - Expected output for Section 1: Agent loop

Real captures from live runs on 22 October 2026 (business date 31 January 2026), for comparison
after class. They are never shown in class: in class, every demo runs live.

Your output will differ: run times, ids, and the agent's wording change on every run.

## The simple question

![The Agent page after the simple question: the posted run, its three tool calls, the live stamp with the trace link, the Structured Query Language (SQL) query, and the answer](agent-simple-question-answer.png)

*The analyst lists the tables, describes one, runs one query, and answers 405,738 orders.*

Notice the live stamp above the SQL ("Started" and "Open trace in LangSmith"): every result in a
demo is a fresh run. The matching terminal text is in
[agent-simple-question-terminal.txt](agent-simple-question-terminal.txt).

Trace: [run 3246b3e9](https://smith.langchain.com/o/10fe45d9-7a3d-4f39-92ad-8c5dc97653d4/projects/p/7ce7a82b-8edc-4fb1-b6bc-d13fe6070f5e/r/3246b3e9-5797-4365-8376-59d05054d28b?poll=true)

## The confident wrong answer

![The Agent page after the spine question: the run holding for approval and its tool calls](agent-confident-wrong-answer-run.png)

*The spine question under the starting knowledge: the analyst answers with a number.*

The spine question is "What was our net revenue in fiscal year 2025?". Notice the run is held for
approval: the reviewer raised a concern, but the analyst still answered with a number.

![The annotated SQL with trap notes for the fiscal year, Eastern time, and internal accounts, the answer, and the gold check showing a mismatch](agent-confident-wrong-answer-sql.png)

*Each wrong fragment of the SQL carries its trap note.*

The SQL reads calendar year 2025, compares Coordinated Universal Time (UTC) timestamps, and keeps the internal accounts. The
answer, 72,416,127.49 dollars, does not match gold, 64,015,091.21 dollars.

![The answer against gold: the agent's value, the gold value, and the mismatch on both databases](agent-confident-wrong-answer-gold.png)

*The gold check fails on both warehouse and warehouse_alt.*

Trace: [run bd50f9ca](https://smith.langchain.com/o/10fe45d9-7a3d-4f39-92ad-8c5dc97653d4/projects/p/7ce7a82b-8edc-4fb1-b6bc-d13fe6070f5e/r/bd50f9ca-cd1e-4575-b17b-89a8bc033e01?poll=true)
