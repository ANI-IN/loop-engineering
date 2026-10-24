# Module: Loop Engineering - Section 3: Event loop

What happens when nobody is watching: questions and the morning digest arrive as events, and
workers run them with approvals, autonomy levels, and a kill switch.

## The problem

**Illustrative scenario.** At Harbor & Pine Outfitters the morning digest posts twice after a
worker retries. Later a California marketing export with customer emails runs while nobody
watches. Someone presses the stop button. New runs stop, but the one already running keeps going
and posts its answer.

> **Terms on this page**
>
> - **Event loop**: Events become jobs that workers run, with approvals, budgets, and a kill switch.
> - **Human approval**: A person approves or rejects a held action before it runs.
> - **Autonomy level**: How much DataPilot may do unattended: report-only, assisted, or unattended.
> - **Kill switch**: The guarded control that stops every worker and forces the report-only level.
> - **Planted bug**: A defect switched on by a flag so a demo shows its failure every time.
>
> All terms: [glossary](../docs/glossary.md).

## Why it happens

- A Postgres queue built on `FOR UPDATE SKIP LOCKED` delivers at least once and is not strictly
  in order, so a handler can see the same event twice
  ([PostgreSQL SELECT](https://www.postgresql.org/docs/current/sql-select.html),
  [You don't need a job queue: Postgres already has SKIP LOCKED](https://www.prisma.io/blog/you-dont-need-a-job-queue-postgres-already-has-skip-locked)).
- A pending approval is an interrupted run. If the run's state lives in process memory, a restart
  loses it ([Human-in-the-loop](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)).
- A stop that is checked only when a job is claimed never reaches a run already in flight.
  Autonomy levels and the kill switch follow the framing of
  [Loop engineering](https://cobusgreyling.github.io/loop-engineering/).

## How this section fixes it

Every event becomes a row and a job; workers claim jobs with a short transaction and a lease. A
deterministic event id makes a duplicate event harmless. Approvals live in the Postgres checkpointer, so they
survive a restart. The kill switch is checked before every model call and every tool call.

The router is a table from event type to handler and policy, deliberately not an agent: routing is
a lookup you can test and audit. The section adds no agent.

![Events arrive by webhook, scheduler, or console at POST /events, which inserts once per event_id; a fixed router picks the queue; the worker claims jobs from the jobs table with a lease and a heartbeat, the reaper requeues expired leases, and the daily budget and the kill switch are checked; a person approves through POST /approvals, and the paused run waits in its checkpoint](diagrams/event-loop.svg)

*Notice that every safeguard here is a row in Postgres, not memory: the event id, the lease, the parked job, and the checkpoint, so a restart loses nothing.*

What the course measured for this section is on the
[evidence page](../docs/evidence/section-3-event-loop.md).

## How to work through this section

| Part | What it gives you | In class |
|---|---|---|
| [concepts.md](concepts.md) | Jobs, idempotency, durable approvals, autonomy and the kill switch | Minutes 0-24 |
| [demo/](demo/README.md) | Four live demos: webhook, approval across a restart, duplicates, kill switch | Minutes 24-39 |
| [demo/walkthrough.md](demo/walkthrough.md) | The claim, the dedup insert, the checkpointer, the kill switch check | Minutes 39-46 |
| [assignment/](assignment/README.md) | Build a nightly revenue anomaly alert | After class |
| [post-class-reading/](post-class-reading/README.md) | Readings on queues, idempotency, and approvals | After class |
| [session-notes.md](session-notes.md) | What class showed, questions, what to try next | After class |

In class, every demo result on the console shows a live stamp: its run's start time in the
viewer's local time and its LangSmith trace link. The `demo/expected/` folder is for you
after class; it is never opened in class.

The poll after this section asks which autonomy level you would grant the revenue digest today.
Section 4: Hill-climbing loop answers it: autonomy is earned from evidence.

## Where next

- First time here? Install everything with [setup/](../setup/README.md), then run the
  [demos](demo/README.md).
- Already set up? Start with [concepts.md](concepts.md).
- Previous section: [Section 2: Verification loop](../section-2-verification-loop/README.md).
- Next section: [Section 4: Hill-climbing loop](../section-4-hill-climbing-loop/README.md).

## Sources

- Source 1: PostgreSQL SELECT, <https://www.postgresql.org/docs/current/sql-select.html>, PostgreSQL Global Development Group, n.d.
- Source 2: You don't need a job queue: Postgres already has SKIP LOCKED, <https://www.prisma.io/blog/you-dont-need-a-job-queue-postgres-already-has-skip-locked>, Prisma, 2026-07-17
- Source 3: Human-in-the-loop, <https://docs.langchain.com/oss/python/langchain/human-in-the-loop>, LangChain, n.d.
- Source 4: Loop engineering, <https://cobusgreyling.github.io/loop-engineering/>, Cobus Greyling, n.d.
