# Thursday review session

> **Terms on this page**
>
> - **Live session**: Everything that runs between one `make preflight` and the next.
> - **Drift canary**: Three easy questions that must pass and two trap questions that must still fail.
> - **Live stamp**: A result's run start time in your local time and its LangSmith trace link.

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
<!-- provisional: make check-assignment and make apply-solution land with the assignments merge -->

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
| Live done-when check of the reference solution | 3 | 3 | 4 |
| Walkthrough of 3 or 4 excerpts | 8 | 10 | 11 |
| Alternatives and volunteered learner approaches | 5 | 7 | 7 |
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
  `make apply-solution NAME=<slug> VARIANT=reference`, then
  `make check-assignment NAME=<slug> TREE=$HOME/.datapilot/assignment-work/<slug>-reference`, the
  copy the first command prints. The check prints its cost estimate first, then `PASS` or `FAIL`
  per requirement with a trace link and a live stamp for each live step, then the actual cost.
- A failed check is reset and run again: `make reset NAME=<slug>`, then the same check.
- The walkthrough excerpts are listed below with their paths and line ranges. Everything else lives
  in each assignment's `solution/SOLUTION.md`.
- Questions beyond each slot go to a written list. The instructor answers them after the session
  and adds them to the [frequently asked questions](faq.md).
- A block that runs long shortens its alternatives first, never the live check or the walkthrough.
- The final rehearsal includes one timed dry run of the whole session.

## Before the session

1. Start a rehearsal session with `make preflight PURPOSE=rehearsal`, then rehearse each live
   check once on the reference solutions, with a reset between. In the session itself every check
   runs again, live.
2. Open the four `SOLUTION.md` pages and the excerpt files below in editor tabs, in block order.
3. Open three terminals: one for the Assignment 4 check, one for the other checks, one for resets.
4. Prepare the chat poll: "How far did you get on each assignment, and where did you get stuck?"
5. Just before 0:00, run `make preflight PURPOSE=thursday-review`. Its canary must pass, and it
   starts the review's own live session; the console's status line shows its start time.

## Opening (0:00 to 0:05)

- Publish the four `solution/` folders.
- Launch the chat poll.
- Start the Assignment 4 check of the reference solution in its own terminal, so its results are
  ready at 1:22. It runs the benchmark, so it is the longest and most costly check of the session.
  Give it its own Compose project and ports, so the other checks can rebuild their own stack
  beside it:

```bash
make apply-solution NAME=hill-climbing-loop VARIANT=reference
COMPOSE_PROJECT_NAME=datapilot-review POSTGRES_PORT=5433 API_PORT=8001 CONSOLE_PORT=8502 \
  make check-assignment NAME=hill-climbing-loop TREE=$HOME/.datapilot/assignment-work/hill-climbing-loop-reference
```

<!-- provisional: the wall time of the Assignment 4 check is measured in the Thursday dry run -->

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
2. The working-method step: lines 128 to 133.
3. Recording each match in `assumptions`, and the unresolved tie: lines 136 to 160.
4. The tie case live: the clarifying question that names both near-identical product names, in
   the check's output.

Point at in the trace: the lookup call before the query, and the match in the assumptions.

## Assignment 2: Verification loop (0:25 to 0:50)

[Assignment page](../section-2-verification-loop/assignment/README.md).

| Part | Minutes | What happens |
|---|---|---|
| Live done-when check | 3 | `make check-assignment NAME=verification-loop` on the reference copy: the ambiguity suite, the leak cases, an approved export |
| Walkthrough | 10 | The excerpts below |
| Alternatives and learner approaches | 7 | The two alternatives in `SOLUTION.md`, then volunteers |
| Common mistakes | 3 | From `SOLUTION.md` |
| Questions | 2 | Overflow goes to the written list |

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

A 5-minute break. Check that the Assignment 4 check is still running in its terminal.

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
| Live done-when check | 5 | Read the check started at 0:00: promotion, zero regressions, the rejected rule |
| Walkthrough | 14 | The excerpts below |
| Alternatives and learner approaches | 8 | The two alternatives in `SOLUTION.md`, then volunteers |
| Common mistakes | 4 | From `SOLUTION.md` |
| Questions | 2 | Overflow goes to the written list |

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
