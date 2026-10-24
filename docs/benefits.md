# What each loop is worth: paired live measurements

Every number on this page comes from live runs on gpt-6-luna on 23 October 2026, the same
questions asked with a loop's protection switched off and then on, in one live session (session 4;
one later repeat of the hill-climbing chain is marked where it appears). The
protections were switched off with the course's planted bugs (the planted items listed in
[planted-items.md](planted-items.md)). Correctness is the gold check: the answer's Structured Query
Language (SQL) query must return the hand-written gold result on both databases, `warehouse` and
`warehouse_alt`. Costs are from the spend ledger, in United States dollars.

The samples are small: one run per question, 6 or 7 questions per row, and one run of each demo
half. Read the rows as what happened in these runs, not as rates. Model answers vary from run to
run; the course's own measurement of that variation is in the
[calibration report](calibration-report.md).

## The comparison

### Section 1: Agent loop

Seven questions without traps, the reviewer off on both sides. "Without" is column names only,
unbounded rows, and no schema scout; "with" is full column descriptions, capped rows, and the scout.

| Measure | Without | With |
|---|---|---|
| Questions answered correctly | 4 of 7 | 6 of 7 |
| Tokens per run, on average | 3,656 | 4,981 |
| Cost of the 7 runs | 0.0032 dollars | 0.0033 dollars |

`agent-unbounded-rows`, one run of each half, a 10,000-row result:

| Measure | Without the row cap | With it |
|---|---|---|
| Tokens in the run | 186,689 | 27,040 |
| Cost | 0.0190 dollars | 0.0035 dollars |
| How it ended | stopped by the run's token budget | held for approval after two reviewer concerns |
| Run | 1ae983f2 | c30c0885 |

The fixed half's 27,040 tokens include the reviewer's two round trips, so the token gap mixes the
row cap with the reviewer's retries; it is not the row cap alone.

### Section 2: Verification loop

Six trap questions under the starting knowledge. "Without" is the naive guard and no reviewer;
"with" is the full layer: the syntax-tree guard, the graders, and the reviewer.

| Measure | Without | With |
|---|---|---|
| Correct answers | 0 of 6 | 0 of 6 |
| Wrong answers that would still post | 6 | 5 |
| Wrong answers held for human approval | 0 | 1 |
| Reviewer concerns raised | none (no reviewer) | 2 (1 held, 1 sent back) |
| Tokens per run, on average | 10,768 | 16,096 |
| Cost of the 6 runs | 0.0062 dollars | 0.0074 dollars |

One run of each half of two demos:

| Demo | Without | With |
|---|---|---|
| `verify-malicious-sql` | All 3 statements reached the database: 25006 twice, then 42501 | 2 stopped by the guard, the third by the role's grants (42501) |
| Its runs | 0b9814c4 | e40f9197 |
| `verify-retry-cap` | 11 attempts, 63,718 tokens, 0.0068 dollars | 3 attempts, 12,682 tokens, 0.0014 dollars |
| Its runs | 526fe0a2 | 386f5a5e |

In both halves of `verify-malicious-sql` the orders table was unchanged: without the guard, the
database's read-only transaction and the role's grants refused the writes.

### Section 3: Event loop

One run of each half of three demos.

| Demo | Without | With |
|---|---|---|
| `events-duplicate-events`: the same event three times | 3 answers, 2 digests | 1 answer, 2 duplicates absorbed, 1 digest |
| Its runs | 11e06819 | c7bd992d |
| `events-approval-survives-restart` | approval lost; the run failed | approved after the restart; posted |
| Its runs | 035816e8 | 13e0b95d |
| `events-kill-switch-in-flight` | posted after the switch was engaged | stopped in flight |
| Its runs | 70235a3e | b497410b |

### Section 4: Hill-climbing loop

The starting knowledge v1 against the version the analyzer team wrote and the gate promoted, v8;
holdout items run 3 times each (passing on 2 of 3), dev items once.

| Measure | v1 (experiment 5dba42c6) | v8 (experiment 2eb8890c) |
|---|---|---|
| Holdout items passed | 2 of 15 | 14 of 15 |
| Dev items passed | 4 of 25 | 19 of 25 |
| Holdout trap items fixed | | 12 of 13 |
| Regressions, dev and holdout | | 0 and 0 |

The analyzer team wrote two candidates on the dev split only: A passed 18 of 25 dev items with 11
rules, B 19 of 25 with 8 rules; B was kept. After approval, the spine question was answered
correctly, 64,015,091.21 dollars, and posted at the unattended level (run 38f16596).

The naive analyzer, twice: each time 21 rules quoting the dev questions, every rule flagged by the
overfit guard, the holdout unchanged at 2 of 15, and the gate blocked the version.

The same chain ran again that evening, in the capture session of the
[calibration report](calibration-report.md): the analyzer team's kept candidate, v9, passed 14 of
15 holdout items against 2 for v1 with 0 regressions, and the spine question was again correct at
the unattended level; the naive analyzer, a third time, wrote 20 rules, all flagged, and was
blocked with the holdout at 2 of 15.

## Where a loop did not help, or cost more

- **The reviewer caught 1 of 6 wrong trap answers.** It shares the analyst's knowledge: without a
  rule for the fiscal year or internal accounts, it approves a confident wrong number. It is a
  second opinion, not a gold check. The verification layer's real value in these runs was against
  unsafe queries and runaway retries, not wrong numbers.
- **The verification layer cost about 49 percent more tokens per run** on the trap questions
  (16,096 against 10,768), for one held answer.
- **The agent loop cost about 36 percent more tokens per run** on easy questions (4,981 against
  3,656), for two more correct answers out of seven; its cost in dollars barely moved (0.0033
  against 0.0032 for the seven runs).
- **One holdout trap item still fails** after promotion: business-day orders in November 2025.
  It fails even though v8 has a business-day holiday rule; the cause is not yet diagnosed.
- **The analyzer's quality varies from run to run.** With one candidate per run, it scored 11, 3,
  and 6 of 15 holdout items at reasoning effort medium (from 21 failed dev items), and 2, 9, and 5 of
  15 at effort high (from 20). The analyzer now writes two candidates and keeps the better one on the
  dev split. That method has two measurements so far, 14 of 15 both times (v8 and v9), too few to
  know its effect on the spread.
- **Wrong answers on fixed questions are not what the event loop prevents.** Its value is in
  delivery, approval, and stopping, so its rows show posts, losses, and stops, not correctness.

## How to reproduce

The demo halves are `make demo NAME=<slug>` with and without the planted item named on the demo's
page; the hill-climbing rows are the Section 4: Hill-climbing loop demos in order. Your numbers
will differ: run times, ids, token counts, and the agent's wording change on every run.
