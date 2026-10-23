# Demo walkthrough for Section 3: Event loop

The code behind the demos of this section: how an event is taken in once, how a worker claims its
job, where a pending approval is kept, and where the kill switch is checked.

> **Terms on this page**
>
> - **Event loop**: Events become jobs that workers run, with approvals, budgets, and a kill switch.
> - **Human approval**: A person approves or rejects a held action before it runs.
> - **Kill switch**: The guarded control that stops every worker and forces the report-only level.
> - **Planted bug**: A defect switched on by a flag so a demo shows its failure every time.
>
> All terms: [glossary](../../docs/glossary.md).

## What this code does

An event arrives at `POST /events` and is inserted once: a repeated `event_id` is counted as a
duplicate and returns the first run. A new event gets its job and its run in the same
transaction. A worker claims one queued job with a lease, in one short Structured Query Language
(SQL) transaction. While the run works, the checkpointer keeps its state in Postgres, so a run that
holds for approval survives a restart. The kill switch is checked before every model and tool call.

```mermaid
sequenceDiagram
    participant Sender as Webhook or make demo
    participant Events as POST /events
    participant Jobs as ops.jobs
    participant Worker
    participant Saver as Postgres checkpointer
    Sender->>Events: event (event_id)
    alt event_id already seen
        Events-->>Sender: the first run, duplicate counted
    else new event
        Events->>Jobs: job and run, one transaction
    end
    Worker->>Jobs: claim one job (FOR UPDATE SKIP LOCKED, lease)
    Worker->>Saver: checkpoint each step of the run
    Note over Worker,Saver: worker restarts; the held approval stays in Postgres
    Worker->>Saver: resume from the checkpoint after approval
    Worker->>Worker: kill switch checked before each model and tool call
```

## The code, explained

### platform/src/datapilot/loop3_events/api/events.py, lines 35-44

```python
# platform/src/datapilot/loop3_events/api/events.py (lines 35-44)
    if planted.planted("BUG_NO_IDEMPOTENCY"):
        event_id = f"{event_id}#{uuid.uuid4().hex[:8]}"  # planted: every delivery looks new
    route = router.route(type, payload)
    inserted = conn.execute(
        "INSERT INTO ops.events (event_id, source, type, payload) VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (event_id) DO NOTHING RETURNING event_id",
        (event_id, source, type, Jsonb(payload)),
    ).fetchone()
    if inserted is None:
        conn.execute("INSERT INTO ops.event_duplicates (event_id) VALUES (%s)", (event_id,))
```

This is duplicate events. The database decides, not the code: `ON CONFLICT (event_id) DO
NOTHING` returns no row for a repeat, and the repeat is recorded as a duplicate instead of a new
job. With the missing idempotency (`BUG_NO_IDEMPOTENCY`) on, a random suffix makes every delivery
look new, and each one posts its own answer.

### platform/src/datapilot/loop3_events/worker.py, lines 70-81

```python
# platform/src/datapilot/loop3_events/worker.py (lines 70-81)
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
```

The claim is one statement. `FOR UPDATE SKIP LOCKED` lets several workers claim at once without
taking the same job. The lease, not an open transaction, marks the job as taken, so the claim
commits at once and no lock is held through the model calls.

### platform/src/datapilot/loop3_events/approvals.py, lines 44-47

```python
# platform/src/datapilot/loop3_events/approvals.py (lines 44-47)
    if planted("BUG_MEMORY_CHECKPOINTER"):
        yield InMemorySaver(serde=SERDE)  # planted: process memory, lost when the worker restarts
        return
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
```

This is the approval that survives a restart. The pending approval is a LangGraph interrupt, and
the checkpointer is where it lives. The Postgres saver keeps it across a worker restart; with the
in-memory checkpointer (`BUG_MEMORY_CHECKPOINTER`) on, the restart loses it.

### platform/src/datapilot/loop3_events/killswitch.py, lines 89-95

```python
# platform/src/datapilot/loop3_events/killswitch.py (lines 89-95)
    def _check(self) -> bool:
        if planted("BUG_KILLSWITCH_AT_CLAIM_ONLY"):
            return False  # planted: the switch is checked at claim only, never in flight
        if self.is_engaged():
            self.guard.stop(StopReason.KILL_SWITCH, "the kill switch is engaged")
            return True
        return False
```

This is the kill switch in flight. The middleware calls `_check` before each model call and each
tool call. When the switch is engaged, the run guard records the stop and the run ends blocked by
the kill switch at its next step. With the kill switch at claim only
(`BUG_KILLSWITCH_AT_CLAIM_ONLY`) on, a run that has already started keeps going.

## If you copy this into your repository

- Keep idempotency in the database: a unique event id and an insert that does nothing on conflict.
  A check in code before the insert races with a second delivery.
- Keep the claim short, with `SKIP LOCKED` and a lease, and commit it before the run starts.
- Keep a durable checkpointer for any run that can wait for a person.
- Keep the kill switch check in middleware before every model and tool call, not only at claim.
- Change the queue names, the lease length, and the checkpointer's schema to your system.
- Check it by sending one event three times, restarting a worker while a run is held, and engaging
  the switch during a slow run.
