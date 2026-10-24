# Chapter 3: Section 3: Event loop

The same analyst now runs from events: a webhook, an export request, a repeated delivery, and a
stop. You watch runs move across the run board on the console's Events page, an approval survive
a worker restart, three deliveries become one answer, and the kill switch stop a run in flight.
Every screenshot and number in this chapter comes from the live runs of 22 October 2026 (business
date 31 January 2026), and every time range from the calibration demo pass of 22 and 23 October
2026.

> Your output will differ: run times, ids, and the agent's wording change on every run.

### Step 1: Send the webhook question

**Where:** The demo terminal, in the repository folder, and the console's Events page.

**Type:** this, or press **Send webhook question** on the Events page.

```bash
make demo NAME=events-webhook-question
```

**You should see:** the status line at the report-only level, and one run that moves across the
lanes to **Done**.

![The Events page: the status line at the report-only level with no family cleared, the run board with one posted run for the question about the previous day's orders in Done, and the empty off-the-board lanes](../../section-3-event-loop/demo/expected/events-webhook-question-board.png)

*The webhook question becomes an event and a job, and moves to Done.*

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

![The Channel with one post: "Posted at the report-only level, unverified" and the answer 291 orders](../../section-3-event-loop/demo/expected/events-webhook-question-channel.png)

*At the report-only level the answer is posted labelled unverified.*

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

![The run board with the export of every marketable California customer's email and first name in Holding for approval, its reason "the query reads personal" cut off, and its Review button](../../section-3-event-loop/demo/expected/events-approval-held.png)

*The California marketing export reads personal data, so the run holds before the query runs.*

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

![After Restart worker: the line "Worker restart requested. The pending approval survived: run ef5eb601 still holding." above the Channel](../../section-3-event-loop/demo/expected/events-approval-after-restart.png)

*The worker restarts; the Postgres checkpointer keeps the pending approval.*

**Look at:** "The pending approval survived".

**What it means:** the run's state is in Postgres, not in the worker's memory, so a restart does not
lose it.

> [!CHECKPOINT]
> The card is still in **Holding for approval** after the restart.

> [!IFDIFFERENT]
> **Restart worker** does nothing → demo controls are off; set `DATAPILOT_ALLOW_DEMO_CONTROLS=1` in `.env`, then `make up`.

> [!INSTRUCTOR]
> Point at the run's short id in the line, then at the same card on the board.

### Step 5: Review and approve

**Where:** The Events page, on the held card.

**Type:** press **Review** on the card, read the dialog, then approve.

**You should see:** the dialog with the exact query and its row count; after approval, the run
resumes and the export is posted.

<!-- capture: the Review dialog of the California export, with the exact query and the row count -->

![After approval: "Worker restart requested. Run ef5eb601 moved on after the restart." and the export posted at the report-only level, unverified](../../section-3-event-loop/demo/expected/events-approval-approved-posted.png)

*Approving resumes the run, and the export is posted.*

**Look at:** the line "moved on after the restart" and the new post in the channel.

**What it means:** one approval, given after a restart, resumes the same run where it stopped.

> [!CHECKPOINT]
> The export appears in the channel.

> [!IFDIFFERENT]
> The dialog asks again for a rewritten query → expected when you ask for changes; each new query is approved before it runs, and an approved query is never asked about twice.

> [!INSTRUCTOR]
> In the captured run the reviewer asked for changes, and the analyst rewrote its query three
> times. Say so if it happens: each version still needed a person.

### Step 6: Show the lost approval with the in-memory checkpointer

**Where:** `.env` in an editor, the demo terminal, and the Events page.

**Type:** set `BUG_MEMORY_CHECKPOINTER=1` in `.env`, then repeat steps 3 and 4.

```bash
make up
make demo NAME=events-approval-survives-restart
```

**You should see:** after **Restart worker**, the pending approval is lost.

<!-- capture: the approval with the in-memory checkpointer planted: the Events page after Restart worker -->

**Look at:** the line under the buttons after the restart.

**What it means:** state held in process memory dies with the process.

> [!CHECKPOINT]
> You can compare this screen with step 4.

> [!IFDIFFERENT]
> The approval survives → the services did not read `.env`; run `make up` again.

> [!INSTRUCTOR]
> Set the flag back to `0` and run `make up`. In 3 of 3 measured runs the approval was lost.

### Step 7: Send the same event three times

**Where:** The demo terminal, and the Events page.

**Type:** this, or press **Send the same event three times** on the Events page.

```bash
make demo NAME=events-duplicate-events
```

**You should see:** one new run in **Done**, marked with the duplicates it absorbed.

![The run board: the webhook question posted once and marked "2 duplicates absorbed", below it the posted California export, and "1 more"](../../section-3-event-loop/demo/expected/events-duplicate-events-board.png)

*The same event three times: one run, one post, and 2 duplicates absorbed.*

**Look at:** "2 duplicates absorbed" on the newest card.

**What it means:** the event's id is stored once; the second and third deliveries find it and add
nothing. One answer is posted, not three.

> [!CHECKPOINT]
> One new card, and the channel has one new post.

> [!IFDIFFERENT]
> Three cards → check that `BUG_NO_IDEMPOTENCY` is `0` in `.env`, then `make up`.

> [!INSTRUCTOR]
> Say: "Webhooks retry. The effect must happen once, however many times the event arrives."

### Step 8: Show three posts with the missing idempotency

**Where:** `.env` in an editor, the demo terminal, and the Events page.

**Type:** set `BUG_NO_IDEMPOTENCY=1` in `.env`, then:

```bash
make up
make demo NAME=events-duplicate-events
```

**You should see:** three runs and three posts for the same event.

<!-- capture: duplicate events with the missing idempotency planted: three posted runs on the board and three posts in the channel -->

**Look at:** the count in **Done** and the channel.

**What it means:** without the stored event id, every delivery is a new job.

> [!CHECKPOINT]
> You can compare the count with step 7.

> [!IFDIFFERENT]
> Only one post → the services did not read `.env`; run `make up` again.

> [!INSTRUCTOR]
> Set the flag back to `0` and run `make up`. In 3 of 3 measured runs the same event posted three answers.

### Step 9: Engage the kill switch on a run in flight

**Where:** `.env` in an editor, the demo terminal, and the Events page.

**Type:** set `DEMO_PACING=1` in `.env` so a run stays in flight long enough, then:

```bash
make up
make demo NAME=events-kill-switch-in-flight
```

On the console, the same demo is **Kill switch** on the status line: arm, then stop.

**You should see:** the kill switch engages while a run is in the **Running** lane; the run stops
at its next step and moves to **Blocked by kill switch**.

![With demo pacing on: the status line forced to the report-only level by the kill switch, a pacing chip of 2 seconds between stages, and the run still in the Running lane, claimed by a worker](../../section-3-event-loop/demo/expected/events-kill-switch-paced-running.png)

*With demo pacing on, the run is visibly in flight when the kill switch is engaged.*

![With demo pacing on: the Running lane empty and the run under Blocked by kill switch, stopped by the kill switch](../../section-3-event-loop/demo/expected/events-kill-switch-paced-stopped.png)

*It stops at its next step and moves off the board to Blocked by kill switch.*

**Look at:** the status line, "report-only level, forced by the kill switch", and the card under
**Blocked by kill switch**.

**What it means:** the kill switch is checked before every model and tool call, not only when a
job is claimed, so it reaches runs already in flight.

> [!CHECKPOINT]
> The run is under **Blocked by kill switch**, and the status line shows the report-only level.

> [!IFDIFFERENT]
> The run finishes before the switch → demo pacing is off; set `DEMO_PACING=1` in `.env`, then `make up`.
> The run keeps going after the switch → check that `BUG_KILLSWITCH_AT_CLAIM_ONLY` is `0` in `.env`, then `make up`.

> [!INSTRUCTOR]
> The status line in these captures also shows two families suspended: they were taken after the
> Section 4: Hill-climbing loop promotion. In class you see "Not cleared" for every family. The
> kill switch stays engaged until `make reset NAME=event-loop` releases it.

### Step 10: Show the kill switch at claim only

**Where:** `.env` in an editor, the demo terminal, and the Events page.

**Type:** set `BUG_KILLSWITCH_AT_CLAIM_ONLY=1` in `.env`, keep `DEMO_PACING=1`, then:

```bash
make reset NAME=event-loop
make up
make demo NAME=events-kill-switch-in-flight
```

**You should see:** the run in flight keeps going after the kill switch engages.

<!-- capture: the kill switch at claim only planted: the Events page with the run still moving after the kill switch -->

**Look at:** the run's lane after the switch.

**What it means:** a stop checked only at claim time never reaches a run already in flight.

> [!CHECKPOINT]
> You can compare the run's lane with step 9.

> [!IFDIFFERENT]
> The run stops → the services did not read `.env`; run `make up` again.

> [!INSTRUCTOR]
> Set both flags back to `0`, run `make up`, then `make reset NAME=event-loop`. This half has no
> measured run yet.

## Result summary

| Item | This run |
|---|---|
| Pending approval across a worker restart | Survived; approved and posted (headline) |
| The webhook question | Posted at the report-only level, unverified |
| The same event three times | One run, 2 duplicates absorbed |
| The kill switch | Run stopped in flight; report-only level forced |

## Time and cost

Times are wall time from the trigger to the checked result, from the calibration demo pass of 22
and 23 October 2026 and the live sessions of 23 October, afternoon and evening
(`docs/calibration-report.md`), each demo run alone with a reset between.

| Demo | Time | Shown in calibration | Cap |
|---|---|---|---|
| The webhook question | 14 to 46 s | 5 of 6; one held by the reviewer, since fixed | 60,000 tokens per run |
| The approval that survives a restart | 50 to 84 s | 4 of 4 | 60,000 tokens per run |
| Duplicate events | 35 to 78 s | 4 of 4 | 60,000 tokens per run |
| The kill switch in flight | 3 to 33 s | 4 of 4 | 60,000 tokens per run |

The daily cap is 2,000,000 tokens (`budgets.tokens_per_day` in `pack.yaml`), shown as "Tokens
today" on the status line. One analyst run costs about 0.001 dollars.

## What to say in class

- "The router is a table, not an agent: the same event always goes to the same handler."
- "The approval lives in Postgres, so a restart does not lose it."
- "Three deliveries, one answer: idempotency is a stored id, not a hope."
- "The kill switch is checked before every step, so it stops runs already in flight."
- If a run held for a concern you did not expect: "The reviewer is still in the loop; that is the
  assisted path, working."
