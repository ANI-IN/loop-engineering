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

From the calibration of 22 and 23 October 2026 and the live session of 23 October, afternoon
(session 4), and the capture session of 23 October, evening, all in the
[calibration report](../calibration-report.md). The kill switch row also counts run 31984983, the
paced capture of 23 October in the section's demo/expected/ folder.

| Claim | Runs | Ids |
|---|---|---|
| A webhook question is posted labelled unverified at the report-only level | 3 of 4 (one held by a reviewer concern about the date, since fixed) | 7cf0509e, 5c2503c4, 8a6823fb |
| The pending approval survives a worker restart, and approving resumes the run | 5 of 5 | ef5eb601, 446dbe72, c85a9984, 13e0b95d, 85609cb3 |
| The same event three times gives one answer and 2 duplicates absorbed | 5 of 5 | 9a3a8296, 65ced5cc, f19be33c, c7bd992d, 44077b18 |
| The kill switch stops a run in flight and forces the report-only level | 7 of 7 | bb8b3e1f, 16b96215, 6a0b1408, 619c716e, b497410b, 31984983, bcf92dcb |
| Planted halves, 23 October (approval lost, 3 posts, kill switch missed) | 2 of 2 each | b81eb2e6, 58fe4dc2, fcf3834f, 1eeb2a0f, 02d72359, 70e1f9b0 |
| A webhook question is posted labelled unverified, 23 October | 4 of 4 | 9d8be803, 8f6c1fa2, be76dea9, 9f6e1d62 |
| Session 4: planted halves (approval lost; 3 answers; posted after the switch) | 1 of 1 each | 035816e8, 11e06819, 70235a3e |
| Session 4: the export after the 2,000-character value cap | 7,670 tokens, against about 109,000 before the cap | 13e0b95d |

The rehearsal and the class have not run yet; their results are added here after them.

## Captures

| File | Date | Run id |
|---|---|---|
| demo/expected/events-webhook-question-board.png, -channel.png | 22 October 2026 | 7cf0509e |
| demo/expected/events-approval-held.png, -after-restart.png, -approved-posted.png | 22 October 2026 | ef5eb601 |
| demo/expected/events-duplicate-events-board.png | 22 October 2026 | 9a3a8296 |
| demo/expected/events-kill-switch-in-flight-board.png | 22 October 2026 | bb8b3e1f |
| demo/expected/events-kill-switch-paced-running.png, -paced-stopped.png | 23 October 2026 | 31984983 |

## Sources and findings

The module records no finding ids. The sources the Section 3 pages cite are in the
Sources lists of its [README](../../section-3-event-loop/README.md#sources) and its
[concepts page](../../section-3-event-loop/concepts.md#sources), drawn from the source register on the
[evidence page for the whole module](general.md#sources-and-findings).

## Commits and tags

See the [evidence page for the whole module](general.md#commits-and-tags).
