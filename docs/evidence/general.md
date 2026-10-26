# Evidence: the whole module

This page holds the evidence for the root README and the shared pages: the model every call ran on,
the measured costs, the build spend, the dated stops of live work, the assignment verification
results, the setting changes made during calibration with their commits, and the source register.
Every number comes from the calibration of 22 and 23 October 2026, the live sessions of 23
October, the live session of 24 October 2026 (session 5), and the live session of 25 October
2026 (session 6), recorded in the [calibration report](../calibration-report.md).

## How to use this page

Results lists each claim the shared pages make, the runs behind it, and the ids to find them.
Captures lists the assignment verification checks, by file, time, and verdict. Sources and findings
points to the source register. Commits and tags lists the calibration's changes. The
[calibration report](../calibration-report.md) links here for each change's commit, and the
[evidence index](../evidence.md) links here for everything module-wide. Times are in Coordinated
Universal Time (UTC).

## Results

From the calibration of 22 and 23 October 2026, the live sessions of 23 October, the live
session of 24 October 2026 (session 5, the rows marked "24 October"), and the live session of 25
October 2026 (session 6, the rows marked "25 October"), all in the
[calibration report](../calibration-report.md).

| Claim | Runs | Ids |
|---|---|---|
| The class model, as the application programming interface (API) returns it | gpt-6-luna on every call recorded | key check and response metadata (below) |
| Cost of one analyst run | about 0.001 dollars | spend ledger (below) |
| Cost of one 70-run experiment | 0.0594 to 0.0914 dollars, where recorded | 3358ea89, 2bcc6ac2, dde64d21, the effort-high starting experiment |
| Experiment wall time, 70 runs at concurrency 8 | 171.3 to 459 seconds | the Section 4 evidence page |
| Build spend at the end of calibration (note 1) | 1.78 dollars billed by OpenAI; the ledger then showed 1.6833 | OpenAI usage page; make spend, 23 October 2026, 01:20 UTC |
| Live work stopped | OpenAI credits exhausted at 00:59 UTC, 23 October 2026 | the worker's 429 errors |
| Live session of 23 October | preflight and one live smoke check, 0.0101 dollars | session e12c9e88 |
| Live work stopped again | LangSmith's monthly trace limit, about 06:50 UTC, 23 October 2026 | 429 on every trace upload |
| Resumed without traces | cap probe, activities, budget switch, export, analyzer at high, 6 retakes | session 817427d6 |
| Live work stopped a third time | the ledger estimated a refused request at 0.81 dollars, about 08:10 UTC | run 0642c561 |
| Resumed after the ledger correction | 5 planted halves twice, the finale chain, the naive analyzer once | session b91fc3f7 |
| Build spend at the end of the session | 3.44 dollars of 10.00 in the ledger; this session 1.7609 of 2.50 | make spend, 23 October 2026, 09:40 UTC |
| Live session of 23 October, afternoon (session 4) | each core demo and planted half of Sections 1 to 3; the finale (note 2) | session ae67ee60 |
| Install time, warm caches, a published clone in WSL | seconds: clone 7, setup 1, up 214, seed 65, check-data 6, preflight 58 | learner-path review, 23 October 2026, session 8f9cb8cf |
| Live session of 23 October, evening (the capture session) | each core demo of Sections 1 to 3; the finale chain; the naive analyzer (below) | 21:17 to 21:55 UTC |
| 24 October: the live session | every demo, the safeguard, every assignment check (note 8) | sessions 56894641 and 385150df |
| 24 October: build spend past the warning line | 6.0342 dollars at 11:17:37 UTC, 6.7152 at 11:40:08, 6.9913 at 11:57:22 | the warning lines the assignment checks logged |
| 24 October: spend this session, per line | 1.5063 dollars of the session's 4.00 (note 8) | make spend, 24 October 2026, 12:20 UTC |
| 25 October: the class story pass, every core demo in class order, both halves | every moment shown (note 9) | rehearsal session c18bcc2e, preflight 12:42:50 UTC |
| 25 October: `make up` with the image built | 63 seconds | the build machine, session 6 notes |
| 25 October: memory of the six class services | about 625 mebibytes (MiB) in all, postgres 248 of them | `docker stats`, the build machine |
| 25 October: disk on the build machine | Docker volumes 4.2 gigabytes (GB), images 6.6 GB, uv cache 1.2 GB | `docker system df`, `du` of the uv cache |
| 25 October: the assignment verification, clean (partly superseded) | every starter failed and every solution passed (note 9) | Captures, below; Assignments 1 and 3 superseded by note 10 |
| 25 October: Assignments 1 and 3 again, from 22:35 UTC, on commit 7c32700 | starters failed; Assignment 1 passed 6 of 6, Assignment 3 5 of 6 (note 10) | Captures, below; session 385150df |

Note 8: on 24 October the demos of Sections 1 to 3 ran both halves from 10:43 to 10:57 UTC; the
Section 4 chain, the class-day safeguard, the over-broad rule, the naive analyzer, and the benefits
measurement ran in rehearsal session 56894641; the assignment checks ran in the assignments
stack's session 385150df. The session's lines at 12:20 UTC: development live checks 0.0456,
calibration 0.8127, assignment verification 0.6439, rehearsal 0.0041 dollars.

Note 9: on 25 October the class story pass ran Sections 1 to 3 from 12:42 to 12:52 UTC, then the
Section 4 chain, the class-day safeguard, and the naive analyzer, all in rehearsal session
c18bcc2e. The memory, in mebibytes: postgres 248, api 92, worker 90, runner 87, scheduler 56,
console 51. In the clean assignment verification, each solution of Assignments 1 to 3 passed 2 of
2 (Assignment 3 on the second drill-down question, from 18:29 UTC; on the earlier one its
reference passed 2 of 4), the Assignment 4 reference 2 of 2, and each Assignment 4 alternative 1
of 1. The Assignment 1 result and the Assignment 3 result of 18:29 UTC are superseded: Assignment
3's by its re-check from 20:33 UTC (Captures, below), then both by the verification of note 10. The disk figures include the build's assignment and test stacks beside the class
stack. Each result is on its section's evidence page.

Note 10: from 22:35 UTC on 25 October, after the test database guard (commit d7e6dc5) and the fix
that lets the api start again (commit 7c32700), `make verify-assignments` checked Assignments 1 and
3 again: Assignment 1 on the code that ships, Assignment 3 on the code before a later change to
requirement 10's reading of the answer text (Captures, below). Assignment 1's starter failed, 0 of 11, and each solution passed 11 of 11
twice, 6 of 6. Assignment 3's starter failed, 0 of 10; the reference and alternative two passed
twice, and alternative one failed once on a wrong answer from the agent and then passed, 5 of 6.

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

The captures published with the solutions, one page each, with the full output, a terminal
image, a console screenshot, and the trace ids of the live runs: for Assignment 1, the
verification of 25 October 2026 from 22:35 UTC, on the code that ships; for Assignment 2, the
clean verification of 25 October 2026, on commit 29d7b2c; for Assignment 3, the verification of 25
October from 22:47 UTC, on commit 7c32700, with the drill-down question and the pass rule that
ship; for Assignment 4, the starter, the reference twice, and each alternative
once, of 25 October, with each alternative's run 2 from 23 October. Each captured folder's README lists its captures.

What "the code that ships" means on these pages: a run is on the code that ships only when no
later commit changed its assignment's check, starter, or solutions, or the platform code they run.
Any other run names the date and the commit it ran on: the newest commit of the build when the
check began, from the times in its capture. By that rule:

- Assignment 1's verification from 22:35 UTC on 25 October 2026 is on the code that ships.
- Assignment 3's verification from 22:47 UTC ran on commit 7c32700. At 23:34 UTC, commit 75e80e4
  changed how requirement 10 reads the answer's text, and left its reading of the answer's row
  unchanged. Five of its six solution checks were judged on the row, so that change cannot alter them.
  Alternative two's run 1 was judged on its text, and the new reading has not judged it.
- Assignment 2's checks, from 13:33 UTC, ran on commit 29d7b2c. Assignment 4's ran on commits
  a1428ca (the starter, 14:18 UTC), 90e946e (the reference, 16:56 and 17:11 UTC), and 887e388
  (the alternatives, 18:59 and 19:18 UTC). All of them ran before commit 5f6e617 (19:35 UTC),
  which turned demo controls off in the check's stack, and before commit d7e6dc5 (21:52 UTC).
- Since those checks, the Assignment 2 check, its starter and solutions, and the agent and
  verification loop code are unchanged. The Assignment 4 check changed only its printed typical
  cost. The platform changes refuse or block a run made with a planted flag on, refuse a run with
  no live session (the check opens its own), or stop a check before it starts. Every planted flag
  was off in these checks, so none of these changes can alter their verdicts. No check of
  Assignment 2 or 4 has run on the later code.

The verification from 22:35 UTC on 25 October 2026 (session 6), each
figure the check's own "Spend:" line and each time its capture's own. It ran after the test
database guard (commit d7e6dc5), which also made Assignment 1's requirement 6 close the superuser
address and `POSTGRES_PORT` and made Assignment 3's requirement 10 judge the category the answer
says rose most, from its own row or its text, and after the fix that lets the api start again
(commit 7c32700). Every capture's "Planted flags" line reads "none on". It supersedes the rows for
Assignment 1 and for Assignment 3's earlier pass rule in the table after it.

| Assignment | Starter | Reference | Alternatives |
|---|---|---|---|
| Assignment 1: Agent loop | FAIL, 0 of 11, as designed, 22:35 | PASS, 11 of 11, twice: 0.47 and 0.39 cents | PASS, 11 of 11, twice each: 0.42 and 0.40 cents; 0.42 and 0.43 cents |
| Assignment 3: Event loop | FAIL, 0 of 10, as designed, 22:47 | PASS, 10 of 10, twice: 0.21 and 0.19 cents | PASS in 3 of 4: 0.33 (FAIL, 9 of 10) and 0.32 cents; 0.20 and 0.22 cents |

The spend activities: Assignment 1 starter 904fc56d, then b2e9876b, d4917682, 47b442a9, f8483c83,
7e33ca9b, ccb50c19; Assignment 3 starter 4bd9fd41, then 725af595, b1ac2534, cca533f6, c922583e,
afdd710d, 6959bb0b, each under "assignment verification-" followed by the slug and the id. The
Assignment 3 drill-down runs: 7dc78543, 93627639, ca5c5e3c, 6c8dc37d, 00012315, 76230e08. So
Assignment 1 passed 6 of 6 and Assignment 3 5 of 6. Assignment 3's failure was alternative one's
first check: its drill-down run ca5c5e3c was held, approved by the check, and posted an answer
saying Hiking rose most, in its own row, against the gold Water Sports, and requirement 10 failed
it, as it must fail a wrong answer. The same files passed the next check. A correct solution can
read FAIL when the agent answers wrongly; the check is right to fail it, and the remedy is to run
it again.

The clean verification of 25 October 2026 (session 6), each figure the check's own "Spend:"
line. A check counts as clean when no planted bug was on in its stack; the check now switches
every planted bug off on its own Compose project.

| Assignment | Starter | Reference | Alternatives |
|---|---|---|---|
| Assignment 1: Agent loop, before requirement 6 changed (superseded) | FAIL, 0 of 11, as designed, 13:21 | PASS, 11 of 11, twice: 0.44 and 0.37 cents | PASS, 11 of 11, twice each: 0.43 and 0.34 cents; 0.43 and 0.41 cents |
| Assignment 2: Verification loop | FAIL, 0 of 10, as designed, 13:34 | PASS, 10 of 10, twice: 1.92 and 1.49 cents | PASS, 10 of 10, twice each: 1.69 and 1.82 cents; 1.92 and 1.83 cents |
| Assignment 3: Event loop, the earlier drill-down question | FAIL, 0 of 10, as designed | PASS in 2 of 4: 0.54 (FAIL), 0.49, 0.53 (FAIL), and 0.36 cents | PASS, 10 of 10, twice each: 0.35 and 0.41 cents; 0.21 and 0.47 cents |
| Assignment 3: Event loop, the `rise_cents` question, an earlier pass rule (superseded) | FAIL, 0 of 10, as designed, 20:33 | PASS, 10 of 10, twice: 0.23 and 0.28 cents | PASS, 10 of 10, twice each: 0.21 and 0.19 cents; 0.31 and 0.28 cents |
| Assignment 4: Hill-climbing loop | FAIL, 1 of 10, as designed, 14:18 | PASS, 10 of 10, twice: 14.53 and 12.91 cents (16:56 and 17:11) | PASS, 10 of 10, once each: 12.62 and 17.09 cents; second checks owed |

The spend activities: Assignment 1 starter 288149ba, then ed71d399, f1ae74d9, 1d0c1f11, 922b0562,
7ac16db5, d60fc9c5; Assignment 2 starter 13e2f7a7, then 893aadb9, 11a45189, b2816239, 1b1ba970,
d1e552ea, 3d047e15; Assignment 3 starter 4ce1a70a, the reference 0ebc1c2b, 384c1f79, 972b166b,
250d1268, alternative one 6bf2b90b, bb4ea8be, alternative two f73e73c1, 74aa8da6; Assignment 4
starter 472510f1, the reference 3ba62426, be1c8b89. Assignment 3's two failures were the
reference's drill-down runs ending escalated at the token budget; the drill-down question changed
after them, at 18:07 UTC (commit f0b820d). On that second question, from 18:29 UTC, the starter
failed, 0 of 10, and every solution passed both of its checks, 6 of 6, at 0.09 to 0.41 cents
(activities a6c481bb, 99c2633f, deb57784, b626fe0a, 53d1446a, 8490477e, ddc36771). Two changes
came after that re-check: at 19:35 UTC the solutions' question asked for the top category's row
alone, with its rise in a column named `rise_cents` (commit 5f6e617), and at 20:23 UTC requirement
10 began judging the posted answer's text alone, with the gold category named first (commit
6314b65). On that code, from 20:33 UTC, the starter failed, 0 of 10, and every
solution passed both of its checks, 6 of 6, at 0.19 to 0.31 cents and 8 to 12 calls a check
(activities 1cfdba05, then 9c08751f, 049ba890, 622908ad, cab8a658, 32f8ef0d, 63ff705f; drill-down
runs 22437f9f, 8297b834, 5c16fdb1, 4333413b, d69abac1, a9b6f5db). Those captures were replaced by
the verification from 22:35 UTC, above. Assignment 1's requirement 6 became a behaviour check at
20:23 UTC (commit 6314b65), after its checks of 13:21 to 13:33. It changed again at 21:52 UTC
(commit d7e6dc5): it also closed the superuser address and `POSTGRES_PORT`, and it fails a lookup
read as any role but the agent's on any connection, opened then or kept from an earlier
requirement. The verification above ran on that code. The Assignment 4 alternatives' checks
are activities 277be0f3 and da4e6711.

Suspect checks, which no page uses as evidence. Demonstration captures switched planted bugs on in
the shared `.env` while these checks started their stacks, from the flag windows in the capture
logs:

- 24 October: Assignment 1 alternative two and Assignment 2 reference (planted halves, 10:52 to
  10:57 UTC), superseded by their checks of 25 October; Assignment 4 reference (the naive
  analyzer, 11:28 to 11:41 UTC), superseded by its clean checks of 25 October; Assignment 4
  alternative one (its stack started in the same window), superseded by its re-check of 25
  October.
- 25 October, from 13:59 UTC: Assignment 3, all six solution checks (two suspect passes each for
  the reference and alternative two; two failures of alternative one caused by the missing
  idempotency), superseded by the clean checks above.
- 25 October, from 14:18 UTC: the first two Assignment 4 reference checks (14.21 and 13.32 cents,
  activities 18a9f9a1 and d523de8a), superseded by the checks of 16:56 and 17:11. The starter of
  that pass fails before any model call, so its capture stands.

The earlier verification of 23 October 2026, from 00:05 Coordinated Universal Time (UTC); the
passes from 06:45 UTC replace the earlier ones of Assignments 2 and 3. With an Assignment
3 pass of 07:58 UTC that OpenAI's 504 answers stopped, and that was run again whole, they spent
1.2393 dollars, the sum of their spend lines, and the ledger's session line for assignment
verification shows the same.

| Assignment | Starter (one pass) | Reference, alternative one, alternative two (two passes each) |
|---|---|---|
| Assignment 1: Agent loop | FAIL, 00:05 UTC | PASS in all six, 00:06 to 00:14 UTC |
| Assignment 2: Verification loop | FAIL, 06:45 UTC | PASS in all six, 06:50 to 07:57 UTC |
| Assignment 3: Event loop | FAIL, 08:11 UTC | PASS in all six, 08:13 to 08:25 UTC |
| Assignment 4: Hill-climbing loop (the run 2 captures of both alternatives) | FAIL, 08:27 UTC | PASS in 3 of 6, one per solution; FAIL in 3 on requirement 10 |

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

So every reference solution passed on the check code as it stood from 21:28 UTC on 23 October
2026; the alternatives were not verified on it. After that session, commit 92ea29b (23:55 UTC the
same night, part of the review of 24 October) changed the checks again with no model call (each
check's own spend activity, the reset's port guard, Assignment 4's minimum-holdout requirement,
its shared baseline, and its kill switch), so each solution was owed its live checks again. The
checks of 24 October below are those checks.

The checks of 24 October 2026 (session 5), on the code of that day (commit 2003b00), from 10:42 to about
12:10 UTC, one each, in the assignments stack's live session 385150df; each figure is the check's
own "Spend:" line and its wall time:

| Assignment | Starter | Reference | Alternatives |
|---|---|---|---|
| Assignment 1: Agent loop | FAIL, 0 of 11, as designed | PASS, 11 of 11, 0.42 cents, 121 seconds | PASS, 11 of 11 each: 0.49 cents; suspect (superseded): 0.48 cents |
| Assignment 2: Verification loop | FAIL, 0 of 10, as designed | Suspect (superseded): PASS, 10 of 10, 2.01 cents | PASS, 10 of 10 each: 1.75 cents, 228 seconds; 1.56 cents, 253 seconds |
| Assignment 3: Event loop | FAIL, 0 of 10, as designed | PASS, 10 of 10, 0.50 cents, 180 seconds | PASS, 10 of 10 each: 0.29 cents, 141 seconds; 0.45 cents, 170 seconds |
| Assignment 4: Hill-climbing loop | FAIL, 1 of 10, as designed | Suspect (superseded): PASS, a first check (note 7), 23.59 cents | Suspect (superseded): 13.64 cents; PASS, 10 of 10: 19.22 cents |

The spend activities, in the same order: starters agent-loop-b1062bbb,
verification-loop-139348b8, event-loop-7fd68d36, hill-climbing-loop-1db56f51; Assignment 1
4fa4b211, c9ffa8c1, 25864206; Assignment 2 dde154a7, f20844d6, 2f4f433d; Assignment 3 c33f204f,
da3c4c1b, b4455d6f; Assignment 4 418329c2, cb0f0613, 045bf95f. Each is recorded in the spend ledger as
"assignment verification-" followed by the slug and the id.

The cap stop, 24 October, session 5: the Assignment 2 reference with check_cap_usd set to 0.005
(printed rounded, "stops at 0.01 dollars") read "STOPPED at the spend cap, 7 of 10 requirements
passed, 0 failed, 3 not run", spent 0 cents in 0 model calls, and exited with code 2 (activity
verification-loop-f6e2672d). One run priced at its whole token budget would pass the cap, so it
started none.

Note 7: the reference ran baseline experiment edc342f4 of v1 itself, because the session's
baseline 1c933bea had measured 46 items otherwise than they are now; the gate promoted its
candidate at 16 of 18 holdout items against 2, with 0 confirmed regressions. Alternative one
and alternative two shared edc342f4 and were promoted at 13 and 8 of 18 against 2. This is the first measured first check of
Assignment 4 with two candidates.

LangSmith refused traces from about 06:48 UTC, at the free plan's monthly limit of unique traces,
so most captures of these passes show the trace id without a link; the run ids, live stamps, and
spend ledger rows stand in for them. The Assignment 2 audit of the earlier failed passes, and the
Assignment 4 analysis of requirement 10, are in each folder's README.

The class story images in [docs/images](../images/README.md) are from live runs of 24 and 25
October 2026: four were retaken on 25 October, from 14:43 UTC, in rehearsal session c18bcc2e (the
simple question, the confident wrong answer's annotated query, the webhook question's Channel, and
the duplicate events board), and the rest are from 24 October. Their run ids are on each
section's evidence page and in the [images README](../images/README.md).

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
