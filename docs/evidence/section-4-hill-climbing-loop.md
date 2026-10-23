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

From the calibration of 22 and 23 October 2026 ([calibration report](../calibration-report.md)).
Experiment ids are in ops.experiments and in the LangSmith project datapilot-experiments or
datapilot-development.

| Claim | Runs | Ids |
|---|---|---|
| Baseline v1: holdout passes | 2 of 15 in 5 of 5 experiments | b44ad06e, 2bcc6ac2, 572dc0ea, bf861054, 51ec1e22 |
| Promoted v4: holdout passes, regressions | 11 of 15 and 12 of 15, 0 regressions | 1e0ec097, 3358ea89 |
| Candidates of the demo pass: holdout passes, regressions | 3 of 15 and 6 of 15, 0 regressions | aa1dfae5, 0cf7df9d |
| Holdout trap items flipped by v4 | 10 of 13 | 3358ea89 |
| The confirming re-run clears an apparent regression | 1 apparent regression, cleared at 3 of 3 re-runs | calibration step confirm, 23:40 UTC |
| Stability under v1 and v4 | v1 0 of 15 unstable (twice); v4 3 of 15, then 4 of 15 | stability runs 23:02, 23:10, 23:18, 23:23 UTC |
| Items the stability filter replaced in the end | 0 (3 replaced, then restored) | see the commits on the module evidence page |
| Families cleared by a promotion | average order value and customers; none; average order value and products | 22 October capture; demo passes 1 and 2 |
| The spine question after promotion | correct, posted at the assisted level | 32c5abc0 |
| Experiment wall time, 70 runs at concurrency 8 | 187 to 285 s over 8 experiments | the ids above |
| The naive analyzer, blocked | not shown once: v7 passed 15 of 15 holdout items, gate ready | 911423fb |
| Analyzer at reasoning effort high: holdout passes | 2, 9, and 5 of 15 against 2 | 25d0f021, 4ae5177b, 66616a62 |
| Promoted v5: holdout passes, regressions | 10 of 15 against 2, 0 regressions | 407ff720 |
| Families cleared by the v5 promotion | average order value and products; revenue fell short | 407ff720 |
| The spine question after the v5 promotion | posted at the assisted level, gold check failed | 631d0ccb |

The rehearsal and the class have not run yet; their results are added here after them.
<!-- provisional: filled after the rehearsal -->

## Captures

| File | Date | Run id |
|---|---|---|
| demo/expected/improve-baseline-experiment-running.png, -ledger.png | 22 October 2026 | experiment b44ad06e |
| demo/expected/improve-analyzer-team-diff.png | 22 October 2026 | request 1bd79879 |
| demo/expected/improve-candidate-experiment-ledger.png | 22 October 2026 | experiment 1e0ec097 |
| demo/expected/improve-candidate-experiment-gate.png | 23 October 2026 | experiment 407ff720 |
| demo/expected/improve-promotion-cleared.png | 22 October 2026 | promotion of v4 |
| demo/expected/improve-cleared-unattended-board.png, -channel.png | 22 October 2026 | 32c5abc0 |

## Sources and findings

The module records no finding ids. The sources the Section 4 pages cite are in the
Sources lists of its [README](../../section-4-hill-climbing-loop/README.md#sources) and its
[concepts page](../../section-4-hill-climbing-loop/concepts.md#sources), drawn from the source register on the
[evidence page for the whole module](general.md#sources-and-findings).

## Commits and tags

See the [evidence page for the whole module](general.md#commits-and-tags).
