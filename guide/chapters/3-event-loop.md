# Chapter 3: Section 3: Event loop

The same analyst now runs from events: a webhook, an export request, a repeated delivery, and a
stop. You watch runs move across the run board on the console's Events page, an approval survive
a worker restart, three deliveries become one answer, and the kill switch stop a run in flight.
Every screenshot in this chapter comes from the live runs of 24 October 2026, 13:56 to 14:09
Coordinated Universal Time, or of 25 October 2026, from 14:49, as each caption says (business date
31 January 2026), and every time range from the calibration's run-through of the demos on 22 and 23 October 2026
and the live sessions of 23, 24, and 25 October.

> Your output will differ: run times, ids, and the agent's wording change on every run.

### Step 1: Send the webhook question

**Where:** The demo terminal, in the repository folder, and the console's Events page.

**Type:** this, or press **Send webhook question** on the Events page.

```bash
make demo NAME=events-webhook-question
```

**You should see:** the status line at the report-only level, and one run that moves across the
lanes to **Done**.

![The Events page: the status line at the report-only level with no family cleared, the run board with one posted run, the question about the previous day's orders, in Done, the empty off-the-board lanes, and the row of buttons](../../section-3-event-loop/demo/expected/events-webhook-question-board.png)

*Run ce15ac5d, 24 October 2026: the webhook question becomes an event and a job, and moves to Done, posted at the report-only level.*

**Look at:** the run's card in **Done**: "Posted at the report-only level" and its live stamp.

**What it means:** the question arrived over Hypertext Transfer Protocol (HTTP), not from a person
at the console. The router turned it into a job, and a worker ran the same analyst as in Section 1:
Agent loop.

> [!CHECKPOINT]
> One card in **Done**, and the off-the-board lanes say "No runs".

> [!IFDIFFERENT]
> The card stops in **Holding for approval** → the reviewer raised a concern; in one calibration run it did not know the business date. Reset with `make reset NAME=event-loop` and run it again.
> No card appears → check `make ps`; the worker must be up.

> [!INSTRUCTOR]
> Point at the status line first: autonomy level, unattended clearance, business date, tokens
> today. Say: "Nothing here is an agent deciding where work goes. The router is a table."

### Step 2: Read the post in the channel

**Where:** The Events page; scroll down to **Channel**.

**Type:** nothing; scroll.

**You should see:** the answer, labelled with its level.

![The Events page scrolled to the Channel: the baseline benchmark strip in Done, the empty off-the-board columns, the buttons, and the Channel's one post, Posted at the report-only level, unverified, with the answer 300 orders](../../section-3-event-loop/demo/expected/events-webhook-question-channel.png)

*25 October 2026, a different run of the same demo from step 1: the post is labelled "Posted at the report-only level, unverified", and its answer is 300 orders.*

**Look at:** the label "Posted at the report-only level, unverified".

**What it means:** at the report-only level, DataPilot posts what it found and says it is not
verified. The question's day is the previous business day, 30 January 2026.

> [!CHECKPOINT]
> The post carries the report-only label.

> [!IFDIFFERENT]
> A different count → read the run's query from its trace link; the wording and the count can vary.

> [!INSTRUCTOR]
> Say: "Every post says how much it was trusted. The level is earned in Section 4: Hill-climbing
> loop."

### Step 3: Request the California export

**Where:** The demo terminal, and the Events page.

**Type:** this, or press **Request California export** on the Events page.

```bash
make demo NAME=events-approval-survives-restart
```

**You should see:** a new card in **Holding for approval**, with a **Review** button.

![The run board with the export, Export the California customers who may receive marketing, in Holding for approval, its reason starting the query reads personal, its live stamp, and its Review button](../../section-3-event-loop/demo/expected/events-approval-held.png)

*25 October 2026: the California marketing export reads personal data, so the run holds before its query runs. Steps 4 and 5 show a run of the same demo from 24 October.*

**Look at:** the card's reason line, which starts "the query reads personal".

**What it means:** the query returns customers' emails and names, so it waits for human approval
before it runs.

> [!CHECKPOINT]
> The card is in **Holding for approval** and shows **Review**.

> [!IFDIFFERENT]
> The card goes straight to **Done** → the query returned no personal column; read its query from the trace link, then reset and run it again.

> [!INSTRUCTOR]
> Do not approve yet. Say: "This approval may wait an hour. What happens if the worker restarts
> meanwhile?"

### Step 4: Restart the worker

**Where:** The Events page.

**Type:** press **Restart worker**.

**You should see:** a line under the buttons about the pending approval.

![After Restart worker: the export still in Holding for approval and the line Worker restart requested. The pending approval survived: run b1b1453b still holding. above an empty Channel](../../section-3-event-loop/demo/expected/events-approval-after-restart.png)

*24 October 2026: the worker restarts, and the Postgres checkpointer keeps the pending approval.*

**Look at:** "The pending approval survived".

**What it means:** the run's state is in Postgres, not in the worker's memory, so a restart does not
lose it.

> [!CHECKPOINT]
> The card is still in **Holding for approval** after the restart.

> [!IFDIFFERENT]
> **Restart worker** does nothing → demo controls are off; set `DATAPILOT_ALLOW_DEMO_CONTROLS=1` in `.env`, then `make up` (a setting, not a planted flag).

> [!INSTRUCTOR]
> Point at the run's short id in the line, then at the same card on the board.

### Step 5: Review and approve

**Where:** The Events page, on the held card.

**Type:** press **Review** on the card, read the dialog, then approve.

**You should see:** the dialog with the exact query and its row count; after approval, the run
resumes and the export is posted.

![The Review dialog, Approve this export?, with the row estimate, the reason it holds, the exact query, and the Approve and run and Reject buttons](../../section-3-event-loop/demo/expected/events-approval-review-dialog.png)

*25 October 2026, a third run of the same demo: before anything runs, the dialog states the exact query, about how many rows it returns, and why it holds: the query reads personal data.*

![After approval: the export posted in Done, the line Worker restart requested. Run b1b1453b moved on after the restart., and the post Posted at the report-only level, unverified, with 5,261 California customers who may receive marketing](../../section-3-event-loop/demo/expected/events-approval-approved-posted.png)

*24 October 2026, the run of step 4: approving resumes the same run, and the export is posted: 5,261 customers, a preview of the first 50 rows.*

**Look at:** the line "moved on after the restart" and the new post in the channel.

**What it means:** one approval, given after a restart, resumes the same run where it stopped.

> [!CHECKPOINT]
> The export appears in the channel.

> [!IFDIFFERENT]
> The dialog asks again for a rewritten query → expected when you ask for changes; each new query is approved before it runs, and an approved query is never asked about twice.

> [!INSTRUCTOR]
> In the captured run the reviewer approved the first query. In an earlier run it asked for
> changes, and the analyst rewrote its query three times. Say so if it happens: each version
> still needed a person.

### Step 6: Show the lost approval with the in-memory checkpointer

**Where:** The demo terminal, and the Events page.

**Type:** this, then press **Restart worker**, wait for the worker to come back, and approve the
held export. `PLANTED=1` restarts the worker with the in-memory checkpointer, holds the demo
terminal until the run ends, then restarts the worker without it; Ctrl+C ends the wait sooner.
`.env` keeps every planted flag at `0`.

```bash
make demo NAME=events-approval-survives-restart PLANTED=1
```

**You should see:** after **Restart worker** the card still reads **Holding for approval**: the
run's record is in Postgres. Its checkpoint was in the worker's memory, so when you approve, there
is nothing to resume: the run fails, and the pending approval is lost.

![After Restart worker and approval with the in-memory checkpointer planted: the line that the pending approval was lost and the run failed, above a Channel with no export](../../section-3-event-loop/demo/expected/events-approval-lost-after-restart.png)

*25 October 2026: with the in-memory checkpointer the record still says holding after the restart, but the checkpoint died with the worker: approving fails the run, and the pending approval is lost.*

**Look at:** the line under the buttons after the approval.

**What it means:** state held in process memory dies with the process.

> [!CHECKPOINT]
> You can compare this screen with step 4.

> [!IFDIFFERENT]
> The approval survives → the run was sent without `PLANTED=1`; run `make demo NAME=events-approval-survives-restart PLANTED=1`.

> [!INSTRUCTOR]
> Wait for the terminal's line that it restarted the worker without the demo's flags before the
> next demo. The approval was lost in every recorded run of this half, 24 and 25 October included.

### Step 7: Send the same event three times

**Where:** The demo terminal, and the Events page.

**Type:** this, or press **Send the same event three times** on the Events page.

```bash
make demo NAME=events-duplicate-events
```

**You should see:** one new question run in **Done**, marked with the duplicates it absorbed, and
one digest run.

![The board with Done holding 3 runs, of which the frame shows one: the webhook question about the previous day's orders, posted at the report-only level, marked 2 duplicates absorbed, then 1 more](../../section-3-event-loop/demo/expected/events-duplicate-events-board.png)

*25 October 2026: the question posted once, and its two repeats were absorbed as duplicates.*

**Look at:** "2 duplicates absorbed" on the question's card (in the captured run, the answer was 300
orders).

**What it means:** the event's id is stored once; the second and third deliveries find it and add
nothing. One answer is posted, not three.

> [!CHECKPOINT]
> One new card, and the channel has one new post.

> [!IFDIFFERENT]
> Three cards → the run was sent with `PLANTED=1`, or the board still holds the planted half's runs; `make reset NAME=event-loop`, then run it again.

> [!INSTRUCTOR]
> Say: "Webhooks retry. The effect must happen once, however many times the event arrives."

### Step 8: Show the repeated posts with the missing idempotency

**Where:** The demo terminal, and the Events page.

**Type:** this; `PLANTED=1` turns the missing idempotency on for this demo's own events only. In
class the planted half runs first; reset between the halves.

```bash
make demo NAME=events-duplicate-events PLANTED=1
make reset NAME=event-loop
```

**You should see:** three question runs and two digests, and their posts: three answers to the
same question and two digests for one day.

![The Channel with the missing idempotency planted: four posts in view, two digests for 30 January 2026 with different figures, and two answers of 300 orders to the same question](../../section-3-event-loop/demo/expected/events-duplicate-events-no-idempotency-channel.png)

*25 October 2026: without the stored event id, each delivery ran again: two digests and repeated answers to one question.*

**Look at:** the count in **Done** (the board shows the newest two strips per lane, so
the three question runs sit under its "more" link) and the posts in the Channel: the repeated
answers and the two digests.

**What it means:** without the stored event id, every delivery is a new job.

> [!CHECKPOINT]
> You can compare the count with step 7.

> [!IFDIFFERENT]
> Only one post → the run was sent without `PLANTED=1`; run `make demo NAME=events-duplicate-events PLANTED=1`.

> [!INSTRUCTOR]
> Nothing to switch back: the flags went with this demo's events only. The same event ran more
> than once in every recorded run of this half, 24 and 25 October included.

### Step 9: Engage the kill switch on a run in flight

**Where:** The demo terminal, and the Events page.

**Type:** this. `make demo` switches demo pacing on for this run, so it stays in flight long
enough, and engages the kill switch while it runs. In class the planted half of step 10 runs
first, then `make reset NAME=event-loop`, then this.

```bash
make demo NAME=events-kill-switch-in-flight
```

On the console, the same demo is **Kill switch** on the status line: arm, then stop.

**You should see:** the kill switch engages while a run is in the **Running** lane; the run stops
at its next step and moves to **Blocked by kill switch**.

![With demo pacing on: the status line forced to the report-only level by the kill switch, the chip Demo pacing on: 2 s between stages, and the run still in the Running lane, claimed by a worker](../../section-3-event-loop/demo/expected/events-kill-switch-paced-running.png)

*Run 1c76de06, 24 October 2026: with demo pacing on, the run is visibly in flight when the kill switch is engaged.*

![With demo pacing on: the Running lane empty and the same run under Blocked by kill switch, stopped by the kill switch](../../section-3-event-loop/demo/expected/events-kill-switch-paced-stopped.png)

*Run 1c76de06, 24 October 2026: it stops at its next step and moves off the board to Blocked by kill switch.*

**Look at:** the status line, "report-only level, forced by the kill switch", and the card under
**Blocked by kill switch**.

**What it means:** the kill switch is checked before every model and tool call, not only when a
job is claimed, so it reaches runs already in flight.

> [!CHECKPOINT]
> The run is under **Blocked by kill switch**, and the status line shows the report-only level.

> [!IFDIFFERENT]
> The run finishes before the switch → it was sent from the console, which sends no pacing; run `make demo NAME=events-kill-switch-in-flight`.
> The run keeps going after the switch → the run was sent with `PLANTED=1`; `make reset NAME=event-loop`, then run it again without it.

> [!INSTRUCTOR]
> The status line in these captures reads "Not cleared" for every family, as in class. The kill
> switch stays engaged until `make reset NAME=event-loop` releases it.

### Step 10: Show the kill switch at claim only

**Where:** The demo terminal, and the Events page.

**Type:** this; `PLANTED=1` sends the run with the kill switch at claim only, and with demo
pacing. The switch stays engaged afterwards, so reset before the next half.

```bash
make demo NAME=events-kill-switch-in-flight PLANTED=1
make reset NAME=event-loop
```

**You should see:** the run in flight keeps going after the kill switch engages.

![With the kill switch at claim only and demo pacing on: the status line with the kill switch engaged at the report-only level, and the run finished on the board, not blocked](../../section-3-event-loop/demo/expected/events-kill-switch-at-claim-only-board.png)

*25 October 2026: with the kill switch checked at claim only, the run in flight never sees it: the status line says the switch is engaged, and the run still posted.*

**Look at:** the run's lane after the switch.

**What it means:** a stop checked only at claim time never reaches a run already in flight.

> [!CHECKPOINT]
> You can compare the run's lane with step 9.

> [!IFDIFFERENT]
> The run stops → the run was sent without `PLANTED=1`; `make reset NAME=event-loop`, then `make demo NAME=events-kill-switch-in-flight PLANTED=1`.

> [!INSTRUCTOR]
> Nothing to switch back; `make reset NAME=event-loop` releases the kill switch. The run posted
> despite the switch in every recorded run of this half, 24 and 25 October included (16 and 30
> seconds).

## Result summary

| Item | This run |
|---|---|
| Pending approval across a worker restart | Survived; approved and posted (headline) |
| The webhook question | Posted at the report-only level, unverified |
| The same event three times | One question run, 2 duplicates absorbed, and one digest |
| The kill switch | Run stopped in flight; report-only level forced |

## Time and cost

Times are wall time from the trigger to the checked result, from the calibration's run-through of the demos on 22
and 23 October 2026 and the live sessions of 23, 24, and 25 October
(`docs/calibration-report.md`), each demo run alone with a reset between.

| Demo | Time | Shown in calibration | Cap |
|---|---|---|---|
| The webhook question | 12 to 46 seconds | 5 of 6 in calibration (one held, since fixed); shown on 24 and 25 October | 60,000 tokens per run |
| The approval that survives a restart | 50 to 84 seconds | 4 of 4 in calibration; shown on 24 and 25 October | 60,000 tokens per run |
| Duplicate events | 35 to 78 seconds | 4 of 4 in calibration; shown on 24 and 25 October | 60,000 tokens per run |
| The kill switch in flight | 3 to 33 seconds | 4 of 4 in calibration; shown on 24 and 25 October | 60,000 tokens per run |

The daily cap is 2,000,000 tokens (`budgets.tokens_per_day` in `pack.yaml`), shown as "Tokens
today" on the status line. One analyst run costs about 0.001 dollars.

## What to say in class

- "The router is a table, not an agent: the same event always goes to the same handler."
- "The approval lives in Postgres, so a restart does not lose it."
- "Three deliveries, one answer: idempotency is a stored id, not a hope."
- "The kill switch is checked before every step, so it stops runs already in flight."
- If a run held for a concern you did not expect: "The reviewer is still in the loop; that is the
  assisted path, working."
