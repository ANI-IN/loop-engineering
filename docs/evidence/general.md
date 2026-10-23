# Evidence: the whole module

This page holds the evidence for the root README and the shared pages: the model every call ran on,
the measured costs, the build spend, the dated stop of live work, the assignment verification
passes, the setting changes made during calibration with their commits, and the source register.
Every number comes from the calibration of 22 and 23 October 2026, recorded in the
[calibration report](../calibration-report.md).

## How to use this page

Results lists each claim the shared pages make, the runs behind it, and the ids to find them.
Captures lists the assignment verification passes, by file, time, and verdict. Sources and findings
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
| Cost of one 70-run experiment | 0.0594 to 0.0828 dollars | 3358ea89, 2bcc6ac2 |
| Build spend at the end of calibration | 1.6833 dollars of 10.00 | make spend, 23 October 2026, 01:20 UTC |
| Live work stopped | OpenAI credits exhausted at 00:59 UTC, 23 October 2026 | the worker's 429 errors |
| Live session of 23 October | preflight and one live smoke check, 0.0101 dollars | session e12c9e88 |
| Live work stopped again | LangSmith's monthly trace limit, about 06:50 UTC, 23 October 2026 | 429 on every trace upload |
| Resumed without traces | cap probe, activities, budget switch, export, analyzer at high, 6 retakes | session 817427d6 |
| Live work stopped a third time | the ledger estimated a refused request at 0.81 dollars, about 08:10 UTC | run 0642c561 |
| Resumed after the ledger correction | 5 planted halves twice, the finale chain, the naive analyzer once | session b91fc3f7 |
| Build spend at the end of the session | 3.44 dollars of 10.00; this session 1.7609 of 2.50 | make spend, 23 October 2026, 09:40 UTC |

The model was read from the key check and the response metadata of the calibration step traps.
The cost of one analyst run is from the spend ledger, activities calibration-experiment and
calibration-traps.

## Captures

The assignment verification passes of 23 October 2026, one page each, with the full output, a
terminal image, a console screenshot, and the trace links of the live runs. The passes from 06:45
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

LangSmith refused traces from about 06:48 UTC, at the free plan's monthly limit of unique traces,
so most captures of these passes show the trace id without a link; the run ids, live stamps, and
spend ledger rows stand in for them. The Assignment 2 audit of the earlier failed passes, and the
Assignment 4 analysis of requirement 10, are in each folder's README.

The class story images in [docs/images](../images/README.md) are from live runs on 22 October 2026;
their run ids are on each section's evidence page.

## Sources and findings

The source register is [slides/source/sources.py](../../slides/source/sources.py): every source the
module cites, numbered in order of first use, with title, link, author, and date. Each teaching page
that cites a source ends with its own Sources list drawn from it. The module records no finding ids.

## Commits and tags

The calibration's changes, on the branch track/calibration:

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

Decisions 2, 3, and 4 of session report 2, on the branch track/analyzer:

| Commit | Change |
|---|---|
| 48546cb | SQL guidance must run over the schema; two candidates chosen on dev |
| | the naive analyzer quotes each failed question; the finale's moment restated |

The live session of 23 October, on the branch track/live-session (commit ids in the
[calibration report](../calibration-report.md)): the live probe of the output-token cap, runs
started from the console recorded under the session's activity, and the autonomy policy described
on the confirmed standard.

Commit 40f10cc makes personal-data routing hold a query that returns a personal column, not one
that filters on it.

No release tag exists yet; the tag, and how to check a copy against it, are added at release.
<!-- provisional: filled at release -->
