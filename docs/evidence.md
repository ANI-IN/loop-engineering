# Evidence

This page is the index of the run ids, finding ids, commit hashes, and capture details behind every
result the course pages report. The evidence pages it links are the only pages that may hold ids;
every other page links here instead. All results so far come from the calibration of 22 and 23
October 2026 and the live sessions of 23, 24, and 25 October, recorded in the
[calibration report](calibration-report.md).

## How to use this page

| Evidence file | What it holds |
|---|---|
| [The whole module](evidence/general.md) | model, costs, build spend, assignment verification, commits, sources |
| [Section 1: Agent loop](evidence/section-1-agent-loop.md) | the numbers on the Section 1 pages, with run ids and captures |
| [Section 2: Verification loop](evidence/section-2-verification-loop.md) | the numbers on the Section 2 pages, with run ids and captures |
| [Section 3: Event loop](evidence/section-3-event-loop.md) | the numbers on the Section 3 pages, with run ids and captures |
| [Section 4: Hill-climbing loop](evidence/section-4-hill-climbing-loop.md) | the numbers on the Section 4 pages, with run ids and captures |

## Results

### The whole module

The class model is gpt-6-luna; one analyst run costs about 0.001 dollars. By the end of the
calibration, in the night of 23 October 2026, OpenAI had billed the build 1.78 dollars of its 10.00-dollar budget. See [the module's results](evidence/general.md#results).

### Section 1: Agent loop

Every trap item fails under version 1 of the knowledge (the starting version): 99 of 99 runs
failed. See
[the Section 1 results](evidence/section-1-agent-loop.md#results).

### Section 2: Verification loop

Every grader passes on the wrong answer to the fiscal year 2025 revenue question in 4 of 4 runs. See
[the Section 2 results](evidence/section-2-verification-loop.md#results).

### Section 3: Event loop

The same event sent three times gives one answer and 2 duplicates absorbed, in 7 of 7 demo runs.
See
[the Section 3 results](evidence/section-3-event-loop.md#results).

### Section 4: Hill-climbing loop

Holdout items are the 15 benchmark questions the analyzer team never sees. The promoted version 9
of the knowledge passes 14 of 15 holdout items against 2 of 15 for version 1 (the starting
version), with 0 regressions, and the finale's answer to the fiscal year 2025 revenue question is
correct and posted at the unattended level (the capture session of 23 October, evening). That
repeats the result of version 8 in the live session the same afternoon. The live session of 24
October promoted version 11 at 13 of 15 and version 13 at 14 of 15, and the live session of 25
October versions 15, 17, and 19 at 13, 12, and 13 of 15. So the two-candidate method has seven
promotions measured, at 12 to 14 of 15 holdout items each. The earlier promoted versions passed 3
to 12 of 15. See [the Section 4 results](evidence/section-4-hill-climbing-loop.md#results).

### Final project

The final project runs on each learner's own dataset, so the course reports no measured result for
it; what a learner shows is listed in the [final project checklist](../final-project/CHECKLIST.md).

## Captures

- [The whole module: assignment verification](evidence/general.md#captures)
- [Section 1: Agent loop](evidence/section-1-agent-loop.md#captures)
- [Section 2: Verification loop](evidence/section-2-verification-loop.md#captures)
- [Section 3: Event loop](evidence/section-3-event-loop.md#captures)
- [Section 4: Hill-climbing loop](evidence/section-4-hill-climbing-loop.md#captures)

## Sources and findings

The source register, and the note on finding ids, are on
[the evidence page for the whole module](evidence/general.md#sources-and-findings).

## Commits and tags

The calibration's commits are listed on
[the evidence page for the whole module](evidence/general.md#commits-and-tags). The public release
carries no tag: each release is a normal commit on the public repository's main branch, made as the
[release checklist](release-checklist.md) describes.
