# Module: Loop Engineering - Expected output for Section 1: Agent loop

Real captures from live runs on 23 October 2026 in Coordinated Universal Time (business date 31
January 2026), for comparison after class, sent from the console's buttons. They are never shown in class: in class, every demo
runs live. Times on the captures are in Coordinated Universal Time (UTC); the console shows your
own local time. The build's LangSmith traces are private, so each capture names its run id instead
of a trace link.

Your output will differ: run times, ids, and the agent's wording change on every run.

## The simple question

![The Agent page after the simple question: the Ask button, the posted run, its three tool calls, the live stamp with the trace link, the Structured Query Language (SQL) query, "No trap found in this query", and the answer 405738 orders](agent-simple-question-answer.png)

*The analyst lists the tables, describes one, runs one query, and answers 405,738 orders.*

Notice the live stamp above the SQL ("Started" and "Open trace in LangSmith"): every result in a
demo is a fresh run. The detail of an earlier run of the same demo (run 3246b3e9, 22 October 2026)
as text (question, SQL, answer, tokens, and trace) is in
[agent-simple-question-terminal.txt](agent-simple-question-terminal.txt). It is not terminal
output: `make demo NAME=agent-simple-question` prints only the run's id, and you read the answer on
the console.

Trace: run c25c1106

## The confident wrong answer

![The Agent page after the spine question: the run holding for approval with the line that it waits for a person's approval, its five tool calls including the schema scout twice, the live stamp, and the start of the annotated SQL](agent-confident-wrong-answer-run.png)

*The spine question under the starting knowledge: the run holds for approval, and the analyst still answers with a number.*

The spine question is "What was our net revenue in fiscal year 2025?". Notice the run is held for
approval: the reviewer raised a concern, but the analyst still answered with a number. Under the
status, the console says what the run waits for: a person's approval on the Events page.

![The annotated SQL from the live stamp down: numbered marks on WHERE, both order_ts comparisons, and both fiscal-year bounds; three trap notes for the fiscal year, Eastern time, and internal accounts; the answer; and the gold check showing a mismatch on both databases](agent-confident-wrong-answer-sql.png)

*Every trap note has its number on a fragment of the SQL; note 1 marks both bounds of the calendar-year range.*

The SQL reads calendar year 2025, compares Coordinated Universal Time timestamps, and keeps the
internal accounts. The answer, 72,394,572.08 dollars, does not match gold, 64,015,091.21 dollars.

![The answer against gold: the agent's value 72394572.08, the gold value 64015091.21, and the mismatch on both databases](agent-confident-wrong-answer-gold.png)

*The gold check fails on both warehouse and warehouse_alt.*

This image is cropped at its top edge, below the note above it, so that no note is cut; the page's
navigation bar is outside it.

Trace: run e6e3170a

The same session's two other runs of the spine question show how the answer varies: one answered
with a six-column breakdown by status, which failed gold on its shape (run 456efa67); the other said
the warehouse does not define the fiscal year and gave no number, so it got no gold check (run
d8d884a3).
