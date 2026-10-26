# Chapter 1: Section 1: Agent loop

The analyst answers a plain question correctly, then answers the fiscal year 2025 revenue question, "What was our net
revenue in fiscal year 2025?", with a confident number that is wrong. Nothing in the agent loop
checks it yet. You run each demo from the demo terminal and watch it on the console's Agent page.
Every screenshot in this chapter comes from the live runs of 25 October 2026, from 14:43
Coordinated Universal Time (business date 31 January 2026), and every time range from the
calibration's run-through of the demos on 22 and 23 October 2026 and the live sessions of 23,
24, and 25 October.

> Your output will differ: run times, ids, and the agent's wording change on every run.

### Step 1: Ask the simple question

**Where:** The demo terminal, in the repository folder, and the console's Agent page at
http://localhost:8501.

**Type:** this, or press **Ask** on the Agent page.

```bash
make demo NAME=agent-simple-question
```

**You should see:** one terminal line with the queued run's id, then the run on the Agent page. The
captured run's detail, as the Agent page shows it:

```text
question: How many orders have been placed in total?
run id: 87a06dba-2a3b-4d02-b122-50c41f3d92bc
status: posted
tool calls: list_tables, describe_table, run_query
final SQL: SELECT COUNT(*) AS total_orders FROM orders;
answer: A total of 405738 orders have been placed.
tokens: 5151; cost $0.0005
model: gpt-6-luna; knowledge version: v1
```

![The Agent page after the simple question: Posted, the tool calls list_tables, describe_table, and run_query, 1.4 seconds in total, the live stamp, the one-line count query, No trap found in this query, the answer 405738 orders, and 5,151 tokens](../../section-1-agent-loop/demo/expected/agent-simple-question-answer.png)

*25 October 2026: the analyst lists the tables, describes one, and runs one query; the live stamp, the query, and the answer are all in the frame.*

**Look at:** the tool timeline, then the live stamp "Started ..." above the query. With traces
flowing it ends in "Open trace"; in this capture LangSmith had refused traces at its monthly
limit, so it reads "Trace not received".

**What it means:** with no trap in the question, the agent loop alone is enough: three tool calls,
one query, a correct count. The live stamp shows this result comes from a run started just now.

> [!CHECKPOINT]
> The page says **Posted**, the answer is a count, and the live stamp shows this run's start time.

> [!IFDIFFERENT]
> `No live session is open: run make preflight PURPOSE=class|rehearsal|thursday-review|development first` → run `make preflight PURPOSE=class` once (Part 0).
> The run stays in one place → `make reset NAME=agent-loop`, then the same `make demo` again.
> More or fewer tool calls → expected; the number of tool calls can vary.

> [!INSTRUCTOR]
> Point at the timeline first, then the query, then the tokens and cost line (5,151 tokens and
> 0.0005 dollars in the captured run). Say: "This is the loop you already know. The next question
> looks just as simple."

### Step 2: Ask the fiscal year 2025 revenue question

**Where:** The demo terminal, and the Agent page.

**Type:** this, or press **Ask the spine question** on the Agent page.

```bash
make demo NAME=agent-confident-wrong-answer
```

**You should see:** the run with its status line and its tool timeline. In the captured run the
analyst also called the schema scout.

![The Agent page after the fiscal year 2025 revenue question: the status line at the report-only level, Holding for approval, the line that the run waits for a person's approval, and the tool calls list_tables, scout_schema, two describe_table calls, and run_query, 20.3 seconds in total](../../section-1-agent-loop/demo/expected/agent-confident-wrong-answer-run.png)

*25 October 2026: under version 1 of the knowledge (the starting version) the run holds for a person's approval; the schema scout takes 11.1 of the 20.3 seconds of tool time.*

**Look at:** the status, **Holding for approval**, and the `scout_schema` bar in the timeline.

**What it means:** the reviewer raised a concern, so the run waits for a person. The analyst
answered anyway. In the captured run its answer was one number, 72,394,572.08 dollars, which it
said was for calendar year 2025 in Coordinated Universal Time (UTC), because the warehouse defines
no fiscal calendar. Nothing in this loop tells you whether it is right.

> [!CHECKPOINT]
> The run has a status and a timeline; the answer text appears below the query once it finishes.

> [!IFDIFFERENT]
> The status reads **Posted** instead of holding → the reviewer's verdict varies; go on, the gold check still decides.
> The page still says "Running the agent" after about a minute → scroll down; then reset and run it again if nothing changes.

> [!INSTRUCTOR]
> Ask the class to guess the number before it appears. Do not explain the hold yet: Section 2:
> Verification loop covers the reviewer.

### Step 3: Read the annotated query

**Where:** The Agent page; scroll down to the query and its trap notes.

**Type:** nothing; scroll.

**You should see:** the query, with numbered marks on its wrong fragments and one note per trap.

![The annotated query: marks 1 on both calendar-year bounds, 2 on both order_ts comparisons, and 3 on WHERE, the Fiscal year, Eastern time, and Internal accounts notes, the answer for calendar year 2025, and the mismatch against gold](../../section-1-agent-loop/demo/expected/agent-confident-wrong-answer-sql.png)

*25 October 2026: mark 1 after both calendar-year bounds, mark 2 on both order_ts comparisons, and mark 3 on WHERE, each with its note.*

1. Trap: Fiscal year. The query reads calendar year 2025; fiscal year 2025 ends on 31 January 2025.
2. Trap: Eastern time. `order_ts` is stored in UTC and is compared without converting it to New
   York time.
3. Trap: Internal accounts. The query keeps the staff and test accounts on the company email domain.

**Look at:** the answer line under the notes: the analyst itself says it read the calendar year.
The captured query keeps `status = 4`, which leaves out cancelled orders, so that filter has no
mark.

**What it means:** the query is valid, safe, and plausible. Each mistake is a business rule the
schema does not show.

> [!CHECKPOINT]
> You can name at least one trap from its note.

> [!IFDIFFERENT]
> Different trap numbers or fewer notes → expected; which traps the query hits varies from run to run.
> No notes at all → the run has not finished; wait, then scroll again.

> [!INSTRUCTOR]
> Read one trap note aloud. Say: "None of these rules is in the schema. A stronger model guesses
> the same way."

### Step 4: Compare the answer against gold

**Where:** The Agent page; scroll to **Answer against gold**.

**Type:** nothing; scroll.

**You should see:** the agent's answer, the gold answer, and the result on both databases.

![The end of the Agent page: the annotated query and its three notes, the answer for calendar year 2025, the agent's answer 72394572.08 against the gold answer 64015091.21, the mismatch on both databases, and 32,421 tokens and 0.0024 dollars](../../section-1-agent-loop/demo/expected/agent-confident-wrong-answer-gold.png)

*25 October 2026: the gold check fails on warehouse and warehouse_alt; row 1 differs from gold on both.*

**Look at:** the **Mismatch** line.

**What it means:** the answer, 72,394,572.08 dollars, is not the gold 64,015,091.21 dollars. The agent loop gave no sign that it was wrong.

> [!CHECKPOINT]
> The page shows **Mismatch** for both databases.

> [!IFDIFFERENT]
> A different wrong value → expected; the calibration run got 76,981,355.95 dollars against the same gold.
> No **Answer against gold** block after about a minute → the gold check has not arrived; reset with `make reset NAME=agent-loop` and run it again.

> [!INSTRUCTOR]
> This is the section's result: a confident, wrong number. Say what did not go the course's way if
> it happens: the reviewer may approve it, and the gold check still fails.

### Step 5: Run the large query, with and without the row cap

**Where:** The demo terminal and the Agent page.

**Type:** the planted half first, then the fixed half. `PLANTED=1` turns the unbounded rows bug on
for that demo's own runs only; `.env` keeps every planted flag at `0`.

```bash
make demo NAME=agent-unbounded-rows PLANTED=1
make demo NAME=agent-unbounded-rows
```

**You should see:** with the unbounded rows bug on, the token counter jumps. With it off, the
query returns at most the row cap, the total count, and a truncation notice. Over every recorded
run, the fixed half used 17,298 to 30,216 tokens and the planted half 182,654 to 187,030 tokens,
about ten times as many. In the captured fixed run the reviewer held the run with two concerns.

![The Agent page after the large query with the unbounded rows bug on: Escalated, the request to run SELECT * FROM order_items LIMIT 10000, four tool calls, and 184,983 tokens in 7.5 seconds](../../section-1-agent-loop/demo/expected/agent-unbounded-rows-planted-tokens.png)

*25 October 2026, the planted half: every row of the 10,000-row query reaches the model, 184,983 tokens for one run, and the run ends escalated.*

![The Agent page after the large query with the row cap: the tool calls, a ten-row query on orders, No trap found in this query, the ten most recent orders with their totals, and 28,468 tokens](../../section-1-agent-loop/demo/expected/agent-unbounded-rows-fixed-tokens.png)

*25 October 2026, the fixed half: the same steps stay small, 28,468 tokens.*

The truncation notice and the total count are in the run_query result, which the run's trace
holds once LangSmith receives it; in this frame the trace link reads Trace not received.

**Look at:** the tokens line of each run, side by side.

**What it means:** a tool that returns everything spends the run's budget on rows the model cannot
use. The row cap (`limits.row_cap` in `platform/packs/datapilot_us/pack.yaml`) keeps the loop
inside its budget.

> [!CHECKPOINT]
> The fixed half's tokens line is far below the planted half's; its run_query result holds the truncation notice and the total count, in the trace once LangSmith receives it.

> [!IFDIFFERENT]
> The token counter does not move with the bug on → the run was sent without `PLANTED=1`; run `make demo NAME=agent-unbounded-rows PLANTED=1`.
> The run is held by a reviewer concern → expected; it happened in the captured run too. Read its tokens anyway.

> [!INSTRUCTOR]
> Nothing to switch back: the planted bug was on for that one demo's runs only. Point at the
> tokens, not the answer: this demo is about what reaches the model.

## Result summary

| Item | This run |
|---|---|
| The fiscal year 2025 revenue question against gold, both databases | Mismatch (headline) |
| The simple question | Posted, correct count |
| The fiscal year 2025 revenue question's status | Holding for approval, reviewer concern |
| Traps marked on that question's query | Fiscal year, Eastern time, internal accounts |
| Tokens for the simple question, secondary | 5,151 (the captured run) |
| Tokens for the fiscal year 2025 revenue question, secondary | 32,421 (the captured run) |

## Time and cost

Times are wall time from the trigger to the checked result, from the calibration's run-through of the demos on 22
and 23 October 2026 and the live sessions of 23, 24, and 25 October
(`docs/calibration-report.md`), each demo run alone with a reset between.

| Demo | Time | Cost of the captured run | Cap |
|---|---|---|---|
| The simple question | 14 to 39 seconds | 0.0005 dollars | 60,000 tokens per run |
| The confident wrong answer | 35 to 76 seconds | 0.0024 dollars | 60,000 tokens per run |
| Unbounded rows | Planted half 12 to 19 seconds; fixed half 26 to 48 seconds | Fixed half 0.0022 dollars; planted half 0.0230 dollars | 60,000 tokens per run |

## What to say in class

- "The loop works: three tool calls and a correct count for a plain question."
- "The answer to the fiscal year 2025 revenue question is confident, valid, and wrong. Each mistake is a rule the schema hides."
- "Nothing in this loop compares the answer with the truth. The gold check is a measurement, not
  part of the agent."
- "The row cap is a tool decision: what reaches the model shapes every later step."
- If the reviewer approved the wrong answer this time: "The reviewer can miss it. That is
  Section 2."
