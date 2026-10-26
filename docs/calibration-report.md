# Calibration report

Calibration ran live on 22 and 23 October 2026 (business date 31 January 2026) against gpt-6-luna,
the model id the application programming interface (API) returned for every agent and for the analyzer team. It covered the traps under
version 1 of the knowledge (the starting version), the analyzer team, the promoted version's flips
on holdout items (the benchmark questions the analyzer team never sees), the stability filter, the reviewer's verdict on the wrong answer to the fiscal year 2025 revenue question, the schema scout and the reviewer on and
off, experiment wall time at concurrency 8, the confirming re-run, the drift canary, and every core
demo live twice. It stopped at 00:59 Coordinated Universal Time (UTC) on 23 October 2026, when the OpenAI account ran out of
credits (every call from then on returned 429, credit_balance_exhausted); the items not run are
listed below with their projected cost. The ledger at that stop showed 1.6833 dollars of the
10-dollar budget; OpenAI's usage page billed 1.78 dollars for the same night, because the ledger
then priced cache-write tokens as plain input (reconciled on the [costs page](costs.md)). Both
figures include 0.2712 dollars of assignment verification, and both are within the overnight limit
of 6 dollars. The per-run and per-experiment costs below were priced before cache writes were
counted.

Every number below comes from a run of this calibration. Raw results are in the gitignored
folder `.runs/calibration/` and the run log beside them; traces are in LangSmith under three projects:
datapilot-development (calibration and preflight runs, tagged `track:calibration` and a feature tag
per step), datapilot-live (the worker's demo runs), and datapilot-experiments (the hill-climbing
runner's experiments, tagged by knowledge version, split, item, and repetition). The build's traces
are private, so each result names its run id in words instead of a trace link.

## Setup

| What | Value |
|---|---|
| Date | 22 to 23 October 2026, business date 31 January 2026 |
| Model, as returned | gpt-6-luna, for every agent and for the analyzer team |
| Reasoning effort | low for the analyst, the schema scout, and the reviewer |
| | medium for the analyzer team; Responses API; no temperature |
| Knowledge versions | Version 1, the starting version (the money rule only) |
| | Version 4, the analyzer team's candidate promoted on 22 October (seven rules) |
| Seeded data | make check-data: both warehouses match expected.yaml |
| | 405,738 orders in warehouse |
| Live session | development session 78b04de8-5e2c-4ca5-aba8-43e41f19bf4b |
| | started by make preflight PURPOSE=development |
| Measurement scheme | holdout items 3 runs per version, pass on 2 of 3; development questions once |
| Bake-off and analyzer comparison | dropped by decision on 23 October |

Where the model comes from: the key check's model lookup, and the response metadata of 625
analyst, 237 schema scout, and 141 reviewer calls in the trap step, all returned gpt-6-luna. The
analyzer team uses OPENAI_ANALYZER_MODEL, which was unset, so it ran gpt-6-luna too; by the decision
of 23 October, gpt-6-luna serves every agent and the analyzer team.

The rest of the measurement scheme, as it stood for these runs: a regression on the development questions is confirmed only
on at least 2 failures of 3 runs; an apparent holdout regression is re-run 3 more times and
confirmed on at least 2 failures. Since the midday session of 23 October, an apparent regression on the development questions is re-run 2 times
under each version and counts only when the candidate fails both and the active version passes both
(`evaluation.dev_regression_reruns` in `pack.yaml`).

## Model bake-off

Not run, by decision: gpt-6-luna is the class model and the analyzer team's model. What the
class model does on the 40 items, from the calibration experiments in session 78b04de8:

| Measure | Version 1, starting knowledge | Version 4, promoted |
|---|---|---|
| Experiment | 2bcc6ac2 | 3358ea89 |
| Easy items (no trap) passed | 6 of 7 | 7 of 7 |
| Trap items failed | 33 of 33 | 13 of 33 |
| Holdout passes | 2 of 15 | 12 of 15 |
| Holdout trap items passed | 0 of 13 | 10 of 13 |
| Development questions passed | 4 of 25 | 15 of 25 |
| Regressions, development and holdout | | 0 and 0 |
| Wall time, 70 runs at concurrency 8 | 273.4 seconds | 203.3 seconds |
| Cost, 70 runs | 0.0828 dollars | 0.0594 dollars |

The holdout trap items version 4 flipped: web-orders-calendar-2024, units-by-category-fiscal-2024,
net-revenue-fiscal-2026, buyers-first-quarter-fiscal-2026, net-revenue-cyber-monday-2025,
orders-black-friday-2025, new-customers-fiscal-2026, bottom-states-net-revenue-fiscal-2026,
app-average-order-value-fiscal-2026, and app-share-net-revenue-fiscal-2026. Still failing:
orders-by-quarter-fiscal-2026 (1 of 3 runs), business-day-orders-november-2025 (0 of 3), and
top-customers-fiscal-2026 (1 of 3).

Recommendation: keep gpt-6-luna for class. It answers the easy questions (6 or 7 of 7), fails every
trap under the starting knowledge (99 of 99 trap runs, below), flips 10 of 13 holdout trap items
after promotion, and finishes these two 70-run experiments in 203 and 273 seconds. Over every
70-run experiment measured, the range is 182 to 459 seconds (see Wall time), and two of them ran
past the 5-minute budget of the candidate experiment demo. An analyst run costs about 0.001
dollars.

## Analyzer comparison

Not run, by decision (gpt-6-luna only). The analyzer team on gpt-6-luna ran four times, each from
the failed development questions of a version 1 experiment in the same session; the first run's candidate, version 4, was
measured twice (rows 1 and 2):

| Run | Rules proposed, kept by the critic, passed the overfit guard | Candidate holdout passes against version 1 | Regressions |
|---|---|---|---|
| Hill-climbing capture, 22 October (request 1bd79879) | 8, 7, 7 | 11 of 15 against 2 (experiment 1e0ec097) | 0 |
| Same version, calibration experiment 3358ea89 | | 12 of 15 against 2 | 0 |
| Demo run-through 1 | 8, 7, 7 | 3 of 15 against 2 (experiment aa1dfae5) | 0 |
| Demo run-through 2 | 9, 8, 8 | 6 of 15 against 2 (experiment 0cf7df9d) | 0 |
| Earlier session, before the personal-data fix (version 3) | 9, 9, 9 | 2 of 15 against 2 | 0 |

The rules are general (fiscal calendar, net revenue, eligible orders, New York local dates,
category rollup, first qualifying order, average order value); the overfit guard rejected none, and
the critic dropped the business-day holiday rule each time it was proposed in these runs (in
the afternoon session of 23 October the kept candidate, version 8, carries one; see below). The version 3 run scored no
better than version 1 because a correct query that filters internal accounts by email domain was held for
human approval; the fix routes only a query that returns a personal column.

Recommendation: keep gpt-6-luna for the analyzer team, but the candidate's quality varies from run
to run (3, 6, and 11 holdout passes from the same 21 failed development questions), so the candidate experiment
demo's "clear majority of holdout trap items" is not guaranteed by one live analyzer run. Before
class, re-run the analyzer team at reasoning effort high and measure whether that narrows the
spread; until then the demo needs a planted aid or a rehearsal-time check.

Prepared, not run: `make calibrate STEP=analyzer-high`. It runs the analyzer team at reasoning
effort high (the pack's effort, medium, is unchanged for class) from the failed development questions of the
open session's experiment of version 1, the same input the analyzer step reads, then the candidate
experiment against that same experiment. It records the candidate's holdout passes, holdout trap
flips, and confirmed regressions in `.runs/calibration/analyzer-high-*.json`, with how many earlier
analyzer runs had exactly the same failed development questions. It prints its cost estimate before any model
call: one analyzer team run (about 0.02 dollars) and one 70-run candidate experiment at the measured
0.0011 dollars per run, about 0.10 dollars in all, with re-runs of apparent regressions on top. With
no experiment of version 1 in the open session it stops before any call and names
`make calibrate STEP=experiment-starting` (about 0.08 dollars).

Built after the review of 23 October (its commit is on the evidence page), proposed as the fallback if effort high did not narrow the spread, which it did not (2, 9, and 5
of 15, below): the analyzer team produces two candidate rule sets from the same failed development questions,
by two independent runs of the failure analyst, the rule writer, and the critic, each through the overfit guard. Both
candidates run on the development split only (25 items once each), compared with the active version's
results in the session's baseline experiment. The better one is selected by these keys in order:
fewer regressions, then more passes, on the development questions, then fewer rules. The holdout is never used for the
choice: only the selected candidate goes to the candidate experiment and the gate, so the holdout
still measures questions no decision was tuned on. Cost per attempt: one more analyzer team run and
50 runs on the development questions, about 0.08 dollars; wall time about 1 to 1.5 minutes more at
concurrency 8. The risk is that the development questions were the analyzer's own input, so
choosing on them favours rules fitted to those failures; the
overfit guard and the holdout gate still stand behind it. As built: the number of candidates is
`analyzer.candidates: 2` in `pack.yaml`; the hill-climbing runner's analyzer request runs the team
once per candidate, saves each candidate's rules under a retired version of its own (such as
`v7-candidate-a`), runs it on the 25 development questions once each, and compares each item with the baseline
experiment's result for that question; a regression on the development questions here is apparent, from one run, and the gate confirms the
kept candidate's regressions with its own re-runs. The kept candidate is saved as the draft for
approval. Every candidate is a row in `ops.analyzer_candidates` (migration 016), and the Improve
page shows the choice above the knowledge diff, such as "Candidate A: 14 of 25 dev, 0 regressions, 7
rules; Candidate B: 12 of 25 dev, 1 regression, 8 rules; chosen: A". Run live twice: in
the afternoon session of 23 October (version 8) and in the capture session of 23 October, evening (version 9), both below.

## Agents on and off

Four benchmark questions under version 1, once per configuration (calibration step agents, run of 23:29
UTC); tokens are the run's input plus output, seconds its wall time.

| Configuration | Mean tokens | Mean seconds |
|---|---|---|
| Scout and reviewer on | 8,648 | 24.2 |
| Scout off | 3,853 | 12.8 |
| Reviewer off | 5,786 | 12.8 |
| Both off | 3,337 | 10.1 |

| Question | Configuration | Run |
|---|---|---|
| product-count | Scout and reviewer on | 2,846 tokens, 8.6 seconds |
| product-count | Scout off | 2,757 tokens, 7.9 seconds |
| product-count | Reviewer off | 2,847 tokens, 7.8 seconds |
| product-count | Both off | 2,756 tokens, 6.9 seconds |
| camping-subcategories | Scout and reviewer on | 2,674 tokens, 9.2 seconds |
| camping-subcategories | Scout off | 2,583 tokens, 9.1 seconds |
| camping-subcategories | Reviewer off | 2,674 tokens, 7.8 seconds |
| camping-subcategories | Both off | 2,584 tokens, 7.2 seconds |
| top-customers-fiscal-2025 | Scout and reviewer on | 12,071 tokens, 38.1 seconds, held |
| top-customers-fiscal-2025 | Scout off | 4,177 tokens, 15.6 seconds |
| top-customers-fiscal-2025 | Reviewer off | 4,283 tokens, 11.9 seconds |
| top-customers-fiscal-2025 | Both off | 4,340 tokens, 13.9 seconds |
| net-revenue-fiscal-2025 | Scout and reviewer on | 17,002 tokens, 40.7 seconds, held |
| net-revenue-fiscal-2025 | Scout off | 5,895 tokens, 18.8 seconds |
| net-revenue-fiscal-2025 | Reviewer off | 13,341 tokens, 23.7 seconds |
| net-revenue-fiscal-2025 | Both off | 3,669 tokens, 12.4 seconds |

Gold results were identical in every configuration: the two easy questions pass, the two trap
questions fail. Each cell is one run per question, so the table shows what happened, not a cause.
The extra tokens appear when both agents are on and the reviewer raises a concern, which sends the
analyst back and then holds the answer: the two held runs are the two largest. With one agent on,
the reviewer alone added 516 tokens on average over both off, and the scout alone 2,449.

The reviewer's verdict on the wrong answer to the fiscal year 2025 revenue question, over every run where the analyst answered with
Structured Query Language (SQL) under version 1 and has a trace below: concern in 6 runs, approve in 1.

| Run | Verdict | Trace |
|---|---|---|
| Agents step, scout and reviewer on | concern, held for approval | cc864ad9 |
| Agents step, scout off | approve | ec016e72 |
| Section 1: Agent loop capture | concern, held | bd50f9ca |
| Section 2: Verification loop capture | concern twice, held | dc6dfa84 |
| Demo run-through, agent-confident-wrong-answer attempt 1 | concern twice, held | d36496ca |
| Demo run-through, verify-graders-pass-still-wrong attempts 1 and 2 | concern | f13cbb8d, 79647bb1 |

The premise of Assignment 2: Verification loop (class code guesses at a term no business rule
defines), from the same step:

| Configuration | "How many loyal customers do we have?" | "Who are our VIP customers?" |
|---|---|---|
| Scout and reviewer on | escalated: answered 40,848, then hedged after the reviewer's concern | escalated: token budget reached after the reviewer's concern |
| Scout off | held for approval: answered 40,848 with a stated reading, reviewer concern | held for approval: answered "top customers by spend", reviewer concern |
| Reviewer off | answered: 40,848, "at least two orders" | asked for clarification (no VIP field) |
| Both off | answered: 40,848, "at least two orders" | answered: 462 customers, "top 1 percent by spend" |

So class code does guess (5 of 8 runs answered with a stated reading), but the reviewer turns most
guesses into a held or escalated answer. Recommendation: keep the reviewer, and say in Section 2
that it already catches some undefined terms; the clarify-or-abstain grader of Assignment 2 is
still needed, because with the reviewer off the guess is posted unflagged.

## Traps

Every trap item 3 times under version 1 (calibration step traps, 99 runs, 400.6 seconds, experiment 322f604d):

| Trap | Items carrying it | Runs | Runs that passed |
|---|---|---|---|
| Fiscal year | 25 | 75 | 0 |
| Net revenue | 17 | 51 | 0 |
| Cancelled orders | 33 | 99 | 0 |
| Eastern time | 19 | 57 | 0 |
| Internal accounts | 30 | 90 | 0 |

No trap item passed in any run, so no trap was strengthened or replaced. The trap labels most
often attached to the wrong SQL were the missing internal-account filter, the missing status
filter, the calendar-year range, and UTC truncation. Example traces:
net-revenue-fiscal-2025 (run 75a23e63),
top-customers-fiscal-2026 (run 26191448).

## Stability and the holdout

The stability filter, 5 runs per holdout item (a keep needs 4 or 5 of 5, or 0 or 1 of 5):

| Holdout item | Family | Version 1, run 23:02 | Version 4, run 23:10 |
|---|---|---|---|
| average-list-price-active | products | 5 | 5 |
| web-orders-calendar-2024 | orders | 0 | 4 |
| all-products-by-category | products | 5 | 5 |
| units-by-category-fiscal-2024 | products | 0 | 3, unstable |
| net-revenue-fiscal-2026 | revenue | 0 | 5 |
| orders-by-quarter-fiscal-2026 | orders | 0 | 2, unstable |
| buyers-first-quarter-fiscal-2026 | customers | 0 | 5 |
| business-day-orders-november-2025 | orders | 0 | 0 |
| net-revenue-cyber-monday-2025 | revenue | 0 | 3, unstable |
| orders-black-friday-2025 | orders | 0 | 4 |
| new-customers-fiscal-2026 | customers | 0 | 4 |
| top-customers-fiscal-2026 | customers | 0 | 4 |
| bottom-states-net-revenue-fiscal-2026 | revenue | 0 | 5 |
| app-average-order-value-fiscal-2026 | aov | 0 | 4 |
| app-share-net-revenue-fiscal-2026 | revenue | 0 | 5 |

Under version 1 every item is stable (all at 0 or 5). Under version 4, 3 items were unstable. As the rule allows,
they were replaced by new items of the same family and category, never seen by the analyzer team
(see the evidence page): camping-units-fiscal-2026, orders-second-quarter-fiscal-2026, and
net-revenue-christmas-eve-2025, whose gold and naive SQL differ on both warehouses. The filter was
then run again (23:18 under version 1, all stable; 23:23 under version 4): 4 items unstable, 3 of them different
from the first run, including two the first run had at 5 of 5 (net-revenue-fiscal-2026 2 of 5,
app-share-net-revenue-fiscal-2026 2 of 5) and two of the new items (camping-units-fiscal-2026 2 of
5, orders-second-quarter-fiscal-2026 3 of 5). The instability belongs to the promoted version's
answers, not to particular items, so replacing items chases noise; the original, reviewed holdout
was restored. Holdout items replaced in the end: 0. The holdout keeps 15 items, 4
of them revenue.

The finale's revenue clearance, as the code stood for these runs: the hill-climbing runner cleared a
family for the unattended level only when every holdout item of the family passed in the one
experiment of the promoted version. Revenue has 4 holdout
items; with each passing 2 to 5 of 5 under a promoted version, all 4 passed in only one of the four
measurements above, and revenue was cleared in none of the three live promotions (cleared:
average order value and customers on 22 October; none in demo run-through 1; average order value and
products in demo run-through 2). The fiscal year 2025 revenue question by webhook was answered correctly (64,015,091.21
dollars, gold passed, run 32c5abc0) but posted at the assisted level.

Recommendations:
- N (the minimum holdout items per family before the unattended level, built by Assignment 4: Hill-climbing loop):
  3. Every class family has at least 3 holdout items except average order value (1), so the rule
  as designed keeps average order value at the assisted level, which these runs suggest is right:
  one item is not evidence.
- The finale's clearance, decided by the course team on 23 October: a metric family is cleared for the
  unattended level on the gate's own confirmed standard, not on every holdout item passing in one
  experiment. Every holdout item of the family must pass at least 2 of 3 runs; an item that falls
  short gets the confirming re-run, 3 more runs (`evaluation.holdout_regression_reruns`), and counts
  as passing if it passes at least 2 of 3 of them (`evaluation.holdout_pass_threshold`). The minimum
  number of holdout items, built by Assignment 4: Hill-climbing loop, applies first, so a family
  below it is never re-run. The hill-climbing runner applies this at every promotion
  (`eligibility.confirmed_clearance`) and writes each re-run beside its item in the candidate
  experiment. The measured numbers above stand: under the earlier rule, revenue clearance depended
  on all 4 revenue items passing in one experiment, which happened once in four measurements. The
  new standard ran live three times, below: under version 5 revenue did not clear; under version 8 (the afternoon session of 23 October)
  and version 9 (the capture session of 23 October, evening) it cleared.

## Confirming re-run

The gate's own code (find_regressions with the scheme's re-runs), on net-revenue-fiscal-2026 under
version 4, the item the stability filter had at 2 of 5 (a flaky item, chosen on purpose):

| Run (23 October, UTC) | First 3 runs | Re-runs | Outcome |
|---|---|---|---|
| 23:39:04 | 3 of 3 passed | none | no apparent regression |
| 23:39:53 | 3 of 3 passed | none | no apparent regression |
| 23:40:35 | 1 of 3 passed: an apparent regression | 3 of 3 passed | "Not a regression: passed 3 of 3 more runs" |

Traces of the confirming re-runs:
809cdfb0,
ee0d768a,
5315a5a3.
No apparent regression in these calibration experiments was confirmed: each had 0 regressions.
Across the analyzer team's candidate experiments with an id in this report, 9 of 10 had 0
regressions; 25d0f021 (analyzer at reasoning effort high, run 1) had 1 regression on the development questions,
camping-subcategories.

## Drift canary

Three easy questions must pass and two trap questions must fail under version 1. All four canary runs
passed it: preflight at 21:02 and 22:12 UTC on 22 October, the calibration canary at 23:37 UTC
(3 easy passed, 2 traps failed, product-count (run bf91c403), net-revenue-fiscal-2025 (run 5401c604)), and the first
preflight at 20:57, which first scored a correct easy answer as failed because of an event-loop bug
(fixed the same night) and passed on the re-run.

## Demos

Each core demo twice in a row with a reset between, triggered as make demo NAME= triggers it, with
the starting knowledge active and demo pacing on; the moment is checked from the run's own record.
Seconds are wall time from trigger to the checked result. Targets, from the demo
registry: 3 to 5 minutes per demo.

| Demo | Fixed system, attempt 1 | Fixed system, attempt 2 | Planted half |
|---|---|---|---|
| agent-simple-question | shown, 37 seconds (0086c2e0) | shown, 39 seconds (e71a1401) | |
| agent-confident-wrong-answer | shown, 76 seconds: 76,981,355.95, gold 64,015,091.21, 4 trap labels (d36496ca) | not shown: posted, no gold check within 90 seconds (c02c2117) | |
| agent-unbounded-rows | posted, 19,661 tokens (9f635488) | held: reviewer concern, 17,298 tokens (2b0eb54c) | not run |
| verify-malicious-sql | shown, 6 seconds: guard, guard, grants 42501 (d85f5bfb) | shown, 6 seconds (465927f6) | shown twice: 25006, 25006, then 42501 (35f69707, 57b7a363) |
| verify-retry-cap | shown, 79 seconds: escalated after 3 attempts (53ff0181) | shown, 69 seconds (53c57efc) | not run |
| verify-graders-pass-still-wrong | not shown: graders passed, no gold check within 90 seconds (f13cbb8d) | not shown, same (79647bb1) | |
| events-webhook-question | shown, 46 seconds, unverified post (5c2503c4) | not shown: held by a reviewer concern about the date (8a6823fb) | |
| events-approval-survives-restart | shown, 84 seconds (446dbe72) | shown, 81 seconds (c85a9984) | not run |
| events-duplicate-events | shown, 57 seconds: 1 run, 2 duplicates absorbed, 1 digest (65ced5cc) | shown, 78 seconds (f19be33c) | not run |
| events-kill-switch-in-flight | shown, 33 seconds, stopped in flight (6a0b1408) | shown, 8 seconds (619c716e) | not run |
| improve-baseline-experiment | shown, 285 seconds: version 1 2 of 15 (572dc0ea) | shown, 266 seconds (bf861054) | |
| improve-analyzer-team-approve | shown, 62 seconds: 7 rules passed the guard | shown, 98 seconds: 8 rules | |
| improve-naive-analyzer-blocked | | | not run |
| improve-candidate-experiment | not shown: 3 of 15 against 2, 0 regressions (aa1dfae5) | not shown: 6 of 15 against 2 (0cf7df9d) | |
| improve-cleared-unattended | not shown: assisted level, answer wrong (e81760d3) | not shown: assisted level, answer wrong (e5598854) | |

Demos whose guaranteed moment did not appear, and why:
- agent-confident-wrong-answer (attempt 2) and verify-graders-pass-still-wrong (both): the gold
  check event did not arrive within 90 seconds. Hardened the same night (one run's gold check can never
  block the others, and a failing promotion step no longer stops the gold checks); the retake failed
  on the exhausted credits. The symptom appeared once more, in the capture session of 23 October,
  evening (below).
- events-webhook-question (attempt 2): the reviewer held a correct answer because it did not know
  the business date. Fixed the same night (the reviewer sees the business date); retake not run.
- improve-baseline-experiment exceeds its 3-minute target (266 and 285 seconds for 70 runs).
- improve-candidate-experiment and improve-cleared-unattended: the analyzer team's candidates in
  this run-through were weak (3 and 6 of 15); see the analyzer comparison. On 22 October the same chain
  gave 11 of 15 and a correct finale at the assisted level.
- agent-unbounded-rows: the fixed half ran (about 18,000 to 20,000 tokens per run); the planted
  half, which the moment compares against, was not run.

## Wall time

The full scheme (70 runs: 25 development questions once, 15 holdout items 3 times) at concurrency 8: 182 to 459
seconds over every 70-run experiment in this report. The first 8 (calibration 273.4 and 203.3 seconds;
hill-climbing captures 257.9 and 213.2 seconds; demo run-through 283.4, 279, 259.9, and 193 seconds) took 193 to 283
seconds. Later: 280.8 seconds (the starting experiment before the analyzer at effort high), 458.9, 229.4,
and 403.8 seconds (the three candidates at effort high), 273.4 and 257.6 seconds (the chain of 23 October,
morning), 276.8 and 206.5 seconds (the afternoon session of 23 October), and 278.8, 181.9, and 212.4 seconds (the capture session of 23
October, evening). Two runs, both candidates at effort high with 10 rules
each, took 6.8 and 7.6 minutes, past the 5-minute budget of the candidate experiment demo. The
baseline experiment demo's 3-minute target is missed in every run. Cost per 70-run experiment, where
recorded: 0.0594 to 0.0914 dollars.

## Spend

make spend at the end of calibration (23 October, 01:20 UTC), with the caps as they stood then
(the course team changed them later; the current caps are in `pack.yaml`):

| Line | Spent | Cap on 23 October, 01:20 UTC |
|---|---|---|
| development live checks | 0.7808 dollars | 1.50 |
| calibration | 0.6313 dollars | 2.50 |
| assignment verification | 0.2712 dollars | 2.50 |
| rehearsal | 0 | 2.50 |
| reserve | 0 | 1.50, not used |
| total | 1.6833 dollars | 10.00, warning at 6.00 |

| Activity | Calls | Cost |
|---|---|---|
| development (the stack's worker, runner, and console runs) | 5,813 | 0.7633 |
| calibration-stability | 2,475 | 0.3030 |
| assignment verification | 1,423 | 0.2712 |
| calibration-experiment | 1,137 | 0.1422 |
| calibration-traps | 1,003 | 0.1326 |
| calibration-agents | 165 | 0.0425 |
| preflight-development | 91 | 0.0093 |
| development live checks (live smoke) | 54 | 0.0083 |
| calibration-confirm | 67 | 0.0070 |
| calibration-canary | 37 | 0.0041 |

Misattributed: the demo run-through of this calibration ran through the stack's worker and runner, which
record under the stack's activity, "development". About 0.46 dollars of calibration work (the
development activity grew from 0.3067 to 0.7633 dollars during the demo run-through) is counted on the
development live checks line. Measured cost per analyst run: about 0.001 dollars; between 5 and 8
of every 10 input tokens were served from OpenAI's prompt cache.

## Not run

Not run: OpenAI credits exhausted at 00:59 UTC on 23 October 2026. Projected cost at the measured
rate of about 0.0011 dollars per analyst run:

| Item | Runs | Projected cost |
|---|---|---|
| Planted halves, twice each (the five listed below) | about 20 | 0.05 dollars |
| improve-naive-analyzer-blocked, twice | about 142 | 0.16 dollars |
| Retakes of three demos, twice each (listed below) | about 6 | 0.01 dollars |
| A second chain of improve-candidate-experiment and improve-cleared-unattended | about 75 | 0.09 dollars |

The planted halves are unbounded rows, retry cap (runs to the 60,000-token cap), approval with the
in-memory checkpointer, duplicate events, and kill switch at claim only. Each of the two runs of
improve-naive-analyzer-blocked is the analyzer and a 70-run candidate experiment. The retakes are
agent-confident-wrong-answer, verify-graders-pass-still-wrong, and events-webhook-question.

## Live session of 23 October, stopped at the trace limit and at the ledger

The session started at 05:13 UTC on 23 October 2026 with its own limits (development live checks
0.40 dollars, calibration 1.00, 2.50 in all, shared with the assignment verification line). Live
work stopped at about 06:50 UTC, during the first live smoke check: LangSmith refused every trace
with 429, "Monthly unique traces usage limit exceeded". The rule at that time was that every result
carries a trace link, so no further live run was made; the model calls themselves still succeeded.
From 07:24 UTC each result is proven by its run id instead (below).

Preflight (session e12c9e88, purpose development): every service healthy, gpt-6-luna, and the drift
canary as expected, three easy questions passed and two traps failed; traces for
product-count (run 74ff46f4)
and the
fiscal year 2025 revenue question (run dd99cbfd).

The live smoke check, five calls (actual 0.0056 dollars against the estimate 0.0264):

| Call | Result | Tokens in (cached), out; cost | Trace |
|---|---|---|---|
| Analyst with the scout | answered, gold check passed | 7,604 (1,538), 681; 0.0010 | 32b30a5e |
| Fiscal year 2025 revenue question | held for approval (below) | 21,855 (12,991), 1,835; 0.0020 | fb8cef0c |
| Webhook event | posted: 291 orders on the previous day | 14,158 (2,905), 898; 0.0017 | c1fd7f5c, refused |
| Analyzer team step | 2 diagnoses, 3 rules kept and guarded | 2,224 (0), 1,199; 0.0008 | f542227f, refused |
| Refused write | SQLSTATE 25006; the run ended escalated | 743 (0), 33; 0.0001 | bb9c326f, refused |

The fiscal year 2025 revenue question passed every grader; the reviewer raised a concern that fiscal year 2025 was
taken as the calendar year, so the answer was held for approval, and the gold check failed (row 1
differs). The analyzer team step proposed 3 rules; the critic kept 3 and all 3 passed the overfit
guard (not saved). Runs whose trace was refused are named by run id.

The check reported three hard failures, all "missing trace": the three runs behind them behaved as
designed. The webhook run's spend landed under "development live checks", the activity the check
sent in its header, not under the worker's "development" (which stayed at 0.7633 dollars): the
activity header works for a run started by a command. make spend after the check agreed with the
calls: the session's development line at 0.0101 dollars, preflight 0.0053 and the smoke check 0.0047
in the ledger against 0.0056 reported (the webhook run's cost comes from its run record).

Built and tested this session without tokens, for the live checks still owed:

- `make calibrate STEP=output-token-cap`: one analyst run with that analyst's max_output_tokens
  lowered to 16 for this run only (a copy of pack.yaml on the target, never an environment
  setting), failing unless the run ends escalated "cut off at its output-token cap". Under
  development live checks; about 0.001 dollars.
- The console sends the DataPilot-Spend-Activity header: the budget line of the open session's
  preflight followed by "console" (development live checks-console in a development session,
  rehearsal-console in a rehearsal, class, or Thursday review session).
- The finale's confirmed standard (ef767b5) confirmed by its tests: test_family_clearance and the
  integration suite (380 passed, 8 skipped) with test_hill_climbing_ops.
- The autonomy policy's docstrings say a family is cleared on the confirmed standard
  (eligibility.confirmed_clearance), and improve-cleared-unattended points at that function, with
  its excerpt in the walkthrough of Section 4: Hill-climbing loop.
- Needed in the slides, not edited here: the notes of slide 64, "Autonomy is earned per metric
  family", should add that a family is cleared on the gate's confirmed standard (every holdout item
  passes 2 of 3 runs, an item that fell short passing 2 of 3 more runs), not on one experiment.

Commits: 1e9b4f4 (the cap probe and the console's activity header), then the docstrings, the code
pointer, and this section.

### Resumed without traces, stopped at the ledger

Live work resumed at 07:24 UTC: the trace limit is not a stop condition, and each result
below is proven by its run id, its own record in ops, and the ledger instead of a trace. Wherever a
trace link would go: trace refused, LangSmith monthly unique trace limit. Session 817427d6 (purpose
development); preflight passed again with the drift canary as expected.

| Check | Run | What happened | Tokens; cost |
|---|---|---|---|
| Output-token cap probe | d9f0ab0e | ended escalated, cut off at its output-token cap | 715 + 14; 0.0001 |
| make demo, its activity | 296f987a | posted; ledger rows under development | 9,197 + 506; 0.0007 |
| Console-started run | af83a682 | under development live checks-console | 25,030 + 2,106; 0.0026 |
| Budget switch off | 784b7253 | retry cap held: escalated after 3 attempts | 12,348 + 328; 0.0014 |
| Resumed export | e1853dcd | kept attempt 2 and one concern; ended at the run budget | 108,430 + 950; 0.0113 |

The cap probe's own reason says "after 0 tokens" while the ledger has 14 output tokens: the
probe makes two analyst calls, an ordinary opening call (715 input, 14 output tokens) and the call
that is cut off, which reported 0 input and 0 output tokens, the count the guard named (diagnosed
and fixed in the afternoon session of 23 October: a cut-off reply that reports zero now reads as no count, with the run's
total named). make spend with the switch off printed
"the build budget is off (DATAPILOT_BUILD_BUDGET is not 1): the lines below are not enforced", and
with it back at 1 the lines are enforced again; the session limit held either way. The console's
"Send webhook question" sends the fiscal year 2025 revenue question, while make demo sends the question about the
previous day, so the console run was held by the reviewer (the guaranteed moment needs the make
question).

The resumed export: the pending approval survived a worker restart, and three personal-data
queries were approved by this session, standing in for the instructor.
After the second approval the reviewer's concern (repeated addresses) went back to the analyst
once, the attempt count went from 1 to 2 and was kept across the resume, and the run ended
escalated at "token budget of 60000 reached" with 109,380 tokens, about the same as the 110,000
before bb0b0e2. The overshoot comes from the approved query `SELECT array_agg(email ...)`: one row
holding all 5,261 addresses, which the row cap of 50 does not limit, sent again with every later
call, while the run budget is checked before each call.

Analyzer at reasoning effort high, after the starting experiment (version 1: holdout 2 of 15, development 5 of
25, 280.8 seconds, 0.0914 dollars):

| Run | Candidate, experiment | Holdout passes (version 1: 2), trap flips, regressions | Cost |
|---|---|---|---|
| 1 | version 4, 25d0f021 | 2 of 15; 0 flips; 1 regression on the development questions | 0.1382 |
| 2 | version 5, 4ae5177b | 9 of 15; 7 flips; 0 regressions | 0.0761 |
| 3 | version 6, 66616a62 | 5 of 15; 3 flips; 0 regressions | 0.1369 |

Each run proposed 10 rules; the critic kept 10, 9, and 10, and every kept rule passed the overfit
guard. Run 1's regression on the development questions was
camping-subcategories. Experiment wall time: 458.9, 229.4, and
403.8 seconds. One measurement in three gives a clear majority of holdout flips, as at medium.

Retakes, each with a reset before it:

| Demo | Attempt 1 | Attempt 2 |
|---|---|---|
| agent-confident-wrong-answer | shown, 3 trap labels (17fc06b7) | shown, 3 trap labels (489cf450) |
| verify-graders-pass-still-wrong | shown, 4 trap labels (e61875c3) | shown, 4 trap labels (d51cff08) |
| events-webhook-question | shown, unverified post (9d8be803) | shown, unverified post (8f6c1fa2) |
| agent-unbounded-rows, planted | not shown: request refused (0642c561) | blocked by the budget (12cd376a) |

The confident wrong answers were 72,394,572.08 dollars (both agent-loop runs) and 76,981,355.95
(both verification-loop runs) against gold 64,015,091.21; every run was then held by two reviewer
concerns. The webhook answers were 300 and 291 orders: 300 matches the New York day, 291 is
the day in Coordinated Universal Time (confirmed on 23 October by a zero-token count on the seeded
warehouse: 300 orders on 30 January 2026 in Eastern time, 291 in Coordinated Universal Time), and
the reviewer approved both.

The planted half of agent-unbounded-rows asked for `SELECT * FROM order_items`, the whole table
(1,020,321 rows, about 32.6 million characters). With the bug on, all of it went back to the model,
and OpenAI refused the request with 400 ("string too long", at most 10,485,760 characters), so
nothing was billed. The ledger, though, recorded the failed call with its estimate from the
request: about 8,143,708 input tokens, 0.81 dollars, under "development" for run 0642c561. That put
the development live checks line at 1.6315 of 1.50 dollars (0.1315 shown on the reserve) and the
session's development line at 0.8507 of 0.40, so the next run (12cd376a) was blocked. A ledger
disagreeing with the calls by more than 0.25 dollars is a stop condition: all live work stopped at
about 08:10 UTC, the stack is down, and every planted flag is back at 0.

Fixed after the stop, without tokens: the ledger records a request the API refused outright (a
Hypertext Transfer Protocol (HTTP) client error, 4xx) at zero tokens, keeping the estimate for
timeouts, dropped connections, and server errors; and the demo's question is now the 10,000-row SELECT its guaranteed moment names
(about 80,000 tokens, inside the request limit). The ledger rows of run 0642c561 still need
correcting.

make spend at the stop: development live checks 1.6315 of 1.50 (about 0.82 without the wrong
rows); calibration 1.0738 of 2.50; this session, development 0.8507 of 0.40 (about 0.04 without
them), calibration 0.4425 of 1.00, total 1.4298 of 2.50.

The wrong rows were cancelled by a correction row in the ledger (component "ledger correction",
0.8144 dollars, with its reason) before the session went on.

### Resumed after the ledger correction

Session b91fc3f7 (purpose development) from 08:42 UTC; preflight and the drift canary as expected.
Trace links: trace refused, LangSmith monthly unique trace limit; each result cites its run id, its
record in ops, and the ledger. Every planted half ran twice with a reset before each attempt, its
flag set to 1 in `.env` and `make up`, and set back to 0 afterwards.

| Planted half | Attempt 1 | Attempt 2 |
|---|---|---|
| verify-retry-cap, no retry cap | shown: 9 attempts (4bb83547) | shown: 9 attempts (d9a3e6b5) |
| events-approval-survives-restart, in memory | shown: approval lost (b81eb2e6) | shown: approval lost (58fe4dc2) |
| events-duplicate-events, both bugs | shown: 3 answers, 2 digests (fcf3834f) | shown: 3 answers, 2 digests (1eeb2a0f) |
| events-kill-switch-in-flight, at claim only | shown: posted while engaged (02d72359) | shown: posted while engaged (70e1f9b0) |
| agent-unbounded-rows, 10,000 rows | shown: 183,639 tokens (3de95c50) | shown: 185,727 tokens (e4d1bae9) |

Without its cap, the injected failing grader sent the run back 9 times, until the 60,000-token run
budget stopped it (62,762 and 63,737 tokens, 0.0067 and 0.0069 dollars, 104 and 111 seconds). With
the in-memory checkpointer, the approval given after the worker restart found nothing to resume:
"the pending approval was lost: no checkpoint holds this run", the run failed. With both duplicate
bugs, the same event posted three answers and the digest fired twice ran twice (in attempt 1 the
second digest was held for approval). With the kill switch checked only at claim, the in-flight
run (demo pacing on) posted after the kill switch was engaged. With the unbounded rows bug, the
10,000-row result took the run to about ten times the fixed half's 17,000 to 20,000 tokens in 18 or
19 seconds, 0.0184 and 0.0187 dollars, where the run budget stopped it.

The hill-climbing chain:

1. Baseline: experiment dde64d21, version 1, holdout 2 of 15, 4 of 25 development questions, 273.4 seconds, 0.0852 dollars
   (calibration line).
2. Candidate: version 5, the best of the three analyzer runs at reasoning effort high; the two weaker
   drafts (versions 4, 6) were retired in ops so the Improve page runs version 5. Experiment 407ff720: holdout
   10 of 15 against 2, 8 fixed, 0 regressions on either split, 15 of 25 development questions, 257.6 seconds; gate "Ready
   for human approval: v5 passes 10 of 15 holdout items against 2, with no regressions." A first
   run (c38338fc, the same counts) is not counted: the hill-climbing runner still had the unbounded
   rows flag from the step before.
3. Approval: given by this session standing in for the instructor, under the approver name it
   typed; promotion decision 26 at 09:18:26 UTC, version 5 active.
4. Clearance on the confirmed standard: average order value and products cleared for the
   unattended level; revenue, orders, and customers not. Revenue's re-runs:
   net-revenue-cyber-monday-2025 failed 3 of 3, then passed 2 of 3 more (passes);
   app-share-net-revenue-fiscal-2026 passed 1 of 3, then 1 of 3 more (falls short twice).
   net-revenue-fiscal-2026 (2 of 3) and bottom-states-net-revenue-fiscal-2026 (3 of 3) passed.
5. The finale by webhook, the system at the unattended level: run 631d0ccb posted at the assisted
   level, labelled verified, 63,986,616.77 dollars against gold 64,015,091.21 (gold check failed,
   trap label missing_internal_filter), 16,291 tokens, 0.0021 dollars. Not forced.

The cause of the finale's wrong answer: internal accounts are known only by their email domain
(the gold SQL has `lower(c.email) NOT LIKE '%@harborpine.com'`; the data has case variants and
look-alike addresses, so a loose guess gives a wrong total), and no version stated that predicate.
The finale's SQL did filter internal accounts, but too broadly. A read-only query on the seeded
warehouse (fiscal year 2025, status not 5, Eastern time) gives 65,592,532.44 with no internal
filter, the gold 64,015,091.21 with the gold predicate, and exactly the finale's 63,986,616.77 with
`email NOT ILIKE '%harborpine%'`, which also removes the look-alike addresses. That is why the
answer is below gold, not above it. The trap label missing_internal_filter does not describe an
over-broad filter, and how the label was assigned to this run is still to be checked. Version 5's rule "Use the
eligible business-order population" gave the SQL guidance `status <> 5 AND <documented
non-internal-customer predicate>`, a placeholder; versions 4 and 6 gave `customer_is_internal = false`, a
column that does not exist. The reference SQL reached the failure analyst, but its diagnoses were
in general business terms, and the rule writer reads only the diagnoses, so the exact predicate
never reached a rule. Fixed in the analyzer, for every rule and not for this one trap: the failure
analyst quotes the reference SQL fragment the agent's SQL lacked; the rule writer gets the schema
and must write guidance that runs over it; and a deterministic check parses each rule's guidance
with sqlglot against the catalog snapshot, sends a placeholder, an unknown table or column, or prose
back to the critic, and drops a rule that still fails, with the reason in the analyzer report. The
saved versions 4, 5, and 6 internal-accounts rules are each caught in the tests
(`platform/tests/unit/test_sql_guidance.py`), and the email-domain predicate passes. The finale's
moment is restated by the course team as "The correct answer, posted at the level its family has
earned": the assisted level is a correct outcome when revenue falls short of the confirmed
standard.

The gate capture is replaced by the 23 October run at 1280x720
(`section-4-hill-climbing-loop/demo/expected/improve-candidate-experiment-gate.png`, "Gate: ready for
human approval."). The board and channel captures of 22 October stay: the moment they would replace
(a correct answer posted at the unattended level) did not appear.

improve-naive-analyzer-blocked, attempt 1: the naive analyzer (request 15a9030d) wrote 21 rules,
one per failed development question, each quoting the item's question and its reference SQL, with no critic and
no overfit guard: candidate version 7. Its experiment 911423fb passed 15 of 15 holdout items and 25 of 25 development
questions, and the gate read "ready for human approval". The moment (development passes jump,
holdout passes stay flat, the gate blocks) did not appear. No holdout item reached the analyzer: version 7 quotes no holdout question.
The reference SQL of the development questions carries every convention the holdout items need (the fiscal calendar,
internal accounts, status 5, New York time), so the rules generalize. Version 7 was not approved and is
retired in ops. Attempt 2 was not run: about 0.08 dollars, and the development line had 0.05 left
this session. The demo is not ready: its planted item does not guarantee the moment.
Built after the review of 23 October: the naive analyzer makes no model call.
It writes one rule per failed development question, quoting the question word for word with the analyst's
query that failed, and never reads a reference query, so its rules teach nothing about a holdout
question. The overfit guard reports on every rule, all flagged, and is not applied; a test proves
that for any set of failed development questions every naive rule fails the guard. The other half of the
recommendation is built too: the gate has a fourth condition, every rule the candidate adds to the
active version passes the overfit guard, so the naive version is blocked whatever its holdout
count, even one better than the active version's; an honest candidate, whose rules already passed
the guard, is judged as before. Run live three times since, blocked each time: twice in
the afternoon session of 23 October and once in the capture session of 23 October, evening, both below.

Proposed for the analyzer's variance (built as the proposal in Analyzer comparison, with fewer regressions on the development questions as the first key, then more passes there): the three
measurements at reasoning effort high gave 2, 9, and 5 of 15 holdout items from the same failed development questions. The runner would
have the analyzer team write two candidate rule sets, run both on the development split only, and keep the
one with more passes on the development questions (fewer regressions on a tie). Only the kept set runs on the holdout,
once, for the gate. The holdout is never used to choose between the two, so the gate's measurement
stays unbiased. Cost as proposed: one more analyzer team step and one more 25-run experiment on the development questions, about 0.04
dollars; as built, both candidates run on the development split (50 runs), about 0.08 dollars (Analyzer comparison).

make spend at the end (09:40 UTC): development live checks 1.1290 of 1.50 (the correction row
included), calibration 1.1590 of 2.50, reserve 0; this session, development 0.3482 of 0.40,
calibration 0.5277 of 1.00, total 1.7609 of 2.50 with the assignment verification line. The
ledger agreed with the run records within a few thousandths of a dollar for each step (the five
planted halves, about 0.058 in the ledger against 0.063 in the runs).

## Live session of 23 October, afternoon

Session ae67ee60 (purpose development) from 16:50 UTC, after the changes of the midday session (two
analyzer candidates, the SQL guidance check, the gate's fourth condition, the re-run of both
versions on a development question that regressed,
the spend caps, trace sampling). LangSmith still refused every trace (its monthly limit, reset on 1
November 2026), so each result below is proven by its run id, its record in ops, and the ledger.

Preflight: the drift canary as expected, 3 easy questions passed and 2 traps failed, gpt-6-luna.
`make live-smoke`: all five calls behaved as designed (an answer whose gold check passed; the fiscal year
2025 revenue question passing every grader and held by a reviewer concern about the fiscal year; a webhook
answer of 300 orders, the Eastern time day; an analyzer team step proposing 3 rules, all kept and
guarded; a refused write ending escalated with SQLSTATE 25006); each is reported as a hard failure
only because its trace is missing.

Every core demo of Sections 1 to 3, once, triggered as `make demo NAME=` triggers it, the moment
checked from the run's own record:

| Demo | Fixed system | Planted half |
|---|---|---|
| agent-simple-question | shown, 14 seconds: 405,738 orders (8d53e57c) | |
| agent-confident-wrong-answer | shown, 52 seconds: 76,981,355.95 against 64,015,091.21, 4 trap labels (f64f5dfe) | |
| agent-unbounded-rows | 27,040 tokens, held by the reviewer, 48 seconds (c30c0885) | shown: 186,689 tokens, escalated at the run budget (1ae983f2) |
| verify-malicious-sql | shown, 2 seconds: guard, guard, then 42501 (e40f9197) | shown: 25006, 25006, then 42501 (0b9814c4) |
| verify-retry-cap | shown, 20 seconds: escalated after 3 attempts (386f5a5e) | shown: 11 attempts until the 60,000-token budget (526fe0a2) |
| verify-graders-pass-still-wrong | shown, 58 seconds: graders passed, gold failed, two reviewer concerns (6630921f) | |
| events-webhook-question | shown, 16 seconds: posted unverified (be76dea9) | |
| events-approval-survives-restart | shown, 53 seconds: held, survived the restart, posted (13e0b95d) | shown: the approval lost, the run failed (035816e8) |
| events-duplicate-events | shown, 35 seconds: 1 run, 2 duplicates absorbed, 1 digest (c7bd992d) | shown: 3 answers, 2 digests (11e06819) |
| events-kill-switch-in-flight | shown, 5 seconds: stopped in flight (b497410b) | shown: posted after the switch was engaged (70235a3e) |

The export run of events-approval-survives-restart (13e0b95d) is the retake owed after the
2,000-character value cap: 7,670 tokens, against about 109,000 before the cap.

The hill-climbing chain, with the runner's spend on the calibration line:

1. Baseline: experiment 5dba42c6, version 1, holdout 2 of 15, 4 of 25 development questions, 276.8 seconds.
2. The analyzer team, two candidates on the development split only: A 18 of 25 development questions, 0 regressions, 11 rules;
   B 19 of 25 development questions, 0 regressions, 8 rules; B kept as version 8; the SQL guidance check rejected none of
   the kept candidate's rules. The overfit guard rejected one rule the critic kept,
   fiscal-quarter-from-february-start, because it copied gold SQL (20 or more tokens in a row of
   orders-by-quarter-fiscal-2026), and passed the other 8. 326 seconds for the whole step.
3. Candidate experiment 2eb8890c: version 8 holdout 14 of 15 against 2, 19 of 25 development questions, 0 regressions on
   either split, every new rule passed the overfit guard; 12 of 13 holdout trap items fixed
   (business-day-orders-november-2025 still fails); gate "Ready for human approval"; 206.5 seconds (211 seconds from the trigger).
4. Human approval, given by the build in place of the instructor and recorded with the approver's name.
   Families cleared for the unattended level on the confirmed standard: revenue, average order
   value, customers, and products; orders not cleared. Revenue cleared for the first time, with no
   re-run: its 4 holdout items each passed 3 of 3 runs in experiment 2eb8890c. Two items passed 2
   of 3 and needed no re-run (orders-by-quarter-fiscal-2026, app-average-order-value-fiscal-2026).
   One clearance re-run: business-day-orders-november-2025 failed 3 of 3, then 0 of 3 more, so
   orders stays below the unattended level.
5. The finale: the first attempt (c203dc8b) was triggered before the promotion had finished, so it
   ran under version 1 and answered 72,394,572.08 (gold failed, escalated); the cause was the driving
   script, which did not wait for the activation. Run again under version 8 (38f16596): 64,015,091.21
   dollars, gold passed, posted at the unattended level, 16,624 tokens, 0.0021 dollars; the Events
   page captured at 1280x720. The class-day safeguard was not needed and could not be shown: it
   needs a version verified in a rehearsal session.

The naive analyzer, twice (`BUG_NAIVE_ANALYZER`): each time 21 rules quoting the development questions with
no model call, all 21 flagged by the overfit guard; the candidate experiment kept the holdout at
2 of 15 (development 5 and 6 of 25), and the gate blocked the version on both counts (no holdout gain, and
the overfit guard on the new rules).

Edge cases: a question naming nothing in the schema ("What is our employee headcount by
department?") ended needs_clarification with a clarifying question (cfe052c3); the console's "Send
webhook question" sent exactly `make demo`'s question and posted unverified (f34a518d); the
output-token cap probe still said "after 0 tokens" (730953ea), which led to the fix above; every
run went on at its normal speed while LangSmith refused its traces.

The two versions called version 8: the hill-climbing reset after the chain removed the session's
experiments and decisions and then the promoted version 8, so the naive analyzer's candidate took the name
again (a defect, being fixed so that a name is never reused). Its
experiments are 37eb24f5 and 45fa8a3d; the promoted version 8 is experiment 2eb8890c.

Assignment verification in this session (assignment verification line):

| Check | Result | Spend |
|---|---|---|
| Assignment 1: Agent loop, reference | PASS, 11 of 11 | 0.48 cents |
| Assignment 2: Verification loop, reference | FAIL, 8 of 9: case 8 of the ambiguity suite ended 0 of 2 (note 1) | 2.16 cents |
| Assignment 3: Event loop, reference | FAIL, 9 of 10: the drill-down run ended blocked_budget (note 2) | 0.33 cents |
| Assignment 4: Hill-climbing loop, reference, first check | FAIL, 9 of 10: 1 confirmed regression on an item that passed under version 1 | 9.93 cents |
| Assignment 4: Hill-climbing loop, reference, second check | PASS, 10 of 10 | 8.70 cents |
| Assignment 4: Hill-climbing loop, alternative one | PASS, 10 of 10 | 14.57 cents |
| Assignment 4: Hill-climbing loop, alternative two | PASS, 10 of 10 | 13.13 cents |
| Each starter | FAIL, as designed | 0 cents |

Note 1: case 8 is "How many orders shipped to Texas in January 2026?"; it is being replaced.
Note 2: the check stack's daily token budget stopped the live run, not the solution; the budget is
being sized for a day of checks. Both are re-verified after those changes.

The paired comparisons of each loop with its protection off and on are on the
[benefits page](benefits.md).

## Live session of 23 October, evening (the capture session)

The capture session ran from 21:17 to 21:55 UTC on 23 October 2026, after the fixes of the first
review, on gpt-6-luna. LangSmith still refused traces at its monthly limit,
so each result below is proven by its run id, its record in ops, and the ledger. The console
captures of the hill-climbing chain, on the
[Section 4 evidence page](evidence/section-4-hill-climbing-loop.md#captures), come from this chain.

Every core demo of Sections 1 to 3, once, triggered as `make demo NAME=` triggers it, under the
starting knowledge, the moment checked from the run's own record:

| Demo | Fixed system | Run |
|---|---|---|
| agent-simple-question | shown, 14 seconds: 405,738 orders | 335bcbe5 |
| agent-confident-wrong-answer | shown, 37 seconds: 76,981,355.95 against 64,015,091.21, 4 trap labels | 82011f72 |
| agent-unbounded-rows | 22,862 tokens, held by two reviewer concerns, 26 seconds | 06c830b5 |
| verify-malicious-sql | shown, 2 seconds: guard, guard, then 42501 | 9359dbfe |
| verify-retry-cap | shown, 14 seconds: escalated after 3 attempts | 3e0c420d |
| verify-graders-pass-still-wrong, attempt 1 | not shown: posted with no gold check, 214 seconds | f467623b |
| verify-graders-pass-still-wrong, attempt 2 | shown, 52 seconds: graders passed, gold failed, held | 5e38f424 |
| events-webhook-question | shown, 14 seconds: posted unverified | 9f6e1d62 |
| events-approval-survives-restart | shown, 50 seconds: held, survived the restart, posted | 85609cb3 |
| events-duplicate-events | shown, 35 seconds: 1 run, 2 duplicates absorbed, 1 digest | 44077b18 |
| events-kill-switch-in-flight | shown, 3 seconds: stopped in flight, report-only level | bcf92dcb |

The fixed half of agent-unbounded-rows has no moment of its own: the demo registry allows it to end
held for approval by a reviewer concern, and the token counter is compared with the planted half.

The first attempt of verify-graders-pass-still-wrong (f467623b) did not show its moment: every
grader of its second attempt passed and the reviewer raised one concern, but the run posted with no
gold check within the 214 seconds the driving script waited. That is the symptom of calibration's
two not-shown attempts, which the change of the same night (one run's gold check can never block
the others) was meant to end. The cause is not confirmed: the run's record was not read again for
a gold check that arrived later. The second attempt (5e38f424) was shown: the graders of its third
attempt all passed, the gold check failed on both warehouses (row 1 differs from gold), and two
reviewer concerns held it for approval. Since the change, the demo was shown in the afternoon session (6630921f)
and in this second attempt, with one attempt not shown between them, so it has not yet been shown in
two consecutive live attempts.

The hill-climbing chain, with the runner's spend on the calibration line:

1. Baseline: experiment 31a76afe, version 1, holdout 2 of 15, 5 of 25 development questions, 278.8 seconds (281 seconds from the
   trigger to the result).
2. The analyzer team, two candidates on the development split only, from 20 failed development questions: A 21 of 25
   development questions, 0 regressions, 8 rules; B 10 of 25 development questions, 0 regressions, 5 rules; A kept as version 9. The critic
   dropped the December 2024 business-day holiday rule; the overfit guard rejected one rule the
   critic kept, fiscal-quarter-numbering, because it copied gold SQL (20 or more tokens in a row of
   orders-by-quarter-fiscal-2026); the SQL guidance check rejected none. 377 seconds for the whole step.
3. Candidate experiment a2ba7a5a: version 9 holdout 14 of 15 against 2, 22 of 25 development questions, 0 regressions on
   either split, every new rule passed the overfit guard; gate "Ready for human approval: v9 passes 14
   of 15 holdout items against 2, with no regressions."; 181.9 seconds (186 seconds from the trigger).
4. Human approval at 21:41:50 UTC, given by the build in place of the instructor and recorded with
   the approver's name.
5. The finale, sent at once: it was held 5 times over 50 seconds, the first time because the
   promotion of version 9 had not finished, the last because its clearance re-runs were still running;
   both named the step to wait for. Then run c91ebcc0: 64,015,091.21 dollars, gold passed, posted at the
   unattended level, 10,231 tokens, 0.0006 dollars. Families cleared for the unattended level on
   the confirmed standard: revenue, average order value, customers, and products; orders not.

The naive analyzer, once (`BUG_NAIVE_ANALYZER`), from one trigger: 20 rules quoting the development
questions with no model call, all 20 flagged by the overfit guard, saved as version 10; its candidate
experiment 02de992f kept the holdout at 2 of 15 (4 of 25 development questions, 212.4 seconds), and the gate blocked the
version on both counts. 285 seconds from the trigger to the verdict.

With this chain, the two-candidate method has two measurements, version 8 in the afternoon session and version 9 here, both
14 of 15 holdout items against 2. Revenue cleared on the confirmed standard in 2 of 6 live
promotions (versions 8 and 9), and the fiscal year 2025 revenue question was correct at the unattended level twice (38f16596
and c91ebcc0). Of the analyzer team's candidate experiments with an id in this report, 9 of 10 had
0 regressions. The naive analyzer was blocked in 3 of 3 runs since it was made deterministic (211,
256, and 285 seconds from the trigger to the verdict).

Assignment verification after the fixes of the first review (assignment verification line, checks
from 21:28 UTC on 23 October 2026, on the assignments stack):

| Check | Result | Spend |
|---|---|---|
| Assignment 1: Agent loop, reference | PASS, 11 of 11 | 0.49 cents |
| Assignment 2: Verification loop, reference | PASS, 10 of 10, with the replaced ambiguity case | 1.86 cents |
| Assignment 3: Event loop, reference | PASS, 10 of 10, with the daily token budget sized for a day of checks | 0.37 cents |
| Assignment 2: Verification loop, alternative one, with check_cap_usd set to 0.25 | Stopped cleanly at the cap (note 3) | 1.08 cents |
| Assignment 4: Hill-climbing loop, reference, later check 1 (note 4) | PASS, 10 of 10, 895 seconds | 13.58 cents |
| Assignment 4: Hill-climbing loop, reference, later check 2 (note 4) | PASS, 10 of 10, 1,320 seconds | 23.95 cents |

Note 3: this run proves the cap stop, not the alternative: 7 of 10 requirements passed, 0 failed,
and 3 were not run. It spent 1.08 cents in 100 model calls, less than the cap, because the check
starts no new run once the runs under way could take it past the cap, each priced at its whole
token budget; the kill switch stopped the runs under way and was released again. The
re-checks of each alternative against the fixed checks (about 1.25 dollars) did not fit this
session's assignment verification cap and are owed.

Note 4: both Assignment 4 checks shared the session's baseline experiment 1c933bea, which an
earlier check had run, so in the check's terms both are later checks; neither ran a baseline of
its own. A first check, which runs the baseline too, is not in this table.

## Live session of 24 October 2026

Every run below is of 24 October 2026, in UTC, on gpt-6-luna, on the code of that day (after the review of 24
October; its commit is on the [evidence page](evidence/general.md#captures)). LangSmith still refused traces at its monthly limit, so each result is
proven by its run id or experiment id, its record in ops, and the spend ledger. The demos ran from
10:43 to 10:57 UTC on the development live checks line; the Section 4 chain ran in rehearsal
session 56894641 (preflight at 11:00:55 UTC) on the calibration line; the assignment checks ran on
the assignments stack from 10:42 to about 12:10 UTC, in its live session 385150df.

### Demos, the fixed half

Every core and optional demo of Sections 1 to 3, once, every planted flag at 0, triggered as
`make demo NAME=` triggers it, the moment checked from the run's own record. Seconds are wall time
from the trigger to the checked result.

| Demo | What happened | Seconds | Run |
|---|---|---|---|
| agent-simple-question | shown: posted, 405,738 orders, three tools (note 3); 5,139 tokens | 16 | e26fcd8d |
| agent-texas-last-quarter (optional) | shown: posted, net revenue by product category, 4 joins; 32,276 tokens | 49 | 75f56196 |
| agent-confident-wrong-answer | shown: 72,394,572.08 against gold 64,015,091.21, 3 trap labels, held (note 1) | 50 | fe75848f |
| agent-unbounded-rows | 30,216 tokens, held by two reviewer concerns | 33 | e1f21cf2 |
| verify-malicious-sql | shown: the guard twice (note 3), then the grants (42501); 0 tokens | 2 | a447bfff |
| verify-cost-guard (optional) | stopped by the cost grader, a cartesian product; 0 tokens (note 2) | 2 | ac6a8270 |
| verify-retry-cap | shown: escalated after 3 attempts; 10,573 tokens | 20 | 39a23b2d |
| verify-graders-pass-still-wrong | shown: attempt 2 passed every grader, failed gold, was held (note 3) | 50 | c3cf3973 |
| events-webhook-question | shown: posted unverified; 5,405 tokens | 12 | 105ee553 |
| events-digest-now (optional) | shown: one post, labelled unverified | 30 | 1049cfd1 |
| events-approval-survives-restart | shown: held, still held after the worker restart, posted after approval | 59 | 43ec464c |
| events-duplicate-events | shown: 1 question run, 2 duplicates absorbed, 1 digest | 37 | ef8db308 |
| events-kill-switch-in-flight | shown: blocked in flight, report-only level | 4 | 2c986f56 |

The fixed half of agent-unbounded-rows has no moment of its own (the demo registry lets it end
held); its token count is compared with the planted half below.

Note 1: the trap labels were calendar_year_range, utc_truncation, and missing_internal_filter; two
reviewer concerns held the answer. Note 2: the grader's reason was "join without a condition on b
(a cartesian product)". The driving script's own moment flag for this run reads not shown, while
its detail line records the cost grader stopping the join and no statement timeout, the fixed
half's outcome in the demo registry; the cause of the flag was not looked into. Note 3: the
malicious SQL guard stopped the parse (two statements) and the statement policy; the simple
question used list_tables, describe_table, and run_query; in the graders demo, gold failed on both
warehouses (row 1 differs), and two reviewer concerns held the answer.

verify-graders-pass-still-wrong was shown here, after its shown retry of the capture session
(5e38f424). That supersedes "it has not yet been shown in two consecutive live attempts" above.

### Demos, the planted halves

From 10:52 to 10:57 UTC, one section's flags at a time, each set back to 0 afterwards:

| Demo, planted half | What happened | Seconds | Run |
|---|---|---|---|
| agent-unbounded-rows | shown: 182,654 tokens, escalated at the run budget | 12 | be82d6f6 |
| verify-malicious-sql, naive guard | shown: the read-only transaction (25006) twice, then the grants (42501) | 2 | 1d9b4169 |
| verify-cost-guard, no cost guard | shown: the statement timeout, no cost grader | 6 | 1760cdd5 |
| verify-retry-cap, no retry cap | shown: escalated after 4 attempts, by the agent itself | 33 | 7e29284d |
| events-approval-survives-restart, in memory | shown: held, then the approval lost; the run failed after approval | 41 | 88a0227a |
| events-duplicate-events, both bugs | shown: 3 question runs, 2 digests | 37 | d5817278 |
| events-kill-switch-in-flight, at claim only | shown: posted despite the kill switch | 16 | 47ad546f |

Without the retry cap the run ended otherwise than in the earlier sessions (9 and 11 attempts,
until the run budget): after its fourth attempt the agent escalated on its own, saying the grader
kept rejecting a count of 405,738 and the case needed review. The missing cap still shows: 4
attempts against the fixed half's 3.

### Edge cases

| Case | What happened | Run or id |
|---|---|---|
| The malicious write | guard, guard, 42501; with the naive guard, 25006 twice, then 42501 | a447bfff, 1d9b4169 |
| The retry cap | escalated after 3 attempts with the cap; 4 attempts without it | 39a23b2d, 7e29284d |
| An approval across a worker restart | survived and posted; with the in-memory checkpointer, lost | 43ec464c, 88a0227a |
| Duplicate events | 1 run, 2 duplicates absorbed, 1 digest; with both bugs, 3 runs and 2 digests | ef8db308, d5817278 |
| The kill switch in flight | blocked in flight at the report-only level; checked at claim only, posted | 2c986f56, 47ad546f |
| "How many VIP customers do we have?" | needs_clarification, asking what defines a VIP customer, 27 seconds | 07bb7b4a |
| "What was revenue for our loyal customers last month?" | needs_clarification, asking how loyal customers are defined, 21 seconds | 994fdcdc |
| An assignment check stopped at a low cap | STOPPED at the cap before any model call; 7 of 10 passed, 3 not run | activity verification-loop-f6e2672d |

The two clarification runs cost 0.0022 and 0.0012 dollars. The second also stated its reading of
"last month" (1 to 31 December 2025) while it asked about the undefined term.

### The hill-climbing chain and the safeguard rehearsal

In the order of step 5 of the instructor guide's day before, in rehearsal session 56894641, with
the runner's spend on the calibration line:

1. Baseline: experiment 74ff242b, version 1, holdout 2 of 15, 5 of 25 development questions, 286.6 seconds of experiment wall
   time. The driving script was resumed while it waited, so this step has no time from the
   trigger.
2. The analyzer team, two candidates on the development split only, from 20 failed development questions: A 13 of 25
   development questions, 0 regressions, 8 rules; B 14 of 25 development questions, 0 regressions, 6 rules; B kept as version 11. The critic
   dropped exclude-christmas-from-business-days; the overfit guard rejected fiscal-quarter-offset,
   because it copied gold SQL (20 or more tokens in a row of orders-by-quarter-fiscal-2026); the
   SQL guidance check rejected none. 359 seconds for the whole step.
3. Candidate experiment b50131b4: version 11 holdout 13 of 15 against 2, 16 of 25 development questions, 0 regressions on
   either split, every new rule passed the overfit guard; gate "Ready for human approval: v11 passes
   13 of 15 holdout items against 2, with no regressions."; 210.3 seconds (212 seconds from the
   trigger).
4. Human approval at 11:15:32 UTC, given by the build in place of the instructor and recorded with
   the approver's name. version 11 was the active version 5 seconds later; the unattended level was set
   at 11:15:42 UTC.
5. The finale, sent at once, was held while the clearance re-runs ran (held at 11:15:42 and still
   at 11:16:32 UTC, each time naming the re-runs). Then run e1769f0e: 64,015,091.21 dollars, gold
   passed, posted at the unattended level under version 11, 8,156 tokens, 0.0004 dollars. Families
   cleared for the unattended level: average order value, customers, and revenue. The driving
   script was resumed after this run, so the finale has no time from the trigger.
6. The safeguard, rehearsed live: `make safeguard-verify` marked version 11 with run e1769f0e;
   `make safeguard-activate` then refused, since version 11 was still the active version, and changed
   nothing; `make reset NAME=hill-climbing-loop` made version 1 active; `make safeguard-activate` made version 11
   active (promotion decision 37) with the families it had cleared in rehearsal; the unattended
   level was set again.
7. The finale on the safeguard: run 037f3718, 64,015,091.21 dollars, gold passed, posted at the
   unattended level, never held, 9,500 tokens, 0.0006 dollars, 19 seconds from the trigger.

The second chain of step 5.4 was not run. With this chain the two-candidate method has three
measurements, versions 8, 9, and 11: 14, 14, and 13 of 15 holdout items against 2, superseding "two
measurements" above. Revenue cleared on the confirmed standard in 3 of 7 live promotions (versions 8, 9,
and 11), superseding "2 of 6". Of the analyzer team's candidate experiments with an id in this
report, 10 of 11 had 0 regressions, superseding "9 of 10". The fiscal year 2025 revenue question was correct at the
unattended level in 4 runs (38f16596, c91ebcc0, e1769f0e, 037f3718). The afternoon session's "the class-day
safeguard was not needed and could not be shown" is superseded: it was shown here.

### The over-broad rule

The first attempt failed after 311 seconds: "NoLiveBaseline: no experiment of v11 was started in this live
session: run the baseline experiment now". The gate compares a candidate with an experiment
of the active version in the same live session. The reset of the safeguard rehearsal deleted the
session's experiment of version 11 (b50131b4, in reset archive 8a7b4646), and the safeguard's activation
runs no experiment, so version 11 was active with none. In class order the demo runs after the candidate
experiment, the gate's own experiment of the version then active, which fills that role.

The second attempt came after `make safeguard-activate` again (promotion decision 40). The baseline
experiment 82ad72d5 of version 11: holdout 12 of 15, 15 of 25 development questions, 211.2 seconds. Then version 11 plus the over-broad
rule, experiment 84417bfe: holdout 7 of 15 against 12, 11 of 25 development questions, 4 regressions on the development questions
(net-revenue-calendar-2024, net-revenue-by-quarter-fiscal-2025, california-net-revenue-fiscal-2026,
net-revenue-black-friday-2024) and 5 holdout regressions (net-revenue-fiscal-2026,
net-revenue-cyber-monday-2025, top-customers-fiscal-2026, bottom-states-net-revenue-fiscal-2026,
app-share-net-revenue-fiscal-2026). Gate "Blocked: v11-plus-over-broad-rule has 9 regressions on
items that passed under v11." Experiment wall time 180.5 seconds; 862 seconds from the trigger to the verdict,
with the confirming re-runs, against the demo registry's 4-minute target. The driving script's
moment flag reads not shown because it looked for a field the result does not carry; the result
holds the regressions and the blocked verdict that the demo registry names.

### The naive analyzer

From a new baseline experiment, 3fc31a32, version 1, holdout 2 of 15, 4 of 25 development questions, 380.7 seconds of
experiment wall time (386 seconds from the trigger; the machine was shared with the assignment checks).
With `BUG_NAIVE_ANALYZER`, the naive analyzer wrote 21 rules, one per failed development question, with no
model call; the overfit guard flagged 21 of 21; saved as version 12. Its candidate experiment c87991fc
kept the holdout at 2 of 15 (4 of 25 development questions, 244.1 seconds), and the gate blocked the version on both
counts. 580 seconds from the trigger to the verdict. The naive analyzer has been blocked in 4 of 4 runs
since it was made deterministic (211, 256, 285, and 580 seconds), superseding "3 of 3".

### Wall time in this session

The 70-run experiments of this session took 180.5, 210.3, 211.2, 244.1, 286.6, and 380.7 seconds
at concurrency 8. The range over every 70-run experiment in this report becomes 180.5 to 459
seconds, superseding the lower end of "182 to 459" in Wall time.

### The benefits measurement

The paired comparisons of each loop with its protection off and on, in the same rehearsal
session; the analysis is on the [benefits page](benefits.md). The counts come from each run's
status and gold check:

| Measure | Without | With |
|---|---|---|
| Agent loop, 7 easy items, 3 rounds: gold passed | 12 of 21 | 17 of 21 |
| Agent loop: mean tokens; cost | 3,738; 0.0097 dollars | 4,857; 0.0083 dollars |
| Verification loop, 20 development trap items, 2 rounds: gold passed | 0 of 40 | 0 of 40 |
| Verification loop: wrong answers held for approval or escalated | 1 of 40 (escalated) | 20 of 40 (17 held, 3 escalated) |
| Verification loop: mean tokens; mean attempts; cost | 9,311; 1.1; 0.0361 dollars | 17,344; 1.88; 0.0605 dollars |

With the verification layer on, 19 of the other 20 wrong answers were approved by the reviewer
and posted. The arms: for the agent loop, without is "column names only, unbounded rows, no
scout" and with is "full column descriptions, capped rows, the scout"; for the verification loop,
without is "naive guard, no reviewer" and with is "the full verification layer". The
verification-loop items come from experiment 9739f3f1 of version 1. The measurement script's summary
field for held or escalated answers reads 40 of 40 in both arms; the run statuses give the counts
above, so that field is not used.

### Assignment checks

Each check's result, its wall time, and its own "Spend:" line, on the assignment verification
line:

| Check | Result | Seconds | Spend |
|---|---|---|---|
| Assignment 1: Agent loop, starter | FAIL, 0 of 11, as designed | not recorded | 0 cents, 0 calls |
| Assignment 2: Verification loop, starter | FAIL, 0 of 10, as designed | not recorded | 0 cents, 0 calls |
| Assignment 3: Event loop, starter | FAIL, 0 of 10, as designed | not recorded | 0 cents, 0 calls |
| Assignment 4: Hill-climbing loop, starter | FAIL, 1 of 10, as designed | not recorded | 0 cents, 0 calls |
| Assignment 1, reference | PASS, 11 of 11 | 121 | 0.42 cents, 43 calls |
| Assignment 1, alternative one | PASS, 11 of 11 | 129 | 0.49 cents, 49 calls |
| Assignment 1, alternative two (suspect, note 5) | PASS, 11 of 11 | 128 | 0.48 cents, 45 calls |
| Assignment 2, reference (suspect, note 5) | PASS, 10 of 10 | 218 | 2.01 cents, 145 calls |
| Assignment 2, alternative one | PASS, 10 of 10 | 228 | 1.75 cents, 150 calls |
| Assignment 2, alternative two | PASS, 10 of 10 | 253 | 1.56 cents, 132 calls |
| Assignment 2, reference, check_cap_usd 0.005 | STOPPED at the cap, 7 of 10 passed, 3 not run (note 2) | not recorded | 0 cents, 0 calls |
| Assignment 3, reference | PASS, 10 of 10 | 180 | 0.50 cents, 14 calls |
| Assignment 3, alternative one | PASS, 10 of 10 | 141 | 0.29 cents, 10 calls |
| Assignment 3, alternative two | PASS, 10 of 10 | 170 | 0.45 cents, 15 calls |
| Assignment 4, reference, first check (note 3; suspect, note 5) | PASS, 10 of 10 | 1,319 | 23.59 cents, 1,671 calls |
| Assignment 4, alternative one, later check (suspect, note 5) | PASS, 10 of 10 | 857 | 13.64 cents, 893 calls |
| Assignment 4, alternative two, later check | PASS, 10 of 10 | 1,577 | 19.22 cents, 1,264 calls |

Every starter failed as designed, and the reference and both alternatives of every assignment
passed. Four of these checks are suspect (note 5), so they stand as evidence of nothing; the clean
checks of 25 October supersede them.

Note 2: the check prints its cap rounded, "stops at 0.01 dollars". One run priced at its whole
token budget would pass the cap, so the check started no live run and made no model call; its 7
deterministic requirements passed and its 3 live ones read NOT RUN. It exited with the stopped
code, 2.

Note 3: the reference ran its own baseline, experiment edc342f4 of version 1, because the session's
baseline 1c933bea had measured 46 items otherwise than they are now; it is the first measured
Assignment 4 check with two candidates that runs a baseline. Candidates: A 21 of 28 development questions, 8 rules;
B 25 of 28 development questions, 9 rules; B kept; the critic dropped the planted rule in both; the gate promoted
the candidate at 16 of 18 holdout items against 2, 0 confirmed regressions, the new family 3 of 3.
Alternative one shared edc342f4: A 12 of 28 development questions, 0 regressions, 10 rules, kept over B, 25 of 28
development questions with 1 regression; promoted at 13 of 18 against 2, 0 confirmed regressions, the new family 0
of 3 (measured, not required). Alternative two shared edc342f4 too: A and B both 9 of 28 development questions with
0 regressions, B kept with 8 rules against 11; promoted at 8 of 18 against 2, 0 confirmed
regressions, the new family 0 of 3. This supersedes note 4's "a first check, which runs the baseline
too, is not in this table": one is now measured, at 23.59 cents and 1,319 seconds, but it is suspect
(note 5), so no clean first check is measured.

Note 5: suspect. Demonstration captures switched planted bugs on in the shared `.env` while these
checks started their stacks, and a check's copy of the repository links that `.env`. Assignment 1
alternative two and the Assignment 2 reference started theirs during the planted halves, 10:52 to
10:57 UTC; the Assignment 4 reference and alternative one during the naive analyzer's window, 11:28
to 11:41 UTC. The clean checks of 25 October supersede all four; alternative one of
Assignment 4 passed its clean check of 25 October once. The check now switches every planted bug off on its
own Compose project, whatever `.env` says.

### Spend

The build total, as the checks logged it, passed the 6-dollar warning line during the session:
6.0342 dollars at 11:17:37 UTC, 6.7152 at 11:40:08, and 6.9913 at 11:57:22. `make spend` at 12:20
UTC, this session's lines against the session's own caps:

| Line | This session | Session cap |
|---|---|---|
| development live checks | 0.0456 dollars | 1.20 |
| calibration | 0.8127 dollars | 1.20 |
| assignment verification | 0.6439 dollars | 1.40 |
| rehearsal | 0.0041 dollars | 0.20 |
| total | 1.5063 dollars | 4.00 |

The assignment verification line agrees with the checks' own "Spend:" lines: they sum to 0.6440
dollars (the starters and the cap stop recorded no ledger rows).

## Live session of 25 October 2026

Every run below is of 25 October 2026, in UTC, on gpt-6-luna. LangSmith still refused traces at
its monthly limit, so each result is proven by its run id or experiment id, its record in ops, and
the spend ledger. The run-through of the class story ran in rehearsal session c18bcc2e (preflight at 12:42:50
UTC): every core demo of Sections 1 to 3 in class order, both halves, then the Section 4 chain,
the class-day safeguard, and the naive analyzer. Its planted halves were switched through `.env`
and `make up`, as the course did then; `make demo NAME=<demo> PLANTED=1` came later the same day.
The same stack then ran the image retakes and two more hill-climbing chains, and the assignments
stack ran the assignment verification.

### The machine

The build machine, Ubuntu on WSL2: `make up` took 63 seconds with the image already built. The six
class services used about 625 mebibytes (MiB) of memory: postgres 248, api 92, worker 90, the
hill-climbing runner 87, the scheduler 56, and the console 51. Docker held 4.2 gigabytes (GB) of
volumes and 6.6 GB of images, and uv's cache 1.2 GB, with the build's assignment and test stacks
beside the class stack.

### Demos, the fixed halves

Every core demo of Sections 1 to 3, once, in class order, from 12:42 to 12:47 UTC. Seconds are
wall time from the trigger to the checked result.

| Demo | What happened | Seconds | Run |
|---|---|---|---|
| agent-simple-question | shown: posted, 405,738 orders, three tools; 5,130 tokens | 16 | f415f991 |
| agent-confident-wrong-answer | shown: 72,394,572.08, gold 64,015,091.21, 3 trap labels, held; 18,751 tokens | 35 | 581e2720 |
| agent-unbounded-rows | 26,683 tokens, held by two reviewer concerns | 30 | 3bc3a42d |
| verify-malicious-sql | shown: the guard twice, then the grants (42501); 0 tokens | 2 | fee55255 |
| verify-retry-cap | shown: escalated after 3 attempts; 10,579 tokens | 16 | 38cea357 |
| verify-graders-pass-still-wrong | shown: attempt 3 passed every grader and failed gold; approved, posted | 48 | 730615ce |
| events-webhook-question | shown: posted unverified; 7,474 tokens | 14 | c4f16531 |
| events-approval-survives-restart | shown: held, still held after the worker restart, posted after approval | 60 | 9dd82764 |
| events-duplicate-events | shown: 1 question run, 2 duplicates absorbed, 1 digest | 37 | e6fb7684 |
| events-kill-switch-in-flight | shown: blocked in flight, report-only level; 754 tokens | 3 | 520c3f8d |

The worker's runs of these ten demos cost 0.0102 dollars in all, from each run's own record.

### Demos, the planted halves

From 12:47 to 12:52 UTC:

| Demo, planted half | What happened | Seconds | Run |
|---|---|---|---|
| agent-unbounded-rows | shown: 187,030 tokens, escalated | 12 | eeaa4e24 |
| verify-malicious-sql, naive guard | shown: the read-only transaction (25006) twice, then the grants (42501) | 2 | 099c03e7 |
| verify-retry-cap, no retry cap | shown: 13 attempts, until the 60,000-token run budget; 61,645 tokens | 49 | b5d14c28 |
| events-approval-survives-restart, in memory | shown: held, still held after the restart, failed after approval | 41 | b62d3c7e |
| events-duplicate-events, both bugs | shown: 3 question runs, 2 digests | 33 | 46c9a1c9 |
| events-kill-switch-in-flight, at claim only | shown: posted despite the kill switch | 30 | c06d22f1 |

These six runs cost 0.0262 dollars, from each run's own record.

### The hill-climbing chain and the safeguard rehearsal

In class order, in rehearsal session c18bcc2e, with the runner's spend on the calibration line:

1. Baseline: experiment a8801f38, version 1, holdout 2 of 15, 4 of 25 development questions, 252 seconds from the trigger.
2. The analyzer team, two candidates on the development split only, from 21 failed development questions: A 7 of 25 development questions,
   0 regressions, 8 rules; B 24 of 25 development questions, 0 regressions, 9 rules; B kept as version 15. The overfit guard
   rejected fiscal-quarter-assignment, which copied gold SQL (20 or more tokens in a row of
   orders-by-quarter-fiscal-2026). 362 seconds for the whole step.
3. Candidate experiment 2c7414d9: version 15 holdout 13 of 15 against 2, 25 of 25 development questions, 0 regressions on
   either split, every new rule passed the overfit guard; gate "Ready for human approval: v15 passes
   13 of 15 holdout items against 2, with no regressions."; 237 seconds from the trigger.
4. Human approval at 13:06:38 UTC, given by the build in place of the instructor and recorded with
   the approver's name. version 15 was the active version 5 seconds later; the unattended level was set
   at 13:06:45 UTC.
5. The finale, sent at once, was held while the clearance re-runs ran (14 holds, each naming the
   re-runs). Then run cb8d3beb: 64,015,091.21 dollars, gold passed, posted at the unattended level
   under version 15, 10,240 tokens, 0.0007 dollars, 162 seconds from the first send. Families cleared for
   the unattended level: average order value, customers, products, and revenue.
6. The safeguard, rehearsed live: `make safeguard-verify` marked version 15 with run cb8d3beb;
   `make safeguard-activate` refused, since version 15 was still the active version, and changed nothing;
   `make reset NAME=hill-climbing-loop` made version 1 active; `make safeguard-activate` made version 15 active
   (promotion decision 48) with the families it had cleared; the unattended level was set again.
7. The finale on the safeguard: run a2de1570, 64,015,091.21 dollars, gold passed, posted at the
   unattended level, never held, 12,395 tokens, 0.0005 dollars, 21 seconds from the trigger.

### The naive analyzer

From a new baseline experiment, dd36c4f5, version 1, holdout 2 of 15, 4 of 25 development questions, 252 seconds from the
trigger. With `BUG_NAIVE_ANALYZER`, the naive analyzer wrote 21 rules, one per failed development question,
with no model call; the overfit guard flagged 21 of 21; saved as version 16. Its candidate experiment
5f596895 passed 0 of 15 holdout items against 2, with 2 holdout regressions
(average-list-price-active and all-products-by-category), and the gate blocked the version. 221
seconds from the trigger to the verdict. The naive analyzer has now been blocked in 6 of 6 runs
since it was made deterministic (256, 211, 285, 580, 463, and 221 seconds), superseding "4 of 4";
the holdout never improved: 2 of 15 in five runs, 0 of 15 in this one.

### The retake chains

Two more chains ran on the same stack for the image retakes, on the development and calibration
lines:

| Step | First chain | Second chain |
|---|---|---|
| Baseline, version 1 | bbecf29e: holdout 2 of 15, development 4 of 25, 246 seconds | cf1decfc: holdout 2 of 15, development 5 of 25, 236 seconds |
| Candidate experiment | a4bfc059, version 17: holdout 12 of 15, development 24 of 25 | 15703840, version 19: holdout 13 of 15, development 23 of 25 |
| Its regressions and time | 0 regressions, 186 seconds | 0 regressions, 176 seconds |
| The finale | run bd7b4a77: gold passed, posted at the unattended level under version 17 | run fa7933bb: blocked by the daily token budget, no answer |

Both promotions cleared average order value, customers, products, and revenue. The second chain's
analyzer team wrote A, 21 of 25 development questions with 7 rules, and B, 21 of 25 with 7 rules, and kept A, as its
gate image shows. The first chain's analyzer step and both chains' analyzer times were not recorded.
The class stack's daily token budget, `budgets.tokens_per_day`, was spent by the second finale: the
status line at 15:03 UTC already read 1,969,486 of 2,000,000 tokens.

### Image retakes

Sixteen console images were retaken from 14:43 to 17:51 UTC, under version 1 except the Section 4 gate
image; each is listed with its run on its section's evidence page. The planted frames among them,
from 14:53 to 15:03 UTC, ran with their flags in `.env`.

### Assignment checks

The assignments stack, with the spend on the assignment verification line. Each figure is the
check's own "Spend:" line. A check counts as clean when no planted bug was on in its stack.

| Check | Result | Spend, clean checks |
|---|---|---|
| Assignment 1: Agent loop, starter, 13:21 | FAIL, 0 of 11, as designed | 0 cents, 0 calls |
| Assignment 1, each solution twice, 13:23 to 13:33 (superseded) | PASS, 11 of 11, in 6 of 6 | 0.34 to 0.44 cents, 40 to 46 calls |
| Assignment 2: Verification loop, starter, 13:34 | FAIL, 0 of 10, as designed | 0 cents, 0 calls |
| Assignment 2, each solution twice, 13:38 to 13:57 | PASS, 10 of 10, in 6 of 6 | 1.49 to 1.92 cents, 130 to 159 calls |
| Assignment 3: Event loop, the earlier drill-down question | starter FAIL; reference PASS in 2 of 4; each alternative 2 of 2 | 0.21 to 0.54 cents, 9 to 19 calls |
| Assignment 3, the second question, 18:29 to 18:45 (superseded) | starter FAIL, 0 of 10; every solution PASS, 10 of 10, in 6 of 6 | 0.09 to 0.41 cents, 5 to 15 calls |
| Assignment 3, the `rise_cents` question on an earlier pass rule, 20:33 to 20:47 (superseded) | starter FAIL, 0 of 10; every solution PASS, 10 of 10, in 6 of 6 | 0.19 to 0.31 cents, 8 to 12 calls |
| Assignment 1 on the code that ships, starter, 22:35 | FAIL, 0 of 11, as designed | 0 cents, 0 calls |
| Assignment 1 on the code that ships, each solution twice, 22:37 to 22:46 | PASS, 11 of 11, in 6 of 6 | 0.39 to 0.47 cents, 42 to 50 calls |
| Assignment 3 after the fix of 22:33, starter, 22:47 | FAIL, 0 of 10, as designed | 0 cents, 0 calls |
| Assignment 3 after the fix of 22:33, each solution twice, 22:49 to 22:58 | PASS in 5 of 6: alternative one failed its first check, 9 of 10 | 0.19 to 0.33 cents, 7 to 10 calls |
| Assignment 4: Hill-climbing loop, starter, 14:18 | FAIL, 1 of 10, as designed | 0 cents, 0 calls |
| Assignment 4, reference twice, 16:56 and 17:11 | PASS, 10 of 10, in 2 of 2: promoted at 14 and 13 of 18 | 14.53 and 12.91 cents, 968 and 878 calls |
| Assignment 4, each alternative once, 18:59 and 19:18 | PASS, 10 of 10, in 2 of 2: promoted at 16 and 5 of 18 | 12.62 and 17.09 cents, 875 and 1,193 calls |

"The code that ships" has one meaning here, given with the captures on the
[evidence page](evidence/general.md#captures): no later commit changed the check, its starter or
solutions, or the platform code they run. Assignment 1's checks from 22:35 UTC are on it. The
Assignment 2 and Assignment 4 checks ran before the change to the check's stack at 19:35 UTC; the
evidence page names the commit each ran on. That change and the later ones refuse or block only runs made with a planted flag on,
or stop a check before it starts, so they cannot alter the verdicts of these checks, which ran with
every planted flag off.

Assignment 3's two failures were the reference's drill-down runs: each never posted and ended
escalated, at 60,693 tokens in the second (activities 0ebc1c2b and 972b166b). The drill-down
question changed after them, at 18:07 UTC, to one the warehouse can answer. Re-checked on the new
question: see the captured README of Assignment 3.

Suspect, and replaced by the checks above: the first Assignment 3 checks, from 13:59 UTC, whose
stacks started while the retakes had the missing retry cap, the missing idempotency, and the kill
switch at claim only with demo pacing switched on in `.env` (the reference and alternative two
passed both checks, alternative one failed both, on the missing idempotency); and the first two
Assignment 4 reference checks, from 14:18 UTC (14.21 and 13.32 cents), whose stacks started during
the image retakes' planted windows. The Assignment 4 starter of that round fails before any model
call, so it stands.

After the question change, `make verify-assignments NAME=event-loop` re-checked Assignment 3 on the
new drill-down question, from 18:29 to 18:45 UTC: the starter failed, 0 of 10, as designed, and
every solution passed both of its checks, 6 of 6 (0.09 to 0.41 cents a check, 5 to 15 calls).
The solutions' question then asked for the top category's row alone, in a column named
`rise_cents` (19:35 UTC), and requirement 10 began judging the posted answer's text alone, with the
gold category named first (20:23 UTC). Re-checked on that code from 20:33 to 20:47
UTC: the starter failed, 0 of 10, and every solution passed both of its checks, 6 of 6 (0.19 to
0.31 cents a check, 8 to 12 calls; drill-down runs of 19,885 to 33,782 tokens). Assignment 1's
requirement 6 became a behaviour check at 20:23 UTC, after its checks of 13:21 to 13:33.

At 21:52 UTC the solutions' question began asking for the rise in cents, requirement 10 began
judging the category the answer says rose most (from its own row, else its text), and
requirement 6 of Assignment 1 also closed the superuser address and `POSTGRES_PORT`; the test
database guard landed in the same change, and the fix that lets the api start again at 22:33 UTC.
On that code, `make verify-assignments NAME="event-loop agent-loop"` ran from
22:35 UTC. Assignment 1's checks are on the code that ships. Assignment 3's ran with one
drill-down run a check, before later changes to how requirement 10 reads the answer's text, one of
which can fail an answer judged on its row when its text says another category rose most, and
before requirement 10 began passing on 2 of 3 runs (26 October 2026). The captures store each
verdict and not the answer text, so only the failure could be judged again with the current judge,
and it fails under it too ([evidence](evidence/general.md#captures)). Assignment 1: the starter failed, 0 of 11, and each solution passed 11 of 11 twice, 6 of 6
(0.39 to 0.47 cents a check, 42 to 50 calls). Assignment 3: the starter failed, 0 of 10; the
reference and alternative two passed both of their checks, and alternative one failed its first
and passed its second, 5 of 6 (0.19 to 0.33 cents a check, 7 to 10 calls; drill-down runs of
18,200 to 33,324 tokens). In the failed check the agent's posted answer said Hiking rose most,
against the gold Water Sports, and requirement 10 failed it, as it must fail a wrong answer; the
run, and why it was the agent's run-to-run variation and not the solution, is on the
[evidence page](evidence/general.md#captures). These are the published captures,
and they supersede the Assignment 1 checks of 13:21 to 13:33 and the Assignment 3 checks of 20:33
to 20:47.
Each Assignment 4 alternative then ran once (`ONCE=1`), sharing baseline edc342f4: alternative one
passed 10 of 10 at 18:59 UTC, promoted at 16 of 18 against 2 (12.62 cents, 875 calls);
alternative two passed 10 of 10 at 19:18 UTC, promoted at 5 of 18 against 2 (17.09 cents, 1,193
calls). Their second checks are owed to rehearsal.

The check now switches every planted bug off on its own Compose project, whatever `.env` says,
and the build runs one live job at a time.

### What this session supersedes

- The two-candidate method has seven measurements, versions 8, 9, 11, 13, 15, 17, and 19: 14, 14,
  13, 14, 13, 12, and 13 of 15 holdout items against 2, superseding "three measurements".
- Revenue cleared on the confirmed standard in 7 of 11 live promotions (versions 8, 9, 11, 13, 15, 17,
  and 19), superseding "3 of 7".
- Of the analyzer team's candidate experiments with an id in this report, 14 of 15 had 0
  regressions, superseding "10 of 11".
- The fiscal year 2025 revenue question was correct at the unattended level in 8 runs: the 4 of 24 October above,
  59174f10 of the capture chain of 24 October, and cb8d3beb, a2de1570, and bd7b4a77.
- Times from the trigger over every recorded run: the baseline 236 to 386 seconds; the candidate
  experiment 176 to 337 seconds; the finale after a promotion, from its first send, 50 seconds of
  holds once, then 74, 115, and 162 seconds. 70-run experiments ran 171.3 to 459 seconds of experiment
  wall time, superseding the lower end of "180.5 to 459".

The session recorded no `make spend` line of its own here; each run's cost is in its row.

## Retakes still owed

Every live run below is a retake from the "Demos" and "Not run" parts, plus the analyzer measurement
prepared above. Each item says whether it has run and where its result is. The costs are projections at the measured 0.0011 dollars per analyst
run: together about 0.42 dollars, or 0.50 with the starting experiment, against the 1.87 dollars
left on the calibration line. Demo runs go through the stack's worker and runner, which record under
"development" (see Spend). Each demo runs twice with `make reset NAME=<section slug>` between the
two attempts, as the live demo runbook asks. A planted half ran then with its flag set to 1 in
`.env` and `make up`; it now runs as `make demo NAME=<demo> PLANTED=1`, with `.env` unchanged.

1. [x] Start the session: `make up`, then `make preflight PURPOSE=development` (the drift canary,
   0.0053 dollars on 23 October; session e12c9e88). Items 2 to 7 then ran without trace links, each
   proven by its run id, its record in ops, and the ledger (above).
2. [x] The three demo retakes, twice each (all shown, 23 October, above) (about 6 runs, 0.01 dollars):
   `make demo NAME=agent-confident-wrong-answer`, `make demo NAME=verify-graders-pass-still-wrong`,
   `make demo NAME=events-webhook-question`.
3. [x] The five planted halves (all shown twice, 23 October, above), twice each (about 20 runs, 0.05 dollars in all; the retry cap's runs
   are the largest share, each running to the 60,000-token cap):
   `make demo NAME=agent-unbounded-rows` with `BUG_UNBOUNDED_ROWS`,
   `make demo NAME=verify-retry-cap` with `BUG_NO_RETRY_CAP`,
   `make demo NAME=events-approval-survives-restart` with `BUG_MEMORY_CHECKPOINTER`,
   `make demo NAME=events-duplicate-events` with `BUG_NO_IDEMPOTENCY` and `BUG_RANDOM_DIGEST_ID`,
   `make demo NAME=events-kill-switch-in-flight` with `BUG_KILLSWITCH_AT_CLAIM_ONLY`.
4. [x] (twice in the afternoon session of 23 October, blocked both times, above; first run on 23 October, moment not shown,
   before the deterministic naive analyzer was built) `make demo NAME=improve-naive-analyzer-blocked` with
   `BUG_NAIVE_ANALYZER`, twice (about 142 runs, 0.16 dollars: each attempt is the analyzer and a
   70-run candidate experiment).
5. [x] (three times, 23 October, above) The analyzer at reasoning effort high: `make calibrate STEP=analyzer-high` (about 0.10
   dollars). If it says there is no experiment of version 1 in the session, first
   `make calibrate STEP=experiment-starting` (about 0.08 dollars).
6. [x] (version 5 promoted; revenue not cleared, above) A second chain of the finale, under the confirmed standard:
   `make demo NAME=improve-candidate-experiment`, approve the candidate on the Improve page, then
   `make demo NAME=improve-cleared-unattended` (about 75 runs, 0.09 dollars, plus about 0.0033
   dollars for each holdout item that falls short at clearance; at most 45 such runs, 0.05 dollars).
   Record which families cleared and every clearance re-run.
7. [x] `make spend`, and the results written into this report.
8. [x] (the afternoon session of 23 October: version 8 at 14 of 15, the finale correct at the unattended level, above) The finale chain with two
   candidates and the SQL guidance check: the baseline experiment if none is open in the session
   (about 0.09 dollars), `make demo NAME=improve-analyzer-team-approve` (two analyzer team runs
   and 50 runs on the development questions, about 0.10 dollars), approve, `make demo NAME=improve-candidate-experiment`
   (70 runs, about 0.09 dollars), then `make demo NAME=improve-cleared-unattended` (one run, about
   0.002 dollars, plus at most 0.05 dollars of clearance re-runs): about 0.25 dollars, 0.34 with
   the baseline. Record both candidates, the one kept, the guidance rejections, which families
   cleared, and the answer to the fiscal year 2025 revenue question against gold. If the answer to the fiscal year 2025 revenue question is wrong, run the class-day
   safeguard live too (`make safeguard-activate BY="<name>"`, then the finale again) and record both.
9. [x] (the afternoon session of 23 October, above) `make live-smoke` once (about 0.006 dollars, development live checks).
10. [x] (the afternoon session of 23 October, results above) One live check of each reference solution of Assignments 1,
    2, and 3 (about 0.03 dollars in all, assignment verification), then Assignment 4's reference
    twice and each alternative once (about 0.76 dollars, assignment verification).
11. [x] (the afternoon session of 23 October: 7,670 tokens, run 13e0b95d) The export run of events-approval-survives-restart
    once (about 0.01 dollars, development live checks).
12. [ ] (owed) The output-token cap probe, `make calibrate STEP=output-token-cap`
    (about 0.0001 dollars), and the console's "Send webhook question" once (about 0.002 dollars).
13. [ ] (owed on or after 1 November 2026 at 00:00 UTC, when LangSmith's monthly
    trace limit resets) One baseline experiment and one demo run, to see about one experiment run in
    five arrive whole and every demo run traced (about 0.14 dollars).
14. [ ] (owed) The planted halves through `make demo NAME=<demo> PLANTED=1` with `.env` unchanged,
    as class runs them: the class run-through of 25 October still set its flags in `.env` and ran
    `make up`. That includes the approval demo's tagged worker restart (two restarts, the
    terminal's wait, and Ctrl+C), and the console's Improve > Run the naive analyzer (planted)
    once. The runs are those of a class run-through's planted halves, about 0.03 dollars.
15. [ ] (owed to rehearsal) The Section 4 finale frames and the promotion image, about 0.30
    dollars.

The midday session of 23 October 2026, from 11:56 UTC, made no live run: any spend waited on a comparison of
the ledger with OpenAI's usage page, and that figure was not yet available, so nothing was spent.
Items 4 and 8 to 12 together are about
1.31 dollars, inside that session's caps (development live checks 0.20, calibration 0.60, assignment
verification 1.10). Items 4 and 8 must record under calibration: the activity header of `make demo`
reaches event-loop jobs, but the hill-climbing runner records its experiments under its own activity
from `.env` (development, whose session cap is 0.20). So, before items 4 and 8, set
`DATAPILOT_SPEND_ACTIVITY=calibration` in `.env` by key and `make up`, and set it back to development
afterwards.

Not a retake: improve-baseline-experiment exceeds its 3-minute target (266 and 285 seconds) in every
run; that is a target or scope decision, not a run owed.

## Changes recorded

Each change's commit is listed on the [evidence page](evidence/general.md).

| Change | Why |
|---|---|
| The analyst answers with stated assumptions (first change below) | The fiscal year 2025 revenue question returned a clarifying question |
| Agent SQL may not read the database clock | A question about the previous day answered 0 (below) |
| A refused write ends the run escalated | Decision of 22 October |
| The cost grader estimates read-only SELECT statements only | A write past the guard must meet the read-only transaction first (25006) |
| An approved query is not held again in the same run | One export asked for the same approval three more times |
| Personal-data routing holds a query that returns a personal column (below) | Correct candidate queries were held, so none could be scored (below) |
| The reviewer sees the business date | A correct answer was held |
| Gold checks cannot block each other | Two runs of the fiscal year 2025 revenue question got no gold check |
| Holdout: three items replaced, then restored | Replacing unstable items did not converge |
| Traps: no change | No trap passed in 99 runs |
| N: no change in class code | The recommended value, 3, built by Assignment 4 |
| A family is cleared on the gate's confirmed standard | Decision of 23 October: revenue cleared in one measurement of four |

In full: the analyst answers with stated assumptions, and returns needs_clarification only for a
question that names nothing in the schema, because the fiscal year 2025 revenue question returned a clarifying
question, leaving nothing for the reviewer or the gold check. A question about the previous day
answered 0 because the SQL read the database clock. Personal-data routing holds a query that returns
a personal column, not one that only filters on it: every correct candidate query filtered internal
accounts by email and was held, so no candidate could be scored. The business date change came from
a correct answer about the previous day that was held.

## Provisional markers this report resolves

| Where | Marker | Measured value |
|---|---|---|
| slides/outline.md, Section 1 numbers | class model prices, re-check after calibration | gpt-6-luna prices (below); about 0.001 dollars per analyst run |
| slides/outline.md, the unbounded rows estimate | the measured token jump | 183,639 and 185,727 tokens with the bug on; 17,298 and 19,661 fixed |
| slides/outline.md and section-1-agent-loop/concepts.md, the scout's cost | tokens and latency with and without the scout | with the scout and the reviewer: 8,648 tokens and 24.2 seconds |
| | | with the scout off: 3,853 tokens and 12.8 seconds (mean of 4 questions) |
| slides/outline.md, the confident wrong answer | the mismatch, confirmed by calibration | 76,981,355.95 against gold 64,015,091.21 (below) |
| slides/outline.md, the malicious SQL codes | the SQLSTATE codes | fixed system: guard, guard, 42501; naive guard: 25006, 25006, then 42501 |
| slides/outline.md and Section 2 notes, the retry cap | attempt count and cost per attempt | escalated after 3 attempts, 14 to 79 seconds |
| slides/outline.md and section-2-verification-loop/concepts.md, the reviewer | verdicts on the wrong answer to the fiscal year 2025 revenue question | concern in 6 runs, approve in 1 |
| section-3-event-loop/concepts.md | duplicate event: answers posted | 1 run and 2 duplicates absorbed, twice |
| section-3-event-loop/concepts.md | approval after a worker restart | the pending approval survived and the export posted after approval, twice |
| section-3-event-loop/concepts.md | in-flight run after the kill switch | stopped in flight and blocked by the kill switch, twice |
| slides/outline.md, Section 4: Hill-climbing loop | experiment wall time at concurrency 8 | 182 to 459 seconds for 70 runs (see Wall time) |
| slides/outline.md and section-4-hill-climbing-loop/concepts.md | items the stability filter replaced | 0 in the end (3 replaced, then restored) |
| slides/outline.md and section-4-hill-climbing-loop/concepts.md | N | 3 (recommendation; Assignment 4 builds it) |
| section-4-hill-climbing-loop/concepts.md | holdout passes, active and candidate; regressions | version 1: 2 of 15; versions 8 and 9: 14; version 4: 11 and 12; 0 regressions |
| section-4-hill-climbing-loop/concepts.md | naive analyzer verdict | blocked in 37eb24f5, 45fa8a3d, 02de992f: holdout 2 of 15, all rules flagged |
| docs/costs.md | measured cost per run | about 0.001 dollars per analyst run; 0.0594 to 0.0914 per 70-run experiment |
| section-4-hill-climbing-loop/demo/README.md | the hill-climbing runner and its measured times | a Compose service; times in Wall time; the analyzer team 326 and 377 seconds |

The measured values in full: gpt-6-luna costs 0.10 dollars input, 0.01 cached input, and 0.50
output per 1M tokens (pack.yaml). The fixed half of the unbounded rows demo used 17,298 and 19,661
tokens per run; the planted half, run twice on 23 October, used 183,639 and 185,727 tokens. The confident wrong
answer was 76,981,355.95 against gold 64,015,091.21 with 4 trap labels, and was held by the
reviewer.
