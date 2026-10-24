# Evidence: the whole module

This page holds the evidence for the root README and the shared pages: the model every call ran on,
the measured costs, the build spend, the dated stops of live work, the assignment verification
results, the setting changes made during calibration with their commits, and the source register.
Every number comes from the calibration of 22 and 23 October 2026 and the live sessions of 23
October, recorded in the [calibration report](../calibration-report.md).

## How to use this page

Results lists each claim the shared pages make, the runs behind it, and the ids to find them.
Captures lists the assignment verification checks, by file, time, and verdict. Sources and findings
points to the source register. Commits and tags lists the calibration's changes. The
[calibration report](../calibration-report.md) links here for each change's commit, and the
[evidence index](../evidence.md) links here for everything module-wide. Times are in Coordinated
Universal Time (UTC).

## Results

From the calibration of 22 and 23 October 2026 ([calibration report](../calibration-report.md)).

| Claim | Runs | Ids |
|---|---|---|
| The class model, as the application programming interface (API) returns it | gpt-6-luna on every call recorded | key check and response metadata (below) |
| Cost of one analyst run | about 0.001 dollars | spend ledger (below) |
| Cost of one 70-run experiment | 0.0594 to 0.0914 dollars, where recorded | 3358ea89, 2bcc6ac2, dde64d21, the effort-high starting experiment |
| Experiment wall time, 70 runs at concurrency 8 | 182 to 459 s | the Section 4 evidence page |
| Build spend at the end of calibration (note 1) | 1.78 dollars billed by OpenAI; the ledger then showed 1.6833 | OpenAI usage page; make spend, 23 October 2026, 01:20 UTC |
| Live work stopped | OpenAI credits exhausted at 00:59 UTC, 23 October 2026 | the worker's 429 errors |
| Live session of 23 October | preflight and one live smoke check, 0.0101 dollars | session e12c9e88 |
| Live work stopped again | LangSmith's monthly trace limit, about 06:50 UTC, 23 October 2026 | 429 on every trace upload |
| Resumed without traces | cap probe, activities, budget switch, export, analyzer at high, 6 retakes | session 817427d6 |
| Live work stopped a third time | the ledger estimated a refused request at 0.81 dollars, about 08:10 UTC | run 0642c561 |
| Resumed after the ledger correction | 5 planted halves twice, the finale chain, the naive analyzer once | session b91fc3f7 |
| Build spend at the end of the session | 3.44 dollars of 10.00 in the ledger; this session 1.7609 of 2.50 | make spend, 23 October 2026, 09:40 UTC |
| Live session of 23 October, afternoon (session 4) | each core demo and planted half of Sections 1 to 3; the finale (note 2) | session ae67ee60 |
| Live session of 23 October, evening (the capture session) | each core demo of Sections 1 to 3; the finale chain; the naive analyzer (below) | 21:17 to 21:55 UTC |

Note 1: the ledger then priced cache-write tokens as plain input, reconciled on the
[costs page](../costs.md); both figures include 0.2712 dollars of assignment verification.
Note 2: also preflight, the live smoke check, the naive analyzer twice, and assignment
verification.

In the capture session one demo, verify-graders-pass-still-wrong, was shown on its second attempt
only; the first posted with no gold check within its window, a cause not yet confirmed. The finale chain gave v9,
14 of 15 holdout items, and the spine answer correct at the unattended level.

The model was read from the key check and the response metadata of the calibration step traps.
The cost of one analyst run is from the spend ledger, activities calibration-experiment and
calibration-traps.

## Captures

The assignment verification checks of 23 October 2026, one page each, with the full output, a
terminal image, a console screenshot, and the trace ids of the live runs. The passes from 06:45
Coordinated Universal Time (UTC) replace the earlier ones of Assignments 2 and 3. With an Assignment
3 pass of 07:58 UTC that OpenAI's 504 answers stopped, and that was run again whole, they spent
1.2393 dollars, the sum of their spend lines, and the ledger's session line for assignment
verification shows the same.

| Assignment | Starter (one pass) | Reference, alternative one, alternative two (two passes each) |
|---|---|---|
| Assignment 1: Agent loop (captures published with the solutions) | FAIL, 00:05 UTC | PASS in all six, 00:06 to 00:14 UTC |
| Assignment 2: Verification loop (captures published with the solutions) | FAIL, 06:45 UTC | PASS in all six, 06:50 to 07:57 UTC |
| Assignment 3: Event loop (captures published with the solutions) | FAIL, 08:11 UTC | PASS in all six, 08:13 to 08:25 UTC |
| Assignment 4: Hill-climbing loop (captures published with the solutions) | FAIL, 08:27 UTC | PASS in 3 of 6, one per solution; FAIL in 3 on requirement 10 |

The checks of session 4 (23 October 2026, from 17:50 UTC), one each unless stated, are history
now: the check code changed after them (see the latest checks below).

| Assignment | Starter | Reference | Alternatives |
|---|---|---|---|
| Assignment 1: Agent loop | FAIL, 1 of 11, as designed | PASS, 11 of 11, 0.48 cents | not run |
| Assignment 2: Verification loop | FAIL, 1 of 9, as designed | FAIL, 8 of 9, 2.16 cents (note 3) | not run |
| Assignment 3: Event loop | FAIL, 0 of 10, as designed | FAIL, 9 of 10, 0.33 cents (note 4) | not run |
| Assignment 4: Hill-climbing loop | FAIL, 3 of 10, as designed | FAIL, 9 of 10, 9.93 cents (note 5); then PASS, 10 of 10, 8.70 cents | PASS, 10 of 10 each: 14.57 and 13.13 cents |

Note 3: the ambiguity suite's "shipped to Texas" case ended 0 of 2; that case is being replaced.
Note 4: the live drill-down run was blocked by the check stack's daily token budget
(blocked_budget), a fault of the stack, not of the solution. Note 5: 1 confirmed regression on an
item that passed under v1.

The latest checks, after the case and budget changes, on 23 October 2026 from 21:28 UTC, in one
live session; each figure is the check's own "Spend:" line:

| Assignment | Reference | Alternatives |
|---|---|---|
| Assignment 1: Agent loop | PASS, 11 of 11, 0.49 cents | not run again |
| Assignment 2: Verification loop | PASS, 10 of 10, 1.86 cents, 135 model calls | alternative one: STOPPED at a 0.25-dollar cap after 1.08 cents (note 6) |
| Assignment 3: Event loop | PASS, 10 of 10, 0.37 cents | not run again |
| Assignment 4: Hill-climbing loop, two candidates | PASS, 10 of 10, twice in a row: 13.58 and 23.95 cents | not run again |

Note 6: the spend cap was set to 0.25 dollars for that one check; with 24 cents of headroom for the
runs under way, it started no new run past 1.08 cents, and its live requirements read NOT RUN. It
is the live proof of the stop at the cap.

So every reference solution passes on the current check. The alternatives are not yet verified on
it, and the review of 24 October changed the checks again with no model call (each check's own
spend activity, the reset's port guard, Assignment 4's minimum-holdout requirement, its shared
baseline, and its kill switch): each solution is owed its live checks again, and the captures
published with the solutions predate these checks, as each captured folder's README says.

LangSmith refused traces from about 06:48 UTC, at the free plan's monthly limit of unique traces,
so most captures of these passes show the trace id without a link; the run ids, live stamps, and
spend ledger rows stand in for them. The Assignment 2 audit of the earlier failed passes, and the
Assignment 4 analysis of requirement 10, are in each folder's README.

The class story images in [docs/images](../images/README.md) are from live runs on 22 and 23
October 2026: the event loop on 22 October, the hill-climbing loop on 23 October between 21:27 and
21:55 Coordinated Universal Time, and the agent and verification loops on 23 October from 22:13
Coordinated Universal Time. Their run ids are on each section's evidence page.

## Sources and findings

The source register is [slides/source/sources.py](../../slides/source/sources.py): every source the
module cites, numbered in order of first use, with title, link, author, and date. Each teaching page
that cites a source ends with its own Sources list drawn from it. The module records no finding ids.

## Commits and tags

The calibration's changes, each a commit in the repository's history:

| Commit | Change |
|---|---|
| e5718ad | every run of a process shares one event loop (the canary's first failure) |
| 1b50629 | an item's repetitions run in repetition order |
| 0d3dc76 | the analyst answers with stated assumptions |
| | agent Structured Query Language (SQL) never reads the database clock |
| 8709427 | the analyst reads an undefined group from the data |
| | and keeps answering after feedback |
| 19a74bd | the hill-climbing runner as a Compose service; the gold check on both databases |
| 7ddec4a | a query approved in a run is not held again |
| 40f10cc | personal-data routing holds a query that returns a personal column (below) |
| 11fdb11 | a refused write ends the run escalated, with no retry |
| 56e1e39 | the cost grader estimates read-only SELECT statements only |
| 4f1a235 | three unstable holdout items replaced |
| 549afde | the original holdout items restored |
| a4b6535 | the reviewer sees the business date |
| | one run's gold check never blocks the others |

The analyzer changes after the review of 23 October:

| Commit | Change |
|---|---|
| 48546cb | SQL guidance must run over the schema; two candidates chosen on dev |
| | the naive analyzer quotes each failed question; the finale's moment restated |

The live session of 23 October (commit ids in the
[calibration report](../calibration-report.md)): the live probe of the output-token cap, runs
started from the console recorded under the session's activity, and the autonomy policy described
on the confirmed standard.

Commit 40f10cc makes personal-data routing hold a query that returns a personal column, not one
that filters on it.

No release tag exists yet; the tag, and how to check a copy against it, are added at release.
<!-- provisional: filled at release -->
