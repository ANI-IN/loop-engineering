# Chapter 2: Section 2: Verification loop

The verification loop stops unsafe Structured Query Language (SQL) and bounds the agent's retries.
Then it passes every grader on the answer to the fiscal year 2025 revenue question, and the answer is still wrong. You run each demo
from the demo terminal and watch it on the console's Verify page. Every screenshot in this chapter
comes from the live runs of 24 October 2026, from 13:54 Coordinated Universal Time (business date
31 January 2026), except two retaken on 25 October 2026 (the retry cap and the trap notes) and the
missing retry cap's image, taken on 26 October 2026, and every time range from the calibration's
run-through of the demos on 22 and 23 October 2026 and the live sessions of
23, 24, and 25 October.

> Your output will differ: run times, ids, and the agent's wording change on every run.

### Step 1: Send the malicious statements to the fixed system

**Where:** The demo terminal, in the repository folder, and the console's Verify page.

**Type:** this, or press **Send malicious SQL** on the Verify page.

```bash
make demo NAME=verify-malicious-sql
```

**You should see:** the **Defense layers** panel, one block per statement, each with the layer
that stopped it.

![The Verify page's defense layers for three statements: the guard stops the stacked statements on parse, the guard's statement policy stops the data-modifying CTE, and the role grants stop the raw DELETE with SQLSTATE 42501; 0 tokens](../../section-2-verification-loop/demo/expected/verify-malicious-sql-layers.png)

*Run 5a2b10bb, 24 October 2026: the syntax-tree guard stops two statements before execution, and the role grants stop the third.*

**Look at:** the red **Stopped it** line under each statement, and which layer it names.

**What it means:** the guard parses each statement before it runs. The raw DELETE is sent with the
read-only default switched off on purpose, so it reaches the database, and the role's grants refuse
it (SQLSTATE 42501). No model call is made: the run shows 0 tokens.

> [!CHECKPOINT]
> Every statement shows **Stopped it**, and no statement changed a row.

> [!IFDIFFERENT]
> A layer you did not expect → the run was sent with `PLANTED=1`; send it again without it.
> The panel is empty → scroll up to the run's status; reset with `make reset NAME=verification-loop` and run it again.

> [!INSTRUCTOR]
> Only timings vary in this demo. Say: "The prompt never sees these statements. Code and grants
> stop them."

### Step 2: Send them again with the naive guard planted

**Where:** The demo terminal, and the Verify page.

**Type:** this. `PLANTED=1` turns the naive guard on for this demo's own runs only; `.env` keeps
every planted flag at `0`.

```bash
make demo NAME=verify-malicious-sql PLANTED=1
```

**You should see:** both statements pass the naive guard, and a deeper layer stops each one. The
terminal only prints the queued run's id; the captured run's defense layers, as the Verify page
shows them, in text:

```text
statement: SELECT 1; DELETE FROM orders
  guard: statement_policy: passed through: starts with select or with
  read-only transaction: stopped it: SQLSTATE 25006: cannot execute DELETE in a read-only transaction
  stopped by: read-only transaction
statement: WITH d AS (DELETE FROM orders RETURNING *) SELECT count(*) FROM d
  guard: statement_policy: passed through: starts with select or with
  read-only transaction: stopped it: SQLSTATE 25006: cannot execute SELECT in a read-only transaction
  stopped by: read-only transaction
statement: DELETE FROM orders
  role grants: stopped it: SQLSTATE 42501: permission denied for table orders
  stopped by: role grants
orders before 405738, after 405738: unchanged True
```

![The defense layers with the naive guard planted: two statements pass the guard's statement policy and the read-only transaction stops each with SQLSTATE 25006, then the role grants stop the raw DELETE with 42501](../../section-2-verification-loop/demo/expected/verify-malicious-sql-naive-guard-layers.png)

*Run 65a1ebe3, 24 October 2026: with the naive guard, the read-only transaction stops the first two statements; the grants still stop the third, on the frame's last line.*

**Look at:** the last line: the order count before and after.

**What it means:** a guard that checks how a statement starts is not a boundary. The read-only
transaction and the role's grants are, and no order row changes.

> [!CHECKPOINT]
> The order count is the same before and after: the defense check ends with `unchanged True`.

> [!IFDIFFERENT]
> The guard still stops the statements → the run was sent without `PLANTED=1`; run `make demo NAME=verify-malicious-sql PLANTED=1`.
> A row count changed → stop the demo and tell the class; this is a security failure, not a varied result.

> [!INSTRUCTOR]
> Nothing to switch back: the naive guard was on for that one demo's runs only. Say: "Defense in
> depth: the layer you forgot is caught by the next one."

### Step 3: Inject a grader that always fails

**Where:** The demo terminal, and the Verify page.

**Type:** this, or press **Inject failing grader** on the Verify page.

```bash
make demo NAME=verify-retry-cap
```

**You should see:** the run goes back to the agent after each failed check, and stops after 3
attempts (`limits.max_retries` in `platform/packs/datapilot_us/pack.yaml`). It ends escalated, with
every reason.

![The Verify page after the retry cap demo: the checklist on attempt 3 of 3 with the injected grader failed, the line Stopped at the cap: escalated, and the tokens line](../../section-2-verification-loop/demo/expected/verify-retry-cap-escalated.png)

*25 October 2026: the injected grader fails every attempt; the cap stops the run after attempt 3 of 3 and it ends escalated, at 12,910 of the 60,000 tokens a run may use.*

**Look at:** the attempt count and the run's final status, **Escalated**.

**What it means:** a loop that cannot stop on its own costs money on every turn. The cap ends it,
and a person sees why.

> [!CHECKPOINT]
> The run ends escalated after 3 attempts.

> [!IFDIFFERENT]
> The run keeps going → the run was sent with `PLANTED=1`; send it again without it.
> The run ends in fewer attempts → read its reasons; a model or token cap may have ended it first.

> [!INSTRUCTOR]
> In calibration this demo escalated after 3 attempts in both runs. If time allows, show the planted
> half with `make demo NAME=verify-retry-cap PLANTED=1`: the cost counter keeps climbing until the
> 60,000-token cap per run (13 attempts on 25 October 2026).

![The Verify page with the missing retry cap planted: the checklist past attempt 3, the run still verifying, and the tokens bar climbing](../../section-2-verification-loop/demo/expected/verify-retry-cap-no-cap-climbing.png)

*With the missing retry cap the run is past attempt 3 and still going; the tokens line keeps climbing toward the cap of 60,000 tokens per run. Here: attempt 7, 31,095 tokens.*

### Step 4: Ask the fiscal year 2025 revenue question through every grader

**Where:** The demo terminal, and the Verify page.

**Type:** this, or press **Ask the spine question** on the Verify page.

```bash
make demo NAME=verify-graders-pass-still-wrong
```

**You should see:** the checklist turns green, the gold check fails, and the reviewer gives its
verdict.

![The run holding for approval with the line that it waits for a person's approval, the checklist on attempt 2 of 3 with all seven graders passed, the agent's answer 72394572.08 against gold 64015091.21 with a mismatch on both databases, and the reviewer's concern that the query assumes fiscal year 2025 is the calendar year](../../section-2-verification-loop/demo/expected/verify-graders-pass-still-wrong-checklist.png)

*Run ccfd37fb, 24 October 2026: all seven graders pass on attempt 2 of 3, the gold check fails on both databases, and the reviewer's concern holds the run.*

**Look at:** the green checklist on the left, then **Mismatch** on the right.

**What it means:** the graders check that the query is safe and well formed. None of them knows
what "fiscal year 2025" means at Harbor & Pine. The reviewer's concern holds the answer for human
approval. In the captured run the answer hedged and still gave a number: "The warehouse does not
define a fiscal calendar, so I cannot confirm the organization's fiscal-year convention.", then,
assuming fiscal year 2025 is the calendar year in Coordinated Universal Time, 72,394,572.08
dollars.

> [!CHECKPOINT]
> Every checklist line reads **Passed**, and the gold check reads **Mismatch**.

> [!IFDIFFERENT]
> The reviewer approves → expected sometimes; in calibration it raised a concern in 6 of 7 runs and approved in 1.
> No **Answer against gold** block after about a minute → reset with `make reset NAME=verification-loop` and run it again.

> [!INSTRUCTOR]
> Ask: "If every grader passes, is the answer right?" Let the screen answer. Then say which way the
> reviewer went in this run.

### Step 5: Read the trap notes

**Where:** The Verify page; scroll down below the checklist.

**Type:** nothing; scroll.

**You should see:** the query with numbered marks and one note per trap.

![The annotated query of a run of the same demo: mark 1 after both calendar-year bounds, mark 2 on orders, mark 3 on both order_ts comparisons, and mark 4 on WHERE; four trap notes for the fiscal year, cancelled orders, Eastern time, and internal accounts; 17,605 tokens](../../section-2-verification-loop/demo/expected/verify-graders-pass-still-wrong-sql.png)

*25 October 2026, a different run of the same demo from the checklist above: the query that passed every grader on attempt 2, each of its four trap notes numbered on a fragment.*

1. Trap: Fiscal year. The query reads calendar year 2025; mark 1 follows both bounds.
2. Trap: Cancelled orders. The query has no status filter, so it keeps cancelled orders; mark 2
   is on `orders`.
3. Trap: Eastern time. `order_ts` is compared in Coordinated Universal Time (UTC).
4. Trap: Internal accounts. The query keeps the staff and test accounts; mark 4 is on `WHERE`.

**Look at:** the tokens line at the bottom: 17,605 tokens and 0.0018 dollars in the captured run.

**What it means:** a grader can only check what someone wrote down. The missing business rules
are the case for Section 4: Hill-climbing loop.

> [!CHECKPOINT]
> You can match each mark in the query to its note.

> [!IFDIFFERENT]
> Fewer traps marked → expected; which traps the query hits varies.

> [!INSTRUCTOR]
> Say: "Verification makes the loop safe and bounded. It does not make it right."

## Result summary

| Item | This run |
|---|---|
| The fiscal year 2025 revenue question against gold, both databases | Mismatch, with every grader passed (headline) |
| Malicious statements, fixed system | Guard, guard, then role grants (42501) |
| Malicious statements, naive guard | Read-only transaction twice (25006), then role grants (42501) |
| Order rows changed | None: 405,738 before and after |
| Reviewer on the answer to the fiscal year 2025 revenue question, secondary | Concern, held for human approval |

## Time and cost

Times are wall time from the trigger to the checked result, from the calibration's run-through of the demos on 22
and 23 October 2026 and the live sessions of 23, 24, and 25 October
(`docs/calibration-report.md`), each demo run alone with a reset between.

| Demo | Time | Cost of the captured run | Cap |
|---|---|---|---|
| Malicious SQL | 2 to 6 seconds | 0 tokens | No model call |
| The retry cap | 14 to 79 seconds | 0.0006 dollars | 3 attempts; 60,000 tokens per run |
| Every grader passes, still wrong | 48 to 58 seconds; shown in 4 of 5 later runs, then on 24 and 25 October | 0.0018 dollars | 60,000 tokens per run |

"Later runs" are those after the change that keeps one run's gold check from blocking another. In
the one not shown, on the evening of 23 October, every grader passed but the run posted with no
gold check within 214 seconds; the cause is not yet confirmed, and the retry showed the moment. If
it happens in class, reset and run it again.

## What to say in class

- "Code and grants stop unsafe statements; a prompt rule would not."
- "The naive guard let two statements through, and the next layer still stopped them."
- "The retry cap turns an endless loop into an escalation a person can read."
- "Every grader passed and the answer is wrong. The graders check safety, not meaning."
- If the reviewer approved: "The reviewer is a model too. It catches some guesses, not all."
