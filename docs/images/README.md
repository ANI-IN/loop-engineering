# Module: Loop Engineering - Images of the class story

One capture per key moment of the class story, from live runs on 22 and 23 October 2026
(business date 31 January 2026). Each section's demo/expected/ folder holds the full set, with run
ids and notes on where a capture is older than the console. The captures of the agent and
verification loops, taken on 23 October from 22:13, and the hill-climbing captures, taken on 23
October between 21:27 and 21:55, are in Coordinated Universal Time; the captures of the event loop,
from 22 October, are in the capturing browser's local time, India Standard Time (5 hours 30 minutes ahead of Coordinated
Universal Time). The console shows your own local time.

Your output will differ: run times, ids, and the agent's wording change on every run.

## Section 1: Agent loop

![The Agent page after the simple question, with the Ask button, the posted run, its three tool calls, the live stamp, the Structured Query Language (SQL) query, and the answer](agent-simple-question-answer.png)

*The simple question: three tool calls, one query, a correct count.*

![The spine question's SQL with three trap notes, each numbered on a fragment of the SQL, the answer of 72,394,572.08 dollars, and the failed gold check](agent-confident-wrong-answer-sql.png)

*The confident wrong answer: trap notes beside the SQL, and gold does not match (run e6e3170a).*

## Section 2: Verification loop

![The defense layers for three malicious statements, the data-modifying CTE shown whole on two lines](verify-malicious-sql-layers.png)

*Malicious SQL: the guard stops two statements and the role grants the third.*

![The run holding for approval, every grader passed on attempt 3 of 3, the gold check failed on both databases, and the reviewer raised a concern](verify-graders-pass-still-wrong-checklist.png)

*Every grader passes, still wrong.*

## Section 3: Event loop

These captures, of 22 October, show an older Events page: a Question text box above the
buttons, which the page no longer has. Two are cut at the top. The section's demo/expected/ page says what changed.

![The answer posted at the report-only level, labelled unverified](events-webhook-question-channel.png)

*The webhook question, posted at the report-only level.*

![The pending approval survived the worker restart](events-approval-after-restart.png)

*The approval that survives a restart.*

![One posted run with 2 duplicates absorbed](events-duplicate-events-board.png)

*The same event three times: one answer.*

![The kill switch stopped the run in flight and forced the report-only level](events-kill-switch-in-flight-board.png)

*The kill switch in flight.*

## Section 4: Hill-climbing loop

![The holdout ledger comparing v1 and the candidate v9: v1 passes 2 of 15, v9 passes 14 of 15, 12 fixed and 0 regressions, some rows with a Trace link and some Not traced](improve-candidate-experiment-ledger.png)

*The candidate experiment: 14 of 15 holdout items against 2, with no regressions (experiment a2ba7a5a).*

![The status line after the promotion: revenue, average order value, customers, and products cleared for the unattended level, orders not cleared](improve-promotion-cleared.png)

*The promotion clears a family when every one of its holdout items passes on the confirmed standard: 2 of 3 runs, or 2 of 3 more runs for an item that fell short.*

The ledger header names who approved v9 as it was typed in the course build's capture session, a
note of that session rather than a person; in class it names the instructor who approves.

![The Channel post of the spine question's answer, 64,015,091.21 dollars, labelled posted at the unattended level](improve-cleared-unattended-channel.png)

*The finale: the spine question answered correctly under the promoted version v9, at the unattended level because revenue was cleared (run c91ebcc0).*
