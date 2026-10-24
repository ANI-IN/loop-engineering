# Evidence: Section 1: Agent loop

This page holds the evidence behind every number on the pages of section-1-agent-loop/: the
calibration runs, their ids, and the captures in the section's demo/expected/ folder.

## How to use this page

The section's [README](../../section-1-agent-loop/README.md), its
[concepts page](../../section-1-agent-loop/concepts.md), and its
[demo page](../../section-1-agent-loop/demo/README.md) link here for their measured runs.
Each row counts runs as "N of M", never as percentages. A spine run counts against
gold only when it answered with a Structured Query Language (SQL) query and got a gold
check. Times are in Coordinated Universal Time (UTC).

## Results

From the calibration of 22 and 23 October 2026 and the live session of 23 October, afternoon
(session 4), and the capture session of 23 October, evening (the rows marked "Evening"), all in the [calibration report](../calibration-report.md). The rows marked "Captures, 23
October" come from the console captures in the section's demo/expected/ folder. All under the starting knowledge v1 on gpt-6-luna.

| Claim | Runs | Ids |
|---|---|---|
| The simple question is answered with list_tables, describe_table, and one query | 4 of 4 posted | 3246b3e9, 0086c2e0, e71a1401, bc033bdd |
| The spine question gets a confident wrong answer that fails gold | answered with SQL and failed gold in 3 of 3 runs that got a gold check | bd50f9ca, d36496ca, dc6dfa84 |
| The spine question got no gold check within 90 seconds | 1 run | c02c2117 |
| Every trap item fails under v1 | 99 of 99 runs failed | experiment 322f604d |
| The scout's cost, scout and reviewer on against scout off | 8,648 tokens, 24.2 s against 3,853 tokens, 12.8 s (mean of 4 questions) | calibration step agents, 23:29 UTC |
| The unbounded rows demo, fixed half | 19,661 and 17,298 tokens | 9f635488, 2b0eb54c |
| The spine question fails gold with trap labels, 23 October | 2 of 2 (3 trap labels each) | 17fc06b7, 489cf450 |
| The unbounded rows demo, planted half (10,000 rows) | 183,639 and 185,727 tokens | 3de95c50, e4d1bae9 |
| Session 4: the simple question | posted, 405,738 orders, 14 s | 8d53e57c |
| Session 4: the spine question fails gold | 76,981,355.95 against 64,015,091.21, 4 trap labels, 52 s | f64f5dfe |
| Session 4: the unbounded rows demo, fixed half | 27,040 tokens, held for approval after two reviewer concerns | c30c0885 |
| Session 4: the unbounded rows demo, planted half | 186,689 tokens, escalated at the run budget | 1ae983f2 |
| Evening: the simple question | posted, 405,738 orders, 14 s | 335bcbe5 |
| Evening: the spine question fails gold | 76,981,355.95 against 64,015,091.21, 4 trap labels, 37 s | 82011f72 |
| Evening: the unbounded rows demo, fixed half | 22,862 tokens, held after two reviewer concerns, 26 s | 06c830b5 |
| Captures, 23 October: the simple question from Agent > Ask | posted, 405,738 orders, 5,126 tokens | c25c1106 |
| Captures, 23 October: Agent > Ask the spine question, run 1 of 3 | held, 72,394,572.08 against 64,015,091.21, 3 trap notes | e6e3170a |
| Captures, 23 October: Agent > Ask the spine question, run 2 of 3 | a six-column answer that failed gold on its shape | 456efa67 |
| Captures, 23 October: Agent > Ask the spine question, run 3 of 3 | an answer with no number and no gold check | d8d884a3 |

The rehearsal and the class have not run yet; their results are added here after them.

## Captures

| File | Date | Run id |
|---|---|---|
| demo/expected/agent-simple-question-answer.png | 23 October 2026 | c25c1106 |
| demo/expected/agent-simple-question-terminal.txt | 22 October 2026 | 3246b3e9 |
| demo/expected/agent-confident-wrong-answer-run.png, -sql.png, -gold.png | 23 October 2026 | e6e3170a |

## Sources and findings

The module records no finding ids. The sources the Section 1 pages cite are in the
Sources lists of its [README](../../section-1-agent-loop/README.md#sources) and its
[concepts page](../../section-1-agent-loop/concepts.md#sources), drawn from the source register on the
[evidence page for the whole module](general.md#sources-and-findings).

## Commits and tags

See the [evidence page for the whole module](general.md#commits-and-tags).
