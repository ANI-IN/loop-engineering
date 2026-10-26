# Module: Loop Engineering - Reading list for Section 3: Event loop

Three readings that go past the class time of the event loop. Each page sums up one primary source
in plain words and shows how to apply it to your own repository. Each page takes a few minutes; the
reading time in the table is for the full source, at 200 words a minute, rounded up to 5 minutes.

> **Terms on this page**
>
> - **Event loop**: Events become jobs that workers run, with approvals, budgets, and a kill switch.
> - **Human approval**: A person approves or rejects a held action before it runs.

## Readings

| Reading | Reading time | Why read it |
|---|---|---|
| [01 A job queue in Postgres](01-postgres-job-queues.md) | 25 minutes | Why a table-backed queue works, and what makes it degrade |
| [02 Idempotency keys](02-idempotency-keys.md) | 20 minutes | Why every retried effect needs a deterministic key |
| [03 Durable human approval](03-durable-human-approval.md) | 25 minutes | How an interrupted run waits for a person, and why it needs a checkpointer |

## How to use these

- Read the first two together: one is the queue, the other the effects it delivers more than once.
- Read the third before you add an approval step to any agent you run.
- After each reading, do the first step of its "Apply it to your repository" list.
