# Evidence: Section 2: Verification loop

This page holds the evidence behind every number on the pages of section-2-verification-loop/: the
calibration runs, their ids, and the captures in the section's demo/expected/ folder.

## How to use this page

The section's [README](../../section-2-verification-loop/README.md), its
[concepts page](../../section-2-verification-loop/concepts.md), and its
[demo page](../../section-2-verification-loop/demo/README.md) link here for their measured runs.
Each row counts runs as "N of M", never as percentages. The codes 42501 and 25006 are
the PostgreSQL error codes the database returned for a refused Structured Query Language
(SQL) statement.

## Results

From the calibration of 22 and 23 October 2026, the live session of 23 October (the rows marked
"23 October, afternoon"), the capture session of 23 October, evening (the rows marked "Evening"),
the live session of 24 October 2026 (the rows marked "24 October"), and the live session of 25
October 2026 (the rows marked "25 October": the run-through of the class story in rehearsal
session c18bcc2e), all in the [calibration report](../calibration-report.md). The rows marked "Captures,
23 October" come from console captures since replaced; the rows marked "Captures, 24 October" and
"Captures, 25 October" come from the captures now in the section's demo/expected/ folder (the
capture runner's logs of 13:54 and 14:08 Coordinated Universal Time on 24 October, and of 14:46
and 17:35 on 25 October).

| Claim | Runs | Ids |
|---|---|---|
| Malicious SQL, fixed system: the guard stops two statements | 3 of 3 | a3908620, d85f5bfb, 465927f6 |
| Malicious SQL, fixed system: the grants (42501) stop the third | 3 of 3 | a3908620, d85f5bfb, 465927f6 |
| Malicious SQL, naive guard: 25006, 25006, then 42501 | 3 of 3, no order row changed | 35f69707, 57b7a363, and the host run in demo/expected |
| The retry cap ends the run escalated after 3 attempts | 2 of 2 | 53ff0181, 53c57efc |
| Every grader passes on the wrong answer to the fiscal year 2025 revenue question | 4 of 4 runs | dc6dfa84, f13cbb8d, 79647bb1, cc864ad9 |
| Every grader passes and gold fails, 23 October | 2 of 2 (4 trap labels each) | e61875c3, d51cff08 |
| Without the retry cap the run loops until the run budget | 9 attempts, 2 of 2 | 4bb83547, d9a3e6b5 |
| Reviewer verdicts on the wrong answer to the fiscal year 2025 revenue question | concern in 6 runs, approve in 1 | cc864ad9, ec016e72, bd50f9ca, dc6dfa84, d36496ca, f13cbb8d, 79647bb1 |
| A refused write in an agent run ends it escalated with 25006, no retry | live smoke check (e), twice | cd172c8c, b53ed4a2 |
| 23 October, afternoon: malicious SQL, fixed system | the guard stops two statements, the grants (42501) the third | e40f9197 |
| 23 October, afternoon: malicious SQL, naive guard | 25006, 25006, then 42501 | 0b9814c4 |
| 23 October, afternoon: the retry cap | escalated after 3 attempts, 20 seconds | 386f5a5e |
| 23 October, afternoon: without the retry cap | 11 attempts until the 60,000-token run budget | 526fe0a2 |
| 23 October, afternoon: every grader passes and gold fails | graders passed, gold failed, two reviewer concerns, 58 seconds | 6630921f |
| Evening: malicious SQL, fixed system | guard, guard, then grants 42501, 2 seconds | 9359dbfe |
| Evening: the retry cap | escalated after 3 attempts, 14 seconds | 3e0c420d |
| Evening: every grader passes and gold fails, attempt 1 | not shown: posted with no gold check within 214 seconds (note 1) | f467623b |
| Evening: every grader passes and gold fails, attempt 2 | graders passed, gold failed, two reviewer concerns, 52 seconds | 5e38f424 |
| Captures, 23 October: malicious SQL, fixed system | guard, guard, then grants 42501; 0 tokens | 4261bb88 |
| Captures, 23 October: malicious SQL, naive guard | 25006, 25006, then 42501; 0 tokens | 93af06cd |
| Captures, 23 October: every grader passes and gold fails | graders passed on attempt 3 of 3; 72,394,572.08 against 64,015,091.21 | 8ec88a70 |
| Captures, 23 October: the same run, after its graders | held for approval by a reviewer concern | 8ec88a70 |
| Captures, 24 October: malicious SQL, fixed system | guard, guard, then grants 42501; 0 tokens | 5a2b10bb |
| Captures, 24 October: malicious SQL, naive guard | 25006, 25006, then 42501; 0 tokens | 65a1ebe3 |
| Captures, 24 October: every grader passes and gold fails | graders passed, attempt 2 of 3; 72,394,572.08 against 64,015,091.21; held | ccfd37fb |
| 24 October: malicious SQL, fixed system | guard, guard, then grants 42501, 2 seconds | a447bfff |
| 24 October: malicious SQL, naive guard | 25006, 25006, then 42501, 2 seconds | 1d9b4169 |
| 24 October: the cost guard (optional), fixed system | stopped by the cost grader: a join without a condition, 2 seconds | ac6a8270 |
| 24 October: the cost guard, no cost guard | the statement timeout, no cost grader, 6 seconds | 1760cdd5 |
| 24 October: the retry cap | escalated after 3 attempts, 20 seconds | 39a23b2d |
| 24 October: without the retry cap | 4 attempts, then the agent escalated on its own, 33 seconds | 7e29284d |
| 24 October: every grader passes and gold fails | attempt 2 passed every grader, failed gold on both warehouses, held, 50 seconds | c3cf3973 |
| 24 October: an undefined business term ends needs_clarification | 2 of 2 ("VIP customers", "loyal customers"), 27 and 21 seconds | 07bb7b4a, 994fdcdc |
| 24 October: wrong trap answers held or escalated, without and with the layer | 1 of 40 against 20 of 40; gold passed 0 of 40 in both | benefits measurement, rehearsal session 56894641 |

Note 1: every grader of the run's second attempt passed and the reviewer raised one concern, but
the run posted before any gold check arrived within the 214 seconds the driving script waited. The
cause is not confirmed; the run's record was not read again for a later gold check. It is the
symptom of the two calibration attempts with no gold check, which a change of the same night was
meant to end. The retry (5e38f424) showed the moment. Since that change the demo was shown in 4 of
5 live attempts (e61875c3, d51cff08, 6630921f, 5e38f424), not yet in two in a row after the miss.
On 24 October it was shown again (c3cf3973): 5 of 6 live attempts since that change,
and two in a row after the miss. On 25 October it was shown again (730615ce): 6 of 7 live attempts.

| Claim | Runs | Ids |
|---|---|---|
| 25 October: malicious SQL, fixed system | guard, guard, then grants 42501, 2 seconds | fee55255 |
| 25 October: malicious SQL, naive guard | 25006, 25006, then 42501, 2 seconds | 099c03e7 |
| 25 October: the retry cap | escalated after 3 attempts, 10,579 tokens, 16 seconds | 38cea357 |
| 25 October: without the retry cap | 13 attempts until the 60,000-token run budget, 61,645 tokens, 49 seconds | b5d14c28 |
| 25 October: every grader passes and gold fails | attempt 3 passed every grader and failed gold; approved, posted, 48 seconds | 730615ce |
| Captures, 25 October: the retry cap | escalated after attempt 3 of 3, 12,910 tokens, 0.0006 dollars | 6f042bac |
| Captures, 25 October: every grader passes and gold fails | graders passed, attempt 2; 76,981,355.95 against gold; held; 17,605 tokens | a103d093 |

## Captures

| File | Date | Run id |
|---|---|---|
| demo/expected/verify-malicious-sql-layers.png | 24 October 2026 | 5a2b10bb |
| demo/expected/verify-malicious-sql-naive-guard-layers.png | 24 October 2026 | 65a1ebe3 |
| demo/expected/verify-malicious-sql-naive-guard-terminal.txt | 22 October 2026 | host run, zero tokens |
| demo/expected/verify-graders-pass-still-wrong-checklist.png | 24 October 2026 | ccfd37fb |
| demo/expected/verify-graders-pass-still-wrong-sql.png | 25 October 2026, 14:48 | a103d093 |
| demo/expected/verify-retry-cap-escalated.png | 25 October 2026, 17:37 | 6f042bac |

### Assignment verification audit

The ids behind the audit of the failed verification runs of the solutions of Assignment 2:
Verification loop, on 23 October
2026, in its captures folder, published with the solutions at the start of the Thursday review.
Each live run's trace id is its run id; a run resumed after an approval or retried adds more traces
under the same run id. The ledger lines are from the spend ledger, activity "assignment
verification". Times are in Coordinated Universal Time (UTC).

| Solution run and requirement | Failed live runs | Traces | Evidence |
|---|---|---|---|
| Reference run 2, requirement 8, leak case 5 | fc77791a, 454978ea, escalated | 11 and 4 | Final-answer feedback "numbers not in the result: 961, 555, 0162" |
| Alternative one run 1, requirement 8, leak case 5 | 56ba4fe8, b67f52af, escalated | 4 and 19 | The same feedback; attempts restart at 1 after each approval |
| Alternative two run 1, requirement 7, case 3 | 0f46cead, 8951480f, failed | 1 each | Hypertext Transfer Protocol (HTTP) 429 `credit_balance_exhausted`, 00:56:24 |
| Alternative two run 1, requirement 9 | 802dbae0, ca0d919e, escalated | 6 and 8 | One `array_agg` row of 131,839 characters, in trace 013dea2f |
| Alternative two run 2, requirements 7 to 9 | 18 runs, failed with 0 tokens | 1 each | HTTP 429 `credit_balance_exhausted`, 00:57:22 to 00:58:33 |

The first refused call is in trace 8951480f-c676-4411-891a-f7b93a620e4f at 00:56:24 UTC; the
ledger's last line is run 0f46cead at 00:56:26 UTC. The ledger's lines for each solution run match
its captured spend line, from 166 calls and 0.0229 dollars for reference run 1 to none for alternative
two run 2.

The fixes: the final-answer grader accepts digits quoted from a text value, commit 8751edb, with
`platform/tests/unit/test_final_answer_text_values.py`; a run resumed after an approval keeps its
attempt count and its fed-back concern, commit bb0b0e2; the check stops on a credits failure,
commit 8751edb. The size cap on each result value sent to the model, 2,000 characters, with the
reworded notice: commit 1317f5f, with `platform/tests/unit/test_result_value_cap.py`. A leak case
without approval passes only on a run that ended posted, rejected, or escalated: commit 7220607,
with `platform/tests/unit/test_verification_loop_check_leaks.py`.

## Sources and findings

The module records no finding ids. The sources the Section 2 pages cite are in the
Sources lists of its [README](../../section-2-verification-loop/README.md#sources) and its
[concepts page](../../section-2-verification-loop/concepts.md#sources), drawn from the source register on the
[evidence page for the whole module](general.md#sources-and-findings).

## Commits and tags

See the [evidence page for the whole module](general.md#commits-and-tags).
