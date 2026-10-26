# Section 3: Event loop. Concepts

Reading time: about 9 minutes.

## The problem

**Illustrative scenario.** Take the three failures from the
[section page](README.md#the-problem): the morning digest that posts twice after a worker retry,
while the finance channel argues about which copy is right; the California marketing export that
runs while nobody watches; and the stop button that leaves the run already in flight to post.

> **Terms on this page**
>
> - **Event loop**: Events become jobs that workers run, with approvals, budgets, and a kill switch.
> - **Human approval**: A person approves or rejects a held action before it runs.
> - **Autonomy level**: How much DataPilot may do unattended: report-only, assisted, or unattended.
> - **Kill switch**: The guarded control that stops every worker and forces the report-only level.
> - **Planted bug**: A defect switched on by a flag so a demo shows its failure every time.
>
> All terms: [glossary](../docs/glossary.md).

## The idea in one sentence

Once nobody watches each run, every event must become a durable job whose effects happen once,
whose approvals survive restarts, and whose stop reaches the run already in flight.

## How it works

The four loops of [The art of loop engineering](https://www.langchain.com/blog/the-art-of-loop-engineering)
match this course's sections. The event loop is the one that runs without you: webhooks and
schedules start work, and nobody reads each answer before it posts.

### Events become jobs

A webhook `POST /events` writes an event row and a job row in one transaction. A worker claims a
job with `FOR UPDATE SKIP LOCKED`, a short claim transaction, and a lease. Heartbeats extend the
lease, and a reaper requeues jobs whose lease expired. Both the finish and the heartbeat are fenced
on the lease owner and the attempt number: a worker can finish or extend a job only while it holds
the lease and the attempt number still matches, so a stale worker can neither finish nor extend a
re-claimed job. The run moves through the lifecycle in
`platform/src/datapilot/contracts/lifecycle.py`: Queued, Running, Verifying, Holding for approval,
and Done on the console run board.

The PostgreSQL documentation describes `SKIP LOCKED` as skipping rows that cannot be locked at
once ([PostgreSQL SELECT](https://www.postgresql.org/docs/current/sql-select.html)). The result is
not strictly first in, first out, and delivery is at least once: a crash after the work but before
the job is marked done runs it again ([You don't need a job queue: Postgres already has SKIP LOCKED](https://www.prisma.io/blog/you-dont-need-a-job-queue-postgres-already-has-skip-locked)). The lock held
during the model call (`BUG_LOCK_DURING_LLM`) is a planted bug with no class demo: the running job
looks queued, and when the worker dies the claim rolls back, so the job runs again with no attempt
counted and an attempt cap never stops it.

Key idea: a job in a table survives what a process does not.

### Idempotency by key

At-least-once delivery means the same event can arrive twice. The insert is
`INSERT ... ON CONFLICT (event_id) DO NOTHING`, so a duplicate event posts one answer and the board counts
the duplicates it ignored. The morning digest uses the deterministic id `digest:YYYY-MM-DD`, so
firing it twice on the same day is one digest. The missing idempotency (`BUG_NO_IDEMPOTENCY`) and
the random digest id (`BUG_RANDOM_DIGEST_ID`) show what happens without the key.

Key idea: at-least-once delivery needs exactly-once effects.

### Approvals that survive restarts

A query that touches a personal data column, listed in `personal_data.columns` in
`platform/packs/datapilot_us/pack.yaml`, holds for human approval. The dialog states the exact Structured Query Language (SQL)
and the row count. The held run is a LangGraph interrupt, and resuming it uses
`Command(resume=...)` ([Human-in-the-loop](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)).

The Postgres checkpointer (`AsyncPostgresSaver` in schema `lg`, with the thread id equal to the run
id) keeps that interrupt on disk. Restart the worker and the approval is still waiting. The
in-memory checkpointer (`BUG_MEMORY_CHECKPOINTER`) loses it.

Key idea: a pending approval is state, so put it where state lives.

### Autonomy levels and the kill switch

The levels follow the framing of [Loop engineering](https://cobusgreyling.github.io/loop-engineering/):

| Level | What DataPilot may do |
|---|---|
| report-only level | Post answers labelled unverified; no exports |
| assisted level | Post answers; personal data and exports need human approval |
| unattended level | Post unattended, for eligible metric families only |

The default is `autonomy.default_level: report_only` in `pack.yaml`. The system demotes itself
after `autonomy.demote_after_consecutive_escalations` escalations in a row (3 in `pack.yaml`). The
kill switch is checked before every model call, which jumps to the end, and before every tool
call, which short-circuits. It stops every worker and forces the report-only level. The kill
switch at claim only (`BUG_KILLSWITCH_AT_CLAIM_ONLY`) checks once, when the job is claimed.

Key idea: the stop must reach the run that is already running.

![The event pipeline: a webhook, the scheduler, or the console sends an event to POST /events, which inserts once per event_id; a fixed router, with no agent, picks the queue in the jobs table; the worker claims a job with a lease and a heartbeat, the reaper requeues an expired lease, and the daily budget is checked at claim; the autonomy policy posts at once or holds the run, which waits as a parked job with its checkpoint until a person approves; the kill switch is checked at claim and before every model call and every tool call](diagrams/event-loop.svg)

*Notice that every safeguard here is a row in Postgres, not memory: the event id, the lease, the parked job, and the checkpoint, so a restart loses nothing.*

### The router is not an agent

The tempting question is: should an agent route the events? No. Routing is a lookup from event
type to handler and policy. A deterministic table gives the same answer every time, costs no
tokens, and you can test and audit it. The event loop adds no agent.

### Before and after

Before: a worker retries, the digest posts twice, the export runs with nobody approving, and the
stop button misses the running job. After: the duplicate event is absorbed as a duplicate, the export holds
for human approval across a worker restart, and the running job stops at its next step as blocked
by kill switch.

## How DataPilot does it

The worker claims a job in one short transaction and finishes it only while it still owns the
lease of the same attempt. These are the three statements:

```python
# platform/src/datapilot/loop3_events/worker.py (lines 70-90)
CLAIM_SQL = """
UPDATE ops.jobs
SET status = 'running', attempts = attempts + 1, lease_owner = %(owner)s,
    lease_until = now() + make_interval(secs => %(lease)s), updated_at = now()
WHERE job_id = (
    SELECT job_id FROM ops.jobs
    WHERE status = 'queued' AND run_after <= now() AND queue = ANY(%(queues)s)
    ORDER BY run_after, job_id
    FOR UPDATE SKIP LOCKED
    LIMIT 1)
RETURNING job_id, event_id, attempts, max_attempts
"""
HEARTBEAT_SQL = (
    "UPDATE ops.jobs SET lease_until = now() + make_interval(secs => %s), updated_at = now() "
    "WHERE job_id = %s AND lease_owner = %s AND attempts = %s AND status = 'running'"
)
FINISH_SQL = (
    "UPDATE ops.jobs SET status = %s, lease_owner = NULL, lease_until = NULL, updated_at = now(), "
    "last_error = %s WHERE job_id = %s AND lease_owner = %s AND attempts = %s "
    "AND status = 'running'"
)
```

The heartbeat and the finish both match on the lease owner and the attempt number, so a worker
whose lease expired cannot overwrite the work of the worker that took the job over. The other
parts live beside it:

- `platform/src/datapilot/loop3_events/api/events.py` holds the insert with
  `ON CONFLICT (event_id) DO NOTHING` and the job row.
- `platform/src/datapilot/loop3_events/approvals.py` sets up the Postgres checkpointer in schema
  `lg`, with the thread id equal to the run id.
- `platform/src/datapilot/loop3_events/killswitch.py` checks the kill switch at claim, before
  every model call, and before every tool call.

## What we measured

| Check | Result |
|---|---|
| Duplicate event: answers posted | 1 answer and 2 duplicates absorbed, in 7 of 7 runs |
| Approval after a worker restart | Survived the restart and posted after approval, in 7 of 7 runs |
| In-flight run after the kill switch | Stopped in flight, at the report-only level, in 9 of 9 runs |

With each planted bug on, the failure appeared in every run: three answers, a lost approval, a post
after the switch. The kill switch count includes the paced capture. The runs are on the
[evidence page for this section](../docs/evidence/section-3-event-loop.md).

## When it helps, and when it does not

It helps when:

- Work starts from webhooks or schedules and nobody reads each answer before it posts.
- A retry or a redelivery can repeat an event.
- An action touches personal data or leaves the system, such as an export.

It does not help when:

- A person asks one question and reads the answer in the console; the agent loop is enough.
- The answer itself is wrong; idempotency posts a wrong answer once. That is the job of
  Section 2: Verification loop and Section 4: Hill-climbing loop.

## Key takeaways

- Turn every event into a job row with a deterministic id, so duplicates are absorbed instead of posted.
- Keep pending approvals in the Postgres checkpointer, so a restart does not lose them.
- Check the kill switch before every model and tool call, and keep the router a table, not an agent.

## Check your understanding

1. Why is a queue built on `SKIP LOCKED` at least once, and what does that force on handlers?

<details><summary>Answer</summary>

A worker can claim a job, do the work, and die before marking it done; the reaper requeues it.
Handlers must make the effect happen once, here with a deterministic event id and
`ON CONFLICT (event_id) DO NOTHING`.

</details>

2. Why does the digest use `digest:YYYY-MM-DD` instead of a random id?

<details><summary>Answer</summary>

Two firings on the same day get the same id, so the second is a duplicate. A random id makes each
firing new, and the channel gets two digests.

</details>

3. Why is checking the kill switch at claim time not enough?

<details><summary>Answer</summary>

A run claimed before the switch was engaged never checks again. Checking before every model call
and every tool call stops it at its next step.

</details>

4. Why is the router not an agent?

<details><summary>Answer</summary>

Routing from event type to handler and policy is a lookup with one right answer. A table is
deterministic, free, and testable; an agent adds cost and variance for no judgement.

</details>

## Further reading

- [Reading list for this section](post-class-reading/README.md)

## Sources

- Source 1: The art of loop engineering, <https://www.langchain.com/blog/the-art-of-loop-engineering>, Sydney Runkle (LangChain), 2026-06-16
- Source 2: PostgreSQL SELECT, <https://www.postgresql.org/docs/current/sql-select.html>, PostgreSQL Global Development Group, n.d.
- Source 3: You don't need a job queue: Postgres already has SKIP LOCKED, <https://www.prisma.io/blog/you-dont-need-a-job-queue-postgres-already-has-skip-locked>, Prisma, 2026-07-17
- Source 4: Human-in-the-loop, <https://docs.langchain.com/oss/python/langchain/human-in-the-loop>, LangChain, n.d.
- Source 5: Loop engineering, <https://cobusgreyling.github.io/loop-engineering/>, Cobus Greyling, n.d.
