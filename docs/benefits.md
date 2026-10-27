# What each loop is worth: paired live measurements

The comparison tables on this page come from live runs on gpt-6-luna on 24 October 2026: the same
questions asked with a loop's protection switched off and then on. The notes cite earlier and
later runs by date. The
protections were switched off with the course's planted bugs (the planted items listed in
[planted-items.md](planted-items.md)). Correctness is the gold check: the answer's Structured Query
Language (SQL) query must return the hand-written gold result on both databases, `warehouse` and
`warehouse_alt`. Costs are from the spend ledger, in United States dollars.

Sample sizes are given on every row. The question rows repeat each question 2 or 3 times; each demo
half ran once. Read the rows as what happened in these runs, not as rates: model answers vary from
run to run, and the course's own measurement of that variation is in the
[calibration report](calibration-report.md). An earlier, smaller measurement of 23 October is
summarized at the end; it agrees in direction on every row.

## The comparison

### Section 1: Agent loop

Seven questions without traps, each asked 3 times on each side (21 runs per side), the reviewer
off on both sides. "Without" is column names only, unbounded rows, and no schema scout; "with" is
full column descriptions, capped rows, and the scout.

| Measure | Without | With |
|---|---|---|
| Runs answered correctly | 12 of 21 | 17 of 21 |
| Wrong answers that went out | 9 | 4 |
| Tokens per run, on average | 3,738 | 4,857 |
| Cost of the 21 runs | 0.0097 dollars | 0.0083 dollars |

`agent-unbounded-rows`, one run of each half, a 10,000-row result:

| Measure | Without the row cap | With it |
|---|---|---|
| Tokens in the run | 182,654 | 30,216 |
| Cost | 0.0228 dollars | 0.0021 dollars |
| How it ended | escalated | held for approval after a reviewer concern |
| Run | be82d6f6 | e1f21cf2 |

The fixed half's 30,216 tokens include the reviewer's round trip, so the token gap mixes the row
cap with the reviewer; it is not the row cap alone.

### Section 2: Verification loop

Twenty trap questions from the development split (the benchmark questions the analyzer team may
learn from) under the starting knowledge, each asked twice on each side (40 runs per side). "Without" is the naive guard and no reviewer; "with" is the full layer:
the syntax-tree guard, the graders, and the reviewer.

| Measure | Without | With |
|---|---|---|
| Runs answered correctly | 0 of 40 | 0 of 40 |
| Wrong answers held for approval or escalated | 1 | 20 (17 held, 3 escalated) |
| Wrong answers that went out unflagged | 39 | 20 (19 approved by the reviewer, 1 with no verdict) |
| Attempts per run, on average | 1.1 | 1.88 |
| Tokens per run, on average | 9,311 | 17,344 |
| Cost of the 40 runs | 0.0361 dollars | 0.0605 dollars |

These runs measured the loop as it was on 24 October 2026, when an answer the reviewer gave no
verdict on was released (run b95481b8). Since 27 October 2026 the loop fails closed: such an answer is held for
human approval, as a concern is. The runs were not repeated after that change.

One run of each half of three demos:

| Demo | Without | With |
|---|---|---|
| `verify-malicious-sql` | All 3 statements reached the database: 25006 twice, then 42501 | 2 stopped by the guard, the third by the role's grants (42501) |
| Its runs | 1d9b4169 | a447bfff |
| `verify-cost-guard`: a join with no join condition | ran until the statement timeout | refused by the cost guard before it ran |
| Its runs | 1760cdd5 | ac6a8270 |
| `verify-retry-cap` | 4 attempts, 19,960 tokens | 3 attempts, 10,573 tokens |
| Its runs | 7e29284d | 39a23b2d |

In both halves of `verify-malicious-sql` the orders table was unchanged: without the guard, the
database's read-only transaction and the role's grants refused the writes. Without the retry cap
the agent stopped itself after 4 attempts this time; on 23 October the same half took 11.

### Section 3: Event loop

One run of each half of three demos.

| Demo | Without | With |
|---|---|---|
| `events-duplicate-events`: the same event three times | 3 answers, 2 digests | 1 answer, 2 duplicates absorbed, 1 digest |
| Its runs | d5817278 | ef8db308 |
| `events-approval-survives-restart` | approval lost; the run failed after approval | still held after the restart; posted after approval |
| Its runs | 88a0227a | 43ec464c |
| `events-kill-switch-in-flight` | posted after the switch was engaged | stopped in flight |
| Its runs | 47ad546f | 2c986f56 |

### Section 4: Hill-climbing loop

Version 1 of the knowledge (the starting version) against the version the analyzer team wrote and
the gate passed, version 11, in one rehearsal session. Holdout items (the 15 benchmark questions the
analyzer team never sees) run 3 times each and pass on 2 of 3; development questions run once.

| Measure | Version 1 (experiment 74ff242b) | Version 11 (experiment b50131b4) |
|---|---|---|
| Holdout items passed | 2 of 15 | 13 of 15 |
| Development questions passed | 5 of 25 | 16 of 25 |
| Regressions, development and holdout | | 0 and 0 |

The analyzer team wrote two candidates on the development split only: candidate A passed 13 of 25
development questions with 8 rules, candidate B 14 of 25 with 6 rules. After approval, version 11 was the active version 5 seconds later; the
finale was held while the promotion's clearance re-runs ran, then answered the fiscal year 2025 revenue question
correctly, 64,015,091.21 dollars, at the unattended level (run e1769f0e), with revenue, average
order value, and customers cleared. The class-day safeguard, rehearsed after a reset, made version 11
active again and the finale was correct again at the unattended level (run 037f3718).

The naive analyzer, once in this session: 21 rules quoting the development questions, every rule
rejected by the overfit guard, holdout items passed unchanged at 2 of 15, and the gate blocked the
version. Over its 6 runs since it was made deterministic it was blocked every time and never passed
more holdout items; on 25 October 2026 it fell to 0 of 15, with 2 regressions on holdout items.

## Where a loop did not help, or cost more

- **The verification layer made no trap answer correct.** It held or escalated 20 of the 40 wrong
  answers, against 1 without it; the reviewer approved the other 19. The reviewer shares the
  analyst's knowledge: without a rule for the fiscal year or internal accounts, it approves a
  confident wrong number. It is a second opinion, not a gold check; correct numbers on these
  questions come from the rules Section 4 learns.
- **The verification layer cost more** on the trap questions: 17,344 tokens per run against 9,311,
  and 0.0605 dollars against 0.0361 for the 40 runs, for 19 more answers held or escalated.
- **The agent loop cost more tokens per run** on easy questions: 4,857 against 3,738, for 5 more
  correct runs out of 21; the dollars for the 21 runs were lower with it (0.0083 against 0.0097).
- **Two holdout items still fail under version 11** (13 of 15 passed). The cause per item is in the experiment's
  results; it is not diagnosed on this page.
- **The analyzer's quality varies from run to run.** With one candidate per run it scored 11, 3,
  and 6 of 15 holdout items at reasoning effort medium, and 2, 9, and 5 of 15 at effort high
  (calibration report). With two candidates and the development split choosing one, seven
  promotions measured to 25 October 2026 passed 14, 14, 13, 14, 13, 12, and 13 of 15 holdout items
  (versions 8, 9, 11, 13, 15, 17, and 19), still too few to know the spread.
- **Wrong answers on fixed questions are not what the event loop prevents.** Its value is in
  delivery, approval, and stopping, so its rows show posts, losses, and stops, not correctness.

## The earlier measurement, 23 October 2026

The same comparison with smaller samples (one run per question, 6 or 7 questions per row): the
agent loop answered 6 of 7 questions correctly against 4 of 7 without it; the verification layer
held 1 of 6 wrong trap answers, against 0 without it; the demo halves showed the same moments as above; version 8 passed 14 of 15 holdout items
against 2 for version 1 (experiments 5dba42c6 and 2eb8890c). The runs are on the
[evidence pages](evidence.md).

## How to reproduce

The demo halves are `make demo NAME=<slug>` with and without the planted item named on the demo's
page; the hill-climbing rows are the Section 4: Hill-climbing loop demos in order. Your numbers
will differ: run times, ids, token counts, and the agent's wording change on every run.
