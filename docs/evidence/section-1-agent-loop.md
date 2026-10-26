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
(session 4), the capture session of 23 October, evening (the rows marked "Evening"), the live
session of 24 October 2026 (session 5, the rows marked "24 October"), and the live session of 25
October 2026 (session 6, the rows marked "25 October": the class story pass in rehearsal session
c18bcc2e), all in the [calibration report](../calibration-report.md). The rows marked "Captures,
23 October" and "Captures, 24 October" come from console captures since replaced; the rows marked
"Captures, 25 October" come from the captures now in the section's demo/expected/ folder (the
capture runner's logs of 14:42 and 14:52 UTC). All under the starting knowledge v1 on gpt-6-luna.

| Claim | Runs | Ids |
|---|---|---|
| The simple question is answered with list_tables, describe_table, and one query | 4 of 4 posted | 3246b3e9, 0086c2e0, e71a1401, bc033bdd |
| The spine question gets a confident wrong answer that fails gold | answered with SQL and failed gold in 3 of 3 runs that got a gold check | bd50f9ca, d36496ca, dc6dfa84 |
| The spine question got no gold check within 90 seconds | 1 run | c02c2117 |
| Every trap item fails under v1 | 99 of 99 runs failed | experiment 322f604d |
| The scout's cost, scout and reviewer on against scout off | 8,648 tokens, 24.2 seconds, against 3,853 tokens, 12.8 seconds (mean of 4) | calibration step agents, 23:29 UTC |
| The unbounded rows demo, fixed half | 19,661 and 17,298 tokens | 9f635488, 2b0eb54c |
| The spine question fails gold with trap labels, 23 October | 2 of 2 (3 trap labels each) | 17fc06b7, 489cf450 |
| The unbounded rows demo, planted half (10,000 rows) | 183,639 and 185,727 tokens | 3de95c50, e4d1bae9 |
| Session 4: the simple question | posted, 405,738 orders, 14 seconds | 8d53e57c |
| Session 4: the spine question fails gold | 76,981,355.95 against 64,015,091.21, 4 trap labels, 52 seconds | f64f5dfe |
| Session 4: the unbounded rows demo, fixed half | 27,040 tokens, held for approval after two reviewer concerns | c30c0885 |
| Session 4: the unbounded rows demo, planted half | 186,689 tokens, escalated at the run budget | 1ae983f2 |
| Evening: the simple question | posted, 405,738 orders, 14 seconds | 335bcbe5 |
| Evening: the spine question fails gold | 76,981,355.95 against 64,015,091.21, 4 trap labels, 37 seconds | 82011f72 |
| Evening: the unbounded rows demo, fixed half | 22,862 tokens, held after two reviewer concerns, 26 seconds | 06c830b5 |
| Captures, 23 October: the simple question from Agent > Ask | posted, 405,738 orders, 5,126 tokens | c25c1106 |
| Captures, 23 October: Agent > Ask the spine question, run 1 of 3 | held, 72,394,572.08 against 64,015,091.21, 3 trap notes | e6e3170a |
| Captures, 23 October: Agent > Ask the spine question, run 2 of 3 | a six-column answer that failed gold on its shape | 456efa67 |
| Captures, 23 October: Agent > Ask the spine question, run 3 of 3 | an answer with no number and no gold check | d8d884a3 |
| 24 October: the simple question | posted, 405,738 orders, 5,139 tokens, 16 seconds | e26fcd8d |
| 24 October: Texas last quarter (optional) | posted, net revenue by product category, 4 joins, 49 seconds | 75f56196 |
| 24 October: the spine question fails gold | 72,394,572.08 against 64,015,091.21, 3 trap labels, held, 50 seconds | fe75848f |
| 24 October: the unbounded rows demo, fixed half | 30,216 tokens, held after two reviewer concerns, 33 seconds | e1f21cf2 |
| 24 October: the unbounded rows demo, planted half | 182,654 tokens, escalated at the run budget, 12 seconds | be82d6f6 |
| 24 October: easy items passing gold, without and with the protections | 12 of 21 against 17 of 21 (7 items, 3 rounds) | benefits measurement, rehearsal session 56894641 |
| Captures, 24 October: the simple question from Agent > Ask | posted, 405,738 orders, 5,130 tokens | 0a195764 |
| Captures, 24 October: Agent > Ask the spine question | held; a hedged answer by status: 72,394,572.08 against 64,015,091.21 | ee3dade4 |
| 25 October: the simple question | posted, 405,738 orders, 5,130 tokens, 16 seconds | f415f991 |
| 25 October: the spine question fails gold | 72,394,572.08 against 64,015,091.21, 3 trap labels, held, 35 seconds | 581e2720 |
| 25 October: the unbounded rows demo, fixed half | 26,683 tokens, held after two reviewer concerns, 30 seconds | 3bc3a42d |
| 25 October: the unbounded rows demo, planted half | 187,030 tokens, escalated, 12 seconds | eeaa4e24 |
| The unbounded rows demo over every recorded run | fixed half 17,298 to 30,216 tokens; planted half 182,654 to 187,030 tokens | the rows above |
| Captures, 25 October: the simple question | posted, 405,738 orders, 5,151 tokens, 0.0005 dollars | 87a06dba |
| Captures, 25 October: the spine question | held; 72,394,572.08 against 64,015,091.21, 3 trap notes, 32,421 tokens | 9182df01 |
| Captures, 25 October: the unbounded rows demo, fixed half | held after two reviewer concerns, 28,468 tokens, 0.0022 dollars | 072af9b6 |
| Captures, 25 October: the unbounded rows demo, planted half | escalated, 184,983 tokens, 0.0230 dollars | 199d2188 |

## Captures

| File | Date | Run id |
|---|---|---|
| demo/expected/agent-simple-question-answer.png | 25 October 2026, 14:43 UTC | 87a06dba |
| demo/expected/agent-simple-question-terminal.txt | 22 October 2026 | 3246b3e9 |
| demo/expected/agent-confident-wrong-answer-run.png, -sql.png, -gold.png | 25 October 2026, 14:45 UTC | 9182df01 |
| demo/expected/agent-unbounded-rows-fixed-tokens.png | 25 October 2026, 14:46 UTC | 072af9b6 |
| demo/expected/agent-unbounded-rows-planted-tokens.png | 25 October 2026, 14:53 UTC | 199d2188 |

## Sources and findings

The module records no finding ids. The sources the Section 1 pages cite are in the
Sources lists of its [README](../../section-1-agent-loop/README.md#sources) and its
[concepts page](../../section-1-agent-loop/concepts.md#sources), drawn from the source register on the
[evidence page for the whole module](general.md#sources-and-findings).

## Commits and tags

See the [evidence page for the whole module](general.md#commits-and-tags).
