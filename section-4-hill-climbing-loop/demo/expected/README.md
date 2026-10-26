# Module: Loop Engineering - Expected output for Section 4: Hill-climbing loop

Real captures from one hill-climbing chain run live on 24 October 2026, 14:10 to 14:37 Coordinated
Universal Time (business date 31 January 2026), for comparison after class. They are never shown in
class: in class, every demo runs live. The approval was given by the course build, standing in for the
instructor. The capturing browser ran in Coordinated Universal Time,
so every time on the captures is in Coordinated Universal Time (UTC); the console shows your own
local time. The build's LangSmith traces are private, so each capture names its run or experiment
id instead of a trace link.

This chain, the capture chain, is not the session's main chain of the same day, whose candidate was
v11 (13 of 15 holdout items against 2); every image here comes from the capture chain, whose
candidate is v13, except the gate's verdict, retaken on 25 October 2026 in a chain whose candidate
is v19.

Your output will differ: run times, ids, and the agent's wording change on every run.

Experiments trace to the LangSmith project datapilot-experiments, filtered by knowledge version.
Experiment runs are traced as a sample, about 1 run in 5, so a ledger row links to its own trace
when one of its runs was traced and reads "Not traced" otherwise. While an item has not run, its
Trace cell is blank.

## The baseline experiment

![The Improve page at the start of the baseline experiment: the status line at the report-only level, Baseline, v1, active, started 14:10:00, the line v1 passes 0 of 0 finished items; 15 not run yet, and every holdout item marked Not run yet with a blank Trace cell](improve-baseline-experiment-running.png)

*Experiment aa1d02ff, 24 October 2026: the baseline benchmark starts under v1, and the ledger fills in as each item's runs finish.*

![The finished baseline ledger under v1: v1 passes 2 of 15 finished items; the mean list price and the assortment by top-level category read Passed 3 of 3 runs, the other visible rows Failed 0 of 3 runs, some with a Trace link and some Not traced](improve-baseline-experiment-ledger.png)

*Experiment aa1d02ff, 24 October 2026: under the starting knowledge v1, 2 of 15 holdout items pass, both without a trap; every trap item in view fails.*

The same experiment passed 4 of 25 dev items, in 291.6 seconds (295 seconds from the trigger).

## The naive analyzer, blocked

![The Improve page after the naive analyzer: the knowledge diff from v1 to v14 under the line Naive analyzer: 21 rules, no critic; the overfit guard flags 21 of 21, not applied., and the first added rule, answer-net-revenue-calendar-2024, quoting a benchmark question and the query that failed](improve-naive-analyzer-blocked-guard.png)

*Candidate v14, 24 October 2026: the naive analyzer writes 21 rules, one per failed dev item, and skips the critic; the overfit guard flags all 21, and its verdict is not applied.*

![The bottom of the candidate ledger for v14 with every visible row Failed under both versions and No change, then Gate: blocked. v14 has 21 rules the overfit guard rejects, each one named, starting answer-net-revenue-calendar-2024](improve-naive-analyzer-blocked-gate.png)

*Candidate v14, 24 October 2026: the gate blocks it; v14 passes 2 of 15 holdout items, no more than v1, and every rule it adds fails the overfit guard.*

The naive analyzer makes no model call: one trigger, with the naive analyzer's planted bug
(`BUG_NAIVE_ANALYZER`) on, made the analyzer and the candidate experiment, 463 seconds from the
trigger to the verdict. On 25 October 2026 a later run of the same demo, v16, passed 0 of 15
holdout items, with 2 holdout regressions, and was blocked too. Each of its rules quotes a
benchmark question word for word, which is what the overfit guard catches.

## The analyzer team and approval

![The knowledge diff from the active version v1 to v13, under the line Candidate A: 22 of 25 dev, 0 regressions, 9 rules; Candidate B: 20 of 25 dev, 0 regressions, 8 rules; chosen: A, with the first added rule, eligible-order-customer-population, and its guidance](improve-analyzer-team-diff.png)

*Candidate v13, 24 October 2026: the analyzer team writes two candidates, runs each on the dev split only, and keeps candidate A, 22 of 25 dev items against 20.*

The failure analyst read the 21 failed dev items. For candidate A, the rule writer proposed eleven
rules; the critic dropped one (`business-day-order-dates`) and narrowed one, and the overfit guard
rejected one (`february-anchored-fiscal-quarters`, which copied a reference query), which left nine.
The rules each carry Structured Query Language (SQL) guidance that runs over the schema: the first,
`eligible-order-customer-population`, has
`o.status <> 5 AND lower(c.email) NOT LIKE '%@harborpine.com'`, the last line of the frame. The
whole step took 326 seconds.

## The candidate experiment

![The holdout ledger comparing v1 and the candidate v13: v1 passes 2 of 15, v13 passes 14 of 15, 12 fixed and 0 regressions; rows marked Fixed: now passes or No change, the working-days item still failing under both](improve-candidate-experiment-ledger.png)

*Experiment 0e1cbfe7, 24 October 2026: v1 passes 2 of 15 holdout items, v13 passes 14 of 15, 12 fixed and 0 regressions.*

The experiment took 335.6 seconds (337 seconds from the trigger). The gate's only failing check was
"human approval not given yet".

![The gate's verdict, Gate: ready for human approval. v19 passes 13 of 15 holdout items against 2, with no regressions., above the Improve page's buttons, the line The system is at the report-only level., and the start of the knowledge diff from v1 to v19, under the line Candidate A: 21 of 25 dev, 0 regressions, 7 rules; Candidate B: 21 of 25 dev, 0 regressions, 7 rules; chosen: A](improve-candidate-experiment-gate.png)

*Experiment 15703840, 25 October 2026, a later chain whose candidate is v19: the gate waits only for a person; v19 also passes 23 of 25 dev items.*

This frame was taken before the Improve page gained its Run the naive analyzer (planted) button,
so your page shows one more button than the frame, while demo controls are allowed. The retake
waits for the next Section 4 capture.

That chain's baseline passed 2 of 15 holdout items and 5 of 25 dev items (experiment cf1decfc);
the candidate experiment took 176 seconds from the trigger. Its finale was blocked by the daily
token budget, so no capture of it replaces the ones below.

## The promotion

![The status line after the promotion at the unattended level: revenue, average order value, customers, and products cleared, orders not cleared; the ledger reads Replaced, v1 and Active, v13, promoted by the course build's approver, with v13 at 14 of 15](improve-promotion-cleared.png)

*Experiment 0e1cbfe7, 24 October 2026: after approval v13 is the active version; revenue, average order value, customers, and products are cleared, orders is not.*

The ledger names the approver as the course build typed it; in class it names the instructor who
approves.

The confirmed standard: an item passes at 2 of 3 runs in the candidate experiment, and an item that
falls short gets 3 more runs and passes at 2 of 3 of them. Orders is not cleared, because one of
its holdout items, the working-days order volume, did not pass. While the promotion and its
clearance re-runs finished, the finale was held 5 times, each time naming the step still running.

## Cleared for the unattended level

![The Events page at the unattended level with four families cleared, and the spine question What was our net revenue in fiscal year 2025? in the Done lane, posted at the unattended level, with Gold check passed: 64,015,091.21 and run 59174f10](improve-cleared-unattended-board.png)

*Run 59174f10, 24 October 2026: the spine question arrives as a webhook under v13, posts at the unattended level, and its strip shows the gold check passed.*

![The run board scrolled down: Done holds the posted spine question with Gold check passed: 64,015,091.21, run 59174f10, then the v13 benchmark strip, 70 of 70 runs done, and 1 more](improve-cleared-unattended-channel.png)

*Run 59174f10, 24 October 2026: the frame stops at the Done lane and the buttons; the Channel post is below it.*

The run's answer, from its record: "Net revenue in fiscal year 2025 was $64,015,091.21.", equal to
gold, posted at the unattended level without approval, 74 seconds after the first send (the held
sends included). Its query reads fiscal year 2025 as 1 February 2024 to 31 January 2025 in New
York time, keeps `status <> 5`, and leaves out the @harborpine.com accounts. Revenue is cleared in
this chain, so with the system set to the unattended level, the revenue answer posts without
approval.

Trace: run 59174f10, under v13
