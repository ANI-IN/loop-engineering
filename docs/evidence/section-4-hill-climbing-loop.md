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
(session 4), the capture session of 23 October, 21:17 to 21:55 UTC (its hill-climbing chain from 21:27), whose
rows name it, the live session of 24 October 2026, in rehearsal
session 56894641 (session 5, the rows marked "24 October"), and the live session of 25 October
2026 (session 6, the rows marked "25 October": the class story pass in rehearsal session c18bcc2e,
and two retake chains), all in the [calibration report](../calibration-report.md). Experiment ids are in
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
| Experiment wall time, 70 runs at concurrency 8 | 182 to 459 seconds; 458.9 and 403.8 seconds at effort high | the ids on this page |
| Cost of one 70-run experiment | 0.0594 to 0.0914 dollars, where recorded | 3358ea89, 2bcc6ac2, dde64d21, the effort-high starting experiment |
| The naive analyzer before the deterministic one (23 October, morning) | not shown: v7 passed 15 of 15 holdout items, gate ready | 911423fb |
| Analyzer at reasoning effort high: holdout passes | 2, 9, and 5 of 15 against 2 | 25d0f021, 4ae5177b, 66616a62 |
| Promoted v5: holdout passes, regressions | 10 of 15 against 2, 0 regressions | 407ff720 |
| Families cleared by the v5 promotion | average order value and products; revenue fell short | 407ff720 |
| The spine question after the v5 promotion | assisted level, gold failed: an internal-account filter that was too broad | 631d0ccb |
| Session 4 baseline v1 | holdout 2 of 15, dev 4 of 25, 276.8 seconds | 5dba42c6 |
| Session 4 analyzer team, two candidates on dev only | A 18 of 25 dev, 11 rules; B 19 of 25, 8 rules; B kept as v8; 326 seconds | analyzer request of session ae67ee60 |
| Promoted v8: holdout passes, regressions | 14 of 15 against 2, dev 19 of 25, 0 regressions on either split, 206.5 seconds | 2eb8890c |
| Holdout trap items fixed by v8 | 12 of 13 (business-day-orders-november-2025 still fails) | 2eb8890c |
| Families cleared by the v8 promotion | revenue, average order value, customers, products; orders not | 2eb8890c, one clearance re-run (0 of 3) |
| The spine question after the v8 promotion | 64,015,091.21 dollars, gold passed, posted at the unattended level | 38f16596 |
| The naive analyzer, blocked | blocked twice: 21 rules, all flagged; holdout 2 of 15; 256 and 211 seconds | 37eb24f5, 45fa8a3d |
| Regressions in the analyzer team's candidate experiments | 0 in 9 of 10; 1 dev regression in 25d0f021 | the ten candidate experiments on this page |
| Capture session, baseline v1 | holdout 2 of 15, dev 5 of 25, 278.8 seconds | 31a76afe |
| Capture session, analyzer team, two candidates on dev only | A 21 of 25 dev, 8 rules; B 10 of 25, 5 rules; A kept as v9; 377 seconds | the analyzer request at 21:38 UTC |
| Capture session, promoted v9: holdout passes, regressions | 14 of 15 against 2, dev 22 of 25, 0 regressions, 181.9 seconds | a2ba7a5a |
| The two-candidate method: holdout passes of the kept candidate | 14 of 15 in 2 of 2 measurements (v8, v9) | 2eb8890c, a2ba7a5a |
| Capture session, the finale held during the promotion | held 5 times over 50 seconds, each naming the step still running | 21:41 to 21:42 UTC |
| Capture session, families cleared by the v9 promotion | revenue, average order value, customers, products; orders not | a2ba7a5a |
| Capture session, the spine question after the v9 promotion | 64,015,091.21 dollars, gold passed, posted at the unattended level | c91ebcc0 |
| Capture session, the naive analyzer, blocked | 20 rules, all flagged; v10 holdout 2 of 15, dev 4 of 25; 285 seconds | 02de992f |
| Revenue cleared by a promotion, on either standard | 2 of 6 live promotions (v8, v9) | the promotions on this page |
| The naive analyzer, blocked since it was made deterministic | 3 of 3, 211 to 285 seconds from the trigger to the verdict | 37eb24f5, 45fa8a3d, 02de992f |
| 24 October: baseline v1 | holdout 2 of 15, dev 5 of 25, 286.6 seconds of experiment wall time | 74ff242b |
| 24 October: analyzer team, two candidates on dev only | A 13 of 25 dev, 8 rules; B 14 of 25, 6 rules; B kept as v11; 359 seconds | the analyzer request of session 56894641 |
| 24 October: candidate v11, holdout passes, regressions | 13 of 15 against 2, dev 16 of 25, 0 regressions on either split, 210.3 seconds | b50131b4 |
| 24 October: the promotion after approval | v11 active 5 seconds after approval; finale held during the re-runs | 11:15:32 to 11:16:32 UTC |
| 24 October: families cleared by the v11 promotion | average order value, customers, revenue | b50131b4 |
| 24 October: the spine question after the v11 promotion | 64,015,091.21 dollars, gold passed, posted at the unattended level | e1769f0e |
| 24 October: the class-day safeguard, rehearsed | verified; refused while v11 was active; after a reset, activated (decision 37) | e1769f0e |
| 24 October: the spine question on the safeguard | 64,015,091.21 dollars, gold passed, posted at the unattended level, 19 seconds | 037f3718 |
| 24 October: the over-broad rule, first attempt | failed after 311 seconds, NoLiveBaseline: the reset deleted v11's experiment | b50131b4, reset archive 8a7b4646 |
| 24 October: the over-broad rule, blocked | v11 12 of 15; with the rule 7 of 15, 9 regressions; 862 seconds | 82ad72d5, 84417bfe |
| 24 October: the naive analyzer, blocked | v1 2 of 15; v12, 21 rules all flagged, holdout 2 of 15, dev 4 of 25; 580 seconds | 3fc31a32, c87991fc |
| 24 October: the two-candidate method, kept candidate (supersedes 2 of 2) | 14, 14, and 13 of 15 in 3 measurements (v8, v9, v11) | 2eb8890c, a2ba7a5a, b50131b4 |
| 24 October: revenue cleared by a promotion (supersedes 2 of 6) | 3 of 7 live promotions (v8, v9, v11) | the promotions on this page |
| 24 October: regressions in the team's candidates (supersedes 9 of 10) | 0 in 10 of 11; 1 dev regression in 25d0f021 | the eleven candidate experiments on this page |
| 24 October: the naive analyzer, blocked since deterministic (supersedes 3 of 3) | 4 of 4, 211 to 580 seconds from the trigger to the verdict | 37eb24f5, 45fa8a3d, 02de992f, c87991fc |
| 24 October: experiment wall time, 70 runs at concurrency 8 | 180.5 to 380.7 seconds here; 180.5 to 459 seconds over every measurement | 84417bfe, 3fc31a32, and the ids above |
| Capture chain, 24 October: baseline v1 | holdout 2 of 15, dev 4 of 25, 291.6 seconds (295 seconds from the trigger) | aa1d02ff |
| Capture chain, 24 October: analyzer team, two candidates on dev only | A 22 of 25 dev, 9 rules; B 20 of 25, 8 rules; A kept as v13; 326 seconds | the analyzer request of the capture chain |
| Capture chain, 24 October: candidate v13, holdout passes, regressions | 14 of 15 against 2, dev 22 of 25, 0 regressions, 335.6 seconds | 0e1cbfe7 |
| Capture chain, 24 October: families cleared by the v13 promotion | revenue, average order value, customers, products; orders not | 0e1cbfe7 |
| Capture chain, 24 October: the spine question after the v13 promotion | 64,015,091.21 dollars, gold passed, unattended level; held 5 times; 74 seconds | 59174f10 |
| Capture chain, 24 October: the naive analyzer, blocked | v14, 21 rules all flagged, holdout 2 of 15; 463 seconds | candidate v14 |
| 25 October: baseline v1 | holdout 2 of 15, dev 4 of 25, 252 seconds from the trigger | a8801f38 |
| 25 October: analyzer team, two candidates on dev only | A 7 of 25 dev, 8 rules; B 24 of 25, 9 rules; B kept as v15; 362 seconds | the analyzer request of session c18bcc2e |
| 25 October: candidate v15, holdout passes, regressions | 13 of 15 against 2, dev 25 of 25, 0 regressions, 237 seconds from the trigger | 2c7414d9 |
| 25 October: the promotion after approval | v15 active 5 seconds after approval; finale held during the re-runs | 13:06:38 to 13:06:43 UTC |
| 25 October: families cleared by the v15 promotion | revenue, average order value, customers, products; orders not | 2c7414d9 |
| 25 October: the spine question after the v15 promotion | 64,015,091.21 dollars, gold passed, unattended level, 162 seconds | cb8d3beb |
| 25 October: the class-day safeguard, rehearsed | verified; refused while v15 was active; after a reset, activated (decision 48) | cb8d3beb |
| 25 October: the spine question on the safeguard | 64,015,091.21 dollars, gold passed, posted at the unattended level, 21 seconds | a2de1570 |
| 25 October: the naive analyzer, blocked | v16, 21 rules all flagged, holdout 0 of 15, 2 holdout regressions; 221 seconds | dd36c4f5, 5f596895 |
| 25 October, retake chain 1: baseline, candidate v17 | v1 2 of 15, 246 seconds; v17 12 of 15, dev 24 of 25, 0 regressions, 186 seconds | bbecf29e, a4bfc059 |
| 25 October, retake chain 1: the spine question after the v17 promotion | gold passed, unattended level; held 9 times, 115 seconds; orders not cleared | bd7b4a77 |
| 25 October, retake chain 2: baseline, candidate v19 | v1 2 of 15, 236 seconds; v19 13 of 15, dev 23 of 25, 0 regressions, 176 seconds | cf1decfc, 15703840 |
| 25 October, retake chain 2: the finale | blocked by the daily token budget; all families but orders cleared | fa7933bb |
| 25 October: the two-candidate method, kept candidate (supersedes 3 measurements) | 14, 14, 13, 14, 13, 12, and 13 of 15 (v8, v9, v11, v13, v15, v17, v19) | 2eb8890c, a2ba7a5a, b50131b4, 0e1cbfe7, 2c7414d9, a4bfc059, 15703840 |
| 25 October: revenue cleared by a promotion (supersedes 3 of 7) | 7 of 11 live promotions (v8, v9, v11, v13, v15, v17, v19) | the promotions on this page |
| 25 October: regressions in the team's candidates (supersedes 10 of 11) | 0 in 14 of 15; 1 dev regression in 25d0f021 | the fifteen candidate experiments on this page |
| 25 October: the naive analyzer, blocked since deterministic (supersedes 4 of 4) | 6 of 6, 211 to 580 seconds; holdout 2 of 15 in five, 0 of 15 in one | 37eb24f5, 45fa8a3d, 02de992f, c87991fc, candidate v14, 5f596895 |
| 25 October: experiment wall time, 70 runs at concurrency 8 | 171.3 to 248.2 seconds here; 171.3 to 459 seconds over every measurement | 15703840 and the ids above |
| Seconds from the trigger, every recorded run | baseline 236 to 386; candidate 176 to 337; finale 50, 74, 115, 162 | the rows above |

## Captures

| File | Date | Run id |
|---|---|---|
| demo/expected/improve-baseline-experiment-running.png, -ledger.png | 24 October 2026, 14:10 and 14:15 UTC | experiment aa1d02ff |
| demo/expected/improve-naive-analyzer-blocked-guard.png, -gate.png | 24 October 2026, 14:37 UTC | candidate v14 |
| demo/expected/improve-analyzer-team-diff.png | 24 October 2026, 14:20 UTC | the analyzer request that wrote v13 |
| demo/expected/improve-candidate-experiment-ledger.png | 24 October 2026, 14:26 UTC | experiment 0e1cbfe7 |
| demo/expected/improve-candidate-experiment-gate.png | 25 October 2026, 17:51 UTC | experiment 15703840 (v19) |
| demo/expected/improve-promotion-cleared.png | 24 October 2026, 14:28 UTC | promotion of v13 |
| demo/expected/improve-cleared-unattended-board.png, -channel.png | 24 October 2026, 14:28 UTC | run 59174f10 |

The captures come from the capture chain of 24 October (development session 218b7e38), not from
the session's main chain, whose candidate was v11, except the gate's verdict, retaken in the
second retake chain of 25 October.

## Sources and findings

The module records no finding ids. The sources the Section 4 pages cite are in the
Sources lists of its [README](../../section-4-hill-climbing-loop/README.md#sources) and its
[concepts page](../../section-4-hill-climbing-loop/concepts.md#sources), drawn from the source register on the
[evidence page for the whole module](general.md#sources-and-findings).

## Commits and tags

See the [evidence page for the whole module](general.md#commits-and-tags).
