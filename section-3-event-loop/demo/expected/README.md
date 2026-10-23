# Module: Loop Engineering - Expected output for Section 3: Event loop

Real captures from live runs on 22 October 2026 (business date 31 January 2026), for comparison
after class. They are never shown in class: in class, every demo runs live.

Your output will differ: run times, ids, and the agent's wording change on every run.

## The webhook question

![The Events page board with one posted run for the webhook question at the report-only level](events-webhook-question-board.png)

*The webhook question becomes an event and a job, and moves to Done.*

The question asks for the orders of the previous business day, 30 January 2026. Your count may be
300 or 291 orders, and both are expected: 300 counts the day in Eastern time (New York), the right
answer, and 291 counts the day in Coordinated Universal Time, the Eastern time trap. The
[demo page](../README.md#what-the-result-means) explains why the reviewer approves both.

![The Channel with the answer posted at the report-only level, labelled unverified](events-webhook-question-channel.png)

*At the report-only level the answer is posted labelled unverified.*

Trace: [run 7cf0509e](https://smith.langchain.com/o/10fe45d9-7a3d-4f39-92ad-8c5dc97653d4/projects/p/7ce7a82b-8edc-4fb1-b6bc-d13fe6070f5e/r/7cf0509e-dbca-4568-a4f7-b234d7695ab8?poll=true)

## The approval that survives a restart

![The board with the California export holding for approval, with its Review button](events-approval-held.png)

*The California marketing export reads personal data, so the run holds before the query runs.*

![After Restart worker: the page says the pending approval survived and the run is still holding](events-approval-after-restart.png)

*The worker restarts; the Postgres checkpointer keeps the pending approval.*

![After approval: the export posted at the report-only level](events-approval-approved-posted.png)

*Approving resumes the run, and the export is posted.*

In this run the reviewer asked for changes, so the analyst rewrote its query three times; each new
query was approved before it ran (an approved query is never asked about twice).

Trace: [run ef5eb601](https://smith.langchain.com/o/10fe45d9-7a3d-4f39-92ad-8c5dc97653d4/projects/p/7ce7a82b-8edc-4fb1-b6bc-d13fe6070f5e/r/ef5eb601-e010-4f81-81ce-b3c206d6d877?poll=true)

## Duplicate events

![The board with one posted run marked 2 duplicates absorbed](events-duplicate-events-board.png)

*The same event three times: one run, one post, and 2 duplicates absorbed.*

Trace: [run 9a3a8296](https://smith.langchain.com/o/10fe45d9-7a3d-4f39-92ad-8c5dc97653d4/projects/p/7ce7a82b-8edc-4fb1-b6bc-d13fe6070f5e/r/9a3a8296-2146-4504-bb08-30cded2b8caa?poll=true)

## The kill switch in flight

![The status line forced to the report-only level by the kill switch, and the run moved to Blocked by kill switch](events-kill-switch-in-flight-board.png)

*The kill switch stops a run in flight and drops the system to the report-only level.*

The run's event says it stopped "in flight". This capture ran without demo pacing.

![With demo pacing on: the kill switch engaged while the run is still in the Running lane](events-kill-switch-paced-running.png)

*With demo pacing on, the run is visibly in flight when the kill switch is engaged.*

![With demo pacing on: the run moved to Blocked by kill switch](events-kill-switch-paced-stopped.png)

*It stops at its next step and moves off the board to Blocked by kill switch.*

Trace: [run 16b96215](https://smith.langchain.com/o/10fe45d9-7a3d-4f39-92ad-8c5dc97653d4/projects/p/7ce7a82b-8edc-4fb1-b6bc-d13fe6070f5e/r/16b96215-ed79-4ca1-9e58-fccb072c9f12?poll=true)

Trace: [run bb8b3e1f](https://smith.langchain.com/o/10fe45d9-7a3d-4f39-92ad-8c5dc97653d4/projects/p/7ce7a82b-8edc-4fb1-b6bc-d13fe6070f5e/r/bb8b3e1f-eaa7-467e-839b-b1ed09bbd9b0?poll=true)
