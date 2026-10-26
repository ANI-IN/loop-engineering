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
(session 4), the capture session of 23 October, evening, the live session of 24 October 2026
(session 5, the rows marked "24 October"), and the live session of 25 October 2026 (session 6,
the rows marked "25 October": the class story pass in rehearsal session c18bcc2e), all in the
[calibration report](../calibration-report.md). The kill switch row also counts run 31984983, the
paced capture of 23 October, since replaced. The rows marked "Captures, 24 October" and "Captures, 25
October" come from the captures now in the section's demo/expected/ folder (the capture runner's
logs of 13:55, 14:04, and 14:09 Coordinated Universal Time on 24 October, and of 14:48, 14:56,
14:58, 15:02, and 17:37 on 25 October).

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
| 24 October: the webhook question | posted unverified, 12 seconds | 105ee553 |
| 24 October: the digest now (optional) | one post, labelled unverified, 30 seconds | 1049cfd1 |
| 24 October: the approval across a worker restart | held, still held after the restart, posted after approval, 59 seconds | 43ec464c |
| 24 October: the same event three times | 1 question run, 2 duplicates absorbed, 1 digest, 37 seconds | ef8db308 |
| 24 October: the kill switch in flight | blocked in flight, report-only level, 4 seconds | 2c986f56 |
| 24 October: planted halves (approval lost; 3 runs; posted despite the switch) | 1 of 1 each, 41, 37, and 16 seconds | 88a0227a, d5817278, 47ad546f |
| Captures, 24 October: the webhook question | posted unverified, 300 orders, 7,629 tokens | ce15ac5d |
| Captures, 24 October: the approval across a worker restart | held, still held after the restart, posted after approval, 5,261 customers | b1b1453b |
| Captures, 24 October: the same event three times | 1 question run, 2 duplicates absorbed; the digest in view, 1 absorbed | 13b14128, e4dab18c |
| Captures, 24 October: the kill switch in flight, no pacing | blocked in flight, report-only level, 754 tokens | 1352df28 |
| Captures, 24 October: the kill switch in flight, demo pacing | seen in the Running lane, then blocked at its next step, 0 tokens | 1c76de06 |
| 25 October: the webhook question | posted unverified, 14 seconds | c4f16531 |
| 25 October: the approval across a worker restart | held, still held after the restart, posted after approval, 60 seconds | 9dd82764 |
| 25 October: the same event three times | 1 question run, 2 duplicates absorbed, 1 digest, 37 seconds | e6fb7684 |
| 25 October: the kill switch in flight | blocked in flight, report-only level, 3 seconds | 520c3f8d |
| 25 October: planted halves (approval lost; 3 runs, 2 digests; posted) | 1 of 1 each, 41, 33, and 30 seconds | b62d3c7e, 46c9a1c9, c06d22f1 |
| Demo runs shown, 24 and 25 October, added to the counts above | 2 of 2 each: approval, duplicates, kill switch | 43ec464c, 9dd82764, ef8db308, e6fb7684, 2c986f56, 520c3f8d |
| Captures, 25 October: the webhook question's Channel | posted unverified, 300 orders, 9,778 tokens | 0ebf3d5c |
| Captures, 25 October: the export held for approval | held, the query reads personal data | 1bc03afe |
| Captures, 25 October: the Review dialog | about 5,261 rows, the exact query, Approve and run, Reject | 72a1f1af |
| Captures, 25 October: the same event three times | 1 question run, 2 duplicates absorbed, 300 orders | 0391e0c2 |
| Captures, 25 October: the in-memory checkpointer | the pending approval lost; the run failed | 712fce2f |
| Captures, 25 October: the missing idempotency | the question and the digest each ran more than once, every post unverified | the six runs of the 14:58 log |
| Captures, 25 October: the kill switch at claim only, demo pacing | posted despite the engaged switch, 9,799 tokens | e7960de0 |

## Captures

| File | Date | Run id |
|---|---|---|
| demo/expected/events-webhook-question-board.png | 24 October 2026 | ce15ac5d |
| demo/expected/events-webhook-question-channel.png | 25 October 2026, 14:49 | 0ebf3d5c |
| demo/expected/events-approval-held.png | 25 October 2026, 14:50 | 1bc03afe |
| demo/expected/events-approval-after-restart.png, -approved-posted.png | 24 October 2026 | b1b1453b |
| demo/expected/events-approval-review-dialog.png | 25 October 2026, 17:38 | 72a1f1af |
| demo/expected/events-approval-lost-after-restart.png | 25 October 2026, 14:57 | 712fce2f |
| demo/expected/events-duplicate-events-board.png | 25 October 2026, 14:52 | 0391e0c2 |
| demo/expected/events-duplicate-events-no-idempotency-channel.png | 25 October 2026, 15:02 | 100d1ba7, 1e05cd0d, 77db15eb, c97e87d2, da2b471c, da6c873e |
| demo/expected/events-kill-switch-at-claim-only-board.png | 25 October 2026, 15:03 | e7960de0 |
| demo/expected/events-kill-switch-in-flight-board.png | 24 October 2026 | 1352df28 |
| demo/expected/events-kill-switch-paced-running.png, -paced-stopped.png | 24 October 2026 | 1c76de06 |

## Sources and findings

The module records no finding ids. The sources the Section 3 pages cite are in the
Sources lists of its [README](../../section-3-event-loop/README.md#sources) and its
[concepts page](../../section-3-event-loop/concepts.md#sources), drawn from the source register on the
[evidence page for the whole module](general.md#sources-and-findings).

## Commits and tags

See the [evidence page for the whole module](general.md#commits-and-tags).
