# Thursday review session

> **Terms on this page**
>
> - **Live session**: Everything that runs between one `make preflight` and the next.
> - **Drift canary**: Three easy questions that must pass and two trap questions that must still fail.
> - **Live stamp**: A result's run start time and its LangSmith trace: a check prints the time in Coordinated Universal Time (UTC), the console in your local time.

The run sheet for the 120-minute review of the four assignments, held on the Thursday after the
class. The instructor runs it from this page; learners read it to see what the session covers.
Review time: the instructor's announcement in the class chat.
<!-- placeholder: the instructor fills in the Thursday review time -->

## How the session works

After the Sunday class, you attempt each assignment on your own and run its live check while you
work, `make check-assignment NAME=<slug>`, against the real stack with your own key. There is no
submission and no hidden grader. At the start of this session the instructor publishes the four
`solution/` folders. You compare them with your own work, and the class discusses them.

The session lasts exactly 120 minutes. Each assignment gets its own block, and each block runs its
own live check of the reference solution, from the solution just published. There is no combined
end-to-end run, and no check is shown from a saved output.

## Timetable

| Time | Segment |
|---|---|
| 0:00 to 0:05 | Publish; chat poll; start the Assignment 4: Hill-climbing loop check |
| 0:05 to 0:25 | Assignment 1: Agent loop (20 minutes) |
| 0:25 to 0:50 | Assignment 2: Verification loop (25 minutes) |
| 0:50 to 0:55 | Break |
| 0:55 to 1:22 | Assignment 3: Event loop (27 minutes) |
| 1:22 to 1:55 | Assignment 4 (33 minutes; its check started at 0:00) |
| 1:55 to 2:00 | Final project brief and close |

Minutes per part of each block:

| Part | Assignment 1 | Assignment 2 | Assignment 3 |
|---|---|---|---|
| Live done-when check of the reference solution | 3 | 5 | 4 |
| Walkthrough of 3 or 4 excerpts | 8 | 10 | 11 |
| Alternatives and volunteered learner approaches | 5 | 5 | 7 |
| Common mistakes | 2 | 3 | 3 |
| Questions | 2 | 2 | 2 |

| Part | Assignment 4 |
|---|---|
| Live done-when check of the reference solution, read from its terminal | 5 |
| Walkthrough of 3 or 4 excerpts | 14 |
| Alternatives and volunteered learner approaches | 8 |
| Common mistakes | 4 |
| Questions | 2 |

## Rules

- Each block runs its own live check of the reference solution:
  `make check-assignment NAME=<slug> TREE=$HOME/.datapilot/assignment-work/<slug>-reference PURPOSE=thursday-review`,
  on the copy made before the session (step 2 below). The check prints its cost estimate first,
  then `PASS` or `FAIL` per requirement with a trace link and a live stamp for each live step, then
  the actual cost. `PURPOSE=thursday-review` makes the first check on each stack start the
  review's own live session there, so the live stamps name it, never an older session.
- The checks of Assignments 1 to 3 run one after another on the check's own stack, the Compose
  project `datapilot-assignments` on ports 55433, 8100, and 8502. The Assignment 4 check runs at the
  same time on a stack of its own (below), so no two stacks ask for the same port.
- A check that stopped (exit 2) says why, such as a spent daily token budget or a kill switch
  engaged from outside. A correct solution can also read FAIL on a model-dependent line; the
  Assignment 4 FAIL line says when the cause is the rule set the model wrote. Either way, reset
  the check's own stack and run the same check again with the reset command the check printed:
  `uv run python -m datapilot.assignments reset <slug>`, with the project and port in front for
  the Assignment 4 stack (below). It acts on that stack only: it refuses the class stack's ports
  and any port its project does not publish. `make reset` resets the class stack.
- The walkthrough excerpts are listed below with their paths and line ranges. Everything else lives
  in each assignment's `solution/SOLUTION.md`.
- Questions beyond each slot go to a written list. The instructor answers them after the session
  and adds them to the [frequently asked questions](faq.md).
- A block that runs long shortens its alternatives first, never the live check or the walkthrough.
- The final rehearsal includes one timed dry run of the whole session.

## Before the session

1. Start a rehearsal session with `make preflight PURPOSE=rehearsal`, then rehearse each live
   check once on the reference solutions, with `PURPOSE=rehearsal` and a reset of the check's stack
   between. Rehearse the Assignment 4 check with the review's own project and ports, as in the
   opening below, so its stack is built and seeded before the day (two databases, about a minute
   each) and the first build does not fall inside the 0:00 slot. In the session itself every
   check runs again, live.
2. Make the four reference copies, which takes no model call:
   `make apply-solution NAME=<slug> VARIANT=reference FORCE=1` for each of `agent-loop`,
   `verification-loop`, `event-loop`, and `hill-climbing-loop`. `FORCE=1` replaces the copy the
   rehearsal left; without it, apply refuses to replace a folder.
3. Open the four `SOLUTION.md` pages and the excerpt files below in editor tabs, in block order.
4. Open three terminals: one for the Assignment 4 check, one for the other checks, one for resets.
5. Prepare the chat poll: "How far did you get on each assignment, and where did you get stuck?"
6. Just before 0:00, run `make preflight PURPOSE=thursday-review`. Its canary must pass. It starts
   the review's live session on the class stack, which the class console's status line shows; the
   checks start theirs on their own stacks.

## Opening (0:00 to 0:05)

- Publish the four `solution/` folders.
- Launch the chat poll.
- Start the Assignment 4 check of the reference solution in its own terminal, so its results are
  ready at 1:22. It runs the benchmark, so it is the longest and most costly check of the session.
  Give it its own Compose project, `datapilot-review`, and its own three ports, 55434, 8101, and
  8503, none of which the class stack (5432, 8000, 8501), the other checks' stack (55433, 8100,
  8502), or the tests' Postgres (55432) uses, so the other checks can rebuild their stack beside
  it:

```bash
COMPOSE_PROJECT_NAME=datapilot-review POSTGRES_PORT=55434 API_PORT=8101 CONSOLE_PORT=8503 \
  make check-assignment NAME=hill-climbing-loop TREE=$HOME/.datapilot/assignment-work/hill-climbing-loop-reference PURPOSE=thursday-review
```

- Its console is at `http://localhost:8503`. To reset its stack, give the same project and port:
  `COMPOSE_PROJECT_NAME=datapilot-review POSTGRES_PORT=55434 uv run python -m datapilot.assignments reset hill-climbing-loop`.
- Its own stack has no baseline in the new review session, so this first check runs the baseline
  experiment as well as the candidate. Measured on 23 October 2026 with two candidates, a check
  that shared its session's baseline took 15 and 22 minutes (two checks): about 1 minute for the
  build and the deterministic requirements, 6.5 to 7 minutes for the two analyzer team runs with
  their 56 dev runs, and 7 to 14.5 minutes for the candidate experiment and its re-runs. The
  baseline experiment adds one 82-run experiment, so a first check takes about 20 to 30 minutes,
  and at most about 38 counted from the one-candidate first check's 33. It ends before the 0:50
  break.
- If it is still running at 0:50, leave it running and read its result at the start of the
  Assignment 4 block; start no second check. A second check in the same session shares the
  baseline and takes 15 to 22 minutes.

## Assignment 1: Agent loop (0:05 to 0:25)

[Assignment page](../section-1-agent-loop/assignment/README.md).

| Part | Minutes | What happens |
|---|---|---|
| Live done-when check | 3 | `make check-assignment NAME=agent-loop` on the reference copy: questions with informal or misspelled names |
| Walkthrough | 8 | The excerpts below |
| Alternatives and learner approaches | 5 | The two alternatives in `SOLUTION.md`, then volunteers |
| Common mistakes | 2 | From `SOLUTION.md` |
| Questions | 2 | Overflow goes to the written list |

Walkthrough excerpts, in
`section-1-agent-loop/assignment/solution/reference/files/platform/src/datapilot/loop1_agent/extension.py`:

1. The score and the lookup: lines 74 to 100.
2. The working-method step: lines 145 to 152.
3. The unresolved tie, and recording each match in `assumptions`: lines 155 to 178.
4. The tie case live: the clarifying question that names both near-identical product names, in
   the check's output.

Point at in the trace: the lookup call before the query, and the match in the assumptions.

## Assignment 2: Verification loop (0:25 to 0:50)

[Assignment page](../section-2-verification-loop/assignment/README.md).

| Part | Minutes | What happens |
|---|---|---|
| Live done-when check | 5 | The check of the reference copy, about 4 minutes |
| Walkthrough | 10 | The excerpts below |
| Alternatives and learner approaches | 5 | The two alternatives in `SOLUTION.md`, then volunteers |
| Common mistakes | 3 | From `SOLUTION.md` |
| Questions | 2 | Overflow goes to the written list |

The live check is `make check-assignment NAME=verification-loop`: the ambiguity suite, the leak
cases, and an approved export, the longest of the three blocks' checks.

Walkthrough excerpts, under
`section-2-verification-loop/assignment/solution/reference/files/platform/src/datapilot/loop2_verification/`:

1. The clarify-or-abstain grader: `graders/clarify_or_abstain.py`, lines 42 to 66.
2. How it decides a business term is defined: the same file, lines 19 to 40.
3. The personal-data leak grader and its exception for approved runs:
   `graders/personal_data_leak.py`, lines 21 to 48.
4. The registration, in stage order: `extension.py`, lines 14 to 19.

Point at: the questions that need clarification are in the ambiguity suite, not the class
benchmark.

## Break (0:50 to 0:55)

A 5-minute break. Read the result line of the Assignment 4 check in its terminal. If it reads
FAIL or STOPPED, keep that output on screen as the evidence, and start the same command again at
once: it shares this session's baseline, so it takes 15 to 22 minutes and ends by about 1:17,
before its block. In the block,
show both outputs and what the FAIL line says, such as a gate that blocked the rule set the model
wrote.

## Assignment 3: Event loop (0:55 to 1:22)

[Assignment page](../section-3-event-loop/assignment/README.md).

| Part | Minutes | What happens |
|---|---|---|
| Live done-when check | 4 | `make check-assignment NAME=event-loop` on the reference copy: the replayed job, a late order, the kill switch |
| Walkthrough | 11 | The excerpts below |
| Alternatives and learner approaches | 7 | The two alternatives in `SOLUTION.md`, then volunteers |
| Common mistakes | 3 | From `SOLUTION.md` |
| Questions | 2 | Overflow goes to the written list |

Walkthrough excerpts, in
`section-3-event-loop/assignment/solution/reference/files/platform/src/datapilot/loop3_events/extension.py`:

1. The schedule and the deterministic event id: lines 72 to 108.
2. The baseline query and the measurement: lines 37 to 46 and 111 to 132.
3. One alert per day, updated in place, with the kill switch checked first: lines 158 to 195.
4. The router table entry: line 33.

Point at: one alert after the replayed job, and its text changing after the late order.

Seasonality point for the alternatives slot: the comparison Fridays are 2, 9, 16, and 23 January
2026, and 2 January sits in the post-holiday dip, which lowers the baseline. Show the alternative
in `SOLUTION.md` that uses a median or holiday-aware baseline, and its trade-off: a holiday
calendar to maintain, and a median that still moves with three or four points. Ask who saw a
normal Friday flagged as an anomaly.

## Assignment 4: Hill-climbing loop (1:22 to 1:55)

[Assignment page](../section-4-hill-climbing-loop/assignment/README.md).

| Part | Minutes | What happens |
|---|---|---|
| Live done-when check | 5 | Read the check started at 0:00, and any second run |
| Walkthrough | 14 | The excerpts below |
| Alternatives and learner approaches | 8 | The two alternatives in `SOLUTION.md`, then volunteers |
| Common mistakes | 4 | From `SOLUTION.md` |
| Questions | 2 | Overflow goes to the written list |

The live check is the one started at 0:00, and its second run when the break started one: read
its promotion, its zero regressions, and the rule the critic dropped.

Walkthrough excerpts:

1. One repeat-customer item with its gold and naive queries:
   `section-4-hill-climbing-loop/assignment/solution/reference/files/platform/packs/datapilot_us/benchmark/repeat_customers.yaml`,
   lines 9 to 35.
2. The trap-sensitivity test: `section-4-hill-climbing-loop/assignment/check.py`, the function
   `_traps`.
3. The critic's guidance:
   `section-4-hill-climbing-loop/assignment/solution/reference/files/platform/src/datapilot/loop4_hill_climbing/extension.py`,
   lines 19 to 24.
4. The minimum-holdout rule: the same file, lines 35 to 36, and the class eligibility it plugs
   into, `platform/src/datapilot/loop4_hill_climbing/eligibility.py`, lines 33 to 45; the
   confirmed standard that follows it is `confirmed_clearance` in the same file.

Point at: the critic's drop decision with its reason, and the gate verdict with zero regressions.

## Final project brief and close (1:55 to 2:00)

- Introduce the [final project](../final-project/README.md): your own dataset, at least three
  original traps, your own benchmark with splits, one extension, and a before-and-after report.
- Say where the written answers will appear: the [frequently asked questions](faq.md).
- Thank the class and close on time.
