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

How to run the four-hour live class of Module: Loop Engineering, on an agent that turns
questions into Structured Query Language (SQL), a text-to-SQL agent. Every demo is live, on
gpt-6-luna, with the class key. When a demo stalls, you reset its section and run it again:
`make reset NAME=<section slug>`, then the same trigger. The times on this page are the times in
`slides/outline.md`; the cues come from `platform/demos/registry.yaml` and the DEMO slides'
speaker notes.

## Class-day cheat sheet

| Time | Block | What you do |
|---|---|---|
| 0:00-0:10 | Opening | Full screen; welcome, the insight, the four loops, the five traps |
| 0:10-0:25 | Designing text-to-SQL | Why warehouses are hard, the nine stages, the design decisions; no demo |
| 0:25-1:03 | Section 1: Agent loop | Concept and code slides to 0:38; three demos, code to 0:53; evidence to recap |
| 1:03-1:45 | Section 2: Verification loop | Concept and code slides to 1:17:30; demos, code to 1:35:30; evidence to recap |
| 1:45-1:55 | Break | Write the return time in the chat; reset the event loop |
| 1:55-2:50 | Section 3: Event loop | Concept and code slides to 2:14; demos and a reserve to 2:38; evidence to recap |
| 2:50-2:55 | Poll | Start the baseline experiment first, then launch the Zoom poll |
| 2:55-3:05 | Break | Queue the naive analyzer behind the baseline: `make demo NAME=improve-naive-analyzer-blocked PLANTED=1` |
| 3:05-3:48 | Section 4: Hill-climbing loop | Start the chain on the opener, about 3:07; demos 3:19-3:34; evidence to recap |
| 3:48-4:00 | Closing | The four loops, ten insights, the design checklist, Monday, assignments, sources |

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
the demo slug for the demo on screen. A reset takes about 7 seconds (6.4 to 6.9 measured on 26
October 2026). Never run `make preflight` during class: it starts a new
live session, and the baseline experiment from the poll belongs to the class session.

The baseline is safe across a reset: `make reset NAME=hill-climbing-loop` clears the candidate and
the knowledge state, keeps the session's baseline experiment, and prints what it kept with its
start time. The full reset, `make reset-discarding-baseline NAME=hill-climbing-loop`, also
discards the baseline. Use it only as a deliberate choice, never to recover a demo in class: the
console then needs a new baseline from the open session. Both first copy every experiment,
decision, and version they delete or retire into the reset archive, and say how many rows;
`make archive` and `make archive-show NAME=<experiment id>` read it back.

Cut first, in this order: the optional demos, then the length of the code walkthrough. Never cut
a core demo or a core concept slide.

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
   restarts; 41 seconds in both measured runs) and each promotion after approval: Section 3's
   timetable needs the first, Section 4's the second.
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
the worker is restarted without the flag at once. The planted half was measured twice, 41
seconds both times; time it again in rehearsal (step 4 of the day before). A live check and the finale refuse to start while `.env` or
a running service has a flag on, and name it: set it to 0 in `.env`, then `make up`.

### Opening (0:00-0:10)

| Time | Slide | What you do |
|---|---|---|
| 0:00-0:00:30 | Module: Loop Engineering | The title |
| 0:00:30-0:01:30 | Your instructor | Your name; one line from everyone in the chat |
| 0:01:30-0:03 | Why agents fail in production | Four failure classes, one number each |
| 0:03-0:05 | The four loops on one map | Walk the map |
| 0:05-0:07:30 | The agent answered. The answer was wrong. | 72,394,572.08 against 64,015,091.21 dollars; three traps on the query |
| 0:07:30-0:09 | One question, five traps no column states | The breakdown of the 0 of 99 trap-question runs |
| 0:09-0:10 | How the class runs | Sections, breaks, the poll; every demo live; reset and run again |

### Designing text-to-SQL (0:10-0:25)

| Time | Slide | What you do |
|---|---|---|
| 0:10-0:12 | Business knowledge decides the answer; check it like code | Internal accounts move the answer by 1,577,441.23 dollars; the SEED audit |
| 0:12-0:14 | Why questions over a real warehouse are hard | Four reasons, with the benchmark figures |
| 0:14-0:18 | Nine stages from question to checked answer | Walk the nine stages and DataPilot's part in each |
| 0:18-0:20:30 | Design decisions: rules, generation, and clarification | Where rules live; one shot or an agent; assume, ask when a term has no rule |
| 0:20:30-0:23 | Design decisions: schema, permissions, cost, and evaluation | Schema at scale, each user's access, cost, execution match on two databases |
| 0:23-0:25 | Build or buy: semantic layers and warehouse assistants | What buying gives; what this approach adds |

No demo runs in this block: keep the console on the Agent page, ready for Section 1.

### Section 1: Agent loop (0:25-1:03)

| Time | Slide or demo | What you do |
|---|---|---|
| 0:25-0:26 | Section opener | Two design questions: what the tools show, how much they return |
| 0:26-0:27:30 | Insight: what the tools show decides the answer | 68.3 percent schema-linking failures (pooled schema); 12 against 17 of 21 |
| 0:27:30-0:29:30 | Story: one tool result used three run budgets | Run 199d2188, 184,983 tokens against a 60,000 budget, checked before each call |
| 0:29:30-0:31:30 | Concept: the agent loop diagram | Walk it left to right |
| 0:31:30-0:33:30 | Mechanism: describe_table | Names only against types, samples, distinct values; what LangChain gives |
| 0:33:30-0:35:30 | Mechanism: format_result | Row cap 50, value cap 2,000 characters, the count, the notice |
| 0:35:30-0:38 | Mechanism: the analyst | Knowledge on every call, 12 and 16 call limits, the envelope |
| 0:38-0:41 | The simple question | Status line; type "How many orders have been placed in total?", Agent > Ask, or `make demo NAME=agent-simple-question` |
| 0:41-0:46 | The confident wrong answer | Agent > Ask the spine question, or `make demo NAME=agent-confident-wrong-answer`; leave a held run held |
| 0:46-0:50 | Unbounded rows | `make demo NAME=agent-unbounded-rows PLANTED=1`, then Agent > Run large query |
| 0:50-0:53 | Code walkthrough | The analyst's prompt and limits, then the tools' result formatting |
| 0:53-0:54 | Buffer | Texas last quarter only if the core demos ended early |
| 0:54-0:56 | Evidence | 12 against 17 of 21; tokens 3,738 against 4,857 |
| 0:56-0:58:30 | Design callout | Retrieve and describe tables on demand; value lookup (Assignment 1: Agent loop) |
| 0:58:30-1:00 | Apply it | Five changes for next week |
| 1:00-1:01:30 | Pitfalls | No cap in the tool, asking whenever unsure, prose answers; measure the scout |
| 1:01:30-1:03 | Recap and question | The final query and the assumptions |

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
- Optional, cut first: Texas last quarter, `make demo NAME=agent-texas-last-quarter`, only in the
  1-minute buffer, 0:53-0:54, when the core demos ended early.

Retries: the core demos keep their slots, 0:38-0:41, 0:41-0:46, and 0:46-0:50, and the code
walkthrough runs 0:50-0:53. A retry that would end after 0:53 takes the code walkthrough's time;
after 0:54, no retry: name the moment for the Thursday review and go on.

### Section 2: Verification loop (1:03-1:45)

| Time | Slide or demo | What you do |
|---|---|---|
| 1:03-1:04 | Section opener | Checks flag wrong answers; they do not fix them: 0 of 40 either way |
| 1:04-1:05:30 | The product name that said delete | Illustrative: the three demo statements pass a first-word guard |
| 1:05:30-1:08:30 | The verification layers, in order | Walk the diagram: seven graders, the executor, the exits, the reviewer last |
| 1:08:30-1:11 | Allowlist the shape | Root check, walk every node, a reason back |
| 1:11-1:13 | Grants are walls | 25006 from the transaction, 42501 from the grants; a refused write ends the run |
| 1:13-1:15 | A stop the model cannot argue with | The cap of 3 in code; 9 to 13 attempts without it |
| 1:15-1:17:30 | Same knowledge, same blind spot | The reviewer approved 19 of 40 wrong answers |
| 1:17:30-1:21:30 | Malicious SQL | `make reset NAME=verification-loop`; `make demo NAME=verify-malicious-sql PLANTED=1`, then Verify > Send malicious SQL |
| 1:21:30-1:25:30 | The retry cap | `make demo NAME=verify-retry-cap PLANTED=1`, then Verify > Inject failing grader |
| 1:25:30-1:29:30 | Every grader passes, still wrong | Verify > Ask the spine question, or `make demo NAME=verify-graders-pass-still-wrong` |
| 1:29:30-1:35:30 | Code walkthrough | The checker, the statement policy, the retry cap; the cost guard only if ahead |
| 1:35:30-1:38 | Evidence | 0 of 40 right either way; 20 flagged against 1; 9,311 against 17,344 tokens |
| 1:38-1:40 | Design callout | Validate before, while, and after the query runs; gold on two databases |
| 1:40-1:41:30 | Apply it | Five checks for next week |
| 1:41:30-1:43:30 | Pitfalls | Four layers that trusted the one above |
| 1:43:30-1:45 | Recap and question | Benchmark questions: the gold check; new questions: the rule or a person |

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

Retries: a retry takes time from the code walkthrough, 1:29:30-1:35:30. After 1:33, do not retry
any demo: name the moment and go on.

### Break (1:45-1:55)

| Time | Slide | What you do |
|---|---|---|
| 1:45-1:55 | Time for a Break | Return time in the chat; `make reset NAME=event-loop`; read Tokens today on the status line |

Write the return time, the local time 10 minutes from now, in the chat. Run
`make reset NAME=event-loop` during the break.

### Section 3: Event loop (1:55-2:50)

| Time | Slide or demo | What you do |
|---|---|---|
| 1:55-1:56 | Section opener | Work that runs twice, waits in memory, or ignores a stop |
| 1:56-1:59 | Insight: every planted bug failed every run | The failures were in delivery, state, and control, not the model |
| 1:59-2:01:30 | Story: two digests for one day | Without a stored event key, repeats became two digests |
| 2:01:30-2:04:30 | The event pipeline diagram | Router, queue, approval, kill switch |
| 2:04:30-2:07:30 | Code: insert once, route, claim with a lease | The code walkthrough, part 1 |
| 2:07:30-2:11 | Code: the approval checkpoint | The code walkthrough, part 2: a pending approval kept in Postgres |
| 2:11-2:14 | Code: the kill switch | The code walkthrough, part 3: the check before every step |
| 2:14-2:17 | The webhook question | Events > Send webhook question, or `make demo NAME=events-webhook-question` |
| 2:17-2:23 | The approval that survives a restart | `make demo NAME=events-approval-survives-restart PLANTED=1`, `make reset NAME=event-loop`, then Events > Request California export |
| 2:23-2:27 | Duplicate events | `make demo NAME=events-duplicate-events PLANTED=1`, `make reset NAME=event-loop`, then Events > Send the same event three times |
| 2:27-2:33 | The kill switch in flight | `make demo NAME=events-kill-switch-in-flight PLANTED=1`, `make reset NAME=event-loop`, `make demo NAME=events-kill-switch-in-flight`, `make reset NAME=event-loop` |
| 2:33-2:36 | The digest now (optional, cut first) | `make demo NAME=events-digest-now` |
| 2:36-2:38 | Reserve | One reset and run again, or questions |
| 2:38-2:40 | Evidence table | Each planted bug failed every time; each fix held |
| 2:40-2:43 | Design callout | From events: hold queries that read personal data |
| 2:43-2:45 | Apply it | Five checks for next week |
| 2:45-2:47:30 | Pitfalls | Three that pass every unit test; a row cap is not a size cap |
| 2:47:30-2:50 | Recap and the question | Three points; the resent export across a restart: one waits. Remaining questions |

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
  new run at claim: **`make reset NAME=event-loop` after each half**, the second before the
  evidence slide, or the finale is blocked too.
- Optional, cut first: the digest now, `make demo NAME=events-digest-now`.

Retries: a retry spends the 2-minute reserve, 2:36-2:38, then the 3 minutes of the optional
digest demo. Start no retry after 2:36: skip it, say so, and name that demo for the Thursday
review.

During the recap and the questions, check that the status line's button reads Kill switch, not
Release kill switch.

### Poll (2:50-2:55)

| Time | Slide | What you do |
|---|---|---|
| 2:50-2:55 | Live Zoom Poll | Start the baseline experiment first, then the poll; read the result aloud |

First start the baseline experiment: Improve > Run experiment on the active version, or
`make demo NAME=improve-baseline-experiment`. It is the class session's baseline; the console
accepts no baseline from another session, so never skip this step. Then launch the Zoom poll:
"Which autonomy level would you grant the revenue digest today, and why?", with the report-only,
assisted, and unattended levels as options. Read the result aloud before the break.

### Break (2:55-3:05)

| Time | Slide | What you do |
|---|---|---|
| 2:55-3:05 | Time for a Break | Return time in the chat; queue the naive analyzer; check the progress strip once |

Write the return time, the local time 10 minutes from now, in the chat. The baseline experiment
keeps running at concurrency 8
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
3:01 in most runs; if it is not there at 3:06, it may still be behind the baseline: read the
baseline, keep talking, and look again at 3:07. The flag was on for those two requests alone, so the
analyzer team runs in Section 4 with nothing to switch back.

### Section 4: Hill-climbing loop (3:05-3:48)

| Time | Slide or demo | What you do |
|---|---|---|
| 3:05-3:08 | Section opener | Read the baseline and the naive verdict; start the chain about 3:07 |
| 3:08-3:10:30 | Problem story | The over-broad rule: 9 confirmed regressions; the chain runs |
| 3:10:30-3:13:30 | The hill-climbing loop diagram | The gate's conditions in order; the honest caveat about the holdout |
| 3:13:30-3:16:30 | Mechanism: the analyzer team and the overfit guard | The chain runs |
| 3:16:30-3:19 | Mechanism: the gate's decide function | The chain runs |
| 3:19-3:34 | Demo: the diff, the candidate ledger, approval, the unattended level, the finale | Steps 3 to 5 below; the safeguard if the gold check fails |
| 3:34-3:36:30 | Evidence chart | Every promotion, on 15 holdout questions |
| 3:36:30-3:39 | Insight: the naive analyzer's history | 15 of 15, then the fourth condition, then 6 of 6 blocked |
| 3:39-3:41 | Insight: autonomy per metric family | Read the poll's result back |
| 3:41-3:43 | Design callout | Where rules live; execution match |
| 3:43-3:45 | Apply it | Six steps |
| 3:45-3:47 | Pitfalls | Four, from our runs |
| 3:47-3:48 | Recap and question | 15 of 15 with copied rules: promoted? No |

The chain needs more machine time than the 15-minute demo slot, so it starts on the opener.
Measured over every recorded run, 23 to 25 October 2026
([evidence](evidence/section-4-hill-climbing-loop.md#results)):

| Step | Measured machine time | Where it runs |
|---|---|---|
| The baseline experiment | 236 to 386 seconds | From the poll, done by about 2:54 to 2:57 |
| The naive analyzer and its candidate experiment | 211 to 580 seconds | Queued at the break, done by about 3:01 in most runs |
| The analyzer team, two candidates | 326 to 377 seconds, five runs | In the block |
| The candidate experiment | 171.3 to 459 seconds; 404 and 459 at analyzer reasoning effort high | In the block |
| The promotion after approval, with its clearance re-runs (measured once) | Active about 5 seconds after approval; re-runs done about 50 seconds after it | In the block |
| The finale after a promotion, from its first send | 50 to 162 seconds when held for the clearance re-runs | In the block |
| The finale on the class-day safeguard | 19 and 21 seconds | Only if the safeguard is used |

Started at about 3:07, the analyzer team ends by about 3:13 (326 to 377 seconds), during slides
57 and 58. The candidate experiment follows during slides 58 to 60, and the gate reads about
3:15 to 3:21: the 459 seconds at the top of its range ran at analyzer reasoning effort high, and
`pack.yaml` runs the analyzer team at medium. In the class run-through of 25 October 2026 the
two took 362 + 237 seconds, about 10 minutes. Approval, the promotion's clearance re-runs, and
the finale (50 to 162 seconds after its first send in 8 recorded runs) follow, so the last run
lands about 3:20 to 3:24. A fresh chain needs about 8 to 14 minutes to the gate, so after 3:24
do not restart it: say so, go to the evidence slide, and report the class run at the Thursday
review. If the gate blocks the class candidate, leave the verdict on screen and go to the
evidence slide (no safeguard). A hill-climbing reset refuses while the runner serves a request
(it says "not reset"); otherwise it takes about 7 seconds. To end a running request:
`docker compose stop hill-climbing-runner`, then `make reset NAME=hill-climbing-loop`, then
`docker compose start hill-climbing-runner`, about 20 seconds in all (stop 11.0, reset 6.6,
start 2.9, timed with no request running on 26 October 2026; rehearse it once with one
running). Never restart the runner instead: a restarted runner keeps serving, so the reset
refuses again. The plan:

1. On the opener, from 3:05: read the baseline's holdout ledger (2 of 15), then the naive
   analyzer's blocked verdict. Both ran before the block. If no verdict shows at 3:06, read the
   baseline, keep talking, and look again at 3:07. If the reset prints "not reset", the naive
   request is still running: never reset mid-request; wait until the Improve page shows it
   finished, or, if it has not finished by 3:08, end it with the stop, reset, and start above.
   Then `make reset NAME=hill-climbing-loop`: it
   keeps the baseline and clears the naive candidate, so the Improve page shows the analyzer
   team's candidate next.
2. About 3:07: Improve > Run analyzer, then at once Improve > Run experiment on the candidate.
   The runner runs the experiment as soon as the team's candidate is written, on that candidate.
   Teach slides 57 to 60 while the chain runs. If the baseline never started, at 3:06 reset, press
   its trigger, then at once the two buttons: the runner takes them in order, so the gate reads
   about 4 to 6 minutes later than planned, still inside the demo slot. If it has not read by
   3:30, go on to the evidence slide and return to it.
3. At 3:19, on the demo slide: the analyzer team's diff, then the candidate's ledger against this
   session's baseline. If the team is still writing at 3:19, say: two analyzer runs and 50
   development runs are in flight. If the gate has not read at 3:19, say: 70 benchmark runs
   are still in flight, and a confirming re-run lengthens them. If the experiment confirms
   apparent regressions and runs long, narrate the cues below, and come back for the approval.
   If it stalls, the request reads as running and the reset refuses: end it with the stop,
   reset, and start above, then Run analyzer and Run experiment on the candidate, but never
   after 3:24.
4. Approve when the gate reads ready; an approval given earlier waits for the gate. Wait for the
   promotion: as soon as the Improve page says the
   version is the active version, set the unattended level (Improve > Set the unattended level);
   every reset sets the report-only level. Then wait for the clearance re-runs:
   the note above the Events buttons goes away and Send webhook question turns on. The status
   line then names the families cleared or, when the promotion cleared none, reads Not cleared
   for every family: the finale then posts at the assisted level, a correct outcome.
5. Send the finale. From the promotion on, Send webhook question sends the fiscal year 2025 revenue
   question, whether a family cleared or none did. If it is still held at 3:34, go on to the
   evidence slide and come back for it.

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
- **The candidate experiment.** Already queued at about 3:07, with the analyzer; trigger it only if it
  never started (Improve > Run experiment on the candidate, or
  `make demo NAME=improve-candidate-experiment`): a second press queues a second 70-run experiment
  on the same candidate. Approve when the gate reads ready; an approval given earlier waits for
  the gate. Point at the
  flips against this session's baseline, zero regressions, then the LangSmith trace list of
  `datapilot-experiments` filtered by knowledge version. **Then wait for the promotion.** Approval
  only marks the version approved; the runner then makes it active and runs the clearance
  re-runs: the finale posted 50 to 162 seconds after its first send when held for them, in 8
  recorded runs. The Improve page says the version is the active version
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

### Closing (3:48-4:00)

| Time | Slide | What you do |
|---|---|---|
| 3:48-3:49:30 | The four loops together | What each loop cannot do alone |
| 3:49:30-3:51:30 | Ten insights to take away | Each with the section whose runs proved it |
| 3:51:30-3:53:30 | Designing text-to-SQL for your warehouse | Ten steps, each with the part of the course that teaches it |
| 3:53:30-3:55 | Use it on Monday | Six actions for the learner's own agent, each under an hour |
| 3:55-3:56:30 | Assignments, final project, and the Thursday review | The deadline in the class chat; solutions when the review starts |
| 3:56:30-3:57:15 | Sources: agent design | Every bracketed number on a slide points to these four pages |
| 3:57:15-3:58 | Sources: verification and research | The sources of Section 2 and the design segment |
| 3:58-3:58:45 | Sources: event-driven systems and products | The sources of Section 3 and the build-or-buy slide |
| 3:58:45-4:00 | Sources: products and the course's evidence | The last questions in the chat; close at 4:00 |

## If something breaks

| What you see | What to do |
|---|---|
| A demo shows the wrong moment or stalls | Reset and run it again: `make reset NAME=<section slug>`, then the same trigger |
| A model call fails or is rate limited | Wait for the retry; if it still fails, reset and run it again |
| The OpenAI API is down | Say so, show the code walkthrough, and return to the demo when the API answers |
| The Improve page does not move | `make logs NAME=hill-climbing-runner`, then `make up` if it stopped |
| The hill-climbing reset says "not reset" | Wait for the request to finish, or stop the runner, reset, start it (Section 4) |
| A run moves to Blocked by kill switch outside Section 3 | Status line > Release kill switch, or `make reset NAME=event-loop`; then the same trigger |
| Send webhook question is off, or `make demo` says "not sent" | Do the step the message names, then the same trigger |
| A planted half shows no change | It was sent without `PLANTED=1`: `make demo NAME=<demo> PLANTED=1` |
| A check or the finale says it does not start while planted flags are on | Set each flag it names to 0 in `.env`, then `make up` |
| The console says "No baseline run in this session yet." | Start the baseline experiment now, as it offers |
| The console says "No live session." | `make preflight PURPOSE=class` once, then the baseline again; a refusal: next row |
| `make preflight PURPOSE=class` refuses for the day's token budget | See "The token budget refusal" below |
| LangSmith refuses traces: a trace link never fills | The live stamp's start time, and the run id `make demo` prints, are the evidence; see below |
| A service is down | `make ps`, then `make up`; the queue and pending approvals survive in Postgres |
| A section runs long | Cut its optional demo, then shorten its code walkthrough |
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
reset would delete the experiment that request still writes to. Wait for it to finish, or end
it: `docker compose stop hill-climbing-runner`, `make reset NAME=hill-climbing-loop`, then
`docker compose start hill-climbing-runner`, about 20 seconds. Never restart the runner
instead: it keeps serving, and the reset refuses again. When LangSmith refuses traces for
its monthly limit, a run's trace link opens a page that never fills
([costs page](costs.md#langsmith-traces)). Say so once, point at the live stamp's start time and
the run id `make demo` prints as the evidence, skip the trace list step of the candidate
experiment, and point at the holdout ledger instead: it is scored locally either way.

There is no recording, and nothing is shown again from a saved run. Every result on screen
carries a live stamp; point at it once per section. Each demo's backup screenshot in
`demo/expected/` is shown only while a reset runs, never instead of a run. An optional demo
with no backup screenshot is cut rather than described.

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
