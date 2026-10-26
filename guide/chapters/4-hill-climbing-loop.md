# Chapter 4: Section 4: Hill-climbing loop

The analyst still lacks the business rules. This loop measures it on the benchmark, has an analyzer
team write rules from the failed dev items, and lets a gate on the holdout items and a person decide
whether the new knowledge version goes live. You watch the Improve page's holdout ledger, the
knowledge diff, and the gate, then the spine question on the Events page. Every screenshot in
this chapter but one comes from one hill-climbing chain run live on 24 October 2026, 14:10 to 14:37
Coordinated Universal Time (business date 31 January 2026), the capture chain, whose candidate is
v13. The gate's verdict in step 6 was retaken on 25 October 2026 in a later chain, whose candidate
is v19. The other chains, with candidates v11, v15, and v17, are in the result summary. Every time
range comes from the calibration and the live sessions of 22 to 25 October 2026.

> Your output will differ: run times, ids, and the agent's wording change on every run.

### Step 1: Start the baseline experiment at the poll

**Where:** The demo terminal, in the repository folder, and the console's Improve page.

**Type:** this at the start of the poll, or press **Run experiment on the active version**.

```bash
make demo NAME=improve-baseline-experiment
```

**You should see:** the holdout ledger under "Baseline, v1, active", every item not run yet.

![The Improve page at the start of the baseline experiment: the status line at the report-only level, Baseline, v1, active, started 14:10:00, and the holdout ledger with every item marked Not run yet](../../section-4-hill-climbing-loop/demo/expected/improve-baseline-experiment-running.png)

*Experiment aa1d02ff, 24 October 2026: the baseline benchmark starts under v1, 0 of 0 items finished and 15 not run yet; the ledger fills in as each item's runs finish.*

**Look at:** the line "Each item runs 3 times and passes on 2 of 3."

**What it means:** the experiment runs the 25 dev items once and the 15 holdout items 3 times each
under the starting knowledge v1. It is this session's baseline, and it runs through the break.

> [!CHECKPOINT]
> The ledger shows "Baseline, v1, active" with a start time from this session.

> [!IFDIFFERENT]
> "No live session." → run `make preflight PURPOSE=class` once, then start the baseline again.
> The ledger does not move → check that the `hill-climbing-runner` service is up with `make ps`.

> [!INSTRUCTOR]
> Start it before the poll, never after. Say: "This is our instrument. We measure before we change
> anything."

### Step 2: Read the baseline ledger

**Where:** The Improve page, after the break.

**Type:** nothing; read the ledger.

**You should see:** each holdout item with its result, and a trace link or "Not traced":
experiment runs are traced as a sample, about 1 run in 5.

![The finished baseline ledger under v1: v1 passes 2 of 15 finished items, the mean list price and the assortment by top-level category Passed 3 of 3 runs, the other visible rows Failed 0 of 3 runs, some with a Trace link and some Not traced](../../section-4-hill-climbing-loop/demo/expected/improve-baseline-experiment-ledger.png)

*Experiment aa1d02ff, 24 October 2026: under the starting knowledge v1, 2 of 15 holdout items pass, both without a trap; it also passed 4 of 25 dev items.*

**Look at:** "v1 passes 2 of 15 finished items".

**What it means:** v1 passes the questions without a trap and fails every trap question. That is
the number the candidate must beat.

> [!CHECKPOINT]
> Every row has a result, and a **Trace** link or "Not traced".

> [!IFDIFFERENT]
> A different pass count → expected; which non-trap items pass can vary.
> Some rows still "Not run yet" → the experiment is still running; read the count when it ends.

> [!INSTRUCTOR]
> Open one row's **Trace** link to show the run in LangSmith, then come back to the ledger: the ledger is
> the source of truth.

### Step 3: Run the naive analyzer and watch the gate block it

**Where:** The demo terminal, and the Improve page.

**Type:** this; the command sends the naive analyzer's flag with its two requests only, with or
without `PLANTED=1`, and `.env` keeps every planted flag at `0`. On the console, Improve > Run the
naive analyzer (planted), shown while demo controls are allowed, queues the same two requests; Run
analyzer runs the analyzer team.

```bash
make demo NAME=improve-naive-analyzer-blocked PLANTED=1
```

**You should see:** the naive analyzer makes no model call. It writes one rule per failed dev
question, quoting the question word for word with the query that failed, and skips the critic. The
overfit guard flags every rule, but its verdict is not applied, so the knowledge diff keeps them
all. The same command then queues the candidate experiment, which the runner takes after the
analyzer. After it, the gate blocks the version and names the rules the overfit guard rejects,
whatever the holdout count. Nothing to switch back before the next step.

![The Improve page after the naive analyzer: the knowledge diff from v1 to v14 under the line Naive analyzer: 21 rules, no critic; the overfit guard flags 21 of 21, not applied., and the first added rule, answer-net-revenue-calendar-2024, quoting a benchmark question and the query that failed](../../section-4-hill-climbing-loop/demo/expected/improve-naive-analyzer-blocked-guard.png)

*Candidate v14, 24 October 2026: the naive analyzer writes 21 rules and skips the critic; the overfit guard flags all 21, and its verdict is not applied.*

![The bottom of the candidate ledger for v14 with every visible row Failed under both versions and No change, then Gate: blocked. v14 has 21 rules the overfit guard rejects, each one named](../../section-4-hill-climbing-loop/demo/expected/improve-naive-analyzer-blocked-gate.png)

*Candidate v14, 24 October 2026: the gate blocks it; v14 passes 2 of 15 holdout items, no more than v1, and every rule it adds fails the overfit guard.*

**Look at:** the guard's flag on every rule, then the gate's verdict and its reason line for the
overfit guard on the new rules.

**What it means:** a rule that quotes a test question is tied to that one question, so it teaches
nothing about the next one. The gate has four conditions, and the fourth is that every rule a
candidate adds passes the overfit guard, so a version written without the guard is blocked even
when its holdout count rises.

> [!CHECKPOINT]
> The gate reads blocked.

> [!IFDIFFERENT]
> The rules look general → the request was sent with Improve > Run analyzer, so the analyzer team ran; run `make demo NAME=improve-naive-analyzer-blocked PLANTED=1`, or Improve > Run the naive analyzer (planted).

> [!INSTRUCTOR]
> Then `make reset NAME=hill-climbing-loop`: it keeps the session's baseline. In its 6 measured
> runs since it was made deterministic, the naive analyzer wrote 20 or 21 rules, all flagged by
> the overfit guard, and the gate blocked it every time. The holdout never improved: 2 of 15 in
> five runs, and 0 of 15 with 2 holdout regressions on 25 October 2026. An earlier version
> read the reference queries, passed 15 of 15, and got through a gate of three conditions; that run
> is why the fourth exists.

### Step 4: Run the analyzer team

**Where:** The demo terminal, and the Improve page.

**Type:** this, or press **Run analyzer**.

```bash
make demo NAME=improve-analyzer-team-approve
```

**You should see:** the knowledge diff from the active version to the candidate, with the new rules
in green.

![The knowledge diff from the active version v1 to v13, under the line Candidate A: 22 of 25 dev, 0 regressions, 9 rules; Candidate B: 20 of 25 dev, 0 regressions, 8 rules; chosen: A, with the first added rule, eligible-order-customer-population, and its guidance](../../section-4-hill-climbing-loop/demo/expected/improve-analyzer-team-diff.png)

*Candidate v13, 24 October 2026: the analyzer team writes two candidates, runs each on the dev split only, and keeps candidate A, 22 of 25 dev items against 20.*

**Look at:** the line above the diff that names both candidates and the one kept; then the first
green rule, `eligible-order-customer-population`. It names no benchmark question, and its
Structured Query Language (SQL) guidance, `o.status <> 5 AND lower(c.email) NOT LIKE
'%@harborpine.com'`, runs over the schema.

**What it means:** in the captured run, the failure analyst read the 21 failed dev items. For
candidate A, the rule writer proposed eleven rules, the critic dropped one and narrowed one, and
the overfit guard rejected one that copied a reference query, which left nine. A rule whose SQL
guidance does not run over the schema is dropped before the guard. Each candidate runs on the dev split only, and the
Improve page names both and the one kept: fewer dev regressions, then more dev passes, then fewer
rules. The holdout never takes part in the choice.

> [!CHECKPOINT]
> The diff shows at least one new rule in green.

> [!IFDIFFERENT]
> A different number of rules → expected; in calibration the team proposed 8 and 9 rules.
> "No candidate version in this session yet." → the analyzer has not finished; wait, then reload.

> [!INSTRUCTOR]
> Read one rule aloud. Say: "A rule must be general to pass the guard. A person still approves it."

### Step 5: Run the candidate experiment

**Where:** The demo terminal, and the Improve page.

**Type:** this, or press **Run experiment on the candidate**.

```bash
make demo NAME=improve-candidate-experiment
```

**You should see:** the holdout ledger with both versions side by side and a **Change** column.

![The holdout ledger comparing v1 and the candidate v13: v1 passes 2 of 15, v13 passes 14 of 15, 12 fixed and 0 regressions, with rows marked Fixed: now passes or No change](../../section-4-hill-climbing-loop/demo/expected/improve-candidate-experiment-ledger.png)

*Experiment 0e1cbfe7, 24 October 2026: v1 passes 2 of 15 holdout items and v13 passes 14 of 15: 12 fixed and 0 regressions; the working-days item still fails.*

**Look at:** the summary line: "12 fixed, 0 regressions".

**What it means:** the candidate fixes holdout items it never saw and breaks none. Both versions
ran in the same session, so the comparison is fair.

> [!CHECKPOINT]
> The summary line names the fixed items and the regressions.

> [!IFDIFFERENT]
> Fewer items fixed → expected; in calibration one candidate gave 3 to 12 of 15 against 2, and two candidates gave 12 to 14 of 15 in seven measurements. Report the count you got.
> A holdout regression → the gate re-runs the candidate 3 more times on the item and counts it only on at least 2 failures.
> A dev regression → the gate re-runs the item 2 more times under each version and counts it only when the candidate fails both and the active version passes both.

> [!INSTRUCTOR]
> Then open the LangSmith trace list of `datapilot-experiments`, filtered by knowledge version, to
> show the candidate's runs. If the candidate is weak, say so: the gate is doing its job.

### Step 6: Read the gate and approve

**Where:** The Improve page; scroll to the gate's verdict above the knowledge diff.

**Type:** read the verdict, then press the approve button, which names the candidate version
(v13 in the chain of steps 5 and 7, v19 in this step's frame).

**You should see:** the verdict and its reason.

![The gate's verdict, Gate: ready for human approval. v19 passes 13 of 15 holdout items against 2, with no regressions., above the Improve page's buttons and the start of the knowledge diff from v1 to v19, under the line Candidate A: 21 of 25 dev, 0 regressions, 7 rules; Candidate B: 21 of 25 dev, 0 regressions, 7 rules; chosen: A](../../section-4-hill-climbing-loop/demo/expected/improve-candidate-experiment-gate.png)

*25 October 2026, the chain whose candidate is v19: the gate is waiting only for a person: more holdout passes and no regressions.*

The frame predates the Run the naive analyzer (planted) button, so your Improve page shows one more
button while demo controls are allowed.

**Look at:** the reason after the label: "Ready for human approval".

**What it means:** the code checks passed; only human approval is left. In the frame's chain, v19
also passes 23 of 25 dev items against v1's 5, with no dev regression; in the chain of steps 5
and 7, v13 passes 22 of 25 against 4.

> [!CHECKPOINT]
> The verdict reads ready for human approval before you approve.

> [!IFDIFFERENT]
> "Gate: blocked." with a reason that starts "Blocked:" → the candidate failed a check; do not approve, read the reason aloud.

> [!INSTRUCTOR]
> Approve on screen, slowly. Say: "The gate never promotes on its own."

### Step 7: Read the promotion on the status line

**Where:** The Improve page, top of the screen.

**Type:** nothing; read the status line.

**You should see:** the candidate (v13 in the captured run) is the active version, and the
families that meet the gate's confirmed standard are cleared.

![The status line after the promotion: Unattended clearance with revenue, average order value, customers, and products cleared and orders not cleared; the ledger reads Replaced, v1 and Active, v13, 14 of 15](../../section-4-hill-climbing-loop/demo/expected/improve-promotion-cleared.png)

*Experiment 0e1cbfe7, 24 October 2026: after approval v13 is the active version; revenue, average order value, customers, and products are cleared, orders is not.*

**Look at:** "Unattended clearance" on the status line.

**What it means:** revenue, average order value, customers, and products are cleared; orders is
not. A family clears on the gate's confirmed standard: every holdout item passes 2 of 3 runs, and an
item that falls short is re-run 3 more times and must pass 2 of them.

> [!CHECKPOINT]
> The ledger names the candidate as active, "Active, v13" in the captured run, and the person who approved it.

> [!IFDIFFERENT]
> Different families cleared → expected; calibration cleared none in one promotion, average order value and products in two, and revenue, average order value, customers, and products in the latest.

> [!INSTRUCTOR]
> Point at revenue on the status line before the finale. If it is under "Not cleared", say: "Revenue has not earned it yet."

### Step 8: Send the spine question at the unattended level

**Where:** The demo terminal, and the Events page.

**Type:** once the Improve page says the candidate is the active version, set the system to the unattended level (or press
**Set the unattended level** on the Improve page), then send the spine question by webhook (or
press **Send webhook question**, which sends the spine question from the promotion on, whether a
family cleared or none did):

```bash
make autonomy LEVEL=unattended BY="<your name>"
make demo NAME=improve-cleared-unattended
```

Every reset sets the report-only level, so this step comes after the last reset. While the
promotion is still running, the kill switch is engaged, or the level is lower, the finale is not
sent and the message names the step that is missing. In the captured run the finale was held 5
times while the promotion and its clearance re-runs finished, and posted 74 seconds after the
first send. In the class story pass of 25 October 2026 it was held while the re-runs ran and posted
162 seconds after the first send.

**You should see:** the spine question answered under the promoted version. In the captured run
(v13), revenue was cleared, and the correct answer posted at the unattended level. In an earlier run
(v4, 22 October), revenue was not cleared, so the answer posted at the assisted level. A few
seconds after the post, the run's strip shows its gold check, "Gold check passed" with the value,
or "Gold check failed" with the agent's value and the gold value.

![The Events page with the status line at the unattended level, revenue, average order value, customers, and products cleared, and the spine question in the Done lane, posted at the unattended level, with Gold check passed: 64,015,091.21 and run 59174f10](../../section-4-hill-climbing-loop/demo/expected/improve-cleared-unattended-board.png)

*Run 59174f10, 24 October 2026: the spine question arrives as a webhook under v13, posts at the unattended level, and its strip shows the gold check passed.*

![The run board scrolled down: Done holds the posted spine question with Gold check passed: 64,015,091.21, run 59174f10, then the v13 benchmark strip, 70 of 70 runs done, and 1 more](../../section-4-hill-climbing-loop/demo/expected/improve-cleared-unattended-channel.png)

*Run 59174f10, 24 October 2026: the frame stops at the Done lane and the buttons; the Channel post, "Net revenue in fiscal year 2025 was $64,015,091.21.", is below it.*

**Look at:** the post's label, and the net revenue, 64,015,091.21 dollars.

**What it means:** the same question that failed in Sections 1 and 2 now matches gold. The answer
posts at the level its family has earned: at the unattended level, without approval, only when
revenue met the gate's confirmed standard; otherwise at the assisted level, which is a correct
outcome.

> [!CHECKPOINT]
> The answer is 64,015,091.21 dollars, and the label states its level.

> [!IFDIFFERENT]
> Posted at the assisted level → revenue was not cleared; say so, it is the honest result.
> A wrong answer → the promoted version did not fix this item in this run; show the ledger row for it. In class, the instructor uses the class-day safeguard in the instructor guide.

> [!INSTRUCTOR]
> Leave the open question: "A family clears for the unattended level on its holdout questions:
> 4 for revenue, 1 for average order value. Is that enough evidence?"

## Result summary

| Promoted version | Holdout items passed against v1's 2 of 15 (headline) | Families cleared for the unattended level | The spine question; rules, secondary |
|---|---|---|---|
| 22 October, v4 | 11 of 15, 9 fixed, 0 regressions | Average order value, customers | Correct, at the assisted level; seven rules of eight |
| 23 October, v8 | 14 of 15, 12 fixed, 0 regressions | All but orders | Correct, at the unattended level; eight rules, candidate B of two |
| 23 October, v9 | 14 of 15, 12 fixed, 0 regressions | All but orders | Correct, at the unattended level; eight rules, candidate A of two |
| 24 October, v11, main chain | 13 of 15, 0 regressions | Average order value, customers, revenue | Correct, at the unattended level; six rules, candidate B of two |
| 24 October, v13, captured | 14 of 15, 12 fixed, 0 regressions | All but orders | Correct, at the unattended level; nine rules, candidate A of two |
| 25 October, v15, class story pass | 13 of 15, 0 regressions; dev 25 of 25 | All but orders | Correct, at the unattended level; nine rules, candidate B of two |
| 25 October, v17, retake chain | 12 of 15, 0 regressions; dev 24 of 25 | All but orders | Correct, at the unattended level |
| 25 October, v19, retake chain | 13 of 15, 0 regressions; dev 23 of 25 | All but orders | Not run: blocked by the daily token budget; seven rules, candidate A of two |

## Time and cost

Times are wall time from the trigger to the checked result, from the calibration of 22 and 23
October 2026 and the live sessions of 23, 24, and 25 October (`docs/calibration-report.md`, and
the chains' logs for their finales), each demo run alone with a reset between. Each range covers
every recorded run; the longest ran while the machine was shared with assignment checks.

| Demo | Time | Shown | Cost |
|---|---|---|---|
| The baseline experiment | 236 to 386 seconds | Every run: v1 at 2 of 15 | 0.0594 to 0.0914 dollars per 70 runs |
| The naive analyzer, blocked | 211 to 580 seconds | 6 of 6 since it was made deterministic | No model call in the analyzer |
| The analyzer team and approval | 326 to 377 seconds in five runs with two candidates | Every run | Not measured alone; it is part of the candidate experiment's chain |
| The candidate experiment | 171.3 to 459 seconds per 70 runs | 3 of 5 in calibration; ready for approval in every chain since | 0.0594 to 0.0914 dollars per 70 runs |
| Cleared for the unattended level | After a promotion 50, 74, 115, and 162 seconds; on the safeguard 19 and 21 | Unattended level after v8 to v17; assisted after v4 and v5 | About 0.0004 to 0.0007 dollars per run |

Experiments run at concurrency 8 (`evaluation.concurrency` in `pack.yaml`). The baseline experiment
is over its 3-minute target. Two candidate experiments, at analyzer reasoning effort high, ran 6.8
and 7.6 minutes, past the 5-minute budget; the analyzer team took 62 to 98 seconds with one candidate.

## What to say in class

- "We measured before we changed anything: v1 passes 2 of 15 holdout items."
- "The analyzer team wrote general rules; the guard and the holdout items check them."
- "The gate found more passes and no regressions, and still waited for a person."
- "The spine answer is right now. It posts at the level revenue has earned: the assisted level
  until every revenue holdout item meets the confirmed standard."
- If the candidate was weak: "One analyzer run is not a guarantee. The gate refused to pretend
  otherwise."
