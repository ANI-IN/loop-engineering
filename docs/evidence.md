# Evidence

This page is the index of the run ids, finding ids, commit hashes, and capture details behind every
result the course pages report. The evidence pages it links are the only pages that may hold ids;
every other page links here instead. All results so far come from the calibration of 22 and 23
October 2026, recorded in the [calibration report](calibration-report.md).

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

The class model is gpt-6-luna; one analyst run costs about 0.001 dollars; the build spent 1.6833
dollars of 10.00 by the end of calibration. See [the module's results](evidence/general.md#results).

### Section 1: Agent loop

Every trap item fails under the starting knowledge v1, 99 of 99 runs. See
[the Section 1 results](evidence/section-1-agent-loop.md#results).

### Section 2: Verification loop

Every grader passes on the wrong spine answer in 4 of 4 runs. See
[the Section 2 results](evidence/section-2-verification-loop.md#results).

### Section 3: Event loop

The same event three times gives one answer and 2 duplicates absorbed, 3 of 3. See
[the Section 3 results](evidence/section-3-event-loop.md#results).

### Section 4: Hill-climbing loop

The promoted v4 passes 11 of 15 and 12 of 15 holdout items against 2 of 15 for v1, with 0
regressions. See [the Section 4 results](evidence/section-4-hill-climbing-loop.md#results).

### Final project

The final project has no measured runs yet; its evidence is added after the class.
<!-- provisional: filled after the rehearsal -->

## Captures

- [The whole module: assignment verification passes](evidence/general.md#captures)
- [Section 1: Agent loop](evidence/section-1-agent-loop.md#captures)
- [Section 2: Verification loop](evidence/section-2-verification-loop.md#captures)
- [Section 3: Event loop](evidence/section-3-event-loop.md#captures)
- [Section 4: Hill-climbing loop](evidence/section-4-hill-climbing-loop.md#captures)

## Sources and findings

The source register, and the note on finding ids, are on
[the evidence page for the whole module](evidence/general.md#sources-and-findings).

## Commits and tags

The calibration's commits are listed on
[the evidence page for the whole module](evidence/general.md#commits-and-tags). No release tag
exists yet; the tag, and how to check a copy against it, are added at release.
<!-- provisional: filled at release -->
