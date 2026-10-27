"""Section 3: Event loop, 2:00-2:48, 48 minutes, 13 slides, under design system 2.

The second rebuild's order: the opener, four pattern slides, the pattern in code, DataPilot's
version, the demo, the one evidence slide, the design callout, apply it, pitfalls, and the recap
with the scoreboard. Every course number comes from the section's evidence page and the paired
measurements page (.dev/deck-evidence.md, part E); every external claim from .dev/deck2-sources.md,
whose forbidden claims (part 4) this block keeps: keyed by meaning is the course's own rule (a
sender's stable event id comes first), the three levels and their drops are Greyling's [2] while
the mapping onto Feng and others is ours, the kill switch at every step is the course's design,
and no queue or workflow engine is said to give exactly-once side effects. The run of show: the
patterns and code to 2:18, the demos from 2:18 to 2:38 (no retry after 2:35), then evidence,
design, apply it, pitfalls, and the recap to 2:48, when the poll starts.
"""

RULES = "design system 2"

DEMO_PAGE = "https://github.com/ANI-IN/loop-engineering/tree/main/section-3-event-loop/demo"
EXPECTED = "section-3-event-loop/demo/expected/"

SLIDES = [
    # 1 section opener --------------------------------------------------------------------------
    dict(
        kind="opener",
        title="Section 3: Event loop",
        minutes=1.5,
        says="Nobody watches each run now: work repeats, waits through restarts, and must stop",
        src="section-3-event-loop/README.md; section-3-event-loop/demo/expected/"
        "events-duplicate-events-no-idempotency-channel.png; Source 27; .dev/deck-evidence.md E33",
        on_slide=[
            "Fixes: an answer posted twice, an approval lost in a restart, a stop that misses "
            "the running job",
            "Insight: Delivery is at least once[^88][^92]; only your handler can ensure the "
            "effect happens once.",
        ],
        notes=[
            "Purpose: Open Section 3 from Section 2's scoreboard, and make the failure of "
            "unattended work felt before any pattern is named.",
            "What to say: Welcome back. Before the break the scoreboard read: the wrong answer "
            "is caught and flagged, but only while someone is watching. For our question the "
            "reviewer held it; across 40 trap runs the layer flagged half, so flagging is not "
            "fixing. Now take the watcher away. Questions arrive as webhooks, the digest fires at 8 a.m. Eastern time, and "
            "nobody reads each answer before it posts. Here is what that looked like in a live "
            "run with one safeguard switched off. The finance channel got two digests for the "
            "same day, 30 January, with different figures, because the scheduler's event "
            "arrived twice and each copy looked new. Nothing crashed; every check passed. The "
            "insight on the band: delivery is at least once, so only your handler can ensure "
            "the effect happens once.",
            "The point to land: The event loop adds no intelligence; it makes runs safe to "
            "repeat, to wait, and to stop.",
            "Example: Amazon's queue documentation, Source 88, and Kafka's, Source 92, both "
            "promise at-least-once delivery; the Prisma write-up of a Postgres queue, Source "
            "27, says the same of its own design.",
            'Ask the room: "Which of your agents runs from a schedule or a webhook today?" '
            "Expect: report bots, ticket triage, and a few who say none yet.",
            "Misconceptions: That event-driven agents need a new framework. They need a key, a "
            "lease, durable state, and a stop, which you already know how to build.",
            "Transition: The first pattern takes the two digests head on: at-least-once "
            "delivery and idempotency keys.",
        ],
    ),
    # 2 pattern: at-least-once delivery and idempotency keys -----------------------------------
    dict(
        kind="pattern",
        title="At-least-once delivery and idempotency keys",
        minutes=3,
        says="Events arrive more than once; a key from what the event means lets it act once",
        src="docs/diagrams/patterns/README.md (pattern-idempotency-key); Sources 86, 87, 88, "
        "92, 95; .dev/deck2-sources.md part 4 item 2",
        figure={
            "diagram": "pattern-idempotency-key",
            "alt": "A sender that retries delivers the same event twice; the key is built from "
            "the meaning, which order, which action, which day, not from the delivery "
            "identifier, since a retry may get a new one; the key goes to a store of keys done "
            "with a unique constraint; a new key does the work once, and a seen key returns "
            "the first result",
        },
        on_slide=[
            "Definition: Events repeat; act once per key: a stable event id, else meaning (our "
            "rule).",
            "Use when: events can arrive twice",
            "Avoid when: the handler only reads",
            "Elsewhere: Stripe: skip webhook event ids already logged[^87]; Kafka: at least "
            "once[^92]",
        ],
        notes=[
            "Purpose: Define at-least-once delivery and the idempotency key keyed by meaning, "
            "the course's rule, before any DataPilot code.",
            "What to say: The problem first, in general terms. Anything that receives events "
            "over a network gets some of them more than once: a sender retries when an "
            "acknowledgement is lost, a queue hands a message out again after a timeout, a "
            "person clicks twice. That is at-least-once delivery, and it is the normal "
            "contract, not a fault. The pattern that makes it safe is the idempotency key. "
            "Walk the diagram left to right. A sender that retries delivers the same event "
            "twice. The handler's key is the sender's stable event id, else the meaning: which "
            "order, which action, which day. The caption under the sender: not an id stamped "
            "on each attempt, because a retry may get a new one; a sender's event id stays the "
            "same. The key goes into a store with a unique constraint. A new key does the "
            "work once; a seen key returns the first result. So which key? If the sender "
            "keeps a stable event id across retries, use it: Stripe's webhook documentation, "
            "Source 87, says log the event ids you processed and skip those. When there is no "
            "such id, or two senders can ask for the same effect, build the key from meaning; "
            "that part is our rule, the course's own. Kafka, Source 92, "
            "delivers at least once by default and notes that a message with a primary key "
            "makes the update idempotent. Stripe's own application programming interface, "
            "Source 86, takes a random key per request instead: that guards one caller's "
            "retries, not two senders asking for the same thing. Alternatives: remember seen "
            "events in memory, which a restart forgets; or make the effect naturally "
            "idempotent, an overwrite by primary key, which is ideal and rarely possible when "
            "the effect is a posted message or an email.",
            "The point to land: Assume every event arrives twice; key the effect by what the "
            "event means, and let a unique constraint decide.",
            "Example: Stripe's webhook consumer, Source 87, is the sourced transfer: a payments "
            "handler that logs each event id and skips repeats. An illustrative coding agent: "
            "key a review by repository, pull request and commit, so a resent webhook opens "
            "no second review.",
            'Ask the room: "What would the key be for your busiest event?" Expect: its '
            "id; ask whether that id survives a retry, and if not, what the event means.",
            "Misconceptions: That exactly-once delivery can be switched on. Kafka's "
            "exactly-once needs the destination's cooperation, Source 92, and Amazon's queue "
            "documentation, Source 88, says design your applications to be idempotent. Also, "
            "never put personal data such as an email address in a key, as Source 86 warns.",
            "Transition: A key stops a repeat from acting twice. Next, what happens when the "
            "worker doing the job dies: durable job queues with leases.",
        ],
    ),
    # 3 pattern: durable job queues with leases ------------------------------------------------
    dict(
        kind="pattern",
        title="Durable job queues with leases",
        minutes=2.5,
        says="A claimed job carries a lease; a dead worker's job returns and may run twice",
        src="docs/diagrams/patterns/README.md (pattern-lease-queue); Sources 26, 28, 89, 90, "
        "91; section-3-event-loop/concepts.md",
        figure={
            "diagram": "pattern-lease-queue",
            "alt": "A jobs table where each claimed job has a lease end; a worker claims a job "
            "and its lease ends in 5 minutes; the worker crashes; the lease ends and the job is "
            "pending again; another worker claims it; so a job may run twice, and managed "
            "queues call the lease a visibility timeout",
        },
        on_slide=[
            "Definition: Claim each job with a lease; when it ends, the job returns to the queue.",
            "Use when: jobs are slow and workers can die",
            "Avoid when: instant work, cheap to resend",
            "Elsewhere: Amazon Simple Queue Service's visibility timeout[^89]; Google's lease "
            "management[^91]",
        ],
        notes=[
            "Purpose: Define the durable job queue with leases, and show the same idea under "
            "its managed-queue names.",
            "What to say: The problem: a worker takes a job and then dies, in a deploy, a crash, "
            "or a lost connection. Who finishes the job? The pattern is a durable job queue "
            "with leases. Walk the diagram. The jobs live in a table, so they survive any "
            "process. A worker claims a job, and the claim carries a lease: an end time, "
            "here five minutes. The worker crashes. The lease ends, the job is pending again, "
            "and another worker claims it. A crash loses no job. But read the note under the "
            "table: the same mechanism is why a job can run twice, which is why the key from "
            "the last slide comes first. Managed queues do exactly this. Amazon Simple Queue "
            "Service calls the lease a visibility timeout, Source 89: an undeleted message "
            "becomes visible again and another consumer can take it; you extend it with a "
            "heartbeat while you work, and it says plainly that a message may still be "
            "delivered more than once. Google's queue, Source 91, names the trade-off: a short "
            "lease means more duplicates, a long one delays the retry of a failed message. "
            "Count every claim as an attempt and park a job that keeps failing: Amazon's "
            "dead-letter queue, Source 90, moves a message after a set number of receives. In "
            "Postgres, skip locked rows, Source 28, lets many workers claim at once.",
            "The point to land: A lease turns ownership into a row with an end time; a crash "
            "returns the job, and a duplicate run is the price.",
            "Example: An illustrative coding agent that runs long test suites: each suite is a "
            "job with a lease and a heartbeat, so a lost build machine hands its suite to "
            "another.",
            'Ask the room: "How long do your slowest agent runs take, and what is your '
            'timeout?" Expect: runs of minutes, and timeouts set long ago for something else.',
            "Misconceptions: That holding a database lock through the whole run is simpler. A "
            "long transaction piles up dead rows, Source 26, and hides the job's real state; "
            "the pitfalls slide shows what it did here.",
            "Transition: Some jobs cannot finish without a person, and must stop on command. "
            "Next: durable approvals and a kill switch checked at every step.",
        ],
    ),
    # 4 pattern: durable execution for human approval, and the kill switch ---------------------
    dict(
        kind="pattern",
        title="Durable approvals and a kill switch at every step",
        minutes=3,
        says="Checkpoint each step so a run waits for a person in the database; read the stop "
        "every step",
        src="docs/diagrams/patterns/README.md (pattern-durable-approval); Sources 10, 93, 95, "
        "96, 98, 100; .dev/deck2-sources.md part 4 items 4 and 5",
        figure={
            "diagram": "pattern-durable-approval",
            "alt": "Steps run while saving state; a checkpoint is saved in a database, and the "
            "process may exit meanwhile; a person approves, hours or days later; the run "
            "resumes from the checkpoint, even after a restart; across the top, a kill switch "
            "is read before every step, and when it is on, the run stops",
        },
        on_slide=[
            "Definition: Paused runs wait in a database checkpoint; our rule: read the stop each "
            "step.",
            "Use when: a run must wait for a person",
            "Avoid when: nothing waits; keep the stop",
            "Elsewhere: Temporal's Approval pattern blocks until a decision or a timeout[^96]",
        ],
        notes=[
            "Purpose: Define durable execution with checkpoints for human approval, and the kill "
            "switch read before every step, the course's design.",
            "What to say: Two problems that look different and share one answer. First, a run "
            "must wait for a person, maybe for hours, and the worker will restart in the "
            "meantime. Second, someone must be able to stop everything, including the run "
            "already going. Walk the diagram. Steps run, saving state as they go. At the "
            "approval the state is a checkpoint in a database, and the process may exit. A "
            "person approves, hours or days later. The run resumes from the checkpoint, even "
            "after a restart. That is durable execution: Temporal, Source 93, defines it as a "
            "run that keeps its state and progress through failures and crashes, and its "
            "Approval pattern, Source 96, blocks until a decision arrives, with a timeout path "
            "for rejection or escalation. In LangGraph an interrupt saves the state through a "
            "persistent checkpointer, Sources 98 and 10. Two cautions. Resuming re-runs the "
            "step that paused, so any effect before the pause must be idempotent. And durable "
            "is not exactly-once: Temporal says its activities may run more than once, Source "
            "95. Decide the hold from data, never from a model, and offer approve or reject "
            "only. Now the bar across the top: the kill switch, read before every step. OpenAI's "
            "governance paper, Source 100, calls interruptibility a critical backstop and says "
            "stopping mid-sequence is the hard part. Reading it before every model call and "
            "every tool call is our design. A stop still waits for the call in flight, and "
            "DataPilot sets no request timeout of its own; in yours, the request timeout is "
            "your worst-case time to stop.",
            "The point to land: A pause is state, so store it where state survives; and a stop "
            "only works if every step reads it.",
            "Example: The sourced transfer is OpenAI's own, Source 100: a scheduling assistant "
            "stopped while arranging a five-person meeting, after only two invites had gone "
            "out; those stay sent. An illustrative "
            "support agent holds every refund over a set amount for approval.",
            'Ask the room: "Where does a paused run of your agent live today?" Expect: in '
            "memory, or nowhere because nothing pauses.",
            "Misconceptions: That the approval is a dialog. The dialog is a view; the approval "
            "is a checkpoint and a decision record. And a stop does not undo what already ran.",
            "Transition: With repeats, crashes, waits and stops handled, how much may the agent "
            "do alone? Next: autonomy levels, earned by forcing failures.",
        ],
    ),
    # 5 pattern: autonomy levels and proving fixes by forcing failures -------------------------
    dict(
        kind="pattern",
        title="Autonomy levels, earned by forcing failures",
        minutes=2.5,
        says="Report-only, assisted, unattended: each step up earned, and any stop drops to "
        "report-only",
        src="docs/diagrams/patterns/README.md (pattern-autonomy-levels); Sources 2, 103, 104; "
        "section-3-event-loop/concepts.md, Autonomy levels; pack.yaml autonomy; "
        ".dev/deck-evidence.md E33 to E35",
        figure={
            "diagram": "pattern-autonomy-levels",
            "alt": "Report-only, where the agent reports and people act; assisted, where it "
            "acts and risky actions wait for a person; unattended, where it acts alone within "
            "its limits; each step up is earned, an incident drops unattended back to assisted, "
            "and a kill switch drops any level to report-only; the evidence to step up is to "
            "force each failure on purpose and show the fix holds",
        },
        on_slide=[
            "Definition: Three levels: report-only, assisted, unattended; each step up is earned.",
            "Use when: an agent acts without a reviewer",
            "Avoid when: a person reads every output",
            "Elsewhere: Greyling: these three levels and their drops[^2]; Feng and others: five "
            "levels[^103]",
        ],
        notes=[
            "Purpose: Define the three autonomy levels, credited to Greyling, and proving each "
            "safeguard by forcing its failure on purpose.",
            "What to say: The problem: an agent that works in a demo is given full autonomy, "
            "and the first incident is how you learn it was not ready. The pattern is "
            "autonomy in levels. Walk the diagram left to right. At the report-only level the "
            "agent reports and people act. At the assisted level it acts, and risky actions "
            "wait for a person. At the unattended level it acts alone, within its limits. "
            "Each step up is earned; coming down is fast: an incident drops unattended to "
            "assisted, and the kill switch drops any level to report-only. The levels and both "
            "drops are Cobus Greyling's, Source 2. Feng and others, Source 103, define five "
            "levels by the user's role; our reading, not theirs: assisted maps to their "
            "approver role, unattended to their observer role. To earn a step, bottom right: "
            "force each failure on purpose and show the fix holds, chaos engineering's idea, "
            "Source 104: a steady state, real faults, a small blast radius. Alternatives: one "
            "on-off switch for the whole agent, simple but all or nothing; an amount threshold "
            "per action, precise but blind to new kinds of risk; or shadow mode, deciding "
            "beside a person, which earns evidence at the cost of running twice. In DataPilot, "
            "report-only posts answers labelled unverified and runs no export; assisted needs "
            "approval for exports and personal data. It is stricter than the diagram: three "
            "escalations in a row, a holdout regression or an exhausted daily budget drop it "
            "straight to report-only.",
            "The point to land: Grant autonomy one earned step at a time, take it back at once, "
            "and earn each step by forcing the failure it guards against.",
            "Example: An illustrative workflow agent that files expense reports starts by "
            "drafting them for a person, then submits small ones alone once a forced duplicate "
            "and a forced restart both held.",
            'Ask the room: "What would your agent need to show before it acts alone?" Expect: '
            "good test scores; push for forced failures, not only happy paths.",
            "Misconceptions: That autonomy is granted per agent. Grant it per capability; "
            "DataPilot grants it per metric family. And the levels are not the driving levels; "
            "do not map them so.",
            "Transition: Those are the four patterns. Here they are as a few lines of generic "
            "code.",
        ],
    ),
    # 6 the pattern in code ---------------------------------------------------------------------
    dict(
        kind="mechanism",
        title="The pattern in code: keyed, leased, stoppable",
        minutes=2.5,
        says="Key and job in one commit, a lease a heartbeat renews, the stop read before each "
        "step",
        src="generic pseudocode written for the course",
        code={
            "language": "python",
            "panel": "Pattern",
            "origin": "generic pseudocode written for the course, in Python syntax",
            "lines": [
                "def on_event(event, db):",
                "    db.insert_key_and_job(event.id or key_from_meaning(event))",
                "",
                "def work(db, me):",
                "    if not (job := db.claim(owner=me, lease=30, heartbeat=True)): return",
                "    for step in job.steps_after_checkpoint():",
                '        if db.kill_switch_on(): return job.finish("stopped")',
                "        step.run(checkpoint=db, fence=job.fence)",
                '    job.finish("done")',
            ],
            "marks": [
                (1, "event.id or key_from_meaning(event)", 1),
                (4, "lease=30, heartbeat=True", 2),
                (6, "db.kill_switch_on()", 3),
                (7, "fence=job.fence", 4),
            ],
        },
        on_slide=[
            "Idea: same code for a payment webhook, a ticket event, a nightly report",
            "1. Event id, else meaning",
            "2. A heartbeat lease",
            "3. Stop read every step",
            "4. Writes fenced on the owner",
        ],
        notes=[
            "Purpose: Show the four patterns as eight lines of generic code a learner can carry "
            "into any event handler and worker.",
            "What to say: Eight lines of code in two functions, a blank line between them. Marker one, line two: the "
            "key is the sender's event id when it has a stable one, else one built from "
            "meaning: kind, subject, business day. The key and its job are inserted in one "
            "transaction: the key's insert does nothing on a conflict, so a repeat adds no "
            "job, and a crash cannot record the key and lose the job. The second function is "
            "the worker. Marker two, line five: claim one job with a lease, committed at once, "
            "and a heartbeat on a timer that renews it at a third of its length, because one "
            "model call can outlast the lease; no job means an empty queue, so return and poll "
            "again. Line six: run the steps after the last checkpoint, so a reclaimed job "
            "resumes. Marker three, line seven: before every step, read the kill switch; it "
            "finishes the job as stopped. Marker four, line eight: run the step and save "
            "its checkpoint, fenced. Checking the lease between steps is not enough, because "
            "the heartbeat can lose it mid-step: a lease is not a lock. So every write the "
            "step makes is conditional on this owner and this attempt, the fencing token, in "
            "the same transaction as the effect; when the lease is lost, that write is refused "
            "and raises, so the worker walks away without marking anything, because the job is "
            "someone else's now. Line nine: mark "
            "the job done, fenced the same "
            "way. Left out: the reaper that returns expired jobs, and the attempt count that "
            "parks a job which keeps failing.",
            "The point to land: Every guarantee here is a row the database checks, not a "
            "variable in the worker's memory.",
            "Example: An illustrative workflow agent that files expense reports runs on the "
            "same eight lines: the report's id is the key, and each submission is a fenced "
            "write.",
            'Ask the room: "Where would a crash after a step acts, before its checkpoint, '
            'leave you?" Expect: the lease runs out, the job returns, and the step runs again, '
            "so it must be idempotent.",
            "Misconceptions: That checking for the key before inserting it is enough. Two "
            "workers can both see no key; only the insert itself is atomic.",
            "Transition: Now DataPilot's version: the insert that absorbs a repeat, and the one "
            "statement that claims a job.",
        ],
    ),
    # 7 DataPilot's version --------------------------------------------------------------------
    dict(
        kind="mechanism",
        title="DataPilot's version: insert once, claim with a lease",
        minutes=3,
        says="A repeated event id inserts nothing; one statement claims a job with a lease",
        src="platform/src/datapilot/loop3_events/api/events.py lines 38-58; "
        "platform/src/datapilot/loop3_events/worker.py lines 70-90 and 183-202; "
        "platform/src/datapilot/loop3_events/killswitch.py lines 89-113; "
        "platform/src/datapilot/loop3_events/approvals.py lines 44-47; Sources 28, 87",
        code={
            "language": "python",
            "panel": "DataPilot",
            "origin": "platform/src/datapilot/loop3_events/api/events.py lines 38-42 (the columns, "
            "values and arguments of the insert shortened to ...; the first line joined; lines 43-58, which record a duplicate "
            "and return the first run, are in the notes), a comment line naming the claim, "
            "then the claim statement of "
            "platform/src/datapilot/loop3_events/worker.py lines 70-81, rewrapped, with "
            "updated_at, the run_after and queue filters, and the returned columns left out",
            "lines": [
                'inserted = conn.execute("INSERT INTO ops.events (event_id, ...) VALUES (...) "',
                '    "ON CONFLICT (event_id) DO NOTHING RETURNING event_id", ...).fetchone()',
                "# the worker's claim statement, in SQL",
                "UPDATE ops.jobs SET status = 'running', attempts = attempts + 1, lease_owner = %(owner)s,",
                "    lease_until = now() + make_interval(secs => %(lease)s), ...",
                "WHERE job_id = (SELECT job_id FROM ops.jobs WHERE status = 'queued' ...",
                "    ORDER BY run_after, job_id FOR UPDATE SKIP LOCKED LIMIT 1)",
            ],
            "marks": [
                (1, "ON CONFLICT (event_id) DO NOTHING", 1),
                (3, "attempts = attempts + 1", 2),
                (4, "lease_until", 3),
                (6, "FOR UPDATE SKIP LOCKED", 4),
            ],
        },
        on_slide=[
            "Idea: Postgres decides what is new, and who owns each job",
            "1. Repeats insert nothing[^87]",
            "2. Counts an attempt",
            "3. Leased, not locked",
            "4. Skip held rows[^28]",
        ],
        notes=[
            "Purpose: Show DataPilot's real code for the key and the lease, explained line by "
            "line, with the approval and kill switch code described.",
            "What to say: Two pieces. The first two lines are the "
            "event endpoint. The event id goes into the events table under a unique "
            "constraint. Marker one: a repeated id hits the conflict and inserts nothing, so "
            "the call returns no row; the lines left out count it as a duplicate and return "
            "the first run. For a webhook the key is the sender's event id, which the sender "
            "keeps across retries, the Stripe pattern of Source 87; for the digest it is built "
            "from meaning, the business day plus the firing. The event, its job and its run "
            "commit in one transaction. After the comment line comes the worker's claim, one "
            "SQL statement. Marker two: the claim "
            "counts an attempt, so a job that keeps killing its worker is marked dead after "
            "its attempts run out, not retried forever. Marker three: the lease, which names its owner and an end time "
            "30 seconds ahead, extended by a heartbeat every 10 seconds. The claim commits at "
            "once. DataPilot's fence is twofold: the post and the run's status change share "
            "one transaction under a row lock that refuses posted to posted, and the finish "
            "statement matches the lease owner and the attempt, so a frozen worker cannot "
            "overwrite a job another worker took over. The last two lines pick the earliest "
            "due queued job; marker four, skip rows other workers have locked, the pattern the PostgreSQL documentation, Source 28, gives for queue-like "
            "tables. Beside this, the approval checkpointer is LangGraph's "
            "Postgres saver, keyed by the run id. The kill switch is middleware that reads the "
            "switch before every model call, ending the run, and before every tool call, "
            "skipping the tool. The channel is a table here too, so a post and the run's status "
            "commit together; outside effects need the pitfalls slide's outbox.",
            "The point to land: Let the database's constraints decide what is new and who owns "
            "a job; the code only asks.",
            "Example: The digest's key is the business day plus the firing, so one firing "
            "delivered twice for 30 January is one digest.",
            'Ask the room: "Which of your queues would let two workers run the same job?" '
            "Expect: any that claim by reading then updating in two steps.",
            "Misconceptions: That skip locked gives exactly-once processing. It gives exclusive "
            "claims; a crash after the effect still repeats the job, which is why the key "
            "comes first.",
            "Transition: Time to see every one of these fail with its bug on, and hold with it "
            "off, live.",
        ],
    ),
    # 8 demo ------------------------------------------------------------------------------------
    dict(
        kind="demo",
        title="Live: events, approvals, duplicates, kill switch",
        minutes=20,
        says="The event-loop demos, live; each safeguard fails with its bug on and holds with it off",
        src="platform/demos/registry.yaml (section event-loop); section-3-event-loop/demo/"
        "README.md; docs/instructor-guide.md, Section 3: Event loop; .dev/deck-evidence.md "
        "E33 to E36; lead rulings round 3, slide 48",
        on_slide=[
            "Badge: DEMO - 3",
            "What to watch for:",
            "- **Webhook:** one strip, Queued to Done",
            "- **Restart:** the held export survives",
            "- **Duplicates:** three sent, one answer",
            "Guaranteed moment: the kill switch stops the run in flight and drops the level to "
            "report-only",
            "Link: Demo page on GitHub | " + DEMO_PAGE,
        ],
        notes=[
            "Purpose: Run the event-loop demos live, both halves where a planted bug exists, so "
            "each safeguard is seen failing and then holding.",
            "What to say: Let's watch the event loop run with nobody pressing Ask. Everything "
            "you see is live, against the same model as in the earlier sections, and every "
            "strip carries its start time and its trace link. Three of these demos run twice: "
            "first with one line of code switched to the broken version, then with the fix. "
            "The model is the same in both halves; only that line differs. Keep an eye on the "
            "run board at the top: each strip is one run moving from Queued to Done, and the "
            "lanes off the board, Failed and Blocked by kill switch, are where the planted "
            "halves end up. The channel at the bottom is what a finance team would read. When "
            "a run is waiting, predict in the chat what happens next before the strip moves.",
            "Demo: The webhook question.",
            "Command: 2:18 to 2:21, the registry's 3 minutes. make demo "
            "NAME=events-webhook-question, or Events > Send webhook question in the console.",
            "Point at: the strip appearing in Queued and moving to Running, Verifying, and Done; "
            "then the channel post labelled unverified, the report-only level from the "
            "autonomy slide; then the live stamp.",
            "Expected output: one strip from Queued to Done and one post labelled unverified, in "
            "12 to 46 seconds in the recorded runs. The count is 300 orders, the Eastern time "
            "day, or 291, the same day in Coordinated Universal Time; the reviewer approved both "
            "in calibration. Keep a 291 on screen and teach it; do not reset for a better "
            "number.",
            "While it runs: say that nobody pressed Ask: a webhook became an event row and a job "
            "row, and a worker claimed it with the claim from the code slide.",
            "If it fails: run make reset NAME=event-loop (about 7 seconds; 6.4 to 6.9 measured on "
            "the class stack), then the same trigger again; a missing trace link is not a "
            "failure. The same rule for every demo here: a retry spends the 1-minute reserve at "
            "2:37; start no retry after 2:35. Past that, skip it, say so, and name that demo "
            "for the Thursday review.",
            "Backup screenshot: " + EXPECTED + "events-webhook-question-board.png, the strip in "
            "Done; point at it only while you reset and run again, never instead of the run.",
            "Demo: The approval that survives a restart.",
            "Command: 2:21 to 2:27, 6 minutes: the registry's 5 for one half, plus the planted "
            "half. Planted half first, measured twice, 41 seconds both times: make demo "
            "NAME=events-approval-survives-restart PLANTED=1 (the in-memory checkpointer; the "
            "command restarts the worker with it and waits for the run to end). When the strip "
            "reaches Holding for approval, press Restart worker, then Approve: the approval "
            "finds no checkpoint to resume and the run fails. Wait for the terminal's line "
            "Restarting worker without the demo's flags, then make reset NAME=event-loop (about "
            "7 seconds) and the fixed half: make demo NAME=events-approval-survives-restart, or "
            "Events > Request California export; at Holding for approval press Restart worker, "
            "wait for the worker to come back (its restart time is not measured on its own; the "
            "whole demo took 50 to 84 seconds), then approve in the dialog.",
            "Point at: planted half, the line that the pending approval was lost and the run in "
            "Failed (the card's words about the trace only mean that day's tracing quota was "
            "used up); fixed half, the dialog's exact query and row count, the strip staying "
            "in Holding for approval across the restart, and Done after Approve.",
            "Expected output: the strip stays in Holding for approval across the restart, then "
            "moves to Done, in 50 to 84 seconds in the recorded runs; the planted half fails "
            "the run with the pending approval lost.",
            "While it runs: say that restarting the worker is the deploy or the crash of a "
            "normal Tuesday, and that the pause is a checkpoint in Postgres keyed by the run.",
            "If it fails: run make reset NAME=event-loop (about 7 seconds), then the same trigger "
            "again, no retry after 2:35; if the Restart worker button does nothing, demo "
            "controls are off, so take the next demo and return to this one after the section. "
            "In the planted half, the terminal can wait up to 900 seconds, and until it prints "
            "Restarting worker without the demo's flags the worker claims only this demo's "
            "runs: if that line has not appeared within a minute of Approve, press Ctrl+C in "
            "the demo terminal, which restarts the worker without the flag at once, then make "
            "reset NAME=event-loop and the fixed half.",
            "Backup screenshot: " + EXPECTED + "events-approval-after-restart.png, the export "
            "still held after the restart; for the planted half, "
            + EXPECTED
            + "events-approval-lost-after-restart.png; point at either only while you reset "
            "and run again.",
            "Demo: Duplicate events.",
            "Command: 2:27 to 2:31, 4 minutes: the registry's 3 for one half, plus the planted "
            "half. make demo NAME=events-duplicate-events PLANTED=1 first (the missing "
            "idempotency and the random digest id); then make reset NAME=event-loop and Events > "
            "Send the same event three times, or make demo NAME=events-duplicate-events.",
            "Point at: with the bugs on, the repeated answers and the two digests in the "
            "channel; with them off, one post and the strip's 2 duplicates absorbed; then the "
            "live stamp.",
            "Expected output: one answer posted, two duplicates absorbed, and one digest, in 35 "
            "to 78 seconds in the recorded runs; the planted half posts 3 answers and 2 "
            "digests.",
            "While it runs: ask the room to predict the count on the board before it appears; "
            "the order of the three deliveries does not matter, the key decides. Ahead by 3 "
            "minutes or more? Run The digest now here, before the kill switch.",
            "If it fails: run make reset NAME=event-loop (about 7 seconds), then the same trigger "
            "again, no retry after 2:35.",
            "Backup screenshot: " + EXPECTED + "events-duplicate-events-board.png, the strip "
            "marked 2 duplicates absorbed; for the planted half, "
            + EXPECTED
            + "events-duplicate-events-no-idempotency-channel.png, the two digests; point at "
            "either only while you reset and run again.",
            "Demo: The kill switch in flight.",
            "Command: 2:31 to 2:37, 6 minutes: the registry's 4 for one half, plus the planted "
            "half and two resets. make demo NAME=events-kill-switch-in-flight PLANTED=1 (the kill "
            "switch at claim only), then make reset NAME=event-loop, then make demo "
            "NAME=events-kill-switch-in-flight, then make reset NAME=event-loop again (each reset "
            "about 7 seconds). Run both halves from the terminal: the console's button sends no "
            "demo pacing.",
            "Point at: with the bug on, the strip still moving after the switch and the post; "
            "with it off, the strip moving to Blocked by kill switch and the status line at the "
            "report-only level.",
            "Expected output: the in-flight strip moves to Blocked by kill switch and the status "
            "line shows the report-only level, in 3 to 33 seconds in the recorded runs; the "
            "planted half posts after the switch.",
            "While it runs: say that which step the run stops at does not matter, as long as no "
            "model call starts after the stop; a model call already running finishes, and the "
            "check before the next step ends the run. DataPilot sets no request timeout of its "
            "own, so in the worst case a stop waits for the client library's default; in "
            "yours, the request timeout is your worst-case time to stop.",
            "If it fails: run make reset NAME=event-loop (about 7 seconds), then the same trigger "
            "again, no retry after 2:35; if the run finished before the switch, it was sent "
            "without pacing, so use the make command.",
            "Backup screenshot: " + EXPECTED + "events-kill-switch-in-flight-board.png, the run "
            "under Blocked by kill switch; point at it only while you reset and run again.",
            "Demo: The digest now.",
            "Command: optional, and cut first: run it only when the section is at least 3 "
            "minutes ahead of the clock, right after Duplicate events and before the kill "
            "switch demo (it is listed last only because it is optional). make demo "
            "NAME=events-digest-now, or Events > Run digest now. Otherwise the 1-minute reserve, "
            "2:37 to 2:38, takes one reset and run again, or questions.",
            "Point at: the one digest post with the previous business day's key figures.",
            "Expected output: one digest post; no measured time is on the evidence page, and the "
            "registry gives it 3 minutes.",
            "While it runs: say that the 8 a.m. Eastern time schedule fires the same job, keyed "
            "by the business day and the firing.",
            "If it fails: run make reset NAME=event-loop (about 7 seconds) and cut it; the "
            "duplicates demo already showed one digest.",
            "Backup screenshot: none is captured for this optional demo; describe the single "
            "digest post while you reset, or move on.",
            "The point to land: Each safeguard failed live with its bug on and held with it off; "
            "that pair is the evidence.",
            "Example: The scheduler's digest is keyed by the business day and the firing, so the "
            "planted random digest id is what let a second digest through.",
            'Ask the room: "Which of the four would have hurt your team most last quarter?" '
            "Expect: duplicates from retries.",
            "Misconceptions: That the planted half is a staged failure. The model runs for real "
            "in both halves; only one line of code differs.",
            "Transition: Those were single runs. Next, the evidence: every recorded run of each "
            "half, with its sample size.",
        ],
    ),
    # 9 evidence --------------------------------------------------------------------------------
    dict(
        kind="evidence",
        title="Prove each safeguard by forcing its failure",
        minutes=2,
        says="Planted bugs failed in 17 of 17 runs; the fixes held in 23 of 23",
        src="docs/evidence/section-3-event-loop.md, Results; docs/benefits.md, Section 3; "
        "section-3-event-loop/concepts.md, What we measured; .dev/deck-evidence.md E33 to E35",
        chart={
            "type": "column",
            "title": "Failed with the bug, held with the fix",
            "categories": ["Sent three times", "Restart while held", "Stopped in a run"],
            "series": [
                ("Bug on, runs that failed", [5, 6, 6]),
                ("Fix on, runs that held", [7, 7, 9]),
            ],
            "x_label": "Failure forced on purpose",
            "y_label": "Runs",
            "maximum": 10,
        },
        on_slide=[
            "Sample: 17 runs with the bug on, 23 with the fix, gpt-6-luna",
            "- Lesson: a deterministic safeguard holds every time; prove it by forcing the failure",
            "- Bug on: the failure in 17 of 17 runs",
            "- Fix on: it held in 23 of 23 runs",
        ],
        notes=[
            "Purpose: Show every recorded run of the three safeguards, off and on, with the "
            "sample size stated plainly.",
            "What to say: You just saw one run of each half; this is every recorded run behind "
            "them, from the section's evidence page, 23 to 25 October. Each pair of bars is one "
            "forced failure: the left bar counts runs that failed with the bug on, the right "
            "bar runs that held with the fix on. Sent three times: with no key, 3 answers and 2 "
            "digests in all 5 runs; with the key, 1 answer and 2 duplicates absorbed in all 7. "
            "A worker restart while an export was held: in memory the approval was lost in all "
            "6; in Postgres it was held and then posted in all 7. Stopped in a run: checked at "
            "claim only, a post after the stop in all 6; checked before every step, stopped in "
            "flight in all 9. The sample line says how much to trust it: 17 "
            "runs with the bug on and 23 with the fix: every time we tried, not rates. The counts are all or nothing because this is "
            "deterministic code around the model, which is the lesson on the right. These live "
            "runs show it holds with the real model in the loop; the same forced failures also "
            "run as automated integration tests against the real Postgres, with a scripted "
            "model in place of the live one.",
            "The point to land: A deterministic safeguard should hold every time; prove it by "
            "making its failure happen on purpose and watching it.",
            "Example: The kill switch's 9 runs include the slowed-down demo run, paced so the "
            "stop can be watched.",
            'Ask the room: "Which of your safeguards have you ever seen fail on purpose?" '
            "Expect: few or none; most are tested only on the happy path.",
            "Misconceptions: That 7 of 7 means it works 100 times in 100. It held in every "
            "recorded run; the guarantee comes from the design, the count shows it was tested.",
            "Transition: Next, the design callout: what the event loop changes in a text-to-SQL "
            "design.",
        ],
    ),
    # 10 design callout -------------------------------------------------------------------------
    dict(
        kind="design_callout",
        title="Your design: which queries wait for a person",
        minutes=2,
        says="Run generated queries from events; hold by the columns they return; start "
        "report-only",
        src="pack.yaml personal_data and autonomy; section-3-event-loop/concepts.md; "
        "section-3-event-loop/demo/README.md; Source 2",
        on_slide=[
            "Decision: what holds a generated query for approval?",
            "| Hold rule | Trade-off |",
            "|---|---|",
            "| Hold every query | Safe; approval risks a reflex click |",
            "| A model judges sensitivity | May flip on resume; a payload can argue |",
            "| Hold queries returning tagged columns | Same every time; tags to maintain |",
            "DataPilot: hold returned tagged columns, Section 2's personal-data tags; approve or "
            "reject only; start at the report-only level[^2].",
        ],
        notes=[
            "Purpose: Turn the event loop into a text-to-SQL design decision: which generated "
            "queries run unattended and which wait for a person.",
            "What to say: When questions arrive as events, nobody reads the generated query "
            "before it runs, so decide in advance which queries wait. Hold every query: safe "
            "on paper, but approval becomes a reflex click, the approval fatigue OpenAI's "
            "governance paper, Source 100, warns about. Let a model judge sensitivity: it can "
            "answer differently when the hold is checked again on resume, and the question "
            "text can argue with it. Hold queries that return tagged columns, the personal-data "
            "tags from Section 2: Verification loop: the same answer every time, at the cost of "
            "the tag list. Returns a tagged column is harder than it sounds: follow aliases, "
            "stars, subqueries and aggregates such as string_agg, and hold anything you cannot "
            "place. Filters are exempt, because no value comes back, but a count filtered on "
            "one email still confirms that a person exists; decide whether that matters for "
            "your data. The person approves or rejects, never edits, because an edited query "
            "skipped the graders. Two more points. Bound the size of what an approved query "
            "returns, the value cap from Section 1: Agent loop. And pin the business date and "
            "its time zone, since an event has no one to ask. That is why every metric family "
            "starts at the report-only level.",
            "The point to land: Decide holds from the columns a query returns, cap what an "
            "approved query returns, and pin the business date.",
            "Example: The California export holds because it returns email; the webhook "
            "question about orders returns no tagged column, so it posts, labelled unverified.",
            'Ask the room: "Which columns in your warehouse would you tag first?" Expect: email, '
            "phone, names, sometimes salary or address.",
            "Misconceptions: That read-only access makes personal data safe. A read-only query "
            "can still export every email; the hold is about where data goes.",
            "Transition: Next, apply it: six checks for your own event-driven agent next week.",
        ],
    ),
    # 11 apply it -------------------------------------------------------------------------------
    dict(
        kind="checklist",
        title="Apply it: six checks for your event loop",
        minutes=1.5,
        says="Six things to do on your own event-driven agent next week",
        src="section-3-event-loop/README.md, Apply it in a real system; "
        "section-3-event-loop/demo/walkthrough.md, If you copy this",
        on_slide=[
            "- Key each effect by a stable event id, or by meaning",
            "- Claim in one short transaction; a heartbeat renews the lease",
            "- Keep pending approvals in a durable checkpointer",
            "- Read the stop before each step; time out every call",
            "- Back off on rate limits; alert on holds and budget blocks",
            "- Force each failure on purpose (send twice, restart, stop mid-run)",
        ],
        notes=[
            "Purpose: Give six concrete actions a learner can take on their own event-driven "
            "agent next week.",
            "What to say: Six checks, each an afternoon or less. One: key every effect, posts, emails, refunds, by the "
            "sender's stable event id or by meaning, under a unique constraint. Two: claim in "
            "one short statement, and renew the lease from a heartbeat. Three: keep every "
            "pause for a person in a durable checkpointer. Four: read the stop before each "
            "step, and set a request timeout on every model and tool call, because a stop "
            "waits for the call in flight; DataPilot sets none of its own. Five: give rate limits and provider errors their "
            "own bounded backoff, never counted as verification retries, and alert on holds, "
            "escalations and budget blocks. Six, the one teams skip: force each failure on "
            "purpose: send one event three times, restart a worker mid-hold, stop a slow run, "
            "and check that exactly one effect happened. Assignment 3: Event loop practises all six on a nightly revenue anomaly alert.",
            "The point to land: Every safeguard you add gets a test that makes its failure "
            "happen on purpose.",
            "Example: In Assignment 3: Event loop, a second delivery of the anomaly alert must "
            "post nothing new, and a late order must update the alert in place.",
            'Ask the room: "Which of the six would take you longest?" Expect: moving approvals '
            "into a durable checkpointer.",
            "Misconceptions: That a message broker removes the need for keys. Brokers deliver at "
            "least once too; the keys and the lease checks still apply.",
            "Transition: Next, the pitfalls: the event-loop mistakes that pass every unit test.",
        ],
    ),
    # 12 pitfalls -------------------------------------------------------------------------------
    dict(
        kind="pitfalls",
        title="Event loop pitfalls that pass every unit test",
        minutes=2,
        says="A key made at arrival, a lock through the model call, an outside effect with no "
        "outbox, no daily budget",
        src="section-3-event-loop/concepts.md; docs/calibration-report.md, The retake chains; "
        "Source 26; lead rulings round 3, ruling 4; deck 2 round 1 rulings 6 and 16, round 2 ruling 3; "
        ".dev/deck-evidence.md E38, E39",
        on_slide=[
            "| Pitfall | What happens | Do instead |",
            "|---|---|---|",
            "| A key per arrival | Every copy looks new and posts | Stable event id, else meaning |",
            "| A lock held during the model call | Dead rows pile up[^26]; the job looks queued "
            "while it runs, and a killed run restarts uncounted | Commit the claim, then "
            "lease |",
            "| An outside effect sent inline | A crash after the send sends it twice | An "
            "outbox, plus the provider's key |",
            "| No daily budget | Unattended runs spend unseen | Check the budget when claiming |",
        ],
        notes=[
            "Purpose: Name four event-loop mistakes that look fine in unit tests and fail in "
            "production, each with its fix.",
            "What to say: Four pitfalls, each one we planted or met. First, a key made at "
            "arrival. A random id per delivery, exactly the planted random digest id, makes "
            "every copy look new; a key from the clock fails too, because a retry a second "
            "later gets a new key. Second, a lock held through the model call. One transaction "
            "around the whole job looks tidy, but Brandur Leach's write-up of Postgres job "
            "queues, Source 26, shows long transactions pile up dead rows and slow every "
            "claim. Killing the worker rolls the claim back: the job is queued again with no "
            "attempt counted and runs again, so an attempt cap never stops it; that lost "
            "attempt count is what our planted bug showed. Third, an effect outside your database sent inline. Our channel is a table "
            "that commits with the run; a chat message, an email or a refund cannot. Write the "
            "intent to an outbox table in the same transaction, and send it with the "
            "provider's own idempotency key, or a crash after the send sends it twice. Fourth, "
            "no daily budget. Ours is 2,000,000 tokens, checked at claim, and on a rehearsal "
            "day it blocked a run at 1,969,486.",
            "The point to land: The event loop's bugs hide until a retry, a restart, or a quiet "
            "weekend triggers them; plant each one and watch it fail.",
            "Example: The lock-through-the-run variant passes every happy-path test, because "
            "nothing is killed mid-run in a happy path.",
            'Ask the room: "Which of these does your system have today?" Expect: no daily '
            "budget, and approvals in memory.",
            "Misconceptions: That a budget per run is enough. Many small runs, each inside its "
            "own budget, still add up when nobody watches.",
            "Transition: Next, the recap: the scoreboard after three loops, and one question "
            "about a support agent.",
        ],
    ),
    # 13 recap with the scoreboard -------------------------------------------------------------
    dict(
        kind="recap",
        title="Recap: the event loop",
        scoreboard=3,
        minutes=2.5,
        says="Three points to keep, the scoreboard after Section 3, and a refund agent question",
        src="section-3-event-loop/README.md; docs/instructor-guide.md, Section 3: Event loop; "
        "Sources 86, 87",
        on_slide=[
            "- One effect per event, keyed in a unique constraint",
            "- A pending approval is state; checkpoint it durably",
            "- Stops reach running work; autonomy is earned",
            "Question: A refund agent runs on ticket webhooks. A refund awaits approval, the "
            "webhook is resent, the worker restarts. What is the key? Where does the wait "
            "live?",
        ],
        notes=[
            "Purpose: Consolidate the event loop, show the scoreboard after Section 3, and check "
            "that learners can apply the patterns to a new agent.",
            "What to say: Three points to keep. One event, one effect, because the key lives in "
            "a unique constraint. A pending approval is state, so it lives in a durable "
            "checkpoint. The stop reaches the running job, and autonomy is earned. Now the "
            "scoreboard: it runs safely unattended, but it is still wrong. Unattended here "
            "means nobody reads each run; the autonomy level is still report-only, which is "
            "why it posts labelled unverified, wrong, until Section 4. The question; thirty "
            "seconds in the chat. The answer: key the refund by the ticket system's event id "
            "if it survives a retry, else by meaning, the ticket, the order and the action, "
            "so the resend hits the unique constraint and creates nothing. The waiting refund "
            "is a checkpoint in the database, so the restart loses nothing and one approval "
            "resumes it. And the refund leaves through an outbox with the payment provider's "
            "own idempotency key, so a retry after a crash cannot refund twice. One refund.",
            "The point to land: The event loop makes runs safe to repeat, wait, and stop; it "
            "does not turn a wrong answer into a right one.",
            "Example: Stripe's interface, Source 86, returns the saved response for a retried "
            "key, the provider-side half of the answer.",
            "Ask the room: the question on the slide. Expect: two refunds, from people who key "
            "by delivery id; zero, from people who expect the restart to lose the approval.",
            "Misconceptions: That idempotency protects correctness. It posts a wrong answer "
            "exactly once.",
            "Transition: Before the break, one poll: which of the four loops does your "
            "production agent have today?",
        ],
    ),
]
