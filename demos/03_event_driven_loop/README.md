# Stage 03 — The Event-Driven Loop (Level 3)

> Folder numbers are **loop levels and session stage order**, not phase numbers.
> New to the vocabulary? Read [`demos/README.md`](../README.md) first.
>
> **Built after the verification loop, deliberately.** The teaching point below only
> works once the verifiers exist.

---

## What this level ADDS

Nobody watching.

Levels 1 and 2 run because a person typed a command and read the output. Here a worker
polls a queue, claims a question, runs the **Level 2 loop**, and writes the answer back
— with no human in the path.

That is the whole point, and it is a point about **Level 2** rather than about queues:

> **The verifiers are now the only thing standing between the queue and whatever
> consumes these answers.**

Everything the previous stage said about a verifier being a measuring instrument stops
being an argument about measurement and becomes an argument about what ships.

### The control flow

```mermaid
flowchart TD
    subgraph PRODUCERS["Producers — a phone, a terminal, the AGENT view's enqueue box"]
        E["enqueue(question)"]
    end
    E -->|"INSERT status='queued'"| T[("<b>question_queue</b><br/>id · question · status · result · claimed_at")]

    subgraph WORKER["Worker — one process, polling, unattended"]
        POLL["poll"] --> CLAIM["<b>UPDATE ... SET status='claimed'</b><br/>WHERE id = (SELECT MIN(id) WHERE status='queued')<br/><b>RETURNING *</b><br/><i>one statement — two workers cannot claim the same row</i>"]
        CLAIM --> GOT{"Row returned?"}
        GOT -->|no| SLEEP["sleep, poll again"]
        SLEEP --> POLL
        GOT -->|yes| L2["Run the <b>LEVEL 2 loop</b><br/>rules looked up from the gold set"]
        L2 --> RES{"Result?"}
        RES -->|"rows"| DONE["status='done', result written"]
        RES -->|"error, or no result"| FAILED["status='failed', reason written"]
    end
    T --> POLL
    DONE --> T
    FAILED --> T

    subgraph ABSENT["Deliberately NOT built"]
        NB["no backoff"]
        NR["no retry"]
        NDL["no dead-letter queue"]
        NC["Ctrl-C leaves an in-flight row<br/><b>claimed</b> forever"]
    end
    FAILED -.->|"stays failed, where the evidence is visible"| ABSENT

    classDef absent fill:#fee2e2,stroke:#b91c1c,color:#0b1220,stroke-dasharray:5 4;
    classDef store fill:#e0f2fe,stroke:#0369a1,color:#0b1220;
    class NB,NR,NDL,NC absent;
    class T store;
```

**The atomic claim is the one part of a queue worth getting right even in a demo.** The
`UPDATE ... RETURNING` is a single statement, so two workers cannot claim the same row:
whichever commits first moves it out of `queued` and the other's subquery finds nothing.
That is the whole of the concurrency story.

**The omissions in red are the point, not an apology.** No backoff — a worker that cannot
reach the model spins and you see it. No dead-lettering — a failed row stays `failed`
where the evidence is visible. No retry — nothing quietly tries again behind your back.
Those are the things you would have to build before this went near anything real, and
**naming them is more useful than half-implementing them**.

The queue lives in its own DuckDB file, separate from the warehouse. The warehouse is
opened read-only by everything that touches it and a queue needs writes; sharing one file
would mean relaxing that guarantee.

A question that is not in the gold set gets **no rules**, which means the verifiers check
nothing for it. That is honest rather than convenient: inventing a rule set for an unknown
question would be the verifier claiming a coverage it does not have.

---

## What this level COSTS

One Level 2 run per queued question, so per-question cost matches stage 02. The
difference is that **nothing here is bounded by someone's attention** — the worker keeps
claiming rows until the queue is empty.

Enqueue a small number of questions for the demo. The meter is the same as everywhere:
tokens measured, dollars estimated, `est.` prefix, every call counted.

Stop the worker with Ctrl-C. An in-flight row stays `claimed`; that is a visible
consequence of having no retry logic, and it is worth showing rather than hiding.

---

## Run it COLD

No prior step required. The queue table is created on first connect.

**This stage needs two terminals.** Make both visible on the projector before you start,
and set the font size large **before** the session — the event-driven terminal is not a
"view" so it gets missed in the legibility check.

### Terminal 1 — the worker

```bash
uv run python demos/03_event_driven_loop/worker.py
```

**What appears:** `worker up. polling every 2.0s.` and a reminder that there is no
backoff, no dead-lettering and no retry. Then nothing, until a row arrives.

**What to observe:** the silence. The worker is running with nothing to do and no one
watching it.

### Terminal 2 — submit a question

```bash
uv run python demos/03_event_driven_loop/enqueue.py \
  --question "What share of beauty orders ended up with a refund?"

# see the whole queue and its status counts
uv run python demos/03_event_driven_loop/enqueue.py --list

# defaults to a gold question if you omit --question
uv run python demos/03_event_driven_loop/enqueue.py
```

**What appears in terminal 2:** `queued id=N` and the status counts.

**What appears in terminal 1, unprompted:** `claimed`, then the Level 2 loop running,
then `done` or `failed`.

**What to observe:** the handoff. Nobody typed anything into terminal 1.

**The question to sit with:** *the verifiers just decided, alone, whether that answer was
good enough to write back. Would you have shipped what they accepted?*

### Draining instead of polling forever

```bash
uv run python demos/03_event_driven_loop/worker.py --drain
```

Stops once the queue is empty. Useful for a dry run; use the polling form in front of a
room, because the waiting is the demonstration.

### If the room cannot reach the enqueue box

There are three paths to a phone and they degrade in this order. **Test the first two
during the dry run**, because the third is the only one that always works.

1. **Share link** — a public tunnel URL, shown with a QR in the AGENT view. Nobody types
   a URL off a projector, so the QR is the actual mechanism.
2. **LAN address** — the laptop's own IP, also shown with a QR. **Many conference access
   points enable client isolation**, which blocks device-to-device traffic and makes this
   fail precisely where it is most needed. Assume nothing.
3. **Shouted from the room, typed by someone who is not the presenter.** Hand the
   keyboard to a person in the front row.

**The third path is not a failure, and this runbook is explicit about that** so nobody
has to improvise an apology. The teaching point of this stage is that **nobody is
watching the worker** — how a row reached the queue is irrelevant to that. A question
typed by an audience member demonstrates it exactly as well, and arguably better, because
the room watches the row appear and then get claimed.

**What you must not do** is type the question yourself and narrate it as though the room
submitted it. Say what happened: *"the wifi is not letting your phones reach my laptop,
so shout it and someone here will type it — watch the worker pick it up."*

---

## Expected SHAPE — and what to say if it does not appear

A row moving through its states — `queued`, `claimed`, then `done` or `failed` — with the
worker log showing a claim and a result. The satisfying part is submitting in one terminal
and watching the other pick it up unprompted.

### If the shape does not appear

*If a row sticks in `claimed`*, that is the no-retry design showing itself. Say so: the
row is stuck because nothing was built to un-stick it, and that is the honest state of a
queue with no dead-letter path.

*If the worker claims nothing*, check the queue actually has a `queued` row — the enqueue
script prints the id it wrote, and `--list` shows the counts. **A silent worker with an
empty queue looks identical to a broken one**, which is itself worth a sentence about
observability.

*If a question fails verification repeatedly*, it lands in `failed` and stays. Point at
it. A queue that quietly drops what it cannot handle is worse than one that leaves the
evidence where you can see it.

*If a submitted question is not in the gold set*, the verifiers check nothing for it and
it will almost certainly come back `done`. Say that out loud — an unverified answer that
looks identical to a verified one is this stage's version of the silent error.

*If both terminals are on one screen and nobody can read them*, that is the legibility
check failing, not the demo. Fix it before the session, not during it.

---

## Where the code lives

| you are looking for | it is in |
|---|---|
| the queue table, the atomic claim, `done`/`failed` | `src/loopeng/queue/store.py` |
| the polling worker and what it does with a failure | `src/loopeng/queue/worker.py` |
| the Level 2 loop it runs | `src/loopeng/verify/loop.py` |
| the room's enqueue box and the QR | `src/loopeng/views/agent.py` |
