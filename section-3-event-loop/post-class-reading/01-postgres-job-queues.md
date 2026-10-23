# [Postgres Job Queues & Failure By MVCC](https://brandur.org/postgres-queues)

Reading time: about 25 minutes.
Source: Brandur Leach, [Postgres Job Queues & Failure By MVCC](https://brandur.org/postgres-queues), 2015-05-18.

> **Terms on this page**
>
> - **Event loop**: Events become jobs that workers run, with approvals, budgets, and a kill switch.
> - **Lease**: The time a worker owns a claimed job; a job whose lease expires goes back to the queue.

## Why it matters

DataPilot's event loop keeps its job queue in a Postgres table, not in a message broker. This
article is the classic account of why teams do that, and of the failure that catches them later.
It explains the trade you make when the queue lives beside the data: transactional consistency in
exchange for care with long transactions.

## Three key ideas

1. **A queue in the database is transactional.** "Storing jobs in a database allows a program to
   take advantage of its transactional consistency; when an operation fails and rolls back, an
   injected job rolls back with it." Jobs also stay "invisible to workers until their transactions
   commit". DataPilot writes the event row and the job row in one transaction for this reason.

2. **Long transactions degrade a hot table.** In the author's incident, a long analytical
   transaction on the same database made the queue back up, because dead rows could not be
   cleaned away while it ran. Workers then had to "seek through thousands of dead rows before
   finally arriving at something that it can use". Keep claim transactions short, and keep long
   queries off the queue's database or under a timeout.

3. **Guard the database's boundaries.** The author recommends watching for transactions alive too
   long, enabling `statement_timeout`, and keeping database use "within the operational boundaries
   of a single component". DataPilot's agent role runs with a statement timeout
   (`limits.statement_timeout_ms` in `pack.yaml`) and an idle-in-transaction timeout.

## Apply it to your repository

1. Find where your agent's work is queued. If a job can be lost when a process dies, move it to a
   table with a claim and a lease.
2. Make the claim one short transaction: `UPDATE ... WHERE id = (SELECT ... FOR UPDATE SKIP LOCKED
   LIMIT 1) RETURNING`, then commit, then do the work.
3. Set a statement timeout and an idle-in-transaction timeout on every role that shares the
   database with the queue.
4. Compare with `CLAIM_SQL` in `platform/src/datapilot/loop3_events/worker.py`.

## Sources

- Source 1: Postgres Job Queues & Failure By MVCC, <https://brandur.org/postgres-queues>, Brandur Leach, 2015-05-18
