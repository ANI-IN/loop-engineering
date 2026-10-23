# Evidence: Section 3: Event loop

This page holds the evidence behind every number on the pages of section-3-event-loop/: the
calibration runs, their ids, and the captures in the section's demo/expected/ folder.

## How to use this page

The section's [README](../../section-3-event-loop/README.md), its
[concepts page](../../section-3-event-loop/concepts.md), and its
[demo page](../../section-3-event-loop/demo/README.md) link here for their measured runs.
Each row counts runs as "N of M", never as percentages; a row that names demo pacing
counts the runs made with the pauses between lifecycle stages turned on.

## Results

From the calibration of 22 and 23 October 2026 ([calibration report](../calibration-report.md)).

| Claim | Runs | Ids |
|---|---|---|
| A webhook question is posted labelled unverified at the report-only level | 3 of 4 (one held by a reviewer concern about the date, since fixed) | 7cf0509e, 5c2503c4, 8a6823fb |
| The pending approval survives a worker restart, and approving resumes the run | 3 of 3 | ef5eb601, 446dbe72, c85a9984 |
| The same event three times gives one answer and 2 duplicates absorbed | 3 of 3 | 9a3a8296, 65ced5cc, f19be33c |
| The kill switch stops a run in flight and forces the report-only level | 4 of 4 (2 with demo pacing) | bb8b3e1f, 16b96215, 6a0b1408, 619c716e |
| Planted halves, 23 October (approval lost, 3 posts, kill switch missed) | 2 of 2 each | b81eb2e6, 58fe4dc2, fcf3834f, 1eeb2a0f, 02d72359, 70e1f9b0 |
| A webhook question is posted labelled unverified, 23 October | 2 of 2 | 9d8be803, 8f6c1fa2 |

The rehearsal and the class have not run yet; their results are added here after them.
<!-- provisional: filled after the rehearsal -->

## Captures

| File | Date | Run id |
|---|---|---|
| demo/expected/events-webhook-question-board.png, -channel.png | 22 October 2026 | 7cf0509e |
| demo/expected/events-approval-held.png, -after-restart.png, -approved-posted.png | 22 October 2026 | ef5eb601 |
| demo/expected/events-duplicate-events-board.png | 22 October 2026 | 9a3a8296 |
| demo/expected/events-kill-switch-in-flight-board.png | 22 October 2026 | bb8b3e1f |
| demo/expected/events-kill-switch-paced-running.png, -paced-stopped.png | 23 October 2026 | 16b96215 |

## Sources and findings

The module records no finding ids. The sources the Section 3 pages cite are in the
Sources lists of its [README](../../section-3-event-loop/README.md#sources) and its
[concepts page](../../section-3-event-loop/concepts.md#sources), drawn from the source register on the
[evidence page for the whole module](general.md#sources-and-findings).

## Commits and tags

See the [evidence page for the whole module](general.md#commits-and-tags).
