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

From the calibration of 22 and 23 October 2026 ([calibration report](../calibration-report.md)), all
under the starting knowledge v1 on gpt-6-luna.

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

The rehearsal and the class have not run yet; their results are added here after them.
<!-- provisional: filled after the rehearsal -->

## Captures

| File | Date | Run id |
|---|---|---|
| demo/expected/agent-simple-question-answer.png | 22 October 2026 | 3246b3e9 |
| demo/expected/agent-simple-question-terminal.txt | 22 October 2026 | 3246b3e9 |
| demo/expected/agent-confident-wrong-answer-run.png, -sql.png, -gold.png | 22 October 2026 | bd50f9ca |

## Sources and findings

The module records no finding ids. The sources the Section 1 pages cite are in the
Sources lists of its [README](../../section-1-agent-loop/README.md#sources) and its
[concepts page](../../section-1-agent-loop/concepts.md#sources), drawn from the source register on the
[evidence page for the whole module](general.md#sources-and-findings).

## Commits and tags

See the [evidence page for the whole module](general.md#commits-and-tags).
