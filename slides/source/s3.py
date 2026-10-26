"""Section 3: Event loop, 1:55-2:50, 55 minutes, 13 slides, under the design system.

Every course number comes from the calibration report, the paired measurements page, and the
evidence page of this section; every source marker uses the deck's numbered sources list. The
run of show inside the block: concepts and code to 2:14, the five demos and a 2-minute reserve
from 2:14 to 2:38, then evidence, design, apply, pitfalls, and the recap to 2:50, when the poll
starts.
"""

RULES = "design system"

DEMO_PAGE = "https://github.com/ANI-IN/loop-engineering/tree/main/section-3-event-loop/demo"
EXPECTED = "section-3-event-loop/demo/expected/"

SLIDES = [
    # 1 section opener --------------------------------------------------------------------------
    dict(
        kind="opener",
        title="Section 3: Event loop",
        minutes=1,
        says="The event loop fixes work that runs twice, waits in memory, or ignores a stop",
        src="section-3-event-loop/README.md",
        on_slide=[
            "Fixes: answers posted twice, approvals lost in a restart, and a stop that misses "
            "the running job",
            "Insight: Every safeguard around the model is a row in Postgres; kept in memory, the "
            "approval was lost in 6 of 6 restarts.",
        ],
        notes=[
            "Purpose: Open Section 3 and name the failures it fixes once nobody watches each run.",
            "What to say: Welcome back. Until now someone pressed a button and watched every "
            "answer. At work, questions arrive as webhooks, the digest fires on a schedule, an "
            "export waits for a person, and nobody reads each answer before it posts. That is "
            "the event loop. The agent does not change: same analyst, graders and reviewer, no "
            "new agent. What changes is how work arrives, waits for a person, and stops.",
            "The point to land: The event loop adds no intelligence; it adds the plumbing that "
            "makes unattended runs safe.",
            "Example: The morning digest posts at 8 a.m. Eastern time, whether or not anyone is "
            "awake.",
            'Ask the room: "Which of your agents runs from a schedule or a webhook today?" '
            "Expect: report bots, ticket triage, a few say none yet.",
            "Misconceptions: That event-driven agents need a new framework. They need a queue, "
            "keys, durable state, and a stop, which you already know how to build.",
            "Transition: First, what the measured failures had in common.",
        ],
    ),
    # 2 insight: the opening insight ------------------------------------------------------------
    dict(
        kind="insight",
        title="Every planted bug failed every run",
        minutes=3,
        says="A one-line bug breaks every time its trigger happens: 17 of 17 planted runs failed",
        src="docs/evidence/section-3-event-loop.md, Results; docs/benefits.md, Section 3; "
        "section-3-event-loop/demo/expected/events-approval-lost-after-restart.png "
        "(run 712fce2f)",
        image={
            "path": EXPECTED + "events-approval-lost-after-restart.png",
            "alt": "The California export's card in the Failed lane, with the in-memory "
            "checkpointer planted: the pending approval was lost, started 14:56:54, run 712fce2f",
            "crop": (0.24, 0.38, 0.585, 0.455),
            "callouts": [(0.29, 0.17, 1)],
        },
        on_slide=[
            "Insight: A one-line bug breaks every time its trigger happens; no evaluation of the "
            "model will see it.",
            "Evidence: Forced live: 17 of 17 planted runs failed while the model answered "
            "normally.",
            "1. Failed: the pending approval was lost",
        ],
        notes=[
            "Purpose: Land the section's opening insight: around the model, one-line bugs in "
            "delivery, state, and control fail every time, and no model evaluation sees them.",
            "What to say: This card is from a live run on 25 October. The California export "
            "returned customer emails, so it held for approval. Then the worker restarted, and a "
            "person approved. Marker one: the Failed lane. The run sits there, not in Holding "
            "for approval, and its card starts the pending approval was lost. The words about "
            "the trace on the card only say the build had used up its tracing quota that day; "
            "they are not part of the failure. In that run the pause lived in the worker's memory, so the restart "
            "erased it, and the approval found nothing to resume. Now the insight behind it. In "
            "this section we planted three bugs, each one line of ordinary code, and forced "
            "each trigger live: a resent event, a restart during a hold, a stop during a run. With the event key missing, one event sent three times posted 3 answers "
            "and 2 digests, in all 5 planted runs. With the approval kept in memory, a worker "
            "restart lost it, in all 6. With the kill switch checked only at claim, the running "
            "job posted after the switch, in all 6. That is 17 of 17, while the model answered "
            "normally. Be careful what that proves. In production these bugs do not fire every "
            "run: a duplicate needs a sender to retry, a lost approval needs a restart during "
            "a hold. That is exactly why they hide. They pass every unit test that never "
            "forces the trigger, and no evaluation of the model can see them. The model still "
            "makes its own mistakes in this section, and you may see one in the demo; those are "
            "the other loops' job.",
            "The point to land: A one-line bug around the model breaks every time its trigger "
            "happens, so force the trigger; no evaluation of the model will see it.",
            "Example: The run on screen used the same analyst as Section 1: Agent loop; only the "
            "place where the pause was saved changed.",
            'Ask the room: "Where does a paused run of your agent live today?" Expect: in '
            "memory, or nowhere because nothing pauses.",
            "Misconceptions: That a better model makes unattended runs safe. The model never saw "
            "the duplicate, the restart, or the switch.",
            "Transition: Here is the failure that teams meet first, from a real run.",
        ],
    ),
    # 3 problem story ---------------------------------------------------------------------------
    dict(
        kind="story",
        title="Delivered again, posted again: two digests for one day",
        minutes=2.5,
        says="Without a stored event key, repeats became two digests and repeated answers",
        src="section-3-event-loop/demo/expected/events-duplicate-events-no-idempotency-"
        "channel.png (25 October 2026, runs on docs/evidence/section-3-event-loop.md)",
        image={
            "path": EXPECTED + "events-duplicate-events-no-idempotency-channel.png",
            "alt": "The Channel with the missing idempotency planted: two digests for 30 January "
            "2026, both posted at the report-only level, unverified, with different net revenue "
            "and average order value",
            "crop": (0.075, 0.3129, 0.171, 0.4),
            "callouts": [(0.905, 0.272, 1), (0.905, 0.898, 2)],
        },
        on_slide=[
            '"The same event, delivered more than once, with no key stored"',
            "1. The digest for 30 January",
            "2. A second digest, other figures",
            "Footer: Delivery is at least once, not exactly once[^27]; no key: 3 answers, 2 "
            "digests in 5 of 5 planted runs",
        ],
        notes=[
            "Purpose: Show, from a real run, how a repeated delivery becomes repeated and "
            "contradictory posts when nothing stores the event's key.",
            "What to say: This is the Channel from a live run on 25 October, with the event key "
            "switched off on purpose. Read it top to bottom. Marker one: the digest for 30 "
            "January, posted at the report-only level. Marker two: a second digest for the same "
            "day, with different figures, because the digest ran twice and the model wrote its "
            "query twice. Now picture the finance channel at 8 a.m.: two numbers for one day, "
            "and nobody knows which to trust, so they trust neither. Further down the same "
            "channel, out of this crop, the webhook question is answered again, once per "
            "delivery. Nothing here crashed. Every "
            "post went through the analyst, the graders, and the reviewer. The defect is one "
            "missing line: the event's identity was never stored, so each copy looked new. Why "
            "do copies arrive at all? Because most webhook senders, schedulers, and queues "
            "deliver at least once. The Prisma article, Source 27, says of its own Postgres "
            "queue that no recovery scheme escapes at-least-once delivery, so write handlers "
            "that are safe to run twice. Across the planted runs, one event sent three times "
            "gave 3 answers and 2 digests in 5 of 5.",
            "The point to land: You cannot stop an event arriving twice; you can stop it taking "
            "effect twice.",
            "Example: A sender retries a webhook after a timeout, though the first delivery had "
            "already been taken in; that second copy is the one the key absorbs.",
            'Ask the room: "Which of your webhooks or schedules could fire twice?" Expect: all '
            "of them, once someone thinks about retries.",
            "Misconceptions: That exactly-once delivery is a setting you can turn on. It is not "
            "on offer; exactly-once effects are what you build.",
            "Transition: So where do the key, the queue, the approval, and the stop sit? Here is "
            "the whole pipeline.",
        ],
    ),
    # 4 concept: the event pipeline -------------------------------------------------------------
    dict(
        kind="concept",
        title="The event pipeline, from router to kill switch",
        minutes=3,
        says="Events are inserted once, routed by a table, claimed with a lease, held, and stopped",
        src="section-3-event-loop/diagrams/event-loop.png (section-3-event-loop/diagrams/"
        "event-loop.excalidraw); section-3-event-loop/concepts.md",
        figure={
            "diagram": "event-loop",
            "alt": "The event pipeline: a webhook, the scheduler, or the console sends an event, "
            "inserted once per event id; a fixed router, with no agent, picks the queue in the "
            "jobs table; the worker claims a job with a lease and a heartbeat, the reaper "
            "requeues an expired lease, and the daily budget is checked at claim; the autonomy "
            "policy posts at once or holds the run as a parked job with a checkpoint until a "
            "person approves; the kill switch is checked at claim, before every model call, and "
            "before every tool call",
        },
        on_slide=[],
        notes=[
            "Purpose: Give the mental model of the whole event loop in one picture before any "
            "code.",
            "What to say: The idea on this slide: an event fires and the agent runs, in Source "
            "1's words; here, every safeguard around it is a row in Postgres, not memory. "
            "Walk the diagram with me, top left first. An event arrives from a "
            "webhook, the scheduler, or the console. Box two: it is inserted once per event id; "
            "a repeated id inserts nothing. Box three: the router, a fixed table from event type "
            "to handler and queue. Notice the dashed oval under it: no agent. We have three event "
            "types, a question, an export, and a digest, so routing is a lookup you can unit test "
            "and audit, and no payload can talk a table into a different route. Box four: the "
            "jobs table is the queue. Box five: a worker claims one job with a lease and keeps it "
            "alive with a heartbeat. Under the queue, the reaper puts a job back when its lease "
            "runs out, and under the worker the daily token budget is checked at claim. Now down "
            "the right edge to the bottom row, read right to left. The autonomy policy decides: "
            "post at once, or hold. A held run becomes a parked job with a checkpoint, which "
            "survives a restart, and waits at the diamond for a person to approve. Then it posts "
            "to the channel. Last, the grey box on the left: the kill switch, checked at claim, "
            "before every model call, and before every tool call. Every safeguard is a row in "
            "the database, so a crash or a deploy loses nothing.",
            "The point to land: Put every piece of event-loop state in the database: the key, "
            "the lease, the pending approval, and the switch.",
            "Example: In Section 4 this same pipeline carries the fiscal year 2025 revenue "
            "question: it arrives as a webhook, and the autonomy policy decides whether it posts "
            "at once or waits.",
            'Ask the room: "Which box would you be tempted to turn into an agent?" Expect: the '
            "router; answer that a closed set of types is a lookup.",
            "Misconceptions: That a supervisor agent should route events. It adds a model call, "
            "a bill, and an injection target to a decision a table makes the same way every "
            "time.",
            "Transition: Now the code, starting where an event comes in.",
        ],
    ),
    # 5 mechanism: insert once, route, claim with a lease ---------------------------------------
    dict(
        kind="mechanism",
        title="Insert once, route by table, claim with a lease",
        minutes=3,
        says="The insert absorbs a repeated id; a table routes; one statement claims a job",
        src="platform/src/datapilot/loop3_events/api/events.py lines 37-44; "
        "platform/src/datapilot/loop3_events/worker.py lines 70-81",
        code={
            "language": "python",
            "origin": "platform/src/datapilot/loop3_events/api/events.py lines 37-40 (the line "
            "inserted = conn.execute( left out at the first ..., the placeholders and arguments "
            "of the insert shortened to ...; lines 41-44, which record a duplicate, are in the "
            "notes), then the claim statement of platform/src/datapilot/loop3_events/worker.py "
            "lines 70-81, rewrapped, with lease_owner, updated_at, the queue filter, and the "
            "returned columns left out",
            "lines": [
                "route = router.route(type, payload)",
                "...",
                '    "INSERT INTO ops.events (event_id, source, type, payload) VALUES (...) "',
                '    "ON CONFLICT (event_id) DO NOTHING RETURNING event_id", ...).fetchone()',
                "...",
                "UPDATE ops.jobs SET status = 'running', attempts = attempts + 1, ...",
                "    lease_until = now() + make_interval(secs => %(lease)s), ...",
                "WHERE job_id = (SELECT job_id FROM ops.jobs WHERE status = 'queued' ...",
                "    ORDER BY run_after, job_id FOR UPDATE SKIP LOCKED LIMIT 1)",
            ],
            "marks": [
                (0, "router.route(type, payload)", 1),
                (3, "ON CONFLICT (event_id) DO NOTHING", 2),
                (6, "lease_until", 3),
                (8, "FOR UPDATE SKIP LOCKED", 4),
            ],
        },
        on_slide=[
            "Idea: the database decides what is new, and who owns each job",
            "1. A fixed table picks the handler",
            "2. A repeated id inserts nothing[^29]",
            "3. A 30-second lease, no held lock",
            "4. Skip rows other workers hold[^28]",
        ],
        notes=[
            "Purpose: Show the real code that makes an event take effect once and lets workers "
            "claim jobs without colliding.",
            "What to say: Two pieces of code, the way an event travels. Marker one: the router. "
            "One line, a lookup in a fixed table of three event types; there is no model call "
            "in the event loop's own code. Marker two: the insert. The event id goes in under a "
            "unique constraint, and a repeated id hits the conflict and inserts nothing. The "
            "database decides, not the code, so two workers or two web processes cannot both "
            "think an event is new. The repeat is recorded as a duplicate, which is the count "
            "you will see on the run board. Where does the id come from? From the event's "
            "meaning: the sender's id for a webhook, the job name and the business date for the "
            "digest, never the arrival time and never a random value. Amazon's Builders' "
            "Library, Source 29, prefers exactly this: a caller-provided request id in the "
            "contract. The second piece is the claim, one statement. Marker three: the lease. "
            "The claim commits at once and the lease, 30 seconds, says who owns the job; a "
            "heartbeat every 10 seconds extends it while the model works. The finish and the "
            "heartbeat match only the lease owner and the attempt number, so a frozen worker "
            "cannot overwrite a job someone else re-claimed. Marker four: skip locked rows, so "
            "many workers claim at once without waiting on each other; the Postgres "
            "documentation, Source 28, describes it for queue-like tables.",
            "The point to land: Key every effect by what the event means, and let a unique "
            "constraint, not application code, decide what is new.",
            "Example: The digest's key is the word digest plus the business day, so firing it "
            "twice for 30 January is one digest.",
            'Ask the room: only if ahead of the clock: "What key would you give the email an '
            "agent sends when a ticket "
            'closes?" Expect: the ticket id plus the email type, not a timestamp.',
            "Misconceptions: That skip locked gives exactly-once processing. It gives exclusive "
            "claims; a crash after the effect still repeats the job, which is why the key comes "
            "first.",
            "Transition: Some jobs cannot finish without a person. Where does such a run wait?",
        ],
    ),
    # 6 mechanism: the approval checkpoint ------------------------------------------------------
    dict(
        kind="mechanism",
        title="A pending approval is state: keep it in Postgres",
        minutes=3.5,
        says="Approval is decided from the query's columns and saved in a Postgres checkpoint",
        src="platform/src/datapilot/loop2_verification/loop.py lines 210-221; "
        "platform/src/datapilot/loop3_events/approvals.py lines 44-47; pack.yaml personal_data",
        code={
            "language": "python",
            "origin": "platform/src/datapilot/loop2_verification/loop.py lines 210-221 "
            "(rewrapped; the already-approved test of the condition and the description left "
            "out), then platform/src/datapilot/loop3_events/approvals.py line 47 (the planted "
            "in-memory branch, lines 44-46, left out at the second ... line and described in "
            "the notes)",
            "lines": [
                'approvals = HumanInTheLoopMiddleware({"run_query": {',
                '    "allowed_decisions": ["approve", "reject"],',
                '    "when": lambda req: self.checker.needs_approval(',
                '        str(req.tool_call["args"].get("sql", "")), export=request.export)',
                "    ...}})",
                "...",
                "from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver",
            ],
            "marks": [
                (1, '"allowed_decisions": ["approve", "reject"]', 1),
                (2, '"when": lambda req:', 2),
                (3, 'req.tool_call["args"].get("sql", "")', 3),
                (6, "AsyncPostgresSaver", 4),
            ],
        },
        on_slide=[
            "Idea: the pause is state, so it lives where state survives a restart",
            "1. No edits: an edit skips the graders",
            "2. Checked again on resume: no model opinion",
            "3. Held by the tagged columns it returns",
            "4. Saved in Postgres; memory loses it[^10]",
        ],
        notes=[
            "Purpose: Show how a run waits for a person durably, and why the hold condition must "
            "be deterministic.",
            "What to say: When a generated query returns personal data, the run must wait for a "
            "person, maybe for hours. A run that waits is state: the conversation so far, the "
            "pending tool call, and the decision owed. Four markers, and two of them are about "
            "agents, not databases. Marker one: the decisions are approve and reject only. An "
            "edit is not offered, because an edited query never went through the graders that "
            "passed the original; if it is wrong, reject it and let the agent ask again. Marker "
            "two: this condition is evaluated again when the run resumes, to find the call it "
            "paused. So it must give the same answer twice: a pure function of the query and "
            "the tags, never a model's judgement and never the clock. Ask a model whether to "
            "hold, and on resume it may say no, and the run loses its own pause. Marker three: "
            "the condition asks the checker whether this exact query returns a column tagged as "
            "personal data in the pack: customer email, phone, first name, last name. A filter "
            "on those columns does not hold, because those values never come back. Marker four: "
            "where the pause lives. The "
            "Postgres checkpointer keeps it in its own schema, keyed by the run id, so any worker "
            "can resume it after a restart. The dots above it hide the planted branch, which "
            "swaps in the in-memory saver, which dies with the process. The LangChain human-in-the-loop page, Source "
            "10, says the same in its own words: in production, use a persistent checkpointer. "
            "Measured: with Postgres the approval survived the restart and posted in 7 of 7 "
            "runs; in memory it was lost in every planted run.",
            "The point to land: Store the pause durably, show the exact action, allow approve or "
            "reject only, and decide the hold from data.",
            "Example: The California marketing export returns customer emails, so it holds; the "
            "dialog states the exact query and about 5,261 rows.",
            'Ask the room: only if ahead of the clock: "Which action of your agent would you '
            "hold for a person, and what "
            'data decides it?" Expect: refunds, outbound email, exports; decided by amount, '
            "recipient, or column.",
            "Misconceptions: That the approval is a dialog in the user interface. The dialog is a "
            "view; the approval is a durable checkpoint and a decision record.",
            "Transition: Approvals stop one action. What stops everything, including the run "
            "already in flight?",
        ],
    ),
    # 7 mechanism: the kill switch --------------------------------------------------------------
    dict(
        kind="mechanism",
        title="Check the kill switch before every step",
        minutes=3,
        says="Middleware checks the switch before each model call and each tool call",
        src="platform/src/datapilot/loop3_events/killswitch.py lines 89-107; Source 8 (custom "
        "middleware); Source 2 (levels and the kill switch)",
        code={
            "language": "python",
            "origin": "platform/src/datapilot/loop3_events/killswitch.py lines 89-107; each "
            "... marks lines left out: the planted check at claim only (lines 90-91), the last "
            "return and the decorator (95-97), and the asynchronous twin and the tool wrapper's "
            "first two lines (100-106); the stop record on the run guard (line 93, between the "
            "check and return True) is left out without a ... line and described in the notes; "
            "the stop message is shortened",
            "lines": [
                "def _check(self) -> bool:",
                "    ...",
                "    if self.is_engaged():",
                "        return True",
                "...",
                "def before_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:",
                '    return {"jump_to": "end"} if self._check() else None',
                "...",
                '        return stopped_message(request, "Run stopped: ...")',
            ],
            "marks": [
                (2, "self.is_engaged()", 1),
                (6, '{"jump_to": "end"}', 2),
                (8, "stopped_message(request", 3),
            ],
        },
        on_slide=[
            "Idea: a model call already running finishes; the next step ends the run",
            "1. Checked at every step, not only at claim",
            "2. Before a model call: end the run[^8]",
            "3. Before a tool call: skip the tool",
        ],
        notes=[
            "Purpose: Show where the stop is checked, and why checking at claim alone fails.",
            "What to say: This is the kill switch middleware, and it is short. Marker one: the "
            "check. If the switch is engaged, the run guard records the stop with its reason, "
            "a line the slide leaves out, and the check returns true, so the run ends as blocked by the kill switch, not as "
            "a failure. The first dots hide the planted line, which returns false before this "
            "check: that is what checking only at claim means, and a run claimed before the "
            "switch never looks again. Marker two: the "
            "check runs before every model call, and when it fires it jumps to the end of the "
            "run. The LangChain custom middleware page, Source 8, documents exactly this hook "
            "and its jump to the end. Marker three: the same check wraps every tool call and "
            "returns a message instead of calling the tool, which covers a tool call the model "
            "had already decided on. Together they stop the run at its next step, not at its "
            "next job. What about the step already running? A model call in flight is not cut "
            "off: it finishes, and the check before the next step ends the run. A query in "
            "flight is bounded by the 5-second statement timeout. That is why the measured stop "
            "is seconds, not instant. "
            "Engaging the switch also forces the system to the report-only level, the framing "
            "of Cobus Greyling's loop engineering patterns, Source 2, where the kill switch "
            "drops any level straight to report-only. Measured: checked before every step, the "
            "run in flight stopped in 9 of 9 runs, in 3 to 33 seconds; checked at claim only, "
            "it posted after the switch in every planted run.",
            "The point to land: Check the stop before the model call, the one step every loop "
            "iteration passes through.",
            "Example: A train's emergency brake works on the moving train, not only at the "
            "station.",
            'Ask the room: only if ahead of the clock: "Does your stop button reach a job that '
            'has already started?" Expect: '
            "most check at the start of a job only.",
            "Misconceptions: That the kill switch rolls back what already ran. It stops new "
            "steps; committed effects stay, which is why the keys and approvals matter.",
            "Transition: Time to see all of it live.",
        ],
    ),
    # 8 demo ------------------------------------------------------------------------------------
    dict(
        kind="demo",
        title="Live: events, approvals, duplicates, and the kill switch",
        minutes=24,
        says="Five event-loop demos, live; the kill switch stops a run in flight",
        src="platform/demos/registry.yaml (section event-loop); section-3-event-loop/demo/"
        "README.md; docs/instructor-guide.md, Section 3: Event loop",
        on_slide=[
            "Badge: DEMO - 3",
            "What to watch for:",
            "- One webhook, one strip from Queued to Done",
            "- A held export surviving a worker restart",
            "- Three deliveries, one answer, two duplicates absorbed",
            "Guaranteed moment: the kill switch stops the run in flight at its next step, and "
            "the system drops to the report-only level.",
            "Link: Demo page on GitHub | " + DEMO_PAGE,
        ],
        notes=[
            "Purpose: Run every event-loop demo live, both halves where a planted bug exists, "
            "so each safeguard is seen failing and then holding.",
            "What to say: Let's watch the event loop run with nobody pressing Ask. Everything "
            "you see is live, against the same model as in the earlier sections, and every strip carries "
            "its start time and its trace link, so you can check it just happened. Three of "
            "these demos run twice: first with one line of the code switched to the broken "
            "version, then with the fix. Watch for the difference between the two halves, "
            "because the model is the same in both. Keep an eye on the run board at the top: "
            "each strip is one run moving from Queued to Done, and the lanes off the board, "
            "Failed and Blocked by kill switch, are where the planted halves end up. The "
            "channel at the bottom is what a finance team would read. When a run is waiting, I "
            "will ask you to predict what happens next; put your answer in the chat before the "
            "strip moves.",
            "Demo: The webhook question.",
            "Command: 2:14 to 2:17, the registry's 3 minutes. make demo "
            "NAME=events-webhook-question, or Events > Send webhook question in the console.",
            "Point at: the strip appearing in Queued and moving to Running, Verifying, and Done; "
            "then the channel post labelled unverified; then the live stamp.",
            "Expected output: one strip from Queued to Done and one post labelled unverified, in "
            "12 to 46 seconds in the recorded runs. The count is 300 orders, the Eastern time "
            "day, or 291, the same day in Coordinated Universal Time; the reviewer approved both "
            "in calibration. Keep a 291 on screen and teach it; do not reset for a better "
            "number.",
            "While it runs: say that nobody pressed Ask: a webhook became an event row and a job "
            "row, and a worker claimed it with the claim from the code slide.",
            "If it fails: run make reset NAME=event-loop (about 7 seconds; 6.4 to 6.9 measured on "
            "the class stack), then the same trigger again; a missing trace link is not a "
            "failure. The same rule for every demo here: a retry spends the 2-minute reserve, "
            "then the 3 minutes of the optional digest demo; start no retry after 2:36. Past "
            "that, skip it, say so, and name that demo for the Thursday review.",
            "Backup screenshot: " + EXPECTED + "events-webhook-question-board.png, the strip in "
            "Done; point at it only while you reset and run again, never instead of the run.",
            "Demo: The approval that survives a restart.",
            "Command: 2:17 to 2:23, 6 minutes: the registry's 5 for one half, plus the planted "
            "half. Planted half first, measured twice, 41 seconds both times (24 and 25 "
            "October): make demo "
            "NAME=events-approval-survives-restart PLANTED=1 (the in-memory checkpointer; the "
            "command restarts the worker with it and waits for the run to end). When the strip "
            "reaches Holding for approval, press Restart worker, then Approve: the approval "
            "finds no checkpoint to resume and the run fails. Wait for the terminal's line "
            "Restarting worker without the demo's flags, then make reset NAME=event-loop (about "
            "7 seconds) and the fixed half: make demo NAME=events-approval-survives-restart, or Events > Request "
            "California export; at Holding for approval press Restart worker, wait for the "
            "worker to come back (its restart time is not measured on its own; the whole demo "
            "took 50 to 84 seconds), then approve in the dialog.",
            "Point at: planted half, the line that the pending approval was lost and the run in "
            "Failed; fixed half, the dialog's exact query and row count, the strip staying in "
            "Holding for approval across the restart, and Done after Approve.",
            "Expected output: the strip stays in Holding for approval across the restart, then "
            "moves to Done, in 50 to 84 seconds in the recorded runs; the planted half fails "
            "the run with the pending approval lost.",
            "While it runs: say that restarting the worker is the deploy or the crash of a "
            "normal Tuesday, and that the pause is a checkpoint in Postgres keyed by the run.",
            "If it fails: run make reset NAME=event-loop (about 7 seconds), then the same trigger "
            "again, no retry after 2:36; if the Restart worker button does nothing, demo controls are off, so take the next demo "
            "and return to this one after the section.",
            "Backup screenshot: " + EXPECTED + "events-approval-after-restart.png, the export "
            "still held after the restart; point at it only while you reset and run again.",
            "Demo: Duplicate events.",
            "Command: 2:23 to 2:27, 4 minutes: the registry's 3 for one half, plus the planted "
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
            "the order of the three deliveries does not matter, the key decides.",
            "If it fails: run make reset NAME=event-loop (about 7 seconds), then the same trigger "
            "again, no retry after 2:36.",
            "Backup screenshot: " + EXPECTED + "events-duplicate-events-board.png, the strip "
            "marked 2 duplicates absorbed; point at it only while you reset and run again.",
            "Demo: The kill switch in flight.",
            "Command: 2:27 to 2:33, 6 minutes: the registry's 4 for one half, plus the planted "
            "half and two resets. make demo NAME=events-kill-switch-in-flight PLANTED=1 (the kill "
            "switch at claim only), then make reset NAME=event-loop, then make demo "
            "NAME=events-kill-switch-in-flight, then make reset NAME=event-loop again (each reset "
            "about 7 seconds). Run both "
            "halves from the terminal: the console's button sends no demo pacing.",
            "Point at: with the bug on, the strip still moving after the switch and the post; "
            "with it off, the strip moving to Blocked by kill switch and the status line at the "
            "report-only level.",
            "Expected output: the in-flight strip moves to Blocked by kill switch and the status "
            "line shows the report-only level, in 3 to 33 seconds in the recorded runs; the "
            "planted half posts after the switch.",
            "While it runs: say which step the run stops at does not matter, as long as no model "
            "call starts after the stop.",
            "If it fails: run make reset NAME=event-loop (about 7 seconds), then the same trigger "
            "again, no retry after 2:36; if the run finished before the switch, it was sent without pacing, so use the make command.",
            "Backup screenshot: " + EXPECTED + "events-kill-switch-in-flight-board.png, the run "
            "under Blocked by kill switch; point at it only while you reset and run again.",
            "Demo: The digest now.",
            "Command: 2:33 to 2:36, the registry's 3 minutes; optional, cut it first when the "
            "section runs late. make demo NAME=events-digest-now, or Events > Run digest now. "
            "The last 2 minutes, 2:36 to 2:38, are a reserve for one reset and run again; if "
            "none is needed, take questions.",
            "Point at: the one digest post with the previous business day's key figures.",
            "Expected output: one digest post; no measured time is on the evidence page, and the "
            "class plan gives it 3 minutes.",
            "While it runs: say that the 8 a.m. Eastern time schedule fires the same job, keyed "
            "by the business day and the firing.",
            "If it fails: run make reset NAME=event-loop (about 7 seconds) and try once more "
            "only before 2:36, or cut it.",
            "Backup screenshot: none is captured for this optional demo; describe the single "
            "digest post while you reset, or move on.",
            "The point to land: Each safeguard failed live with its bug on and held with it off; "
            "that pair is the evidence.",
            "Example: In the paired measurement, one event sent three times gave 3 answers "
            "without the key and 1 answer with it.",
            'Ask the room: "Which of the four would have hurt your team most last quarter?" '
            "Expect: duplicates from retries.",
            "Misconceptions: That the planted half is a staged failure. The model runs for real "
            "in both halves; only one line of code differs.",
            "Transition: Those were single runs. Here is what every recorded run showed.",
        ],
    ),
    # 9 evidence: without and with --------------------------------------------------------------
    dict(
        kind="comparison",
        title="Measured: each bug failed every time, each fix held",
        minutes=2,
        says="Duplicates 7 of 7, approval 7 of 7, kill switch 9 of 9; each planted bug failed",
        src="docs/evidence/section-3-event-loop.md, Results; docs/benefits.md, Section 3; "
        "section-3-event-loop/concepts.md, What we measured",
        on_slide=[
            "| Live runs, gpt-6-luna | Without the fix (planted) | With the fix |",
            "|---|---|---|",
            "| One event sent three times | 3 answers, 2 digests: 5 of 5 | 1 answer: 7 of 7 |",
            "| Worker restart while held | Approval lost: 6 of 6 | Held, then posted: 7 of 7 |",
            "| Kill switch during a run | Posted after the stop: 6 of 6 | Stopped in flight: "
            "9 of 9 |",
            "Insight: Force each failure on purpose: a fix you never saw fail is untested.",
        ],
        notes=[
            "Purpose: Show every recorded run of the three safeguards, with sample sizes, off "
            "and on.",
            "What to say: You just saw one run of each half; this is every recorded run behind "
            "them, from the section's evidence page. Read each row left to right. One event sent "
            "three times: 3 answers and 2 digests in all 5 planted runs; with the key, 1 answer "
            "and 2 duplicates absorbed in 7 of 7. A worker restart while an export was held: in "
            "memory the approval was lost in all 6; in Postgres it was held and posted, 7 of 7. "
            "The kill switch during a run: checked at claim only, a post after the stop in all "
            "6; checked before every step, stopped in flight, 9 of 9. These are small samples, "
            "so read them as every time we tried, not as rates. The counts are all or nothing "
            "because this is deterministic code: the guarantee comes from the constraint, and "
            "the count shows that the planted half really breaks it. That is the practice on "
            "the insight line.",
            "The point to land: Deterministic safeguards should hold every time; test them by "
            "switching each failure on and watching it happen.",
            "Example: The kill switch count of 9 includes the slowed-down demo run, where "
            "the run moved slowly enough to watch it stop.",
            'Ask the room: "Which of your safeguards have you ever seen fail on purpose?" '
            "Expect: few or none; most are tested only on the happy path.",
            "Misconceptions: That 7 of 7 means the fix works 100 times out of 100. It means it "
            "held in every recorded run; the guarantee comes from the constraint, not the count.",
            "Transition: So what does this loop change in a text-to-SQL design?",
        ],
    ),
    # 10 design callout -------------------------------------------------------------------------
    dict(
        kind="design_callout",
        title="From events: hold queries returning personal data",
        minutes=3,
        says="Run generated queries from events; hold by column tags; pin the business date",
        src="pack.yaml personal_data and autonomy; section-3-event-loop/demo/README.md, What "
        "the result means; docs/calibration-report.md, Resumed without traces; Source 2 (levels)",
        on_slide=[
            "Decision: which generated queries wait for a person?",
            "| Hold rule | Trade-off |",
            "|---|---|",
            "| Hold every query | Safe; approval risks a reflex click |",
            "| A model judges sensitivity | May flip on resume; a payload can argue |",
            "| Hold queries returning tagged columns | Same every time; tags to maintain |",
            "DataPilot: hold returned tagged columns; approve or reject only; start at the "
            "report-only level[^2].",
        ],
        notes=[
            "Purpose: Turn the event loop into design decisions for the learner's own "
            "text-to-SQL system: what runs unattended, what waits, and against which clock.",
            "What to say: When questions arrive as events, nobody reads the generated query "
            "before it runs, so you must decide in advance which queries wait for a person. "
            "Three rules, top to bottom. Hold every query: safe on paper, but approval risks "
            "becoming a reflex click. Let a model judge sensitivity: it can answer "
            "differently when the run resumes, and the question text can argue with it. Hold "
            "queries returning tagged columns: the same answer every time, decided from the "
            "parsed query, at the cost of keeping a tag list. DataPilot tags customer email, "
            "phone, and names; a query that returns them holds with its exact text and row "
            "estimate, and the person may approve or reject, never edit. A query that only "
            "filters on the email domain, such as the internal-accounts rule, does not hold, "
            "because no email comes back. Remember that approved rows travel to the model provider with "
            "the run. Two more design points. First, size: an approved export once returned one "
            "aggregated row holding all 5,261 addresses, which a 50-row cap does not limit; the "
            "pitfalls slide has what that cost. Second, the clock: an event-time question about the previous day resolves against the business "
            "date and Eastern time. The webhook question answered 300 orders on the Eastern time "
            "day and 291 on the Coordinated Universal Time day, and the reviewer approved both. "
            "That is why every metric family starts at the report-only level, labelled "
            "unverified, the level framing of Source 2.",
            "The point to land: Decide holds from the columns a query returns, cap the size of what an "
            "approved query returns, and pin the business date.",
            "Example: The California export holds because it returns email; the webhook question "
            "about orders returns no tagged column, so it posts, labelled unverified.",
            'Ask the room: "Which columns in your warehouse would you tag first?" Expect: email, '
            "phone, names, sometimes salary or address.",
            "Misconceptions: That read-only access makes personal data safe. A read-only query "
            "can still export every email; the hold is about where data goes.",
            "Transition: What do you do with this next week?",
        ],
    ),
    # 11 apply-it checklist ---------------------------------------------------------------------
    dict(
        kind="checklist",
        title="Apply it: five checks for your event loop",
        minutes=2,
        says="Five things to do on your own event-driven agent next week",
        src="section-3-event-loop/README.md, Apply it in a real system; "
        "section-3-event-loop/demo/walkthrough.md, If you copy this",
        on_slide=[
            "- Key every event by its meaning, under a unique constraint",
            "- Claim in one short transaction; a lease covers the work",
            "- Keep pending approvals in a durable checkpointer",
            "- Check the stop before every model call and tool call",
            "- Test each by forcing it: send twice, restart, stop mid-run",
        ],
        notes=[
            "Purpose: Give five concrete actions a learner can take on their own event-driven "
            "agent next week.",
            "What to say: Five checks, each an afternoon or less. One: list every effect your "
            "agent has, posts, emails, tickets, exports, and key each by what the event means, "
            "under a unique constraint, with a second-arrival rule: ignore, update, or reject. "
            "Two: if your jobs live in a table, claim in one short statement that commits at "
            "once, with a lease, and keep no transaction open across a model call. Three: move "
            "every pause for a person into a durable checkpointer, and keep the hold condition "
            "a function of the action, never a model's opinion. Four: put your stop check in "
            "middleware before every model call and every tool call. Five, the one teams skip: "
            "force each failure. Send one event three times, restart a worker while a run is "
            "held, engage the stop during a slow run. If you cannot force the failure, you do "
            "not know that the fix holds. Assignment 3: Event loop practises this on a nightly "
            "revenue anomaly alert with a deterministic key.",
            "The point to land: Every safeguard you add gets a test that makes its failure "
            "happen on purpose.",
            "Example: In Assignment 3, a second delivery of the anomaly alert must post nothing "
            "new, and a late order must update the alert in place.",
            'Ask the room: "Which of the five would take you longest?" Expect: moving approvals '
            "into a durable checkpointer.",
            "Misconceptions: That a message broker removes the need for keys. Brokers deliver at "
            "least once too; the keys and the lease checks still apply.",
            "Transition: Before the recap, the mistakes teams repeat here.",
        ],
    ),
    # 12 pitfalls -------------------------------------------------------------------------------
    dict(
        kind="pitfalls",
        title="Event loop pitfalls that pass every unit test",
        minutes=2.5,
        says="Two event-loop mistakes and the row cap that is not a size cap",
        src="section-3-event-loop/concepts.md; docs/calibration-report.md, The retake chains; Source 26 (long "
        "transactions)",
        on_slide=[
            "| Pitfall | What happens | Do instead |",
            "|---|---|---|",
            "| A key made at arrival | Every copy looks new and posts | Key by meaning |",
            "| A lock held through the model call | Dead rows pile up[^26]; the job looks queued "
            "while it runs, and a killed run restarts uncounted | Commit the claim; lease the "
            "work |",
            "Insight: A row cap is not a size cap: one row held 5,261 addresses, 109,380 tokens.",
        ],
        notes=[
            "Purpose: Name the event-loop mistakes that look fine in unit tests and fail in "
            "production, each with its fix.",
            "What to say: Two pitfalls on the table, and one more in words, each one we either planted or met. First, a key made at "
            "arrival. A random id per delivery, which is exactly the planted random digest id, "
            "makes every copy look new; a key from the wall clock breaks the other way, because "
            "a retry a second later gets a new key. Key by meaning. Second, a lock held through "
            "the model call. It looks tidy, one transaction around the whole job, but Brandur "
            "Leach's write-up of Postgres job queues, Source 26, shows long transactions pile up "
            "dead rows and slow every claim. In our tests the job also looks queued while it "
            "runs, and killing the worker rolls the claim back: the job is queued again with no "
            "attempt counted, though its run had already started, so an attempt cap never "
            "stops it and anything it posted goes out again. We plant this one in the code and "
            "its tests, with no class demo. Third, not on the table: no daily budget. "
            "Unattended work spends with nobody watching; our daily worker budget is 2,000,000 "
            "tokens, checked at claim, and on a rehearsal day it blocked a run at 1,969,486. "
            "Now the insight. A row cap of 50 felt like a size limit. Then an approved export "
            "returned one aggregated row holding all 5,261 addresses, resent with every later "
            "call, and the run ended at 109,380 tokens against the 60,000-token budget. A cap of "
            "2,000 characters a value brought the same export down to 7,670.",
            "The point to land: Bound the size of every value a tool returns, not only the "
            "number of rows.",
            "Example: The fix for the export was one setting, a cap on characters per value, "
            "and the run's tokens fell from about 109,000 to 7,670.",
            'Ask the room: "Which of these does your system have today?" Expect: no daily '
            "budget, and approvals in memory.",
            "Misconceptions: That a budget per run is enough. Many small runs, each inside its "
            "own budget, still add up when nobody watches.",
            "Transition: Let me check what stuck before the poll.",
        ],
    ),
    # 13 recap and question ---------------------------------------------------------------------
    dict(
        kind="recap",
        title="Recap: the event loop",
        minutes=2.5,
        says="Three points to keep, and a resent export held across a worker restart",
        src="section-3-event-loop/README.md; docs/instructor-guide.md, Section 3: Event loop; "
        "docs/calibration-report.md, Resumed without traces",
        on_slide=[
            "- One event, one effect: the key lives in the database",
            "- A pending approval is state: keep it durable",
            "- The stop reaches the running job",
            "Question: A sender resends the California export while the first is held, then the "
            "worker restarts. How many exports wait for approval, and why?",
        ],
        notes=[
            "Purpose: Consolidate the event loop and check, with one question, that learners "
            "can combine the event key and the durable approval.",
            "What to say: Three points to keep. One event, one effect, because the key lives in "
            "a unique constraint. A pending approval is state, so it lives in a durable "
            "checkpointer. And the stop is checked before every step, so it reaches the job "
            "already running. Now the question; give the room thirty seconds in the chat. The "
            "answer: one. The resend carries the same event id, so the insert hits the unique "
            "constraint, inserts nothing, and is counted as a duplicate. The first export's "
            "pending approval is a checkpoint in Postgres, so it survives the restart, and "
            "approving it posts once. Take any remaining questions here; park longer ones for "
            "the Thursday review.",
            "The point to land: The event loop makes runs safe to repeat, wait, and stop; it "
            "does not turn a wrong answer into a right one.",
            "Example: The webhook question answered 300 orders in one run and 291, the day in "
            "Coordinated Universal Time, in another; both posted once, labelled unverified, and "
            "the key could not tell them apart.",
            "Ask the room: the question on the slide. Expect: one; a common wrong answer is two, "
            "from people who think the key is made when the event arrives, and another is zero, "
            "from people who expect the restart to lose the approval.",
            "Misconceptions: That idempotency protects correctness. It posts a wrong answer "
            "exactly once.",
            "Transition: A 291 would post once, labelled unverified, and the key cannot tell it "
            "from 300. So which autonomy level would you grant the revenue digest today? That is "
            "the poll.",
        ],
    ),
]
