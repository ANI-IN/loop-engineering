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

The full idea is in [concepts.md](concepts.md) (in class, minutes 0 to 24).

## How to work through this section

### How it works in the code

- [`submit_event`](../platform/src/datapilot/loop3_events/api/events.py) inserts each event once
  per `event_id` and queues its job; a duplicate is counted, not run.
- [`CLAIM_SQL`](../platform/src/datapilot/loop3_events/worker.py) claims a job with
  `FOR UPDATE SKIP LOCKED` and a lease that the worker's heartbeat extends; `reap` in `reaper.py`
  requeues a job whose lease ran out.
- [`checkpointer`](../platform/src/datapilot/loop3_events/approvals.py) keeps a paused run in
  Postgres, so a held approval survives a restart.
- [`KillSwitchMiddleware`](../platform/src/datapilot/loop3_events/killswitch.py) checks the switch
  before every model call and every tool call.
- [`route`](../platform/src/datapilot/loop3_events/router.py) looks up the handler and the queue
  for an event type in a fixed table.

The [walkthrough](demo/walkthrough.md) explains these lines (minutes 39 to 46).

### The demo

Four core demos, live, in minutes 24 to 39: the webhook question (`events-webhook-question`), the
approval that survives a restart (`events-approval-survives-restart`), duplicate events
(`events-duplicate-events`), and the kill switch in flight (`events-kill-switch-in-flight`).
Each shows one safeguard on the run board, and every result carries a live stamp. Run them with
the [demo page](demo/README.md); the measured runs are on the
[evidence page](../docs/evidence/section-3-event-loop.md). The poll after this section asks which
autonomy level you would grant the revenue digest; Section 4: Hill-climbing loop answers it.

### The assignment

[Assignment 3: Event loop](assignment/README.md) adds a nightly revenue anomaly alert: a scheduled
job with a deterministic key, at most one alert a day, that follows the autonomy level and the
kill switch. It is done when `make check-assignment NAME=event-loop` reads PASS on every line.
Effort: about 2 to 2.5 hours; the cost of a check is on the
[costs page](../docs/costs.md#assignments).

### Apply it in a real system

- Give every external event a deterministic id and a unique constraint, so a retry is harmless.
- Keep paused runs and their approvals in a durable checkpointer, never in process memory.
- Check the stop control before every model call and tool call, not only when a job is claimed.

### Further reading

The [reading list](post-class-reading/README.md) has three: a job queue in Postgres, idempotency
keys, and durable human approval.

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
