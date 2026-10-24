# Module: Loop Engineering - Expected output for Section 4: Hill-climbing loop

Real captures from one live session on 23 October 2026, 21:27 to 21:55 Coordinated Universal
Time (business date 31 January 2026), for comparison after class. They are never shown in class:
in class, every demo runs live. The approval was given by the build, standing in for the
instructor. The capturing browser ran in Coordinated Universal Time, so every time on the captures
is in Coordinated Universal Time; the console shows your own local time. The build's LangSmith
traces are private, so each capture names its run or experiment id instead of a trace link.

Your output will differ: run times, ids, and the agent's wording change on every run.

In the captures with the Improve page's buttons, the four buttons share one row, which cuts two
labels ("Run experiment on the active v..." and "Run experiment on the candid..."). The page now
puts them in two rows, so every label shows whole: Run experiment on the active version, Run
analyzer, and Run experiment on the candidate, then Add the over-broad rule to the active version.

Experiments trace to the LangSmith project datapilot-experiments, filtered by knowledge version.
Experiment runs are traced as a sample, about 1 run in 5, so a ledger row links to its own trace
when one of its runs was traced and reads "Not traced" otherwise. While an item has not run, its
Trace cell is blank.

## The baseline experiment

![The Improve page at the start of the baseline experiment: "Baseline, v1, active", started 21:27:06, and every holdout item marked Not run yet with a blank Trace cell](improve-baseline-experiment-running.png)

*The baseline benchmark starts: the ledger fills in as each item's runs finish.*

![The finished baseline ledger under v1: v1 passes 2 of 15 finished items; rows read Passed 3 of 3 runs or Failed 0 of 3 runs, some with a Trace link and some Not traced](improve-baseline-experiment-ledger.png)

*Under the starting knowledge v1, 2 of 15 holdout items pass, and 5 of 25 dev items (experiment 31a76afe, 278.8 seconds).*

## The naive analyzer, blocked

![The Improve page after the naive analyzer: the knowledge diff from v1 to v10 under the line "Naive analyzer: 20 rules, no critic; the overfit guard flags 20 of 20, not applied."](improve-naive-analyzer-blocked-guard.png)

*The naive analyzer writes 20 rules, one per failed dev item; the overfit guard flags all 20, and its verdict is not applied.*

![The candidate ledger for v10 with every row No change, then "Gate: blocked." v10 has 20 rules the overfit guard rejects, each named, starting answer-net-revenue-calendar-2024](improve-naive-analyzer-blocked-gate.png)

*The gate blocks v10: it passes 2 of 15 holdout items against 2 and 4 of 25 dev items, and every rule it adds fails the overfit guard (experiment 02de992f).*

The naive analyzer makes no model call: one trigger made two requests, the analyzer and the
candidate experiment. Each of its rules quotes a benchmark question word for word, which is what
the overfit guard catches.

## The analyzer team and approval

![The knowledge diff from the active version v1 to v9, under the line "Candidate A: 21 of 25 dev, 0 regressions, 8 rules; Candidate B: 10 of 25 dev, 0 regressions, 5 rules; chosen: A"](improve-analyzer-team-diff.png)

*The analyzer team writes two candidates, runs each on the dev split only, and keeps candidate A as v9.*

The failure analyst read the 20 failed dev items. For candidate A, the rule writer proposed ten
rules; the critic dropped one (a business-day holiday rule), and the overfit guard rejected one
(`fiscal-quarter-numbering`, which copied a reference query). The eight kept rules each carry
Structured Query Language (SQL) guidance that runs over the schema: the first, `eligible-orders`,
has `o.status <> 5 AND lower(c.email) NOT LIKE '%@harborpine.com'`, below the part of the diff this
capture shows.

## The candidate experiment

![The holdout ledger comparing v1 and v9: v1 passes 2 of 15, v9 passes 14 of 15, 12 fixed and 0 regressions, rows marked Fixed: now passes or No change](improve-candidate-experiment-ledger.png)

*v1 passes 2 of 15 holdout items, v9 passes 14 of 15: 12 fixed and 0 regressions (experiment a2ba7a5a, 181.9 seconds).*

![The gate's verdict above the knowledge diff: "Gate: ready for human approval." v9 passes 14 of 15 holdout items against 2, with no regressions](improve-candidate-experiment-gate.png)

*The gate is ready for human approval: more holdout passes and no regressions on either split; v9 also passes 22 of 25 dev items.*

## The promotion

![The status line after the promotion at the unattended level: revenue, average order value, customers, and products cleared, orders not cleared; the ledger reads "Replaced, v1" and "Active, v9"](improve-promotion-cleared.png)

*After approval the gate promotes v9; a family is cleared when every one of its holdout items passes on the confirmed standard.*

The ledger header after "Active, v9, promoted by" names the approver as it was typed in the course
build's capture session, a note of that session rather than a person: in class it names the
instructor who approves.

The confirmed standard: an item passes at 2 of 3 runs in the candidate experiment, and an item that
falls short gets 3 more runs and passes at 2 of 3 of them. Revenue, average order value, customers,
and products are cleared; orders is not, because one of its holdout items did not pass. While the
promotion and its clearance re-runs finished, the finale was held 5 times over 50 seconds, each
time naming the step still running.

## Cleared for the unattended level

![The Events page at the unattended level with four families cleared, and the spine question "What was our net revenue in fiscal year 2025?" in the Done lane, posted at the unattended level](improve-cleared-unattended-board.png)

*The spine question arrives as a webhook under the new active version.*

The console now also shows the run's gold check on its strip, "Gold check passed: 64,015,091.21"
here, a few seconds after the post; this capture was taken before the strip showed it.

![The Channel post "Posted at the unattended level, unattended": net revenue in fiscal year 2025 was 64,015,091.21 dollars](improve-cleared-unattended-channel.png)

*The answer is correct and matches gold, and it posts at the unattended level, without approval.*

Revenue is cleared in this run, so with the system set to the unattended level, the revenue answer
posts without approval. Run c91ebcc0, under v9.
