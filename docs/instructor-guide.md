# Instructor guide

> **Terms on this page**
>
> - **Live session**: Everything that runs between one `make preflight` and the next.
> - **Drift canary**: Three easy questions that must pass and two trap questions that must still fail.
> - **Baseline experiment**: The benchmark run under the active knowledge version, started in the open live session.
> - **Live stamp**: A result's run start time in your local time and its LangSmith trace link.
> - **Planted bug**: A defect switched on by a flag so a demo shows its failure every time.
> - **Development split**: The benchmark questions the analyzer team may learn from.
> - **Holdout split**: The benchmark questions the analyzer team never sees; the gate decides on them.

How to run the four-hour live class of Module: Loop Engineering. Every demo is live, on
gpt-6-luna, with the class key. When a demo stalls, you reset its section and run it again:
`make reset NAME=<section slug>`, then the same trigger. The times on this page are the times in
`slides/outline.md`; the cues come from `platform/demos/registry.yaml` and the DEMO slides'
speaker notes.

## Class-day cheat sheet

| Time | Block | What you do |
|---|---|---|
| 0:00-0:10 | Opening | Full screen; welcome, keys, setup checks, the fiscal year 2025 revenue question |
| 0:10-0:55 | Section 1: Agent loop | Concepts to 0:33; three core demos and the code to 0:50; questions |
| 0:55-1:45 | Section 2: Verification loop | Concepts to 1:19; three core demos and the code to 1:37; questions |
| 1:45-1:55 | Break | Write the return time in the chat; reset the event loop |
| 1:55-2:50 | Section 3: Event loop | Concepts to 2:19; four core demos, a reset, and the code to 2:41; questions |
| 2:50-2:55 | Poll | Start the baseline experiment first, then launch the Zoom poll |
| 2:55-3:05 | Break | Queue the naive analyzer behind the baseline: `make demo NAME=improve-naive-analyzer-blocked PLANTED=1` |
| 3:05-3:50 | Section 4: Hill-climbing loop | Concepts to 3:25; five core demos and the code to 3:45; questions |
| 3:50-4:00 | Closing | All results, which loop when, assignments, final project, questions |

Three terminals, opened before the class:

| Terminal | Runs |
|---|---|
| Stack | `make up`, `make ps`, `make logs NAME=<service>` |
| Demo | `make demo NAME=<slug>`, its planted half `make demo NAME=<slug> PLANTED=1`, `make reset NAME=<section slug>`, and `make autonomy LEVEL=<level> BY="<your name>"` |
| Editor | The code walkthrough files of each section |

The services run in Docker Compose, the hill-climbing runner among them: the service
`hill-climbing-runner` serves the Improve page and writes the gold checks. Never start a second
runner; `make hill-climbing-runner` refuses while the service serves. To see what it is doing:
`make logs NAME=hill-climbing-runner`.

Three commands when a demo stalls:

```bash
make ps
make reset NAME=agent-loop
make demo NAME=agent-confident-wrong-answer
```

Swap the section slug (`agent-loop`, `verification-loop`, `event-loop`, `hill-climbing-loop`) and
the demo slug for the demo on screen. Never run `make preflight` during class: it starts a new
live session, and the baseline experiment from the poll belongs to the class session.

The baseline is safe across a reset: `make reset NAME=hill-climbing-loop` clears the candidate and
the knowledge state, keeps the session's baseline experiment, and prints what it kept with its
start time. The full reset, `make reset-discarding-baseline NAME=hill-climbing-loop`, also
discards the baseline. Use it only as a deliberate choice, never to recover a demo in class: the
console then needs a new baseline from the open session. Both first copy every experiment,
decision, and version they delete or retire into the reset archive, and say how many rows;
`make archive` and `make archive-show NAME=<experiment id>` read it back.

Cut first, in this order: the optional demos, then the "Reference: skip if short on time" slides.
Never cut a core demo or a core concept slide.

Parking lot: when a question will not fit, say "Great question for Thursday. Put it in the chat
with the word Thursday and we answer it in the review session." The questions go into
[the review session](review-session.md) and then the [frequently asked questions](faq.md).

## The day before

Keys first. Confirm every learner has an OpenAI key from the operations team, and that operations
has enabled gpt-6-luna on every learner key: an OpenAI project's model settings can hide a model
from its keys. Recommend that operations issue the keys from a dedicated OpenAI project with a
per-learner spending limit of 3 dollars and the alert that
[the costs page](costs.md#the-learner-key-limit) recommends, sized from the measured cost of the
assignment checks; each check also stops at its own spend cap of 1.00 dollar.
When a key is missing or rejected, `make preflight` says "Your OpenAI key was not accepted. Check
it with the operations team."; when it cannot use the model, it adds "The model gpt-6-luna is not
available to it." It never prints the key.

**Rehearse on an earlier Eastern time day than the class.** The class stack counts its worker's
tokens per Eastern time day, against `budgets.tokens_per_day` (2,000,000 tokens) in `pack.yaml`,
and the count starts again at midnight Eastern time. A rehearsal's chains take a large share of a
day: on 25 October 2026 a class run-through and two more Section 4 chains, run to retake images,
took the class stack to 1,969,486 tokens. `make preflight PURPOSE=class` therefore refuses to start the class session while less than
the tokens of one class run-through are left of the day, about 520,000 tokens
(`budgets.class_pass_tokens`: a run-through of every core demo, both finales, and a margin for
repeated demos). Its line `token budget` shows the day's count with
any purpose, so read it at the end of the rehearsal, and hold the rehearsal on the day before the
class, never on its morning.

1. **Re-run calibration for a new cohort.** gpt-6-luna has no dated snapshot, so its behaviour can
   drift between cohorts. Run each step with `make calibrate STEP=<step>`: `canary`, `traps`,
   `experiment-starting`, `analyzer`, `experiment-candidate`, `stability-starting`,
   `stability-candidate`, `agents`, and `confirm`. Two more steps are optional:
   `analyzer-high` (the analyzer team at reasoning effort high) and `output-token-cap` (a probe of
   the output-token cap). Record the date and the model id the OpenAI
   application programming interface (API) returns in `docs/calibration-report.md`.
2. **Start a rehearsal session**: `make preflight PURPOSE=rehearsal`. Its canary asks three easy
   questions, which must pass, and two trap questions, which must still fail under the starting
   knowledge. A failed canary means the model changed: stop and re-run calibration before class.
3. **Run the live smoke suite**: `make live-smoke`. Five real calls across the system, each with
   its tokens, cost, and trace link; it fails only on a hard breakage. When it reports
   `missing trace`, LangSmith is refusing traces (on the free plan, its monthly limit): plan the
   class with the recovery row "LangSmith refuses traces" below.
4. **Rehearse every core demo twice in a row**, with `make reset NAME=<section slug>` between, on
   the class model, in the order of the class, planted flags included (see "Planted flags in
   class" below). Note what varied, and time the approval demo's planted half (two worker
   restarts) and each promotion after approval: Section 3's timetable needs the first, Section
   4's the second.
5. **Rehearse the Section 4 chain twice**, as in class, and the class-day safeguard once between
   the two, in this order:
   1. The first chain: the baseline, the naive analyzer and its candidate experiment, the
      analyzer team, the candidate experiment, approval, the wait for the promotion,
      `make autonomy LEVEL=unattended BY="<your name>"`, and the finale, sent with
      `make demo NAME=improve-cleared-unattended`: it prints the finale's run id in full
      (`runs ['<run id>']`), which step 2 needs and the console does not show.
   2. **Mark the finale's version for the class-day safeguard, right after the first correct
      finale, before any reset.** Every `make reset` clears the runs, their gold checks, and the
      families cleared, which this step reads. When the finale's strip on the Events page shows
      "Gold check passed", mark the version it ran under (the one the Improve page names as the
      active version) with the run id `make demo` printed:
      `make safeguard-verify NAME=<version> RUN=<finale run id> BY="<your name>"`. It refuses a
      run that is not a posted finale of a rehearsal session under that version with a passed
      gold check, and it records the families the version had cleared then, so the record
      survives the resets that follow. Check it with `make safeguard-status`.
   3. **Rehearse the safeguard live, once, as class would.** Right after step 2 the verified
      version is still the active one, so `make safeguard-activate` refuses ("already the active
      version, so the safeguard has nothing to switch") and changes nothing. First
      `make reset NAME=hill-climbing-loop`, which makes the baseline's version active again and
      sets the report-only level; then `make safeguard-activate BY="<your name>"`,
      `make autonomy LEVEL=unattended BY="<your name>"`, and the finale, again with `make demo`.
      Record both finale run ids.
   4. `make reset NAME=hill-climbing-loop`, then the second chain, as in step 1.

   Record each run id and time in `docs/calibration-report.md`.
6. **If no rehearsal finale was correct**, this rehearsal verified no version. An older
   verification may still be on the stack, such as a previous cohort's, but
   `make safeguard-activate` refuses one older than 7 days or not from a rehearsal session of this
   stack, unless you name it with `NAME=<version>`; `make safeguard-status` shows its age and
   session. Run the chain again until a finale is correct, and verify it at once. If time runs out, teach the finale without the
   safeguard, and say in class that a wrong answer stays on screen as the gate's evidence.
7. **The optional demos** (Texas last quarter, the cost guard, the digest now, the over-broad
   rule) have not yet passed live twice in a row: rehearse each twice with a reset between, or
   plan to cut it.
8. **Open each section's code** once, from the DEMO slide's speaker notes and the section's
   `demo/walkthrough.md`, so the editor tabs are ready.
9. **Check the screen.** Present the console in F11 full screen. The status line, all five lanes,
   and the off-the-board row must be visible on the Events page without scrolling.
10. **Check the retaken images**, last: `make check-images ARGS=--rehearsal` passes. With
    `--rehearsal`, the image check's exceptions that expire at the rehearsal no longer excuse, so
    it fails on any image the rehearsal still owes a retake. Remove each such exception from
    `EXCEPTIONS` in `platform/scripts/check_images.py` with its retake: the check also fails on an
    exception whose image no longer has the problem.

## Thirty minutes before

The [preflight checklist](preflight-checklist.md) holds these steps as one tick list.

1. Check that `.env` sets every `BUG_` flag and `DEMO_PACING` to 0, and leave them there all
   day: each planted half switches its flags on for its own runs (`PLANTED=1`), and the finale
   refuses to start while a flag is on.
2. `make up`, then `make ps`: six services up (`postgres`, `api`, `worker`, `scheduler`,
   `hill-climbing-runner`, and `console`), with `api` and `postgres` healthy; `migrate` has
   exited. The `hill-climbing-runner` service serves the Improve page and writes the gold check of
   every live run that answers a benchmark question.
3. Reset every section: `make reset NAME=agent-loop`, then `verification-loop`, `event-loop`, and
   `hill-climbing-loop`. Each reset releases the kill switch.
4. `make preflight PURPOSE=class`: every check passes, including `token budget`, the canary lines
   read `as expected`, and the last line starts `Live session started at`. If it refuses with a
   line that starts "Less than one class pass is left of this Eastern time day's token budget", no
   class session started: see "If something breaks" below. Everything until the next preflight belongs to the
   class session, including the baseline experiment at the poll.
5. Open the console at http://localhost:8501 on the Agent page, press F11 for full screen, and
   share that window. Keep the terminals and the editor in separate windows.
6. Confirm the status line: the class session's start time, the report-only level, the kill switch
   released, "Business date: 31 January 2026", and "Planted None: the fixed system": no run has
   a planted flag on yet.
7. `make safeguard-status`: it names the version verified in rehearsal, for the
   class-day safeguard in Section 4, and prints the line `ok make safeguard-activate takes it`. If it
   names none, or prints `x  make safeguard-activate refuses it` with a reason (older than 7 days,
   or not from a rehearsal session of this stack), see step 6 of the day before.

## Section by section

Each section runs the same way: the concept slides, then the DEMO slide, whose speaker notes hold
every core demo in order with its console control, what to point at, what to say, what may vary,
and the reset. The DEMO slide itself shows its badge, what to watch for, the guaranteed moment
of its title demo, and a labelled link to the demo page on GitHub. For every demo, point last at
the live stamp: the run's start time in your local time and its trace link.

### Planted flags in class

A planted half is `make demo NAME=<demo> PLANTED=1` in the demo terminal: the demo's planted
bugs are on for its own runs and requests only, and `.env` never changes, so no `make up` falls
between the halves. The fixed half is the console control or `make demo NAME=<demo>`. The console
has no control for a flag, apart from Improve > Run the naive analyzer (planted), shown while demo
controls are allowed, whose demo has no fixed half; a chip on the status line names the flags the newest run had on.

| Planted half | The flag goes |
|---|---|
| `make demo NAME=agent-unbounded-rows PLANTED=1` | With the run's event, to the worker |
| `make demo NAME=verify-malicious-sql PLANTED=1` | With the run's event, to the worker |
| `make demo NAME=verify-retry-cap PLANTED=1` | With the run's event, to the worker |
| `make demo NAME=events-duplicate-events PLANTED=1` | With its events, to the `api` service; the digest id is made in `make demo` itself |
| `make demo NAME=events-kill-switch-in-flight PLANTED=1` | With the run's event, to the worker, with demo pacing |
| `make demo NAME=improve-naive-analyzer-blocked PLANTED=1` | With its two requests, to the hill-climbing runner |
| `make demo NAME=events-approval-survives-restart PLANTED=1`, on request | A worker restart with it; another without it once the run ends |

The in-memory checkpointer acts when the worker starts, so that half restarts the worker twice and
refuses while any run is in flight. It is four steps: `make demo
NAME=events-approval-survives-restart PLANTED=1`, which prints "Restarting worker with
BUG_MEMORY_CHECKPOINTER on, for this demo only" and sends the export; then Restart worker in the
console once the run holds; then approve the held export; then wait for the terminal's line
"Restarting worker without the demo's flags (as .env sets them)". The terminal waits up to 900
seconds for the run to end (`wait_seconds` in `platform/src/datapilot/loop3_events/commands.py`),
then restarts the worker anyway. Until the terminal restarts the worker back, the worker claims
only this demo's runs, so every other run waits in Queued: press Ctrl+C before the next demo, and
the worker is restarted without the flag at once. Its restart time is owed to
rehearsal (step 4 of the day before). A live check and the finale refuse to start while `.env` or
a running service has a flag on, and name it: set it to 0 in `.env`, then `make up`.

### Opening (0:00-0:10)

| Time | Slide | What you do |
|---|---|---|
| 0:00-0:01 | Title, instructor | Your name and contact |
| 0:01-0:01:30 | Welcome, in the chat | Ask for one line: which agent you run, and what stops it when it is wrong |
| 0:01:30-0:02:30 | How the class runs | Four sections, two breaks, one poll; every demo live; reset and run again |
| 0:02:30-0:03 | Support | The chat, and the parking lot for Thursday |
| 0:03-0:04 | Your key, LangSmith | The key from the operations team; LangSmith on the learner's own account |
| 0:04-0:05 | Setup checks | Services healthy, then the preflight canary |
| 0:05-0:06:30 | Recap, problem statement | From the Harness Engineering module to four loops; DataPilot |
| 0:06:30-0:08 | The fiscal year 2025 revenue question, why it matters | "What was our net revenue in fiscal year 2025?" and its five traps |
| 0:08-0:10 | Four loops, measurement, glossary | The loops in one picture; gold queries on two databases; the terms |

### Section 1: Agent loop (0:10-0:55)

| Time | Slide or demo | What you do |
|---|---|---|
| 0:10-0:15 | Agenda, failure story, the tempting question | "Will a stronger model fix the revenue number?" No |
| 0:15-0:33 | Concepts 1 to 4, cheat sheet | Schema linking, context as a budget, structured output, subagents |
| 0:33-0:36 | The simple question | Agent: type "How many orders have been placed in total?" and press Ask, or `make demo NAME=agent-simple-question` |
| 0:36-0:41 | The confident wrong answer | Agent > Ask the spine question, or `make demo NAME=agent-confident-wrong-answer` |
| 0:41-0:45 | Unbounded rows | `make demo NAME=agent-unbounded-rows PLANTED=1`, then Agent > Run large query |
| 0:45-0:50 | Code walkthrough | The tools, the analyst, the prompt, the answer envelope |
| 0:50-0:53 | Questions | Why not put the rules in the prompt? Does the scout pay for itself? |
| 0:53-0:55 | Reference slides | Only if time is left |

Demo cues:

- **The simple question.** Type "How many orders have been placed in total?", the question
  `make demo` sends, and press Ask. Point at the tool timeline (list tables, describe table, run query), the
  envelope's status and Structured Query Language (SQL), then the tokens and cost. May vary: wording, tool calls, latency.
- **The confident wrong answer.** Point at the answer text, the answer-versus-gold ledger with the
  mismatch, and the annotated SQL naming each trap. May vary: which traps the SQL hits, the value,
  whether a reviewer concern holds the run for approval (leave it held: the gold check still
  shows), and a run that gives no number, so it gets no gold check (reset Section 1 and ask
  again). The status line reads "Planted None: the fixed system".
- **Unbounded rows.** With the unbounded rows bug (`BUG_UNBOUNDED_ROWS`) on, `make demo
  NAME=agent-unbounded-rows PLANTED=1`, the token counter jumps; with it off (Agent > Run large
  query), the row cap, the total count, and the truncation notice. May vary: exact tokens, and whether the run with the bug
  off ends held for approval by a reviewer concern, which it did twice in calibration; the token
  counter is the moment either way.
- Optional, cut first: Texas last quarter, `make demo NAME=agent-texas-last-quarter`.

### Section 2: Verification loop (0:55-1:45)

| Time | Slide or demo | What you do |
|---|---|---|
| 0:55-1:00 | Agenda, failure story, the tempting question | "If every grader passes, is the answer right?" No |
| 1:00-1:19 | Concepts 1 to 4, cheat sheet | Allowlist the shape, permissions as the boundary, stops, a checker's blind spots |
| 1:19-1:23 | Malicious SQL | `make demo NAME=verify-malicious-sql PLANTED=1`, then Verify > Send malicious SQL |
| 1:23-1:27 | The retry cap | `make demo NAME=verify-retry-cap PLANTED=1`, then Verify > Inject failing grader |
| 1:27-1:31 | Every grader passes, still wrong | Verify > Ask the spine question, or `make demo NAME=verify-graders-pass-still-wrong` |
| 1:31-1:37 | Code walkthrough | The statement policy, the executor, the caps, the reviewer |
| 1:37-1:42 | Questions | Why two databases? Can the reviewer be fooled? |
| 1:42-1:45 | Reference slides | Only if time is left |

Demo cues:

- **Malicious SQL.** With the naive guard (`BUG_NAIVE_GUARD`), the read-only role refuses the
  statements; with the syntax-tree guard, its parse step stops the stacked statements and its
  statement policy the data-modifying common table expression. Point at the defense-layer panel:
  each statement, the layer that stopped it, and the layers it never reached. Only timings vary.
- **The retry cap.** With the missing retry cap (`BUG_NO_RETRY_CAP`), the cost counter climbs; with
  the cap, the run stops after 3 attempts (`limits.max_retries`) and ends escalated.
- **Every grader passes, still wrong.** The checklist turns green, the reviewer gives its verdict,
  and the gold check fails on both databases. May vary: the reviewer's verdict.
- Optional, cut first: the cost guard, `make demo NAME=verify-cost-guard`.

### Break (1:45-1:55)

Write the return time, 1:55, in the chat. Run `make reset NAME=event-loop` during the break.

### Section 3: Event loop (1:55-2:50)

| Time | Slide or demo | What you do |
|---|---|---|
| 1:55-2:00 | Agenda, failure story, the tempting question | "Should an agent route the events?" No |
| 2:00-2:19 | Concepts 1 to 4, cheat sheet | Idempotent effects, the queue as a table, durable approval, the kill switch |
| 2:19-2:22 | The webhook question | Events > Send webhook question, or `make demo NAME=events-webhook-question` |
| 2:22-2:27 | The approval that survives a restart | Events > Request California export, or `make demo NAME=events-approval-survives-restart` |
| 2:27-2:30 | Duplicate events | `make demo NAME=events-duplicate-events PLANTED=1`, `make reset NAME=event-loop`, then Events > Send the same event three times |
| 2:30-2:34 | The kill switch in flight | `make demo NAME=events-kill-switch-in-flight PLANTED=1`, `make reset NAME=event-loop`, then `make demo NAME=events-kill-switch-in-flight` |
| 2:34-2:41 | Code walkthrough | The router, the claim with its lease, the approval, the kill switch check |
| 2:41-2:47 | Questions | Why not a message broker? What if nobody approves? Why 300 orders, then 291? |
| 2:47-2:50 | Reference slides | Only if time is left |

Demo cues:

- **The webhook question.** One strip moves from Queued to Done; one post labelled unverified at
  the report-only level. May vary: time in each lane, and the count. The question asks how many
  orders were placed on the previous day, and the business date is 31 January 2026, so that day
  is 30 January 2026. The answer is 300 orders when the analyst counts the business day in Eastern
  time (New York), and 291 when it counts the day in Coordinated Universal Time. Both have come up
  in calibration, and the reviewer approved both. 300 is the right answer. Keep the post on screen
  and use it as the teaching point below; do not reset and run it again for a better number.

The two counts, in a few sentences you can say as they are:

> "This answer says 300 orders [or 291]. The right number is 300. The company's days are Eastern
> time days, so 30 January runs from midnight to midnight in New York. The services store time in
> Coordinated Universal Time, which is five hours ahead in January. Count by that clock and the day
> starts and ends five hours early, and you get 291. That is the Eastern time trap, one of the five
> traps in the benchmark, still here.
>
> Why didn't the reviewer catch it? The reviewer reads the question, the query, and the result,
> with the same starting knowledge as the analyst, and that knowledge has no time-zone rule. Both
> counts look like a fair answer for the previous day. The reviewer has no gold answer, and it never
> overrides a grader; it can only raise a concern it can see.
>
> This is why the orders family runs at the report-only level. Nothing has proven it yet, so its
> answers post labelled unverified, and a person checks before anyone acts on them. A wrong count
> here costs a second look, not a decision. In Section 4 the hill-climbing loop earns the rule:
> benchmark items that carry the Eastern time trap fail, the analyzer team proposes a time-zone
> rule, and the gate promotes it only when more holdout questions pass with no regressions and a
> person approves."

If a learner asks which one to trust, say: 300, the Eastern time day; 291 is the same question
answered on the wrong clock.

- **The approval that survives a restart.** The run holds for human approval with the exact SQL
  and row count; restart the worker; with the Postgres checkpointer the approval survives. With
  the in-memory checkpointer (`BUG_MEMORY_CHECKPOINTER`) it is lost.
- **Duplicate events.** With idempotency, one question run with two duplicates absorbed and one
  digest; with the missing idempotency (`BUG_NO_IDEMPOTENCY`), three question runs and two
  digests, with their posts: three answers to one question and two digests for one day.
- **The kill switch in flight.** `make demo` sends the webhook question with demo pacing on for
  that run, and arms and engages the switch while its strip is in Running: run both halves from
  the terminal, since the console's button sends no pacing. With the kill switch at claim only
  (`BUG_KILLSWITCH_AT_CLAIM_ONLY`, the `PLANTED=1` half, first), it keeps going; with the check
  before every step, the in-flight run moves to blocked by kill switch, and the status line shows
  the report-only level. Each half leaves the switch engaged, and an engaged switch blocks every
  new run at claim: **`make reset NAME=event-loop` after each half**, the second before the code
  walkthrough, or the finale is blocked too.
- Optional, cut first: the digest now, `make demo NAME=events-digest-now`.

During the questions, check that the status line's button reads Kill switch, not Release kill
switch.

### Poll (2:50-2:55)

First start the baseline experiment: Improve > Run experiment on the active version, or
`make demo NAME=improve-baseline-experiment`. It is the class session's baseline; the console
accepts no baseline from another session, so never skip this step. Then launch the Zoom poll:
"Which autonomy level would you grant the revenue digest today, and why?", with the report-only,
assisted, and unattended levels as options. Read the result aloud before the break.

### Break (2:55-3:05)

Write the return time, 3:05, in the chat. The baseline experiment keeps running at concurrency 8
(`evaluation.concurrency` in `pack.yaml`); measured, a baseline took 236 to 386 seconds from the trigger
(the longest on a machine shared with assignment checks), so it ends at about 2:54 to 2:57. Check once that the benchmark progress strip on the run board is counting up.

At the start of the break, queue the naive analyzer and its candidate experiment:
`make demo NAME=improve-naive-analyzer-blocked PLANTED=1`, or Improve > Run the naive analyzer
(planted), shown while demo controls are allowed. The command plants the naive analyzer with or
without `PLANTED=1`; the Run analyzer button runs the analyzer team. The runner takes requests in the order they were made, so both wait
for the baseline: the naive analyzer takes seconds and makes no model call, then its 70-run
candidate experiment runs. The naive analyzer took 211 to 580 seconds from the trigger to the
verdict in its 6 measured runs; the longest ran on a machine shared with assignment checks, and
the class run-through of 25 October 2026 took 221 seconds. Its blocked verdict is on the Improve page by about
3:01 in most runs; if it is not there at 3:25, read the baseline ledger first and come back to
it. The flag was on for those two requests alone, so the
analyzer team runs in Section 4 with nothing to switch back.

### Section 4: Hill-climbing loop (3:05-3:50)

| Time | Slide or demo | What you do |
|---|---|---|
| 3:05-3:09 | Agenda, failure story, the tempting question | "Promote rules when the development score rises?" No |
| 3:09-3:25 | Concepts 1 to 4, cheat sheet | The benchmark as an instrument, overfitting, the paired gate, earned autonomy |
| 3:25-3:40 | Five core demos, in order | The five demos in the cues below |
| 3:40-3:45 | Code walkthrough | The evaluator, the analyzer, the overfit guard, the gate |
| 3:45-3:48 | Questions | Start from the open question below |
| 3:48-3:50 | Reference slides | Only if time is left |

The demos need more machine time than their 15 minutes, measured over every recorded run, 23 to
25 October 2026 ([evidence](evidence/section-4-hill-climbing-loop.md#results)):

| Step | Measured machine time | Where it runs |
|---|---|---|
| The baseline experiment | 236 to 386 seconds | From the poll, done by about 2:54 to 2:57 |
| The naive analyzer and its candidate experiment | 211 to 580 seconds | Queued at the break, done by about 3:01 in most runs |
| The analyzer team, two candidates | 326 to 377 seconds, five runs | In the block |
| The candidate experiment | 176 to 337 seconds; 404 and 459 seconds at analyzer reasoning effort high | In the block |
| The promotion after approval, with its clearance re-runs | Active about 5 seconds after approval; the finale is held during the re-runs | In the block |
| The finale after a promotion, from its first send | 50 seconds of holds once; then posted at 74, 115, and 162 seconds | In the block |
| The finale on the class-day safeguard | 19 and 21 seconds | Only if the safeguard is used |

So only the analyzer team, the candidate experiment, the promotion, and the finale run in the
block: from 326 + 176 + 74 seconds, about 9.6 minutes, to 377 + 337 + 162 seconds, about 14.6
minutes. In the class run-through of 25 October 2026, in class order, the chain took 362 + 237 + 162
seconds, about 12.7 minutes. Plan from the largest: started at 3:28, the finale can land as late as
about 3:43, in the code walkthrough slot, so show the code walkthrough during the clearance re-runs
when the chain runs long. The plan for 3:25-3:40:

1. 3:25: read the baseline's holdout ledger, then the naive analyzer's blocked verdict. Both ran
   before the block. Then `make reset NAME=hill-climbing-loop`: it keeps the baseline and clears
   the naive candidate, so the Improve page shows the analyzer team's candidate next.
2. 3:28: Improve > Run analyzer, then at once Improve > Run experiment on the candidate. The
   runner runs the experiment as soon as the team's candidate is written, on that candidate.
3. While the team and the experiment run, narrate the cues below. If the experiment confirms
   apparent regressions and runs long, show the code walkthrough during the wait, and come back
   for the approval.
4. Approve when the gate reads ready; an approval given earlier waits for the gate. Wait for the
   promotion: as soon as the Improve page says the
   version is the active version, set the unattended level (Improve > Set the unattended level);
   every reset sets the report-only level. Then wait for the clearance re-runs:
   the note above the Events buttons goes away and Send webhook question turns on. The status
   line then names the families cleared or, when the promotion cleared none, reads Not cleared
   for every family: the finale then posts at the assisted level, a correct outcome.
5. Send the finale. From the promotion on, Send webhook question sends the fiscal year 2025 revenue
   question, whether a family cleared or none did.

Cut the optional demo first, as always; it is not in the 15 minutes.

Demo cues:

- **The baseline experiment.** Open the grouped progress strip into the holdout ledger; the trap
  items fail under the starting knowledge. Trigger: Improve > Run experiment on the active version,
  only if it never started.
- **The naive analyzer, blocked.** Queued at the break: `make demo
  NAME=improve-naive-analyzer-blocked PLANTED=1` queues the analyzer with the naive analyzer
  (`BUG_NAIVE_ANALYZER`, for its own requests) and then its candidate experiment. The naive
  analyzer makes no model call: it writes one rule per failed development question, quoting the question
  word for word with the query that failed, and skips the critic. The
  overfit guard flags every rule, but its verdict is not applied, so the knowledge diff keeps them
  all. After the candidate experiment, the gate reads blocked and names the rules the overfit
  guard rejects, whatever the holdout count. If the holdout count rises, say: a higher score does
  not license rules that copy the test.
- **The analyzer team and approval.** Improve > Run analyzer, or
  `make demo NAME=improve-analyzer-team-approve`. Point at one diagnosis, one rule, the critic's
  decision, the guard, the line naming both candidates and the one kept on the development split, and the
  knowledge diff waiting for approval. A rule whose SQL guidance does not run over the schema is
  dropped before the guard. The overfit guard rejects any rule that quotes a benchmark question
  or copies gold SQL and passes the rest: live, it rejected a rule the critic kept because it
  copied 20 or more tokens of a gold query. If it rejects one, point at it: that is the guard
  working.
- **The candidate experiment.** Already queued at 3:28, with the analyzer; trigger it only if it
  never started (Improve > Run experiment on the candidate, or
  `make demo NAME=improve-candidate-experiment`): a second press queues a second 70-run experiment
  on the same candidate. Approve when the gate reads ready; an approval given earlier waits for
  the gate. Point at the
  flips against this session's baseline, zero regressions, then the LangSmith trace list of
  `datapilot-experiments` filtered by knowledge version. **Then wait for the promotion.** Approval
  only marks the version approved; the runner then makes it active and runs the clearance
  re-runs: the finale was held 50 seconds once, and posted 74, 115, and 162 seconds after its first
  send in three later chains. The Improve page says the version is the active version
  first: set the unattended level then, during the re-runs. The status line names the families
  cleared once the re-runs finish, or reads Not cleared for every family when none cleared. Until
  the re-runs finish and the system is at the unattended level, Events > Send webhook question
  stays off and says why, and `make demo NAME=improve-cleared-unattended` refuses the same way: a
  finale sent earlier would answer under the previous version, or at the report-only level.
- **Cleared for the unattended level.** First check the status line: the kill switch released
  (Section 3 ended with a reset), and the unattended level, set during the wait (if not, set it
  now: Improve > Set the unattended level, or `make autonomy LEVEL=unattended BY="<your name>"`).
  Every reset sets the report-only
  level, and at that level the finale posts labelled unverified whatever its family cleared. Then
  Events > Send webhook question, or `make demo NAME=improve-cleared-unattended`. The moment is
  the correct answer, posted at the level its family has earned: without approval at the
  unattended level when revenue cleared on the gate's confirmed standard, and at the assisted
  level when it fell short. The assisted level is a correct outcome; say: the gate held back
  autonomy the evidence did not earn. Then point at the finale's strip on the Events page: it
  shows "Gold check passed" with the value, or "Gold check failed" with the agent's value and the
  gold value (64,015,091.21 dollars), once the runner has written the check, a few seconds after
  the post. If the answer itself is wrong, use the class-day safeguard below, live.
- Optional, cut first: the over-broad rule, blocked, `make demo NAME=improve-overbroad-rule-blocked`.

End the demos on the open question, and leave it open: "A family clears for the unattended level
on its holdout questions: 4 for revenue, 1 for average order value. Is that enough evidence?"

### The class-day safeguard for the finale

Use it only when the finale's answer is wrong: the version the gate promoted live in class posts
an answer to the fiscal year 2025 revenue question that the gold check marks wrong: the finale's
strip on the Events page shows "Gold check failed" with the agent's value and the gold value. It is never a recording: the finale runs again, live,
on the version that was promoted and verified in rehearsal (step 5 of the day before). When
`make safeguard-status` names no verified version, there is no safeguard: leave the wrong answer
on screen as the gate's evidence, and say so.

1. Say it plainly, then switch (the words below).
2. In the demo terminal: `make safeguard-activate BY="<your name>"`. It makes the
   verified version the active one through the normal activation path and records a safeguard
   activation in the promotion history, beside the gate's own decisions on the class candidate,
   which stay as they are. It prints the sentence it recorded.
3. Show the status line: it names the class-day safeguard, the active version verified in
   rehearsal, and the version it replaced. The families cleared are the ones that version cleared in rehearsal, on the
   gate's confirmed standard under its own clearance record; a family it did not clear there is
   not cleared now.
4. Run the finale again, live: Events > Send webhook question, or
   `make demo NAME=improve-cleared-unattended`. The system is still at the unattended level from
   the first finale. It posts at the level its family earned under that version, and the post says
   the clearance came from rehearsal.
5. If this run stalls, send it again. Do not reset first: `make reset NAME=hill-climbing-loop`
   makes the baseline's version active again (it archives what it removes) and sets the
   report-only level. If you did reset, run the activate command again, set the unattended level
   again (`make autonomy LEVEL=unattended BY="<your name>"`), then the finale.

What to say, in your own words: "The live loop promoted a version that still misses one trap. This
is exactly why promotion is gated and the evidence is kept: the gate's record of this version stays
as it is, and nothing is hidden. We now run the same finale, live, on the version that earned its
level in rehearsal." Then point at the live stamp and the gold check on the new run's strip, and
at the failed gold check on the first finale's strip, as the evidence of both.

### Closing (3:50-4:00)

| Time | Slide | What you do |
|---|---|---|
| 3:50-3:53 | Final run, all results | One question through four loops; one row per section, as counts |
| 3:53-3:55:30 | Which loop when, use it at work | Match the failure to the loop; four questions to ask of any agent system |
| 3:55:30-3:57 | Assignments, final project, the Thursday review | Four live checks; solutions published when the review starts |
| 3:57-4:00 | Takeaways, references, questions | End at 4:00 |

## If something breaks

| What you see | What to do |
|---|---|
| A demo shows the wrong moment or stalls | Reset and run it again: `make reset NAME=<section slug>`, then the same trigger |
| A model call fails or is rate limited | Wait for the retry; if it still fails, reset and run it again |
| The OpenAI API is down | Say so, show the code walkthrough, and return to the demo when the API answers |
| The Improve page does not move | `make logs NAME=hill-climbing-runner`, then `make up` if it stopped |
| The hill-climbing reset says "not reset" | Wait until the Improve page shows the request finished, then reset |
| A run moves to Blocked by kill switch outside Section 3 | Status line > Release kill switch, or `make reset NAME=event-loop`; then the same trigger |
| Send webhook question is off, or `make demo` says "not sent" | Do the step the message names, then the same trigger |
| A planted half shows no change | It was sent without `PLANTED=1`: `make demo NAME=<demo> PLANTED=1` |
| A check or the finale says it does not start while planted flags are on | Set each flag it names to 0 in `.env`, then `make up` |
| The console says "No baseline run in this session yet." | Start the baseline experiment now, as it offers |
| The console says "No live session." | `make preflight PURPOSE=class` once, then the baseline again; a refusal: next row |
| `make preflight PURPOSE=class` refuses for the day's token budget | See "The token budget refusal" below |
| LangSmith refuses traces: a trace link never fills | The live stamp's start time, and the run id `make demo` prints, are the evidence; see below |
| A service is down | `make ps`, then `make up`; the queue and pending approvals survive in Postgres |
| A section runs long | Cut its optional demo, then its reference slides |
| An approved version never becomes active | See "A promotion that never finishes" below |
| "The OpenAI account behind your key has no credits left" | Stop live work; see "No credits left" below |
| The finale's answer is wrong under the version promoted in class | The class-day safeguard in Section 4: `make safeguard-activate BY="<your name>"`, then the finale again, live |

**The token budget refusal.** Preflight for the class prints a line that starts "Less than one
class pass is left of this Eastern time day's token budget" and starts no class session. The
session open before it, often the day-before rehearsal session, stays open: every run you start
now would belong to it, and the status line would show its start, so do not teach in it. The
count starts again only at midnight Eastern time, in the time the message gives. Only the course
owner raises or resets the class stack's count, and no course command changes it. Tell the course
owner, then follow these steps that morning:

1. Read the `token budget` line: the tokens used today, the cap, and the count left. The
   command at the end of the message starts the class anyway, with that count in it.
2. Start the class session knowingly: run the command at the end of the message,
   `make preflight PURPOSE=class ACCEPT_TOKENS_LEFT=<count>`, with the digits of the printed
   command, without commas (`300000`, never `300,000`). Preflight takes the count only when it
   equals the day's count left, so a guess or a value from an earlier day is refused. With 0
   tokens left the message says the budget is spent and offers no command: every run would be
   blocked, so no class session starts that day.
   The `token budget` line then ends "started knowingly with ACCEPT_TOKENS_LEFT=...", the canary
   runs, and the class session starts and ends the open one. The cap stays as it is.
3. Plan the day against the count left. The comment of `budgets.class_pass_tokens` in `pack.yaml`
   holds the measured worker tokens of 25 October 2026: 394,313 for a run-through of every core demo
   (126,761 with the planted halves off, 267,552 with them on), 10,240 for the class finale, and
   12,395 for the safeguard finale. Only worker runs count: the experiments and the analyzer team
   on the Improve page run outside the worker.
4. With less left than a run-through and both finales, cut the planted half of the unbounded rows demo in
   Section 1 first: alone it took 182,654 to 187,030 tokens in every recorded run
   ([Section 1 evidence](evidence/section-1-agent-loop.md)). Then run no demo twice, and cut the
   optional demos.
5. Read "Tokens today" on the status line at each break, and keep the two finales' tokens for
   Section 4.
6. When the cap is reached, every new run shows "Blocked by budget", the status line reads "Cap
   reached: new runs blocked", and the whole system drops to the report-only level. Show each
   demo that is left through its code walkthrough, say it did not run live, and run it on a later
   Eastern time day.

Next time, rehearse on an earlier Eastern time day (see the day before).

**A promotion that never finishes.** The finale's control says "... is approved, and its promotion
has not finished". The gate stopped part way, the active version changed since the gate, or a
reset deleted the experiment the gate recorded as its baseline. When the Improve page shows no
request running, press Improve > Run experiment on the candidate again (its gate then decides),
or run `make reset NAME=hill-climbing-loop`.

**No credits left.** The OpenAI account refuses every call with the Hypertext Transfer Protocol
(HTTP) status 429. Stop live work, ask the operations team to add credits, then reset and run the
same trigger again.

A reset that says "not reset" names the request the hill-climbing runner is still running: the
reset would delete the experiment that request still writes to. When LangSmith refuses traces for
its monthly limit, a run's trace link opens a page that never fills
([costs page](costs.md#langsmith-traces)). Say so once, point at the live stamp's start time and
the run id `make demo` prints as the evidence, skip the trace list step of the candidate
experiment, and point at the holdout ledger instead: it is scored locally either way.

There is no recording, and nothing is shown again from a saved run. Every result on screen
carries a live stamp; point at it once per section. The `demo/expected/` folders are for learners
after class and are never opened in class.

## After class

- Collect the questions marked Thursday from the chat for [the review session](review-session.md).
- Record the minutes each block took, against the times above.
- Write each section's `session-notes.md` from the real class run.
- Stop the services, the hill-climbing runner among them, with `make down`; the database volume
  is kept.
- Re-run calibration before the next cohort.

### Publishing the solutions for the Thursday review

The four `solution/` folders are on no branch of the published repository, until the review
starts. They stay in the course's private source repository, on its `dev` branch, and the course
owner publishes them to the published `main` branch at 0:00 of
[the review session](review-session.md). Steps 1 to 4 take no model call; run them in the hour
before the review, then steps 5 and 6 at 0:00. In Ubuntu on WSL2:

1. Make a fresh clone of the published `main` branch:
   `git clone https://github.com/ANI-IN/loop-engineering.git <clone>`.
2. From the private source repository, build the release into the clone, with the solutions:
   `uv run python platform/scripts/build_release.py --repo . --ref dev --with-solutions --deny <word> --into <clone>`,
   with one `--deny <word>` for each of the deny words in the private release checklist. The
   build runs the published tree's strict style check and unit tests, prints
   `solutions published: N files` and `staged in <clone>`, and fails on any problem: fix it on
   `dev` and build again.
3. Commit in the clone as a normal commit, with the identity of the course owner:
   `git -C <clone> commit -m "release: the four assignment solutions, for the Thursday review"`.
4. Run the continuous integration workflow's own steps on that commit:
   `make ci-local REPO=<clone>`. It reads committed history, so commit first; go on only when it
   exits with 0.
5. At 0:00, push without force: `git -C <clone> push origin main`. When the push is refused
   because `main` moved, start again from step 1; never force it.
6. Watch the continuous integration run of the push until it passes: `gh run watch`.

Every later release keeps `--with-solutions`: a release into a clone that already publishes the
solutions refuses to run without it, so a release never unpublishes them.
