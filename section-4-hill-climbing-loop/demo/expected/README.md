# Module: Loop Engineering - Expected output for Section 4: Hill-climbing loop

Real captures from live runs on 22 October 2026 (business date 31 January 2026), for comparison
after class. They are never shown in class: in class, every demo runs live. The approval was given
by the calibration run, standing in for the instructor.

Your output will differ: run times, ids, and the agent's wording change on every run.

Experiments trace to the LangSmith project
[datapilot-experiments](https://smith.langchain.com/o/10fe45d9-7a3d-4f39-92ad-8c5dc97653d4/projects/p/2e40b196-7ef5-4232-9f7a-cc770ef4aecb),
filtered by knowledge version. Experiment runs are traced as a sample, about 1 run in 5, so a
ledger row links to its own trace when one of its runs was traced and reads "Not traced" otherwise.

## The baseline experiment

![The holdout ledger at the start of the baseline experiment, every item not run yet](improve-baseline-experiment-running.png)

*The baseline benchmark starts: the ledger fills in as each item's runs finish.*

![The finished ledger of the baseline experiment under v1](improve-baseline-experiment-ledger.png)

*Under the starting knowledge v1, 2 of 15 holdout items pass (experiment b44ad06e).*

## The analyzer team and approval

![The knowledge diff from v1 to the candidate v4, with the new rules in green](improve-analyzer-team-diff.png)

*The analyzer team's candidate v4: seven general rules, kept by the critic and passed by the overfit guard.*

The failure analyst read the 21 failed dev items, the rule writer proposed eight rules, and the
critic dropped one (a business-day holiday rule). The overfit guard passed the other seven.

## The candidate experiment

![The holdout ledger comparing v1 and v4: 9 items fixed, no regressions](improve-candidate-experiment-ledger.png)

*v1 passes 2 of 15 holdout items, v4 passes 11 of 15: 9 fixed and 0 regressions (experiment 1e0ec097).*

![The gate's verdict above the knowledge diff: "Gate: ready for human approval." v5 passes 10 of 15 holdout items against 2](improve-candidate-experiment-gate.png)

*The gate is ready for human approval: more holdout passes and no regressions on either split.*

This capture comes from a later run, on 23 October: candidate v5 passes 10 of 15 against 2
(experiment 407ff720). Trace refused: LangSmith monthly unique trace limit; the run is in ops.

## The promotion

![The status line after the promotion: average order value and customers cleared for the unattended level](improve-promotion-cleared.png)

*After approval the gate promotes v4; the families whose holdout items all pass are cleared.*

Average order value and customers are cleared; revenue, orders, and products are not, because at
least one of their holdout items still fails.

## Cleared for the unattended level

![The board with the fiscal year 2025 question posted](improve-cleared-unattended-board.png)

*The spine question arrives as a webhook under the new active version.*

![The Channel with the correct answer, 64,015,091.21 dollars, posted at the assisted level](improve-cleared-unattended-channel.png)

*The answer is now correct and matches gold; it posts at the assisted level, not the unattended one.*

The revenue family is not cleared in this run (one revenue holdout item still fails), so with the
system set to the unattended level, the revenue answer gets the assisted level.

Trace: [run 32c5abc0](https://smith.langchain.com/o/10fe45d9-7a3d-4f39-92ad-8c5dc97653d4/projects/p/7ce7a82b-8edc-4fb1-b6bc-d13fe6070f5e/r/32c5abc0-1cde-4374-a95b-95a8c7fff923?poll=true)
