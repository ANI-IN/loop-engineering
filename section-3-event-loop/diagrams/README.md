# Module: Loop Engineering - Diagrams for Section 3: Event loop

Each diagram here has an `.excalidraw` source, a `.svg` with the font embedded for pages, and a
`.png` at 2x for slides. The colours, the shapes, the step frames, and how the renders are made are
explained once, in [the shared diagrams page](../../docs/diagrams/README.md#colours-and-shapes).
This section also uses [the run lifecycle](../../docs/diagrams/README.md#the-run-lifecycle).

## The event loop

![The event pipeline: a webhook, the scheduler, or the console sends an event to POST /events, which inserts once per event_id; a fixed router, with no agent, picks the queue in the jobs table; the worker claims a job with a lease and a heartbeat, the reaper requeues an expired lease, and the daily budget is checked at claim; the autonomy policy posts at once or holds the run, which waits as a parked job with its checkpoint until a person approves; the kill switch is checked at claim and before every model call and every tool call](./event-loop.svg)

*Notice that every safeguard here is a row in Postgres, not memory: the event id, the lease, the parked job, and the checkpoint, so a restart loses nothing.*

The snippet for this folder's README or the section's `concepts.md` (both sit one level above
`diagrams/`):

```markdown
![The event pipeline: a webhook, the scheduler, or the console sends an event to POST /events, which inserts once per event_id; a fixed router, with no agent, picks the queue in the jobs table; the worker claims a job with a lease and a heartbeat, the reaper requeues an expired lease, and the daily budget is checked at claim; the autonomy policy posts at once or holds the run, which waits as a parked job with its checkpoint until a person approves; the kill switch is checked at claim and before every model call and every tool call](diagrams/event-loop.svg)

*Notice that every safeguard here is a row in Postgres, not memory: the event id, the lease, the parked job, and the checkpoint, so a restart loses nothing.*
```

- **What it teaches**: the event pipeline in order: idempotency keys, the router that is
  deliberately not an agent, the jobs table as the queue with claim, lease, heartbeat, and
  reaper, the durable approval, and where the kill switch is checked.
- **Slide topic**: the event loop, in Section 3: Event loop.
- **Files**: `event-loop`, with step frames `event-loop-step-1` (the senders and the idempotent
  insert), `-step-2` (the router, the jobs table, the worker), `-step-3` (the reaper and the daily
  budget), `-step-4` (the autonomy policy, the parked job and its checkpoint, the approval, the
  post), and `-step-5` (the kill switch).
- **Source in the code**: `platform/src/datapilot/loop3_events/api/events.py`, `scheduler.py`,
  `router.py`, `worker.py` (claim, a 30-second lease, a heartbeat at a third of it, the fenced
  finish), `reaper.py`, `autonomy.py`, `killswitch.py`, `approvals.py`, `api/control.py`,
  `budget.py`, the jobs
  table in `platform/ops/sql/ops/001_ops_schema.sql` and `002_event_loop.sql` (3 attempts), and
  `budgets` in `platform/packs/datapilot_us/pack.yaml` (2,000,000 tokens a day).
