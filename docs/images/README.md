# Module: Loop Engineering - Images of the class story

One capture per key moment of the class story, from live runs on 22 October 2026 (business date 31
January 2026). Each section's demo/expected/ folder holds the full set, with trace links.

Your output will differ: run times, ids, and the agent's wording change on every run.

## Section 1: Agent loop

![The Agent page after the simple question, with the live stamp, the Structured Query Language (SQL) query, and the answer](agent-simple-question-answer.png)

*The simple question: three tool calls, one query, a correct count.*

![The spine question's SQL with trap notes and the failed gold check](agent-confident-wrong-answer-sql.png)

*The confident wrong answer: each wrong fragment carries its trap note, and gold does not match.*

## Section 2: Verification loop

![The defense layers for three malicious statements](verify-malicious-sql-layers.png)

*Malicious SQL: the guard stops two statements and the role grants the third.*

![Every grader passed, the gold check failed on both databases, and the reviewer raised a concern](verify-graders-pass-still-wrong-checklist.png)

*Every grader passes, still wrong.*

## Section 3: Event loop

![The answer posted at the report-only level, labelled unverified](events-webhook-question-channel.png)

*The webhook question, posted at the report-only level.*

![The pending approval survived the worker restart](events-approval-after-restart.png)

*The approval that survives a restart.*

![One posted run with 2 duplicates absorbed](events-duplicate-events-board.png)

*The same event three times: one answer.*

![The kill switch stopped the run in flight and forced the report-only level](events-kill-switch-in-flight-board.png)

*The kill switch in flight.*

## Section 4: Hill-climbing loop

![The holdout ledger comparing v1 and the candidate v4: 9 fixed, no regressions](improve-candidate-experiment-ledger.png)

*The candidate experiment: 11 of 15 holdout items against 2, with no regressions.*

![The status line after the promotion: two metric families cleared](improve-promotion-cleared.png)

*The promotion clears the families whose holdout items all pass.*

![The correct answer to the spine question posted to the channel](improve-cleared-unattended-channel.png)

*The finale: the spine question answered correctly under the promoted version.*
