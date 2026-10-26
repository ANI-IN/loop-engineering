# Module: Loop Engineering - Images of the class story

One capture per key moment of the class story, from live runs on 24 October 2026, 13:53 to 14:37
Coordinated Universal Time, and four retaken on 25 October 2026 from 14:43 (business date 31
January 2026). Each section's demo/expected/ folder
holds the full set, with run ids and what each frame shows and leaves out. Times on the captures
are in Coordinated Universal Time (UTC); the console shows your own local time.

Your output will differ: run times, ids, and the agent's wording change on every run.

## Section 1: Agent loop

![The Agent page after the simple question: Posted, the tool calls list_tables, describe_table, and run_query, 1.4 seconds in total, the live stamp of run 87a06dba, the one-line count query, No trap found in this query, the answer 405738 orders, and 5,151 tokens](agent-simple-question-answer.png)

*The simple question, run 87a06dba, 25 October 2026: three tool calls, one query, a correct count, and the run posted.*

![The spine question's annotated Structured Query Language (SQL) query: marks 1 on both calendar-year bounds, 2 on both order_ts comparisons, and 3 on WHERE, the Fiscal year, Eastern time, and Internal accounts notes, the answer 72,394,572.08 for calendar year 2025, and the mismatch against gold 64015091.21](agent-confident-wrong-answer-sql.png)

*The confident wrong answer, run 9182df01, 25 October 2026: one number for calendar year 2025, three trap notes, and gold does not match on either database.*

## Section 2: Verification loop

![The defense layers for three malicious statements: the guard stops the stacked statements on parse and the data-modifying CTE on its statement policy, and the role grants stop the raw DELETE with SQLSTATE 42501](verify-malicious-sql-layers.png)

*Malicious SQL, run 5a2b10bb, 24 October 2026: the guard stops two statements and the role grants the third, with 0 tokens.*

![The run holding for approval, all seven graders passed on attempt 2 of 3, the agent's answer 72394572.08 against gold 64015091.21 with a mismatch on both databases, and the reviewer's concern about the fiscal year](verify-graders-pass-still-wrong-checklist.png)

*Every grader passes, still wrong, run ccfd37fb, 24 October 2026: the checklist is green, gold fails on both databases, and the reviewer's concern holds the run.*

## Section 3: Event loop

![The Events page scrolled to the Channel: the baseline benchmark strip in Done, the empty off-the-board columns, the buttons, and the Channel's one post, Posted at the report-only level, unverified, with the answer 300 orders](events-webhook-question-channel.png)

*The webhook question, run 0ebf3d5c, 25 October 2026: posted at the report-only level, labelled unverified, with its answer in the frame; its own strip in Done is above the frame.*

![After Restart worker: the export still in Holding for approval, the line The pending approval survived: run b1b1453b still holding., and a Channel with no posts](events-approval-after-restart.png)

*The approval that survives a restart, run b1b1453b, 24 October 2026: the run still holds after the worker restarts.*

![The board with Done holding 3 runs, of which the frame shows one: the webhook question about the previous day's orders, posted at the report-only level, run 0391e0c2, marked 2 duplicates absorbed, then 1 more](events-duplicate-events-board.png)

*Duplicate events, run 0391e0c2, 25 October 2026: the question posted once, and its two repeats were absorbed as duplicates.*

![The status line forced to the report-only level by the kill switch, with the line that all workers stopped, the Release kill switch button, and the run under Blocked by kill switch](events-kill-switch-in-flight-board.png)

*The kill switch in flight, run 1352df28, 24 October 2026: the run stops in flight and the system is held at the report-only level.*

## Section 4: Hill-climbing loop

These come from the capture chain of 24 October 2026, whose candidate is v13; the session's main
chain of the same day promoted v11.

![The holdout ledger comparing v1 and the candidate v13: v1 passes 2 of 15, v13 passes 14 of 15, 12 fixed and 0 regressions, some rows with a Trace link and some Not traced](improve-candidate-experiment-ledger.png)

*The candidate experiment, experiment 0e1cbfe7, 24 October 2026: 14 of 15 holdout items against 2, with no regressions.*

![The status line after the promotion: revenue, average order value, customers, and products cleared for the unattended level, orders not cleared; the ledger reads Replaced, v1 and Active, v13](improve-promotion-cleared.png)

*The promotion of v13, experiment 0e1cbfe7, 24 October 2026: four families are cleared on the confirmed standard, 2 of 3 runs or 2 of 3 more for an item that fell short; orders is not.*

![The run board scrolled down: Done holds the posted spine question with Gold check passed: 64,015,091.21, run 59174f10, then the v13 benchmark strip, 70 of 70 runs done](improve-cleared-unattended-channel.png)

*The finale, run 59174f10, 24 October 2026: correct under v13, posted at the unattended level, gold check passed; the Channel post is below the frame.*
