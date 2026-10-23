# Chapter 4: Section 4: Hill-climbing loop

The analyst still lacks the business rules. This loop measures it on the benchmark, has an analyzer
team write rules from the failed dev items, and lets a gate on the holdout items and a person decide
whether the new knowledge version goes live. You watch the Improve page's holdout ledger, the
knowledge diff, and the gate, then the spine question on the Events page. Every screenshot and
number in this chapter comes from the live runs of 22 October 2026 (business date 31 January
2026), and every time range from the calibration of 22 and 23 October 2026.

> Your output will differ: run times, ids, and the agent's wording change on every run.

### Step 1: Start the baseline experiment at the poll

**Where:** The demo terminal, in the repository folder, and the console's Improve page.

**Type:** this at the start of the poll, or press **Run experiment on the active version**.

```bash
make demo NAME=improve-baseline-experiment
```

**You should see:** the holdout ledger under "Baseline, v1, active", every item not run yet.

![The Improve page at the start of the baseline experiment: the status line, "Baseline, v1, active" with its start time, and the holdout ledger with every item marked Not run yet](../../section-4-hill-climbing-loop/demo/expected/improve-baseline-experiment-running.png)

*The baseline benchmark starts: the ledger fills in as each item's runs finish.*

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

**You should see:** each holdout item with its result and its trace link.

![The finished baseline ledger under v1: v1 passes 2 of 15 finished items, the visible rows Passed 3 of 3 runs or Failed 0 of 3 runs, each with a Trace link](../../section-4-hill-climbing-loop/demo/expected/improve-baseline-experiment-ledger.png)

*Under the starting knowledge v1, 2 of 15 holdout items pass.*

**Look at:** "v1 passes 2 of 15 finished items".

**What it means:** v1 passes the questions without a trap and fails every trap question. That is
the number the candidate must beat.

> [!CHECKPOINT]
> Every row has a result and a **Trace** link.

> [!IFDIFFERENT]
> A different pass count → expected; which non-trap items pass can vary.
> Some rows still "Not run yet" → the experiment is still running; read the count when it ends.

> [!INSTRUCTOR]
> Open one **Trace** link to show the run in LangSmith, then come back to the ledger: the ledger is
> the source of truth.

### Step 3: Run the naive analyzer and watch the gate block it

**Where:** `.env` in an editor, the demo terminal, and the Improve page.

**Type:** set `BUG_NAIVE_ANALYZER=1` in `.env`, then:

```bash
make up
make demo NAME=improve-naive-analyzer-blocked
```

**You should see:** the naive analyzer makes no model call. It writes one rule per failed dev
question, quoting the question word for word with the query that failed, and skips the critic. The
overfit guard flags every rule, but its verdict is not applied, so the knowledge diff keeps them
all. After the candidate experiment, the gate blocks the version and names the rules the overfit
guard rejects, whatever the holdout count.

<!-- capture: the naive analyzer, blocked: the Improve page with the rules that quote benchmark questions, the holdout ledger, and the gate's blocked verdict -->

**Look at:** the guard's flag on every rule, then the gate's verdict and its reason line for the
overfit guard on the new rules.

**What it means:** a rule that quotes a test question is tied to that one question, so it teaches
nothing about the next one. The gate has four conditions, and the fourth is that every rule a
candidate adds passes the overfit guard, so a version written without the guard is blocked even
when its holdout count rises.

> [!CHECKPOINT]
> The gate reads blocked.

> [!IFDIFFERENT]
> The rules look general → `BUG_NAIVE_ANALYZER` is not on in the services; set it to `1` in `.env`, then `make up`.

> [!INSTRUCTOR]
> Set the flag back to `0`, run `make up`, then `make reset NAME=hill-climbing-loop`: it keeps the
> session's baseline. This demo has no measured run of the naive analyzer as it is now. Its one
> live attempt, before it was made deterministic, read the reference queries, passed 15 of 15
> holdout items, and the gate of three conditions let it through; that run is why the fourth exists.

### Step 4: Run the analyzer team

**Where:** The demo terminal, and the Improve page.

**Type:** this, or press **Run analyzer**.

```bash
make demo NAME=improve-analyzer-team-approve
```

**You should see:** the knowledge diff from the active version to the candidate, with the new rules
in green.

![The knowledge diff from v1 to the candidate v4: the version line, the money rule kept, the starting note removed in red, and the new rule eligible-order-population in green](../../section-4-hill-climbing-loop/demo/expected/improve-analyzer-team-diff.png)

*The analyzer team's candidate v4: general rules, kept by the critic and passed by the overfit guard.*

**Look at:** the first green rule, `eligible-order-population`: it names no benchmark question.

**What it means:** in the captured run, the failure analyst read the 21 failed dev items, the rule
writer proposed eight rules, the critic dropped one, and the overfit guard passed the other seven.
The team now writes two candidates this way. A rule whose Structured Query Language (SQL) guidance does not run over the schema
is dropped before the guard. Each candidate runs on the dev split only, and the Improve page names
both and the one kept: fewer dev regressions, then more dev passes, then fewer rules. The holdout
never takes part in the choice. The capture shows one candidate, from before this change.

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

![The holdout ledger comparing v1 and the candidate v4: v1 passes 2 of 15, v4 passes 11 of 15, 9 fixed and 0 regressions, with rows marked Fixed: now passes or No change](../../section-4-hill-climbing-loop/demo/expected/improve-candidate-experiment-ledger.png)

*v1 passes 2 of 15 holdout items and v4 passes 11 of 15: 9 fixed and 0 regressions.*

**Look at:** the summary line: "9 fixed, 0 regressions".

**What it means:** the candidate fixes holdout items it never saw and breaks none. Both versions
ran in the same session, so the comparison is fair.

> [!CHECKPOINT]
> The summary line names the fixed items and the regressions.

> [!IFDIFFERENT]
> Fewer items fixed → expected; in calibration the same chain gave 3 and 6 of 15 against 2. Report the count you got.
> A holdout regression → the gate re-runs the candidate 3 more times on the item and counts it only on at least 2 failures.
> A dev regression → the gate re-runs the item 2 more times under each version and counts it only when the candidate fails both and the active version passes both.

> [!INSTRUCTOR]
> Then open the LangSmith trace list of `datapilot-experiments`, filtered by knowledge version, to
> show the candidate's runs. If the candidate is weak, say so: the gate is doing its job.

### Step 6: Read the gate and approve

**Where:** The Improve page; scroll to the gate's verdict above the knowledge diff.

**Type:** read the verdict, then press **Approve v4** (the button names the candidate version).

**You should see:** the verdict and its reason.

![The gate's verdict above the knowledge diff: "Gate: ready for human approval." v5 passes 10 of 15 holdout items against 2, with no regressions.](../../section-4-hill-climbing-loop/demo/expected/improve-candidate-experiment-gate.png)

*The gate is waiting only for a person: more holdout passes and no regressions.*

**Look at:** the reason after the label: "Ready for human approval".

**What it means:** the code checks passed; only human approval is left. This capture comes from a
later run (23 October, candidate v5, experiment 407ff720) than the other images of this chapter,
so its version and counts differ. Trace refused: LangSmith monthly unique trace limit; the run is experiment 407ff720 in ops.

> [!CHECKPOINT]
> The verdict reads ready for human approval before you approve.

> [!IFDIFFERENT]
> "Gate: blocked." with a reason that starts "Blocked:" → the candidate failed a check; do not approve, read the reason aloud.

> [!INSTRUCTOR]
> Approve on screen, slowly. Say: "The gate never promotes on its own."

### Step 7: Read the promotion on the status line

**Where:** The Improve page, top of the screen.

**Type:** nothing; read the status line.

**You should see:** v4 is the active version, and the families that meet the gate's confirmed
standard are cleared.

![The status line after the promotion: Unattended clearance with average order value and customers cleared, and revenue, orders, and products not cleared; the ledger under Baseline, v4, active passes 11 of 15](../../section-4-hill-climbing-loop/demo/expected/improve-promotion-cleared.png)

*After approval the gate promotes v4 and clears the families that meet the confirmed standard.*

**Look at:** "Unattended clearance" on the status line.

**What it means:** average order value and customers are cleared. Revenue, orders, and products are
not. A family clears on the gate's confirmed standard: every holdout item passes 2 of 3 runs, and an
item that falls short is re-run 3 more times and must pass 2 of them. This capture is from 22
October, under the earlier rule that every holdout item pass in one experiment.

> [!CHECKPOINT]
> The ledger heading reads "Baseline, v4, active".

> [!IFDIFFERENT]
> Different families cleared → expected; calibration cleared none in one promotion and average order value and products in two others, the last on the confirmed standard.

> [!INSTRUCTOR]
> Point at revenue under "Not cleared" before the finale. Say: "Revenue has not earned it yet."

### Step 8: Send the spine question at the unattended level

**Where:** The demo terminal, and the Events page.

**Type:** set the system to the unattended level, then send the spine question by webhook, or press
**Send webhook question** with the spine question.

<!-- capture: the control or command that sets the system to the unattended level, as run in the finale -->

```bash
make demo NAME=improve-cleared-unattended
```

**You should see:** the spine question answered under v4. In the captured run, revenue was not
cleared, so the answer posted at the assisted level.

![The Events page with the status line at the unattended level, average order value and customers cleared, and the spine question posted at the assisted level](../../section-4-hill-climbing-loop/demo/expected/improve-cleared-unattended-board.png)

*The spine question arrives as a webhook under the new active version.*

![The Channel post "Posted at the assisted level, verified": net revenue in fiscal year 2025 was 64,015,091.21 dollars](../../section-4-hill-climbing-loop/demo/expected/improve-cleared-unattended-channel.png)

*The answer is now correct and matches gold; it posts at the assisted level, not the unattended one.*

<!-- capture: the finale with the revenue family cleared: the spine question posted at the unattended level, without approval -->

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

| Item | This run |
|---|---|
| Holdout items passed, v1 against v4 | 2 of 15 against 11 of 15, 0 regressions (headline) |
| Holdout items fixed by v4 | 9 |
| Families cleared for the unattended level | Average order value, customers |
| The spine question under v4 | Correct, posted at the assisted level |
| Rules in v4, secondary | Seven, after the critic dropped one of eight |

## Time and cost

Times are wall time from the trigger to the checked result, from the calibration of 22 and 23
October 2026 (`docs/calibration-report.md`), each demo run alone with a reset between.

| Demo | Time | Shown in calibration | Cost |
|---|---|---|---|
| The baseline experiment | 266 to 285 s | 2 of 2 | 0.0594 to 0.0828 dollars per 70 runs |
| The naive analyzer, blocked | Not measured as it is now | 0 of 1, before it was made deterministic | Not measured |
| The analyzer team and approval | 62 to 98 s | 2 of 2 | Not measured |
| The candidate experiment | 187 to 285 s per 70 runs, 8 experiments | 0 of 2: weak candidates | 0.0594 to 0.0828 dollars per 70 runs |
| Cleared for the unattended level | Not measured | 0 of 2: assisted level | About 0.001 dollars per run |

Experiments run at concurrency 8 (`evaluation.concurrency` in `pack.yaml`). The baseline experiment
is over its 3-minute target; the candidate experiment stays inside its 5-minute budget.

## What to say in class

- "We measured before we changed anything: v1 passes 2 of 15 holdout items."
- "The analyzer team wrote general rules; the guard and the holdout items check them."
- "The gate found more passes and no regressions, and still waited for a person."
- "The spine answer is right now. It posts at the level revenue has earned: the assisted level
  until every revenue holdout item meets the confirmed standard."
- If the candidate was weak: "One analyzer run is not a guarantee. The gate refused to pretend
  otherwise."
