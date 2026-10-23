# Module: Loop Engineering - Diagrams for Section 3: Event loop

Each diagram here has an `.excalidraw` source, a `.svg` with the font embedded for pages, and a
`.png` at 2x for slides. The colours, the shapes, the step frames, and how the renders are made are
explained once, in [the shared diagrams page](../../docs/diagrams/README.md#colours-and-shapes).
This section also uses [the run lifecycle](../../docs/diagrams/README.md#the-run-lifecycle).

### The event loop

![Events arrive by webhook, scheduler, or console at POST /events, which inserts once per event_id; a fixed router picks the queue; the worker claims jobs from the jobs table with a lease and a heartbeat, the reaper requeues expired leases, and the daily budget and the kill switch are checked; a person approves through POST /approvals, and the paused run waits in its checkpoint](./event-loop.svg)

*Notice that every safeguard here is a row in Postgres, not memory: the event id, the lease, the parked job, and the checkpoint, so a restart loses nothing.*

The snippet for this folder's README or the section's `concepts.md` (both sit one level above
`diagrams/`):

```markdown
![Events arrive by webhook, scheduler, or console at POST /events, which inserts once per event_id; a fixed router picks the queue; the worker claims jobs from the jobs table with a lease and a heartbeat, the reaper requeues expired leases, and the daily budget and the kill switch are checked; a person approves through POST /approvals, and the paused run waits in its checkpoint](diagrams/event-loop.svg)

*Notice that every safeguard here is a row in Postgres, not memory: the event id, the lease, the parked job, and the checkpoint, so a restart loses nothing.*
```

- **What it teaches**: idempotency keys, the jobs table with claim, lease, heartbeat, and reaper,
  the router that is deliberately not an agent, the durable approval, and where the kill switch
  is checked.
- **Slide topic**: the event loop, in Section 3: Event loop.
- **Files**: `event-loop`, with step frames `event-loop-step-1` (the key and the idempotent
  insert), `-step-2` (the router, the jobs table, the worker), `-step-3` (the reaper and the daily
  budget), `-step-4` (the durable approval), and `-step-5` (the kill switch).
- **Source in the code**: `platform/src/datapilot/loop3_events/api/events.py`, `scheduler.py`,
  `router.py`, `worker.py` (claim, a 30-second lease, a heartbeat at a third of it, the fenced
  finish), `reaper.py`, `killswitch.py`, `approvals.py`, `api/control.py`, `budget.py`, the jobs
  table in `platform/ops/sql/ops/001_ops_schema.sql` and `002_event_loop.sql` (3 attempts), and
  `budgets` in `platform/packs/datapilot_us/pack.yaml` (2,000,000 tokens a day).
