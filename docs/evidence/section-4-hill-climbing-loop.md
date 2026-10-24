# Evidence: Section 4: Hill-climbing loop

This page holds the evidence behind every number on the pages of section-4-hill-climbing-loop/: the
calibration runs, their ids, and the captures in the section's demo/expected/ folder.

## How to use this page

The section's [README](../../section-4-hill-climbing-loop/README.md), its
[concepts page](../../section-4-hill-climbing-loop/concepts.md), and its
[demo page](../../section-4-hill-climbing-loop/demo/README.md) link here for their measured runs.
Each row counts holdout items or runs as "N of M", never as percentages; an
experiment's holdout result is the number of the 15 holdout items it passed. Times are in
Coordinated Universal Time (UTC).

## Results

From the calibration of 22 and 23 October 2026 and the live session of 23 October, afternoon
(session 4), and the capture session of 23 October, 21:27 to 21:55 UTC, whose rows name it, all in
the [calibration report](../calibration-report.md). Experiment ids are in
ops.experiments; the build's LangSmith traces are private, and from 06:48 UTC on 23 October
LangSmith refused traces at its monthly limit, so later rows are proven by run id, ops record, and
the spend ledger.

| Claim | Runs | Ids |
|---|---|---|
| Baseline v1: holdout passes | 2 of 15 in 5 of 5 experiments of 22 October | b44ad06e, 2bcc6ac2, 572dc0ea, bf861054, 51ec1e22 |
| Baseline v1 on 23 October: holdout passes | 2 of 15 in 3 of 3 experiments | dde64d21, 5dba42c6, 31a76afe |
| Promoted v4: holdout passes, regressions | 11 of 15 and 12 of 15, 0 regressions | 1e0ec097, 3358ea89 |
| Candidates of the demo pass: holdout passes, regressions | 3 of 15 and 6 of 15, 0 regressions | aa1dfae5, 0cf7df9d |
| Holdout trap items flipped by v4 | 10 of 13 | 3358ea89 |
| The confirming re-run clears an apparent regression | 1 apparent regression, cleared at 3 of 3 re-runs | calibration step confirm, 23:40 UTC |
| Stability under v1 and v4 | v1 0 of 15 unstable (twice); v4 3 of 15, then 4 of 15 | stability runs 23:02, 23:10, 23:18, 23:23 UTC |
| Items the stability filter replaced in the end | 0 (3 replaced, then restored) | see the commits on the module evidence page |
| Families cleared by a promotion | average order value and customers; none; average order value and products | 22 October capture; demo passes 1 and 2 |
| The spine question after promotion | correct, posted at the assisted level | 32c5abc0 |
| Experiment wall time, 70 runs at concurrency 8 | 182 to 459 s; 458.9 and 403.8 s at effort high | the ids on this page |
| Cost of one 70-run experiment | 0.0594 to 0.0914 dollars, where recorded | 3358ea89, 2bcc6ac2, dde64d21, the effort-high starting experiment |
| The naive analyzer before the deterministic one (23 October, morning) | not shown: v7 passed 15 of 15 holdout items, gate ready | 911423fb |
| Analyzer at reasoning effort high: holdout passes | 2, 9, and 5 of 15 against 2 | 25d0f021, 4ae5177b, 66616a62 |
| Promoted v5: holdout passes, regressions | 10 of 15 against 2, 0 regressions | 407ff720 |
| Families cleared by the v5 promotion | average order value and products; revenue fell short | 407ff720 |
| The spine question after the v5 promotion | assisted level, gold failed: an internal-account filter that was too broad | 631d0ccb |
| Session 4 baseline v1 | holdout 2 of 15, dev 4 of 25, 276.8 s | 5dba42c6 |
| Session 4 analyzer team, two candidates on dev only | A 18 of 25 dev, 11 rules; B 19 of 25, 8 rules; B kept as v8; 326 s | analyzer request of session ae67ee60 |
| Promoted v8: holdout passes, regressions | 14 of 15 against 2, dev 19 of 25, 0 regressions on either split, 206.5 s | 2eb8890c |
| Holdout trap items fixed by v8 | 12 of 13 (business-day-orders-november-2025 still fails) | 2eb8890c |
| Families cleared by the v8 promotion | revenue, average order value, customers, products; orders not | 2eb8890c, one clearance re-run (0 of 3) |
| The spine question after the v8 promotion | 64,015,091.21 dollars, gold passed, posted at the unattended level | 38f16596 |
| The naive analyzer, blocked | blocked twice: 21 rules, all flagged; holdout 2 of 15; 256 and 211 s | 37eb24f5, 45fa8a3d |
| Regressions in the analyzer team's candidate experiments | 0 in 9 of 10; 1 dev regression in 25d0f021 | the ten candidate experiments on this page |
| Capture session, baseline v1 | holdout 2 of 15, dev 5 of 25, 278.8 s | 31a76afe |
| Capture session, analyzer team, two candidates on dev only | A 21 of 25 dev, 8 rules; B 10 of 25, 5 rules; A kept as v9; 377 s | the analyzer request at 21:38 UTC |
| Capture session, promoted v9: holdout passes, regressions | 14 of 15 against 2, dev 22 of 25, 0 regressions, 181.9 s | a2ba7a5a |
| The two-candidate method: holdout passes of the kept candidate | 14 of 15 in 2 of 2 measurements (v8, v9) | 2eb8890c, a2ba7a5a |
| Capture session, the finale held during the promotion | held 5 times over 50 seconds, each naming the step still running | 21:41 to 21:42 UTC |
| Capture session, families cleared by the v9 promotion | revenue, average order value, customers, products; orders not | a2ba7a5a |
| Capture session, the spine question after the v9 promotion | 64,015,091.21 dollars, gold passed, posted at the unattended level | c91ebcc0 |
| Capture session, the naive analyzer, blocked | 20 rules, all flagged; v10 holdout 2 of 15, dev 4 of 25; 285 s | 02de992f |
| Revenue cleared by a promotion, on either standard | 2 of 6 live promotions (v8, v9) | the promotions on this page |
| The naive analyzer, blocked since it was made deterministic | 3 of 3, 211 to 285 s from the trigger to the verdict | 37eb24f5, 45fa8a3d, 02de992f |

The rehearsal and the class have not run yet; their results are added here after them.

## Captures

| File | Date | Run id |
|---|---|---|
| demo/expected/improve-baseline-experiment-running.png, -ledger.png | 23 October 2026, 21:27 and 21:31 UTC | experiment 31a76afe |
| demo/expected/improve-naive-analyzer-blocked-guard.png, -gate.png | 23 October 2026, 21:44 and 21:49 UTC | experiment 02de992f, candidate v10 |
| demo/expected/improve-analyzer-team-diff.png | 23 October 2026, 21:38 UTC | the analyzer request that wrote v9 |
| demo/expected/improve-candidate-experiment-ledger.png, -gate.png | 23 October 2026, 21:41 UTC | experiment a2ba7a5a |
| demo/expected/improve-promotion-cleared.png | 23 October 2026, 21:42 UTC | promotion of v9 |
| demo/expected/improve-cleared-unattended-board.png, -channel.png | 23 October 2026, 21:43 UTC | run c91ebcc0 |

## Sources and findings

The module records no finding ids. The sources the Section 4 pages cite are in the
Sources lists of its [README](../../section-4-hill-climbing-loop/README.md#sources) and its
[concepts page](../../section-4-hill-climbing-loop/concepts.md#sources), drawn from the source register on the
[evidence page for the whole module](general.md#sources-and-findings).

## Commits and tags

See the [evidence page for the whole module](general.md#commits-and-tags).
