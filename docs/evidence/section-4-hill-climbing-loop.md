# Evidence: Section 4: Hill-climbing loop

This page holds the evidence behind every number on the pages of section-4-hill-climbing-loop/: the
calibration runs, their ids, and the captures in the section's demo/expected/ folder.

## How to use this page

The section's [README](../../section-4-hill-climbing-loop/README.md), its
[concepts page](../../section-4-hill-climbing-loop/concepts.md), and its
[demo page](../../section-4-hill-climbing-loop/demo/README.md) link here for their measured runs.
Holdout items are the 15 benchmark questions the analyzer team never sees; development questions
are the 25 it learns from. Each row counts holdout items or runs as "N of M", never as
percentages; an experiment's holdout result is the number of the 15 holdout items it passed. A
knowledge version is written version 1 of the knowledge (the starting version), version 8, and so
on; "against 2" is version 1's 2 of 15 in the same session. Times are in Coordinated Universal Time
(UTC).

## Results

From the calibration of 22 and 23 October 2026, the live session of 23 October, afternoon, the
capture session of 23 October, 21:17 to 21:55 UTC (its hill-climbing chain from 21:27), the live
session of 24 October 2026 (rehearsal session 56894641, with a second chain for the captures), and
the live session of 25 October 2026 (the class story in rehearsal session c18bcc2e, then two more
chains that retook captures), all in the [calibration report](../calibration-report.md). Each table
below is one of them. Experiment ids are in ops.experiments; the build's LangSmith traces are
private, and from 06:48 UTC on 23 October LangSmith refused traces at its monthly limit, so later
rows are proven by run id, ops record, and the spend ledger.

### Calibration, 22 and 23 October

| Claim | Runs | Ids |
|---|---|---|
| Baseline version 1: holdout passes | 2 of 15 in 5 of 5 experiments of 22 October | b44ad06e, 2bcc6ac2, 572dc0ea, bf861054, 51ec1e22 |
| Baseline version 1 on 23 October: holdout passes | 2 of 15 in 3 of 3 experiments | dde64d21, 5dba42c6, 31a76afe |
| Promoted version 4: holdout passes, regressions | 11 of 15 and 12 of 15, 0 regressions | 1e0ec097, 3358ea89 |
| Candidates of the demo run-through: holdout passes, regressions | 3 of 15 and 6 of 15, 0 regressions | aa1dfae5, 0cf7df9d |
| Holdout trap items flipped by version 4 | 10 of 13 | 3358ea89 |
| The confirming re-run clears an apparent regression | 1 apparent regression, cleared at 3 of 3 re-runs | calibration step confirm, 23:40 UTC |
| Holdout items unstable under versions 1 and 4 | version 1: 0 of 15 (twice); version 4: 3 of 15, then 4 of 15 | stability runs 23:02, 23:10, 23:18, 23:23 UTC |
| Items the stability filter replaced in the end | 0 (3 replaced, then restored) | see the commits on the module evidence page |
| Families cleared by a promotion | average order value and customers; none; average order value and products | 22 October capture; demo run-throughs 1 and 2 |
| The fiscal year 2025 revenue question after promotion | correct, posted at the assisted level | 32c5abc0 |
| Experiment wall time, 70 runs at concurrency 8 | 182 to 459 seconds; 458.9 and 403.8 seconds at effort high | the ids on this page |
| Cost of one 70-run experiment | 0.0594 to 0.0914 dollars, where recorded | 3358ea89, 2bcc6ac2, dde64d21, the effort-high starting experiment |
| The naive analyzer before the deterministic one (23 October, morning) | not shown: version 7 passed 15 of 15 holdout items, gate ready | 911423fb |
| Analyzer at reasoning effort high: holdout passes | 2, 9, and 5 of 15 against 2 | 25d0f021, 4ae5177b, 66616a62 |
| Promoted version 5: holdout passes, regressions | 10 of 15 against 2, 0 regressions | 407ff720 |
| Families cleared by the version 5 promotion | average order value and products; revenue fell short | 407ff720 |
| The fiscal year 2025 revenue question after the version 5 promotion | assisted level, gold failed: an internal-account filter that was too broad | 631d0ccb |

### Live session of 23 October, afternoon

| Claim | Runs | Ids |
|---|---|---|
| Baseline version 1 | holdout 2 of 15, development 4 of 25, 276.8 seconds | 5dba42c6 |
| Analyzer team, two candidates on the development questions only | A: 18 of 25, 11 rules; B: 19 of 25, 8 rules; B kept as version 8; 326 seconds | analyzer request of session ae67ee60 |
| Promoted version 8: holdout passes, regressions | 14 of 15 against 2, development 19 of 25, 0 regressions, 206.5 seconds | 2eb8890c |
| Holdout trap items fixed by version 8 | 12 of 13 (business-day-orders-november-2025 still fails) | 2eb8890c |
| Families cleared by the version 8 promotion | revenue, average order value, customers, products; orders not | 2eb8890c, one clearance re-run (0 of 3) |
| The fiscal year 2025 revenue question after the version 8 promotion | 64,015,091.21 dollars, gold passed, posted at the unattended level | 38f16596 |
| The naive analyzer, blocked | blocked twice: 21 rules, all flagged; holdout 2 of 15; 256 and 211 seconds | 37eb24f5, 45fa8a3d |
| Regressions in the analyzer team's candidate experiments | none in 9 of 10; 1 on a development question in 25d0f021 | the ten candidate experiments on this page |

### Capture session of 23 October, evening

| Claim | Runs | Ids |
|---|---|---|
| Baseline version 1 | holdout 2 of 15, development 5 of 25, 278.8 seconds | 31a76afe |
| Analyzer team, two candidates on the development questions only | A: 21 of 25, 8 rules; B: 10 of 25, 5 rules; A kept as version 9; 377 seconds | the analyzer request at 21:38 UTC |
| Promoted version 9: holdout passes, regressions | 14 of 15 against 2, development 22 of 25, 0 regressions, 181.9 seconds | a2ba7a5a |
| The two-candidate method: holdout passes of the kept candidate | 14 of 15 in 2 of 2 promotions (versions 8 and 9) | 2eb8890c, a2ba7a5a |
| The finale held during the promotion | held 5 times over 50 seconds, each naming the step still running | 21:41 to 21:42 UTC |
| Families cleared by the version 9 promotion | revenue, average order value, customers, products; orders not | a2ba7a5a |
| The fiscal year 2025 revenue question after the version 9 promotion | 64,015,091.21 dollars, gold passed, posted at the unattended level | c91ebcc0 |
| The naive analyzer's version 10, blocked | 20 rules, all flagged; holdout 2 of 15, development 4 of 25; 285 seconds | 02de992f |
| Revenue cleared by a promotion, on either standard | 2 of 6 live promotions (versions 8 and 9) | the promotions on this page |
| The naive analyzer, blocked since it was made deterministic | 3 of 3, 211 to 285 seconds from the trigger to the verdict | 37eb24f5, 45fa8a3d, 02de992f |

### Live session of 24 October

| Claim | Runs | Ids |
|---|---|---|
| Baseline version 1 | holdout 2 of 15, development 5 of 25, 286.6 seconds of experiment wall time | 74ff242b |
| Analyzer team, two candidates on the development questions only | A: 13 of 25, 8 rules; B: 14 of 25, 6 rules; B kept as version 11; 359 seconds | the analyzer request of session 56894641 |
| Candidate version 11: holdout passes, regressions | 13 of 15 against 2, development 16 of 25, 0 regressions, 210.3 seconds | b50131b4 |
| The promotion after approval | version 11 active 5 seconds after approval; finale held during the re-runs | 11:15:32 to 11:16:32 UTC |
| Families cleared by the version 11 promotion | average order value, customers, revenue | b50131b4 |
| The fiscal year 2025 revenue question after the version 11 promotion | 64,015,091.21 dollars, gold passed, posted at the unattended level | e1769f0e |
| The class-day safeguard, rehearsed | verified; refused while version 11 was active; after a reset, activated | e1769f0e |
| The fiscal year 2025 revenue question on the safeguard | 64,015,091.21 dollars, gold passed, posted at the unattended level, 19 seconds | 037f3718 |
| The over-broad rule, first attempt | failed at 311 seconds, NoLiveBaseline: a reset deleted version 11's experiment | b50131b4, reset archive 8a7b4646 |
| The over-broad rule, blocked | version 11: 12 of 15; with the rule: 7 of 15, 9 regressions; 862 seconds | 82ad72d5, 84417bfe |
| The naive analyzer, blocked | version 1: 2 of 15; version 12: 21 rules all flagged, 2 of 15; 580 seconds | 3fc31a32, c87991fc |
| The two-candidate method, kept candidate (replaces 2 of 2) | 14, 14, and 13 of 15 in 3 promotions (versions 8, 9, and 11) | 2eb8890c, a2ba7a5a, b50131b4 |
| Revenue cleared by a promotion (replaces 2 of 6) | 3 of 7 live promotions (versions 8, 9, and 11) | the promotions on this page |
| Regressions in the team's candidates (replaces 9 of 10) | none in 10 of 11; 1 on a development question in 25d0f021 | the eleven candidate experiments on this page |
| The naive analyzer, blocked since deterministic (replaces 3 of 3) | 4 of 4, 211 to 580 seconds from the trigger to the verdict | 37eb24f5, 45fa8a3d, 02de992f, c87991fc |
| Experiment wall time, 70 runs at concurrency 8 | 180.5 to 380.7 seconds here; 180.5 to 459 seconds over every measurement | 84417bfe, 3fc31a32, and the ids above |

On 24 October the naive analyzer's version 12 also passed 4 of 25 development questions.

### Capture chain of 24 October

| Claim | Runs | Ids |
|---|---|---|
| Baseline version 1 | holdout 2 of 15, development 4 of 25, 291.6 seconds (295 from the trigger) | aa1d02ff |
| Analyzer team, two candidates on the development questions only | A: 22 of 25, 9 rules; B: 20 of 25, 8 rules; A kept as version 13; 326 seconds | the analyzer request of the capture chain |
| Candidate version 13: holdout passes, regressions | 14 of 15 against 2, development 22 of 25, 0 regressions, 335.6 seconds | 0e1cbfe7 |
| Families cleared by the version 13 promotion | revenue, average order value, customers, products; orders not | 0e1cbfe7 |
| The fiscal year 2025 revenue question after the version 13 promotion | 64,015,091.21 dollars, gold passed, unattended level; held 5 times; 74 seconds | 59174f10 |
| The naive analyzer, blocked | version 14, 21 rules all flagged, holdout 2 of 15; 463 seconds | candidate version 14 |

### Live session of 25 October

| Claim | Runs | Ids |
|---|---|---|
| Baseline version 1 | holdout 2 of 15, development 4 of 25, 252 seconds from the trigger | a8801f38 |
| Analyzer team, two candidates on the development questions only | A: 7 of 25, 8 rules; B: 24 of 25, 9 rules; B kept as version 15; 362 seconds | the analyzer request of session c18bcc2e |
| Candidate version 15: holdout passes, regressions | 13 of 15, development 25 of 25, 0 regressions, 237 seconds from the trigger | 2c7414d9 |
| The promotion after approval | version 15 active 5 seconds after approval; finale held during the re-runs | 13:06:38 to 13:06:43 UTC |
| Families cleared by the version 15 promotion | revenue, average order value, customers, products; orders not | 2c7414d9 |
| The fiscal year 2025 revenue question after the version 15 promotion | 64,015,091.21 dollars, gold passed, unattended level, 162 seconds | cb8d3beb |
| The class-day safeguard, rehearsed | verified; refused while version 15 was active; after a reset, activated | cb8d3beb |
| The fiscal year 2025 revenue question on the safeguard | 64,015,091.21 dollars, gold passed, posted at the unattended level, 21 seconds | a2de1570 |
| The naive analyzer, blocked | version 16: 21 rules all flagged; holdout 0 of 15, 2 regressions; 221 seconds | dd36c4f5, 5f596895 |
| First retake chain: baseline version 1 | holdout 2 of 15, 246 seconds | bbecf29e |
| First retake chain: candidate version 17 | 12 of 15, development 24 of 25, 0 regressions, 186 seconds | a4bfc059 |
| First retake chain: the finale after the version 17 promotion | gold passed, unattended level; held 9 times, 115 seconds; orders not cleared | bd7b4a77 |
| Second retake chain: baseline version 1 | holdout 2 of 15, 236 seconds | cf1decfc |
| Second retake chain: candidate version 19 | 13 of 15, development 23 of 25, 0 regressions, 176 seconds | 15703840 |
| Second retake chain: the finale | blocked by the daily token budget; all families but orders cleared | fa7933bb |
| The two-candidate method, kept candidate (replaces 3 promotions) | 14, 14, 13, 14, 13, 12, and 13 of 15 (versions 8, 9, 11, 13, 15, 17, 19) | 2eb8890c, a2ba7a5a, b50131b4, 0e1cbfe7, 2c7414d9, a4bfc059, 15703840 |
| Revenue cleared by a promotion (replaces 3 of 7) | 7 of 11 live promotions (versions 8, 9, 11, 13, 15, 17, 19) | the promotions on this page |
| Regressions in the team's candidates (replaces 10 of 11) | none in 14 of 15; 1 on a development question in 25d0f021 | the fifteen candidate experiments on this page |
| The naive analyzer, blocked since deterministic (replaces 4 of 4) | 6 of 6, 211 to 580 seconds; holdout 2 of 15 in five, 0 of 15 in one | 37eb24f5, 45fa8a3d, 02de992f, c87991fc, candidate version 14, 5f596895 |
| Experiment wall time, 70 runs at concurrency 8 | 171.3 to 248.2 seconds here; 171.3 to 459 seconds over every measurement | 15703840 and the ids above |
| Seconds from the trigger, every recorded run | baseline 236 to 386; candidate 176 to 337; finale 50, 74, 115, 162 | the rows above |

A retake chain is one more run of the hill-climbing chain, to retake captures. The finale of the
first retake chain asked the fiscal year 2025 revenue question.

## Captures

| File | Date | Run id |
|---|---|---|
| demo/expected/improve-baseline-experiment-running.png, -ledger.png | 24 October 2026, 14:10 and 14:15 UTC | experiment aa1d02ff |
| demo/expected/improve-naive-analyzer-blocked-guard.png, -gate.png | 24 October 2026, 14:37 UTC | candidate version 14 |
| demo/expected/improve-analyzer-team-diff.png | 24 October 2026, 14:20 UTC | the analyzer request that wrote version 13 |
| demo/expected/improve-candidate-experiment-ledger.png | 24 October 2026, 14:26 UTC | experiment 0e1cbfe7 |
| demo/expected/improve-candidate-experiment-gate.png | 25 October 2026, 17:51 UTC | experiment 15703840 (version 19) |
| demo/expected/improve-promotion-cleared.png | 24 October 2026, 14:28 UTC | promotion of version 13 |
| demo/expected/improve-cleared-unattended-board.png, -channel.png | 24 October 2026, 14:28 UTC | run 59174f10 |

The captures come from the capture chain of 24 October (development session 218b7e38), not from
the main chain of that live session, whose candidate was version 11, except the gate's verdict, retaken in the
second retake chain of 25 October.

## Sources and findings

The module records no finding ids. The sources the Section 4 pages cite are in the
Sources lists of its [README](../../section-4-hill-climbing-loop/README.md#sources) and its
[concepts page](../../section-4-hill-climbing-loop/concepts.md#sources), drawn from the source register on the
[evidence page for the whole module](general.md#sources-and-findings).

## Commits and tags

See the [evidence page for the whole module](general.md#commits-and-tags).
