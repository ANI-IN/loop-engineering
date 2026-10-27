"""Section 3: Event loop, 2:05-2:48, 43 minutes, 12 slides, under design system 3.

The reference deck's rhythm: the agenda with the star on the event loop, the failure story
(Wednesday's two digests, in the evidence's true form: the digest fired twice, each delivery got a
random id), the question slide, the four techniques, the design callout, the cheat sheet, the DEMO
slide, the measured slide with the scoreboard, and Ask about anything. Every course number comes
from .dev/deck3-evidence.md (parts 1 and 3), docs/evidence/section-3-event-loop.md and
docs/benefits.md; every external claim from the verified quotes of .dev/deck2-sources.md, whose
forbidden claims this block keeps: keyed by meaning is the course's own rule (a sender's stable
event id comes first), the three levels are DataPilot's and are not mapped onto Feng and others,
the kill switch read at every step is the course's design, and no queue or workflow engine is said
to give exactly-once effects. The approval: the gate's knowledge approval needs a typed person's
name (the owner's decision of 27 October 2026); the console's run approval dialog still records
"console"; production systems take a signed-in identity. The second deck's code slides are in the
technique notes (the generic pattern) and in the DEMO notes (DataPilot's code, from the
walkthrough page). The run of show: the techniques to 2:20:30, the demos from 2:23:30 to 2:43:30
(no retry after 2:40:30), then the measured slide and questions to 2:48, when the poll starts.
"""

RULES = "design system 3"

DEMO_PAGE = "https://github.com/ANI-IN/loop-engineering/tree/main/section-3-event-loop/demo"
EXPECTED = "section-3-event-loop/demo/expected/"
CODE = "platform/src/datapilot/loop3_events/"

SLIDES = [
    # 52 agenda -----------------------------------------------------------------------------------
    dict(
        kind="agenda",
        title="Today's Agenda",
        minutes=0.5,
        says="The four loops, the star on the event loop",
        src="the owner's specification of 27 October 2026, section 1",
        on_slide=[
            "1. Agent loop: what it sees",
            "2. Verification loop: is it right?",
            "3. Event loop: runs unattended",
            "4. Hill-climbing loop: improves safely",
            "Now: 3",
        ],
        notes=[
            "Purpose: Show where the class is after the break: the third of the four loops, "
            "running with nobody watching.",
            "What to say: Welcome back. The star has moved to the third loop: the event loop, "
            "and whether the agent runs unattended. Until now someone pressed Ask and watched "
            "each answer. From here, questions arrive as webhooks and a schedule fires a daily "
            "digest, and nobody reads each run before it posts.",
            "The point to land: The event loop adds no intelligence; it makes runs safe to "
            "repeat, to wait and to stop.",
            "Example: The daily digest fires at 8 a.m. Eastern time whether or not anyone is "
            "at a desk.",
            "Ask the room: none here; the question comes at the end of the section.",
            "Misconceptions: That event-driven agents need a new framework. They need a key, a "
            "lease, durable state and a stop.",
            "Transition: Here is what Wednesday looked like with nobody watching.",
        ],
    ),
    # 53 failure story ----------------------------------------------------------------------------
    dict(
        kind="failure",
        title="Failure story: The digest that posted twice",
        minutes=2.5,
        says="Five steps from a scheduled digest to two different numbers for one day",
        src="the owner's specification of 27 October 2026, section 3, item 2 (Wednesday); "
        ".dev/deck3-evidence.md, Wednesday; section-3-event-loop/concepts.md; "
        "docs/evidence/section-3-event-loop.md, Results and Captures",
        on_slide=[
            "Lead: An illustrative question: what was revenue on the last business day? The daily "
            "digest answers it.",
            "1. At 8 a.m. Eastern time, the daily digest fires.",
            "2. A worker retries, so the same event arrives twice.",
            "3. Each arrival gets a random id, so both look new.",
            "4. Two jobs run; their revenue totals differ.",
            "5. Leadership gets two digests and trusts neither.",
        ],
        notes=[
            "Purpose: Walk the illustrative path from a scheduled digest to two different numbers "
            "for one day, each step causing the next.",
            "What to say: This story is illustrative: it is how Wednesday plays out when the "
            "event handler trusts each arrival. Step one: at 8 a.m. Eastern time the scheduler "
            "fires the daily digest, the morning summary of the previous business day. Nobody pressed "
            "anything; an event did. Step two: a worker retries the delivery. Perhaps an "
            "acknowledgement was lost, perhaps a worker restarted; senders and queues do this "
            "as a matter of course. The same event now arrives twice. Step three: the handler "
            "stamps each arrival with a random id of its own. That looks harmless, even tidy, but "
            "it means the second copy cannot be recognised as a copy. Step four: both copies "
            "become jobs, and each job runs the agent on its own. The model is not "
            "deterministic, so the two runs reach two different totals. Step five, in red: "
            "leadership gets two digests for the same day with two revenue figures, and now "
            "trusts neither. Notice that no step crashed and every check passed. The failure "
            "is in the plumbing around the agent: who decides that an event is new.",
            "The point to land: A repeated event is normal; acting on it twice is the bug, and "
            "nothing about it looks like an error.",
            "Example: This happened in the course's own runs with the planted random digest id "
            "and the missing idempotency switched on: the capture of 25 October 2026 shows two "
            "digests for 30 January 2026, $155,373.53 and $146,555.17, both across 291 orders. "
            "In every one of the 5 planted runs, the same question sent three times was "
            "answered three times and the digest posted twice; run d5817278 is one of them. "
            "Thursday's failures, an approval lost in a worker restart and a run that posted "
            "after someone pressed stop, come back with the third and fourth techniques.",
            'Ask the room: "At which step could your system have stopped this?" Expect: step '
            "three, with a stable key, and some who say step two, by retrying less.",
            "Misconceptions: That fewer retries fix it. Retries are how delivery stays "
            "reliable; the handler must make the second arrival harmless.",
            "Transition: So why not skip the queue and call the agent straight from the webhook?",
        ],
    ),
    # 54 question ---------------------------------------------------------------------------------
    dict(
        kind="question",
        title="Event loop: Why not call the agent from the webhook?",
        minutes=2.5,
        says="The naive design, a direct call per webhook, and why it fails unattended",
        src="the owner's specification of 27 October 2026, section 4, item 3; sources.py "
        "entries 87 and 88; .dev/deck2-sources.md, [87] and [88]",
        on_slide=[
            "Lead: Questions now arrive as webhooks and on a schedule; nobody watches each run.",
            "Key idea: Events arrive at least once; the database decides what is new, who owns "
            "it, what waits.",
            "1. Delivery is at least once, so an event arrives twice; a direct call answers twice[^88]",
            "2. A run takes minutes; if its process dies mid-run, nothing records the work",
            "3. A run that waits for a person, or must stop, needs state that outlives it",
        ],
        notes=[
            "Purpose: Answer the naive design, call the agent straight from the webhook, with "
            "the section's key idea and three reasons.",
            "What to say: Here is the obvious design. A webhook arrives, the handler calls the "
            "agent, and the answer posts. It works in every demo. Why add a queue, keys and "
            "leases? The key idea: events arrive at least once, so the database, not the "
            "handler's memory, must decide three things: what is new, who owns each job, and "
            "what is waiting. Three reasons. One: delivery repeats. Amazon's queue documentation "
            "explains that a copy of a message kept on a server that was unavailable is not "
            "deleted, so the message is delivered again; and it says plainly, design your "
            "applications to be idempotent, Source [^88]. A handler "
            "that calls the agent directly answers every copy. Two: a run is slow. Ours take "
            "seconds to minutes, several model calls each. If the process dies in the middle, "
            "a deploy or a crash, a direct call leaves no record that the work was ever "
            "started, so nothing finishes it. A job row with a lease does. Three: some runs "
            "must wait or stop. A customer export waits for a person's approval, maybe for "
            "hours, and someone must be able to stop a run already going. Both need state that "
            "outlives the process. Stripe's webhook guide gives the same advice from the "
            "payments side: process incoming events with an asynchronous queue, Source [^87].",
            "The point to land: The webhook handler should only record the event; a worker "
            "does the work, and the database keeps the facts.",
            "Example: In DataPilot the webhook handler writes an event row and a job row in one "
            "transaction and returns; a worker claims the job a moment later.",
            'Ask the room: "What does your webhook handler do after it receives an event?" '
            "Expect: it does the work inline, and a few who already queue it.",
            "Misconceptions: That a message broker removes the need for keys. Brokers deliver "
            "at least once too; the keys and the leases still apply.",
            "Transition: The first technique answers reason one: an idempotency key built from "
            "what the event means.",
        ],
    ),
    # 55 technique 1 ------------------------------------------------------------------------------
    dict(
        kind="technique",
        title="1) Idempotency keys by meaning",
        minutes=2.5,
        says="A repeated event finds its key and does nothing new: event id first, else meaning",
        src="docs/diagrams/patterns/README.md (pattern-idempotency-key); sources.py entry 87; "
        ".dev/deck2-sources.md part 4 item 2; section-3-event-loop/concepts.md",
        figure={
            "diagram": "pattern-idempotency-key",
            "alt": "Idempotency keys: a sender that retries delivers the same event twice; the "
            "key is the sender's stable event id, or else the meaning, which order, which "
            "action, which day, never a delivery attempt's id, since a retry may get a new one; "
            "the key goes to a store of keys done with a unique constraint; a new key does the "
            "work once, and a seen key returns the first result",
        },
        on_slide=[
            "- **What:** a key that names the effect, so a repeated event finds its key and "
            "does nothing new.",
            "- **How:** use the sender's stable event id, else a key from meaning: order, action, "
            "day.",
            "- **In code:** insert the key and the job in one transaction; on a conflict, do "
            "nothing.",
            "- **Example:** the scheduled digest's key is its business day, so a second firing is "
            "absorbed.",
            "- **Elsewhere:** payment webhooks log the event ids they processed and skip "
            "repeats.[^87]",
            "Key idea: Key each effect by what the event means, and let a unique constraint "
            "decide.",
        ],
        notes=[
            "Purpose: Teach the first technique: an idempotency key, the sender's stable event "
            "id first, else built from the event's meaning, enforced by a unique constraint.",
            "What to say: Walk the diagram from left to right. A sender that retries delivers "
            "the same event twice. The handler needs a key that is the same both times. The "
            "best key is the sender's own event id, when the sender keeps it across retries. "
            "Without one, build the key from meaning: which order, which action, which day. "
            "Never use an id stamped on each delivery attempt, because a retry may get a new "
            "one; that was exactly Wednesday's bug. The key goes into a store with a unique "
            "constraint. A new key does the work once; a key already there returns the first "
            "result. The code line on the slide does it: the key and its job go in one "
            "transaction, so a repeat adds no job and a crash cannot keep the key and lose the "
            "job; you will see DataPilot's insert in the demo. The scheduled digest's key is "
            "the business day alone, so a second firing on the same day is absorbed; only a "
            "digest asked for on demand adds its own occasion to the key. Stripe's webhook guide, Source [^87], gives the payments version: "
            "log the event ids you processed, and do not process logged events again. Keying "
            "by meaning when no stable id exists is the course's own rule.",
            "The point to land: Assume every event arrives twice; the database's unique "
            "constraint, not the code's memory, decides what is new.",
            "Example: An illustrative coding agent keys a review by repository, pull request "
            "and commit, so a resent webhook opens no second review.",
            'Ask the room: "What would the key be for your busiest event?" Expect: its id; ask '
            "whether that id survives a retry, and if not, what the event means.",
            "Misconceptions: That checking for the key before inserting it is enough. Two "
            "workers can both see no key; only the insert itself is atomic.",
            "Transition: A key stops a repeat from acting twice. Next: what happens when the "
            "worker doing the job dies.",
        ],
    ),
    # 56 technique 2 ------------------------------------------------------------------------------
    dict(
        kind="technique",
        title="2) A job queue with leases",
        minutes=2.5,
        says="A claimed job carries a lease; a dead worker's job returns and may run twice",
        src="docs/diagrams/patterns/README.md (pattern-lease-queue); sources.py entry 27; "
        ".dev/deck2-sources.md, [27]; section-3-event-loop/demo/walkthrough.md",
        figure={
            "diagram": "pattern-lease-queue",
            "alt": "A job queue with leases: in a jobs table each claimed job has a lease end; a "
            "worker claims a job and its lease ends in 5 minutes; the worker crashes; the lease "
            "ends and the job is pending again; another worker claims it; so a job may run "
            "twice, and managed queues call the lease a visibility timeout",
        },
        on_slide=[
            "- **What:** jobs live in a table; a worker claims one with a lease, an end time, "
            "not a lock held open.",
            "- **How:** claim the oldest queued job, skipping rows others hold;[^27] a heartbeat "
            "renews the lease.",
            "- **In code:** commit the claim at once; every later write checks this owner and "
            "attempt.",
            "- **Example:** a worker crashes mid-run; its lease ends, and another worker takes "
            "the job.",
            "- **Elsewhere:** managed queues call it a visibility timeout; a build farm hands lost "
            "machines' tests on.",
            "Key idea: A lease lets ownership expire: a crash returns the job, so it may run "
            "twice.",
        ],
        notes=[
            "Purpose: Teach the second technique: a durable job queue whose claims carry leases, "
            "and the same idea under its managed-queue name.",
            "What to say: A worker takes a job and dies, in a deploy or a crash. Who finishes "
            "it? Walk the diagram. The jobs live in a table, so they survive any process. A "
            "worker claims a job with a lease: an owner and an end time. The worker crashes, "
            "the lease ends, and another worker claims the job. So a job can run twice, which "
            "is why the key comes first. Read the code line: the claim commits at once, "
            "and the heartbeat renews the lease, because one model call can outlast it. Every "
            "later write checks this owner and this attempt, so a worker that lost its lease "
            "cannot overwrite a job another worker now holds. You will see DataPilot's claim "
            "statement in the demo; its lease is 30 seconds, and it counts each attempt, so a "
            "job that keeps killing its worker is marked dead after its maximum attempts. How "
            "does the post happen only once if a job runs twice? In DataPilot the post is a row "
            "in the same database, written in one transaction with the run's status, so a "
            "second run finds the run already posted. A post to an outside system needs an "
            "outbox and that system's own idempotency key. The Prisma write-up of a Postgres queue, Source [^27], calls "
            "SKIP LOCKED half the trick: it claims the row, and a lease column returns it after "
            "a crash. It adds the honest caveat: this queue delivers at least once, not exactly "
            "once, so write handlers that are safe to run twice.",
            "The point to land: A lease turns ownership into a row with an end time; a crash "
            "returns the job, and a possible second run is the price.",
            "Example: An illustrative coding agent gives each long test suite a lease and a "
            "heartbeat, so a lost build machine hands the suite on.",
            'Ask the room: "How long do your slowest agent runs take, and what is your '
            'timeout?" Expect: runs of minutes, and timeouts set long ago for something else.',
            "Misconceptions: That a lock held through the whole run is simpler. It hides the "
            "job's real state, and a killed worker's claim rolls back uncounted.",
            "Transition: Some runs cannot finish without a person. Next: durable approval with a "
            "checkpointer.",
        ],
    ),
    # 57 technique 3 ------------------------------------------------------------------------------
    dict(
        kind="technique",
        title="3) Durable approval with a checkpointer",
        minutes=2.5,
        says="A waiting run is a checkpoint in a database; record who approved what, and resume "
        "only an idempotent step",
        src="docs/diagrams/patterns/README.md (pattern-durable-approval); sources.py entry 99; "
        ".dev/deck2-sources.md, [99]; DECISIONS.md, 27 October 2026, item 2; "
        ".dev/deck3-evidence.md, Thursday",
        figure={
            "diagram": "pattern-durable-approval",
            "alt": "Durable approval: steps run while saving state; a checkpoint is saved in a database,"
            " and the process may exit meanwhile; hours or days later a person approves, and the "
            "approval is recorded: who, and what they approved; the run resumes from the "
            "checkpoint, even after a restart; the failure without it: a restart loses a wait "
            "held in memory",
        },
        on_slide=[
            "- **What:** a run that waits for a person saves a checkpoint in a database; the "
            "process may exit.",
            "- **How:** the run resumes from its checkpoint; the paused step runs again, so make "
            "it idempotent.",
            "- **Who:** record the signed-in approver and exactly what they approved: query and rows.",
            "- **Elsewhere:** a deploy pipeline's manual approval waits for days and records who "
            "approved; agent frameworks keep the same wait in a checkpointer.[^99]",
            "Key idea: A pause is state: keep it where a restart cannot lose it, with who "
            "approved what.",
        ],
        notes=[
            "Purpose: Teach the third technique: a waiting run lives in a durable checkpoint, "
            "the approval records who approved what, and only an idempotent step resumes.",
            "What to say: Thursday's first failure. A California customer export reads personal "
            "data, so it must wait for a person. The worker restarted while it waited, and the "
            "approval was gone: the wait lived in the worker's memory. Walk the diagram. Steps "
            "run, saving state as they go. At the approval the state is a checkpoint in a "
            "database, and the process may exit. Hours or days later a person approves, and the "
            "run resumes from the checkpoint, even after a restart. Two rules make it safe. "
            "First, resuming runs the paused step again, so anything that step did before the "
            "pause must be idempotent. Second, record the approver from a signed-in identity, "
            "and exactly what they approved: the query and its row count, not only yes. A typed "
            "name is only a claim, and an approval nobody owns proves nothing. LangGraph's "
            "persistence guide, Source [^99], lists human-in-the-loop workflows and fault "
            "tolerance among what checkpointers are for; workflow engines keep a waiting run "
            "the same way. Decide what holds from data, never from a model. In DataPilot the "
            "wait is a LangGraph interrupt in the Postgres checkpointer, keyed by the run. "
            "DataPilot is part of the way there: the gate's approval in Section 4 takes a typed "
            "name and refuses an empty name or console, while the run approval you will see in "
            "the demo still records console, a known gap.",
            "The point to land: A pause is state, so store it where state survives, and record "
            "who released it and what they released.",
            "Example: With the in-memory checkpointer planted, the export's approval was lost in "
            "6 of 6 runs and the run failed; with the Postgres checkpointer, 7 of 7 held "
            "and posted after approval.",
            'Ask the room: "Where does a paused run of your agent live today?" Expect: in '
            "memory, or nowhere, because nothing pauses.",
            "Misconceptions: That the approval is a dialog. The dialog is a view; the approval "
            "is a checkpoint and a record of who approved what.",
            "Transition: A run that waits is safe. Next: a run that must stop, and how much the "
            "agent may do alone.",
        ],
    ),
    # 58 technique 4 ------------------------------------------------------------------------------
    dict(
        kind="technique",
        title="4) A kill switch checked every step, and autonomy levels",
        minutes=2.5,
        says="A stop read before every model and tool call; three levels, each earned, any "
        "stop drops to report-only",
        src="docs/diagrams/patterns/README.md (pattern-autonomy-levels); sources.py entry 103; "
        ".dev/deck2-sources.md, [103] and part 4 items 3 and 4; pack.yaml autonomy; "
        "section-3-event-loop/concepts.md, Autonomy levels",
        figure={
            "diagram": "pattern-autonomy-levels",
            "alt": "Autonomy levels: report-only, where the agent reports and people act; "
            "assisted, where it acts and risky actions wait for a person; unattended, where it "
            "acts alone within its limits; each step up is earned, and an incident drops "
            "unattended back to assisted; a kill switch, read before every step, drops any "
            "level to report-only; the evidence to step up is to force each failure on purpose "
            "and show the fix holds",
        },
        on_slide=[
            "- **What:** a switch in the database that every run reads before each model call "
            "and each tool call.",
            "- **How:** time out every call: the timeout is your worst-case time to stop.",
            "- **Levels:** report-only, assisted, unattended; each step up is earned; an "
            "incident drops a level at once (DataPilot: straight to report-only).",
            "- **Elsewhere:** autonomy is a design choice[^103]; a build pipeline checks for "
            "cancel between steps.",
            "Key idea: A stop works only if every step reads it; autonomy is earned, and taken "
            "back at once.",
        ],
        notes=[
            "Purpose: Teach the fourth technique: a kill switch read before every step, and "
            "autonomy granted in levels that are earned and lost.",
            "What to say: Thursday's second failure. Someone pressed stop, and a run already "
            "under way posted anyway, because the switch was read only when a job was claimed. "
            "A stop must reach running work, so every run reads the switch before each model "
            "call and each tool call. A model call already in flight finishes; the check before "
            "the next step ends the run. Time out every call: that timeout is your worst-case "
            "time to stop. Reading the switch at every step is the "
            "course's design. Now walk the diagram, the autonomy levels. At the report-only "
            "level the agent reports and people act. At the assisted level it acts, and risky "
            "actions wait for a person. At the unattended level it acts alone, within its "
            "limits. A level is earned in two ways: forcing each failure on purpose and showing "
            "the fix holds proves the safeguards once; clearing a family's holdout questions "
            "proves the answers family by family, in Section 4. Coming down is fast. The drawing shows a gentler design, an incident "
            "dropping unattended to assisted; DataPilot is stricter: a holdout regression, an "
            "exhausted daily budget, three escalations in a row or the kill switch drop the "
            "level straight to report-only. These three levels are DataPilot's. Feng, McDonald and Zhang, Source [^103], define five levels by the role a "
            "user takes, and argue that autonomy is a deliberate design decision, separate "
            "from what the model can do. In DataPilot the report-only level posts answers "
            "labelled unverified, and an export still runs and posts after approval, with its "
            "rows withheld.",
            "The point to land: Read the stop before every step, grant autonomy one earned step "
            "at a time, and take it back at once.",
            "Example: With the switch read at claim only, a run posted after the stop in 6 of 6 "
            "planted runs; read before every step, it stopped in flight in 9 of 9.",
            'Ask the room: "What would your agent need to show before it acts alone?" Expect: '
            "good test scores; push for forced failures, not only happy paths.",
            "Misconceptions: That a stop undoes what already ran. It prevents the next step; "
            "posts and messages already sent stay sent.",
            "Transition: Those are the four techniques. What do they change in a text-to-SQL "
            "design?",
        ],
    ),
    # 59 design callout ---------------------------------------------------------------------------
    dict(
        kind="design_callout",
        title="Text-to-SQL design: Which queries wait for a person",
        minutes=1.5,
        says="Run generated queries from events; hold by the columns they return; start "
        "report-only",
        src="pack.yaml personal_data and autonomy; section-3-event-loop/concepts.md; "
        "section-3-event-loop/demo/README.md",
        on_slide=[
            "Lead: Nobody reads a query run from an event, so decide which wait.",
            "Decision: what holds a generated query for approval?",
            "| Hold rule | Trade-off |",
            "|---|---|",
            "| Every query | Safe; approvals become reflex clicks |",
            "| A model judges | May flip on resume; a question can argue |",
            "| Tagged columns returned | Same every time; tags to maintain |",
            "Hard part: trace columns through aliases, stars and aggregates; hold what you cannot "
            "place.",
            "DataPilot: holds returned tagged columns; approve or reject; starts report-only.",
        ],
        notes=[
            "Purpose: Turn the event loop into a text-to-SQL design decision: which generated "
            "queries run unattended and which wait for a person.",
            "What to say: When questions arrive as events, nobody reads the generated query "
            "before it runs, so decide in advance which queries wait. Three rules, read by row. "
            "Hold every query: safe on paper, but a person who approves fifty queries a day "
            "reads none of them. Let a model judge: it can answer differently when the hold is "
            "checked again on resume, and the question text can argue with it. Hold queries "
            "that return tagged columns, the personal data tags from Section 2: Verification "
            "loop: the same answer every time, at the cost of the tag list. The hard part, under "
            "the table: trace each returned column through aliases, stars and aggregates, and "
            "hold what you cannot place. The person approves or rejects, never edits, because "
            "an edited query skipped the graders. Cap what an approved query returns, and pin "
            "the business date and its time zone, since an event has nobody to ask.",
            "The point to land: Decide holds from the columns a query returns, cap what an "
            "approved query returns, and pin the business date.",
            "Example: The California export holds because it returns email; the webhook "
            "question about orders returns no tagged column, so it posts, labelled unverified.",
            'Ask the room: "Which columns in your warehouse would you tag first?" Expect: email, '
            "phone, names, sometimes salary or address.",
            "Misconceptions: That read-only access makes personal data safe. A read-only query "
            "can still export every email; the hold is about where data goes.",
            "Transition: Next, the four techniques on one page, to take with you.",
        ],
    ),
    # 60 cheat sheet ------------------------------------------------------------------------------
    dict(
        kind="table",
        title="Cheat Sheet: The event loop",
        minutes=1.5,
        says="The four techniques: what each does, and how to apply it in your own system",
        src="section-3-event-loop/README.md, Apply it in a real system; "
        "section-3-event-loop/demo/walkthrough.md, If you copy this",
        on_slide=[
            "Lead: Four techniques for any agent that runs from events.",
            "| Technique | What it does | How to apply it in your system |",
            "|---|---|---|",
            "| Idempotency keys by meaning | One effect per event, however often it arrives | "
            "Key by the sender's event id, else meaning, under a unique constraint |",
            "| A job queue with leases | A crashed worker's job returns to the queue | Claim in "
            "one short statement; a heartbeat renews the lease |",
            "| Durable approval | A wait for a person survives restarts | Checkpoint in a "
            "database; record who approved what, from their login |",
            "| Kill switch and levels | Stops reach running "
            "work; autonomy is earned | Read the switch before each call; time out every call; "
            "start at report-only |",
        ],
        notes=[
            "Purpose: Give the four techniques as one table a learner can apply to their own "
            "event-driven agent next week.",
            "What to say: One row per technique, read across. Idempotency keys: one effect per "
            "event, however often it arrives; key every post, email or refund by the sender's stable event id or by "
            "meaning, under a unique constraint. A job queue with leases: a crashed worker's "
            "job comes back; claim in one short statement, commit at once, and renew the lease "
            "from a heartbeat rather than holding a lock. "
            "Durable approval: a wait for a person survives restarts; keep every pause in a "
            "database checkpoint and record the signed-in approver and what they approved. The "
            "kill switch and autonomy levels: read the switch before each step, time out every "
            "model and tool call, and start every new capability at the report-only level. Then "
            "do the check teams skip: force each failure on purpose, and check that exactly "
            "one effect happened. The full list is in the section's README, under Apply it in a "
            "real system.",
            "The point to land: Every safeguard you add gets a test that makes its failure "
            "happen on purpose.",
            "Example: In Assignment 3: Event loop, a second delivery of the nightly revenue "
            "anomaly alert must post nothing new, and a late order must update the alert in "
            "place.",
            'Ask the room: "Which row would take you longest?" Expect: moving approvals into a '
            "durable checkpointer.",
            "Misconceptions: That a safeguard tested on the happy path works. It is proven only "
            "once its failure was forced and it held.",
            "Transition: Now let us watch each safeguard fail with its bug on, and hold with "
            "the fix, live.",
        ],
    ),
    # 61 demo -------------------------------------------------------------------------------------
    dict(
        kind="demo",
        title="Section 3: Event loop - Implementation Notes: Repeat, restart, stop",
        minutes=20,
        says="The event-loop demos, live; each safeguard fails with its bug on and holds with "
        "the fix",
        src="platform/demos/registry.yaml (section event-loop); section-3-event-loop/demo/"
        "README.md and walkthrough.md; docs/instructor-guide.md, Section 3: Event loop; "
        "docs/evidence/section-3-event-loop.md; .dev/deck3-evidence.md part 3",
        on_slide=[
            "Badge: DEMO - 3",
            "What to watch for:",
            "- **Webhook:** one strip, Queued to Done",
            "- **Restart:** the held export survives",
            "- **Duplicates:** three sent, one answer",
            "Guaranteed moment: the kill switch stops the run in flight and drops the level to "
            "report-only.",
            "Link: Demo page on GitHub | " + DEMO_PAGE,
        ],
        notes=[
            "Purpose: Run the event-loop demos live, both halves where a planted bug exists, so "
            "each safeguard is seen failing and then holding.",
            "Do: Before class, from the guide's pre-class list: check that demo controls are "
            "on; Restart worker in the approval demo needs them, and they cannot be turned on "
            "in class.",
            "Do: Run sheet. 2:23:30: the webhook question, one strip to Done.",
            "Do: 2:26:30: the approval, the planted half, then the fixed half with Restart worker.",
            "Do: 2:32:30: duplicate events, the planted half, then three sends and one answer.",
            "Do: 2:36:30: the kill switch, the planted half, then the fixed half, a reset after "
            "each.",
            "Do: 2:40:30: start no retry after this; 2:42:30-2:43:30, the reserve, absorbs a "
            "retry already running, otherwise questions.",
            "What to say: Let's watch the event loop run with nobody pressing Ask. Everything you see is live, against the same model as in the earlier "
            "sections, and every strip carries its start time and its trace link. Three of "
            "these demos run twice: first with one line of code switched to the broken version, "
            "then with the fix. The model is the same in both halves; only that line differs. "
            "Each strip on the run board is one run moving from Queued to Done; Failed and "
            "Blocked by kill switch are where the planted halves end up. The channel at the "
            "bottom is what a finance team would read. When a run is waiting, predict in the "
            "chat what happens next.",
            "Demo: The webhook question.",
            "Command: 2:23:30 to 2:26:30. make demo NAME=events-webhook-question, or Events > "
            "Send webhook question in the console.",
            "Point at: the strip moving from Queued to Running, Verifying and Done; the channel "
            "post labelled unverified, the report-only level; the live stamp.",
            "Expected output: one strip from Queued to Done and one post labelled unverified, in "
            "12 to 46 seconds in the recorded runs; the count is 300 orders or 291.",
            "While it runs: say that nobody pressed Ask: a webhook became an event row and a job "
            "row. If it says 291: the right number is 300; the business counts Eastern time "
            "days, and counting by the stored Coordinated Universal Time clock starts the day "
            "five hours early. The reviewer shares the analyst's knowledge, so it approves "
            "both; Section 4 learns the rule. Do not reset for a better number. Open "
            + CODE
            + "api/events.py lines 35-44, the insert that does nothing on a conflict, the first "
            "technique; then " + CODE + "worker.py lines 70-81, the claim with SKIP LOCKED, an "
            "attempt counted and a 30-second lease, the second technique.",
            "If it fails: for every demo here, make reset NAME=event-loop (about 7 seconds), then "
            "the same trigger again; a missing trace link is not a failure. A retry spends the "
            "reserve at 2:42:30; start none after 2:40:30. Past that, skip it, say so, and name "
            "that demo for the Thursday review.",
            "Backup screenshot: " + EXPECTED + "events-webhook-question-board.png; point at it "
            "only while you reset, never instead of the run.",
            "Demo: The approval that survives a restart.",
            "Command: 2:26:30 to 2:32:30. Planted half first, 41 seconds both times measured: "
            "make demo NAME=events-approval-survives-restart PLANTED=1 (the in-memory "
            "checkpointer). At Holding for approval press Restart worker, then Approve: the run "
            "fails. Wait for the line Restarting worker without the demo's flags, then make "
            "reset NAME=event-loop and the fixed half: make demo "
            "NAME=events-approval-survives-restart, or Events > Request California export; at "
            "Holding for approval press Restart worker, wait for the worker, then approve in "
            "the dialog (50 to 84 seconds in all).",
            "Point at: planted half, the line that the pending approval was lost and the run in "
            "Failed (words about the trace only mean that day's tracing quota was used up); "
            "fixed half, the dialog's exact query and row count, the strip held across the "
            "restart, and Done after Approve. Say once: this run approval records console, a "
            "known gap; the gate's approval in Section 4 takes a typed name, and production "
            "systems take a signed-in identity.",
            "Expected output: the strip stays in Holding for approval across the restart, then "
            "moves to Done; the planted half fails with the pending approval lost.",
            "While it runs: say that a worker restart is the deploy or crash of a normal "
            "Tuesday. Open " + CODE + "approvals.py lines 44-47: the planted line yields the "
            "in-memory saver; the fix is LangGraph's Postgres saver, keyed by the run.",
            "If it fails: the reset rule above. If Restart worker does nothing, demo controls "
            "are off and cannot be turned on in class: say so, show the backup screenshot, and "
            "name this demo for the Thursday review. If Restarting worker without the demo's flags has not "
            "appeared a minute after Approve, press Ctrl+C in the demo terminal, then reset.",
            "Backup screenshot: " + EXPECTED + "events-approval-after-restart.png; for the "
            "planted half, " + EXPECTED + "events-approval-lost-after-restart.png.",
            "Demo: Duplicate events.",
            "Command: 2:32:30 to 2:36:30. make demo NAME=events-duplicate-events PLANTED=1 (the "
            "missing idempotency and the random digest id); then make reset NAME=event-loop and "
            "make demo NAME=events-duplicate-events, or Events > Send the same event three "
            "times.",
            "Point at: with the bugs on, the repeated answers and the two digests; with them "
            "off, one post and 2 duplicates absorbed on the strip; the live stamp.",
            "Expected output: one answer posted, two duplicates absorbed, and one digest, in 35 "
            "to 78 seconds; the planted half posts 3 answers and 2 digests.",
            "While it runs: ask the room to predict the count first; the key decides, not the "
            "order. Open " + CODE + "scheduler.py lines 28-31: the scheduled digest's id is "
            "digest and the business day alone, so a second firing is absorbed; an on-demand "
            "digest adds its own occasion; the planted line returns a random id, Wednesday's "
            "story. Ahead by 3 minutes or more? Run The digest now here.",
            "If it fails: the reset rule above.",
            "Backup screenshot: " + EXPECTED + "events-duplicate-events-board.png; for the "
            "planted half, " + EXPECTED + "events-duplicate-events-no-idempotency-channel.png, "
            "the two digests.",
            "Demo: The kill switch in flight.",
            "Command: 2:36:30 to 2:42:30, from the terminal (the console's button sends no demo "
            "pacing): make demo NAME=events-kill-switch-in-flight PLANTED=1 (checked at claim "
            "only), make reset NAME=event-loop, make demo NAME=events-kill-switch-in-flight, make "
            "reset NAME=event-loop again.",
            "Point at: with the bug on, the strip still moving after the switch, and the post; "
            "with it off, Blocked by kill switch and the status line at the report-only level.",
            "Expected output: the in-flight strip moves to Blocked by kill switch and the status "
            "line shows the report-only level, in 3 to 33 seconds; the planted half posts after "
            "the switch.",
            "While it runs: open " + CODE + "killswitch.py lines 89-95: the check runs before "
            "every model and tool call; the planted line returns at once, so the switch is read "
            "only at claim. A model call in flight finishes; no new one starts. DataPilot sets "
            "no request timeout of its own; in yours, the timeout is your worst-case stop.",
            "If it fails: the reset rule above; a run that finished before the switch was sent "
            "without pacing, so use the make command.",
            "Backup screenshot: " + EXPECTED + "events-kill-switch-in-flight-board.png.",
            "Demo: The digest now.",
            "Command: optional, cut first: only when 3 minutes ahead, right after Duplicate "
            "events. make demo NAME=events-digest-now, or Events > Run digest now.",
            "Point at: the one digest post with the previous business day's key figures.",
            "Expected output: one digest post; no time is measured, and the registry gives it 3 "
            "minutes.",
            "While it runs: say that the 8 a.m. Eastern time schedule fires the same job, keyed "
            "by the business day.",
            "If it fails: reset and cut it; the duplicates demo already showed one digest.",
            "Backup screenshot: none is captured; describe the single post, or move on.",
            "The point to land: Each safeguard failed live with its bug on and held with the "
            "fix; that pair is the evidence.",
            "Example: The scheduled digest is keyed by its business day alone, so the planted "
            "random digest id is what let a second digest through.",
            'Ask the room: "Which of the four would have hurt your team most last quarter?" '
            "Expect: duplicates from retries.",
            "Misconceptions: That the planted half is a staged failure. The model runs for real "
            "in both halves; only one line of code differs.",
            "Transition: Those were single runs. Next, every recorded run of each half, with its "
            "sample size.",
        ],
    ),
    # 62 measured ---------------------------------------------------------------------------------
    dict(
        kind="evidence",
        title="Measured: With and without the event loop's safeguards",
        scoreboard=3,
        minutes=2,
        says="The planted bugs failed in all 17 of their runs; the fixes held in 23 of 23",
        src="docs/evidence/section-3-event-loop.md, Results; docs/benefits.md, Section 3; "
        ".dev/deck3-evidence.md part 3, Section 3",
        chart={
            "type": "column",
            "title": "Failed with the bug, held with the fix",
            "categories": ["Sent 3 times", "Restart, held", "Stopped mid-run"],
            "series": [
                ("Bug on, runs that failed", [5, 6, 6]),
                ("Fix on, runs that held", [7, 7, 9]),
            ],
            "x_label": "Failure forced on purpose",
            "y_label": "Runs",
            "maximum": 10,
        },
        on_slide=[
            "Lead: A safeguard in code should hold every time; prove it by forcing its failure.",
            "Sample: every recorded run, 17 with the bugs on, 23 with the fix, gpt-6-luna",
            "- **Bug on:** the failure in 17 of 17 runs",
            "- **Fix on:** it held in 23 of 23 runs",
        ],
        notes=[
            "Purpose: Show every recorded run of the three safeguards, off and on, with the "
            "sample size stated plainly, and where the fiscal year question stands.",
            "What to say: You just saw one run of each half; this is every recorded run behind "
            "them, from the section's evidence page, 23 to 25 October 2026. Each pair of bars is "
            "one forced failure: the left bar counts runs that failed with the bug on, the "
            "right bar runs that held with the fix. Sent three times: with no key, 3 answers and "
            "2 digests in all 5 runs; with the key, 1 answer and 2 duplicates absorbed in all 7. "
            "A worker restart while an export was held: in memory the approval was lost in all "
            "6; in Postgres it was held and then posted in all 7. Stopped in a run: checked at "
            "claim only, a post after the stop in all 6; checked before every step, stopped in "
            "flight in all 9. The sample line says how much to trust it: every time we tried, "
            "not rates. The counts are all or nothing because this is deterministic code around "
            "the model. The event loop adds no model calls; what it saved here was 2 duplicate "
            "question runs and 1 duplicate digest per triple send. Now the scoreboard: it runs "
            "safely unattended, but it is still wrong. Unattended means nobody reads each run; "
            "the level is still report-only, so the fiscal year 2025 answer would post labelled "
            "unverified, and wrong, until Section 4.",
            "The point to land: A deterministic safeguard should hold every time; prove it by "
            "making its failure happen on purpose and watching it.",
            "Example: The single runs of 24 October 2026: d5817278 and ef8db308 for the triple "
            "send, 88a0227a and 43ec464c for the restart, 47ad546f and 2c986f56 for the kill "
            "switch; the 9 kill switch runs include the slowed-down demo run.",
            'Ask the room: "Which of your safeguards have you ever seen fail on purpose?" '
            "Expect: few or none; most are tested only on the happy path.",
            "Misconceptions: That 7 of 7 means it works 100 times in 100. It held in every "
            "recorded run; the guarantee comes from the design, and the count shows it was "
            "tested.",
            "Transition: Questions on the event loop before the poll.",
        ],
    ),
    # 63 Ask about anything (copied) --------------------------------------------------------------
    dict(
        kind="qa",
        title="Ask about anything",
        minutes=2.5,
        says="Questions about the event loop, and one question about a refund agent",
        src="the reference deck, slide 31",
        on_slide=[
            "No Question Is Too Small Every Question Deserves an Answer!!",
            "Ask about anything:",
            "Concepts from today's sections",
            "How this applies to your work",
            "Implementation details",
            "Clarifications on what we covered",
            "Quick Request",
            "Please do not mind if a question gets skipped accidentally",
            "Repost politely in chat if needed",
            "We will try our best to cover as many questions as possible",
            "**Remember:** If you're wondering about it, others probably are too.",
        ],
        notes=[
            "Purpose: Take questions on the event loop, and check that learners can apply it to a "
            "new agent.",
            "What to say: Before the chat's questions, ask this, 30 seconds: a "
            "refund agent runs on ticket webhooks; a refund awaits approval, the webhook is "
            "resent, and the worker restarts. What is the key, and where does the wait live? "
            "The answer: key by the ticket system's event id if it survives a retry, else by "
            "the ticket, the order and the action; keep the wait in a database checkpoint; "
            "send the refund through an outbox with the payment provider's own key. One refund.",
            "Do: Give the chat thirty seconds before you read the answer, then take questions.",
            "Do: Check that the status line's button reads Kill switch, not Release kill switch; "
            "if not, run the event loop's reset from the DEMO slide's notes.",
            "Transition: Next, a short poll, then a break.",
        ],
    ),
]
