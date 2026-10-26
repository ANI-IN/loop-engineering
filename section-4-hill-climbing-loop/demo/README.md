# Module: Loop Engineering - Demos for Section 4: Hill-climbing loop

## The problem

**Illustrative scenario.** The pasted fixes from the [section page](../README.md#the-problem): the
score on the failed questions jumps, the change ships, and next month's questions are still wrong.

These demos run that loop live and put a gate in its way. A baseline experiment measures version 1
of the knowledge (the starting version) on the benchmark. A naive analyzer writes rules that quote
the questions, and the gate blocks them. The analyzer team writes two candidates of general rules,
the one with the better results on the development split is kept, a person approves it, and the
candidate experiment decides on the holdout split.

> **Terms on this page**
>
> - **Hill-climbing loop**: Experiments find failures, an analyzer team proposes rules, and a gate decides.
> - **Knowledge version**: A numbered set of business rules given to the agent in its prompt.
> - **Development split**: The benchmark questions the analyzer team may learn from.
> - **Holdout split**: The benchmark questions the analyzer team never sees; the gate decides on them.
> - **Promotion gate**: The check that a new knowledge version must pass before it becomes active.
> - **Regression**: An item that passed under the active version and fails under the candidate, confirmed by re-runs.
> - **Human approval**: A person approves or rejects a held action before it runs.
> - **Autonomy level**: How much DataPilot may do unattended: report-only, assisted, or unattended.
>
> All terms: [glossary](../../docs/glossary.md).

## What you'll see

Every experiment item is a fresh, real run of the analyst with real model calls. Results are scored
locally first: an answer passes only if its Structured Query Language (SQL) returns the gold result
on both warehouses. Experiment runs are traced in LangSmith as a sample, about 1 run in 5, to stay
inside the free plan's monthly traces: a row of the holdout ledger links to its trace when one of
its runs was traced and reads "Not traced" otherwise, and every row is scored all the same. The
analyzer team makes real model calls too, and the knowledge diff shows exactly what it proposes.

Times and cost, measured live from 22 to 25 October 2026, over every recorded run:

- the baseline experiment, 236 to 386 seconds from the trigger;
- the analyzer team, 326 to 377 seconds with two candidates, in five runs;
- the candidate experiment, 176 to 337 seconds from the trigger, and 171.3 to 459 seconds of
  experiment wall time;
- the naive analyzer, 211 to 580 seconds from the trigger to the verdict, in 6 runs;
- after approval, the version active in about 5 seconds, then the clearance re-runs; the finale
  posted 74, 115, and 162 seconds after its first send in three chains;
- one 70-run experiment, 0.0594 to 0.0914 dollars.

In class order on 25 October 2026, in seconds: the baseline 252, the analyzer team 362, the
candidate experiment 237, the finale 162 from its first send, the finale on the class-day
safeguard 21, and the naive analyzer 221. The runs are on the
[evidence page](../../docs/evidence/section-4-hill-climbing-loop.md#results), and `run.sh` states the most
an experiment can cost at the caps in `platform/packs/datapilot_us/pack.yaml`.

```mermaid
flowchart LR
    B[Baseline experiment on the active version] --> F[Failed development items]
    F --> T[Analyzer team writes two candidates]
    T --> O[Overfit guard on each rule]
    O --> K[One candidate kept on the development split]
    K --> D[Knowledge diff]
    D --> C[Candidate experiment]
    C --> G{Promotion gate}
    G -->|more holdout items passed, zero confirmed regressions, rules pass the guard, a person approves| P[Promoted]
    G -->|otherwise| X[Blocked]
```

## Run it

Finish the [setup pages](../../setup/README.md) first, including the
[pre-class checks](../../setup/pre-class.md). Then start the services, confirm the data, and open
a live session in a terminal at the repository root:

```bash
make up
make check-data
make preflight PURPOSE=development
```

Every run belongs to a live session, which `make preflight` opens; with none open, a demo fails
with "No live session is open". Preflight first asks five questions that show the model still
behaves as the course measured it, one agent run each. In class the instructor runs
`make preflight PURPOSE=class` instead.

Open the console at http://localhost:8501 on the Improve page. Run every core demo of this section
from the same terminal, one at a time, with:

```bash
bash section-4-hill-climbing-loop/demo/run.sh
```

Add `--optional` to run the over-broad rule after the core demos, or name one demo to run it alone.
Each `make demo` prints the request ids it queued; the experiments and the analyzer report show up
on the Improve page.

The order matters here. The baseline experiment is the comparison for every later gate verdict, so
it runs first and stays across a `make reset NAME=hill-climbing-loop`. The naive analyzer runs with
`make demo NAME=improve-naive-analyzer-blocked PLANTED=1`, which queues the analyzer and then the
candidate experiment with `BUG_NAIVE_ANALYZER` on for those two requests alone; the runner takes
them in that order. The analyzer team then runs on the fixed system, with no change to `.env`.
Approve the candidate in the knowledge diff when the gate reads ready for approval; an approval
given earlier waits for the gate. Wait until the Improve page says the version is the active
version, and set the unattended level at once: `make autonomy LEVEL=unattended BY="<your name>"`, or
Improve > Set the unattended level (every reset sets the report-only level, and at that level the
finale's trigger refuses and says why). Then wait for the clearance re-runs to finish: the status
line names the families cleared, or reads Not cleared for every family when none cleared (the finale
then posts at the assisted level), and the finale's trigger stops refusing. From the promotion on,
Events > Send webhook question sends the fiscal year 2025 revenue question, and the finale's strip
shows its gold check once the runner writes it. The over-broad rule runs only after a candidate has
been promoted.

The hill-climbing runner that claims these requests is a Compose service, `hill-climbing-runner`,
started by `make up`; `make ps` shows it.

<!-- generated:demo-table -->
| Demo | Tier | Run it | Target minutes |
|---|---|---|---|
| The baseline experiment | core | `make demo NAME=improve-baseline-experiment` | 3 |
| The naive analyzer, blocked | core | `make demo NAME=improve-naive-analyzer-blocked` | 4 |
| The over-broad rule, blocked | optional | `make demo NAME=improve-overbroad-rule-blocked` | 4 |
| The analyzer team and approval | core | `make demo NAME=improve-analyzer-team-approve` | 6 |
| The candidate experiment | core | `make demo NAME=improve-candidate-experiment` | 5 |
| Cleared for the unattended level | core | `make demo NAME=improve-cleared-unattended` | 3 |

Each demo also runs from the console (Improve > Run experiment on the active version; Improve > Run the naive analyzer (planted); Improve > Add the over-broad rule to the active version; Improve > Run analyzer; Improve > Run experiment on the candidate; Events > Send webhook question).
Recovery for every demo in Section 4: Hill-climbing loop: `make reset NAME=hill-climbing-loop`, then the same
trigger again. The target minutes are the class plan's, from `platform/demos/registry.yaml`, not
measured times.
<!-- /generated:demo-table -->

### Files and links

- [run.sh](run.sh): the launcher; its header states what it runs, the caps, and the target minutes
- [walkthrough.md](walkthrough.md): the code behind these demos, explained
- [Version 1 of the knowledge](../../platform/packs/datapilot_us/knowledge/v1.yaml) and
  [the over-broad rule's version](../../platform/packs/datapilot_us/knowledge/v2-overbroad.yaml)
- [The benchmark](../../platform/packs/datapilot_us/benchmark/): the development and holdout splits
- [The measurement scheme](../../platform/packs/datapilot_us/pack.yaml): `evaluation`
- [expected/](expected/): real output from a real run, for comparison after class, never in class
- [Evidence page](../../docs/evidence/section-4-hill-climbing-loop.md): the measured runs

## What to watch

| Step | Screen | What appears |
|---|---|---|
| The baseline experiment | Improve page | The holdout ledger filling in: start time, and trace or "Not traced" |
| The naive analyzer, blocked | Improve page | Rules quoting questions, all flagged by the overfit guard; the verdict blocked |
| The analyzer team and approval | Improve page | Both candidates' development results, the one kept, and its knowledge diff |
| The candidate experiment | Improve page, then LangSmith | Holdout flips marked against the baseline; the gate verdict |
| Cleared for the unattended level | Events page and status line | The correct answer, posted at the level its family has earned |

Each demo's entry below comes from the demo registry: how to start it, what guarantees its moment,
and what may differ from run to run.

<!-- generated:demo-runbook -->
### The baseline experiment

- **Tier**: core
- **Start it**: Improve > Run experiment on the active version in the console, or `make demo NAME=improve-baseline-experiment`
- **Guaranteed by**: the near-empty version 1 of the knowledge (the starting version); the five traps in the seeded data
- **What appears**: Started at the poll, the experiment runs the 40 benchmark items under version 1 of the knowledge (the starting version); the trap items fail and the holdout ledger fills in locally, each row stamped with its run's start time and linked to its LangSmith trace when the trace sample took one of its runs (about 1 run in 5), otherwise marked "Not traced". This run is the session's baseline.
- **Expected live outcome**: The number of holdout items version 1 passes, with the trap items failed.
- **What can vary**: which non-trap items pass; wall time
- **Recovery**: `make reset NAME=hill-climbing-loop`, then the same trigger again

### The naive analyzer, blocked

- **Tier**: core
- **Start it**: Improve > Run the naive analyzer (planted) in the console, or `make demo NAME=improve-naive-analyzer-blocked`
- **Guaranteed by**: the naive analyzer (`BUG_NAIVE_ANALYZER`)
- **What appears**: Two requests, queued together at the break with `make demo NAME=improve-naive-analyzer-blocked PLANTED=1`: the analyzer, then the candidate experiment; the runner takes them in that order, after the baseline. Its planted half is its only half, so the command switches the naive analyzer on for its own two requests with or without PLANTED=1. The console's Improve page queues the same two requests with the same flag from its Run the naive analyzer (planted) button, shown only while demo controls are allowed; its Run analyzer button runs the analyzer team, never the naive analyzer. The naive analyzer, with no model call, writes one rule per failed development question, quoting it word for word with the analyst's query that failed, and never reads a reference query. It skips the critic and applies no overfit guard: the guard flags every rule and the Improve page says so, yet the knowledge diff keeps them all. Then the candidate experiment runs, and the gate blocks the version because the overfit guard rejects its rules, whatever its holdout count.
- **Expected live outcome**: The overfit guard flags every rule, not applied by the analyzer; the gate verdict reads blocked, naming the rules the overfit guard rejects.
- **What can vary**: how many development questions failed; how many development questions pass; how many holdout items pass; the time from the trigger to the verdict (211 to 580 seconds in 6 measured runs; the longest on a machine shared with assignment checks)
- **Recovery**: `make reset NAME=hill-climbing-loop`, then the same trigger again

### The over-broad rule, blocked

- **Tier**: optional, cut first when the section runs late
- **Start it**: Improve > Add the over-broad rule to the active version in the console, or `make demo NAME=improve-overbroad-rule-blocked`
- **Guaranteed by**: the over-broad rule
- **What appears**: Run only after a candidate has been promoted. The active version plus one pre-authored rule, "exclude discounted orders from revenue", breaks revenue items that pass under the active version; the ledger marks the regressions and the gate blocks it.
- **Expected live outcome**: Regressions marked on the ledger and a blocked verdict.
- **What can vary**: which items regress
- **Recovery**: `make reset NAME=hill-climbing-loop`, then the same trigger again

### The analyzer team and approval

- **Tier**: core
- **Start it**: Improve > Run analyzer in the console, or `make demo NAME=improve-analyzer-team-approve`
- **What appears**: The failure analyst diagnoses the failed development questions, the rule writer proposes general rules, the critic keeps, narrows, or drops each one, a rule whose SQL guidance does not run over the schema is dropped, and the overfit guard rejects any rule that quotes a benchmark question or copies gold SQL and passes the rest. The team writes two candidates this way, each runs on the development split only, and the Improve page names the one kept by its results there; the knowledge diff shows it for human approval.
- **Expected live outcome**: A candidate version with general rules in the diff viewer, and the line naming both candidates and the one kept.
- **What can vary**: rule wording; number of rules; which candidate is kept; which rules, if any, the overfit guard rejects (live, it rejected a critic-kept rule that copied 20 or more tokens of a gold query); wall time: 326 to 377 seconds with two candidates in the five measured runs
- **Recovery**: `make reset NAME=hill-climbing-loop`, then the same trigger again

### The candidate experiment

- **Tier**: core
- **Start it**: Improve > Run experiment on the candidate in the console, or `make demo NAME=improve-candidate-experiment`
- **What appears**: The candidate version flips holdout trap items with zero regressions on either split. The live holdout ledger in the console, scored locally against this session's baseline, marks the flips; then the LangSmith trace list of datapilot-experiments, filtered by knowledge version, shows the candidate's traced runs, a sample of about 1 run in 5. The gate reads ready for human approval; once approved, the runner makes the version active and runs the clearance re-runs (50 seconds after the approval, measured once). In class it is queued at once after the analyzer (Improve > Run analyzer, then Improve > Run experiment on the candidate); trigger it again only if it never started, since a second press queues a second experiment.
- **Expected live outcome**: Holdout flips marked against this session's baseline, no regressions, gate verdict ready for human approval.
- **What can vary**: which items flip; how many flip: 0 to 12 of 13 holdout trap items in the measured runs, a majority in 6 of 10 measured runs, so check the candidate in rehearsal; wall time: 171.3 to 459 seconds; confirming re-runs of an apparent regression lengthen it
- **Recovery**: `make reset NAME=hill-climbing-loop`, then the same trigger again

### Cleared for the unattended level

- **Tier**: core
- **Start it**: Events > Send webhook question in the console, or `make demo NAME=improve-cleared-unattended`
- **What appears**: The correct answer, posted at the level its family has earned. Before it, the Improve page says the approved version is the active version, and the system is set to the unattended level (Improve > Set the unattended level, or `make autonomy LEVEL=unattended BY="<your name>"`); the trigger refuses, saying which step is missing, while a promotion is pending, the kill switch is engaged, or the level is lower. The fiscal year 2025 revenue question arrives as a webhook and is answered correctly under the new active version; it posts at the unattended level when the promotion cleared its metric family on the gate's own confirmed standard (every holdout item at 2 of 3 runs, an item that fell short passing 2 of 3 more runs), and at the assisted level when the family fell short. From the promotion on, Events > Send webhook question sends this question whether a family cleared or none did. Its strip on the Events page then shows the gold check the runner writes after the post: "Gold check passed", or "Gold check failed" with the agent's value and the gold value, the class-day safeguard's trigger.
- **Expected live outcome**: A correct answer, posted at the unattended level if its family cleared on the confirmed standard, and at the assisted level if it did not.
- **What can vary**: wording; latency; the level: assisted or unattended; the answer is correct either way
- **Recovery**: `make reset NAME=hill-climbing-loop`, then the same trigger again
<!-- /generated:demo-runbook -->

## What the result means

The gate decides on the holdout split, which the analyzer team never reads. A candidate is promoted
only with more holdout items passed than in the active version's baseline experiment of this live
session, which the gate records when it runs, zero regressions on either split, every new rule
passing the overfit guard, and a person's approval. Each apparent regression is re-run before it
counts (`evaluation.holdout_regression_reruns` and `evaluation.dev_regression_reruns` in
`pack.yaml`). An apparent regression on the development split is re-run under both versions, 2 more
runs each, and counts only when the candidate fails both and the active version passes both: the
ledger says "Apparent regression: confirming with 2 more runs of each version".

A blocked naive analyzer is the expected result: rules that quote development questions word for
word teach nothing about the holdout questions, and the gate blocks the version because the overfit
guard rejects every one of those rules, whatever the holdout count. A passed gate on the candidate
means general rules fixed traps on questions the analyzer team never saw. Report the counts as the
ledger shows them: which items flip can differ from run to run, and one session is one measurement.

A family cleared for the unattended level met the same standard as the gate: each of its holdout
items passed 2 of 3 runs, and an item that fell short passed 2 of 3 more runs before it counted. A
family that stays at the assisted level had an item that fell short twice; the correct answer is
still posted, at the assisted level, with approval where that level asks for it. Either way the
moment is the same: the correct answer, posted at the level its family has earned.

If the version promoted live in class gives a wrong finale answer, the finale runs again, live, on
the version promoted and verified in rehearsal: the class-day safeguard in the
[instructor guide](../../docs/instructor-guide.md#the-class-day-safeguard-for-the-finale).

## If it fails

| What you see | Why | What to do |
|---|---|---|
| `run.sh` says the services do not answer | The services are not running | `make up`, then `make ps` until every service is healthy |
| The gate refuses to compare the experiments | The baseline came from another live session | Run the baseline experiment again in this session |
| The naive analyzer's rules look general, or no rule quotes a question | It was queued with Improve > Run analyzer, which runs the analyzer team | `make demo NAME=improve-naive-analyzer-blocked PLANTED=1`, or Improve > Run the naive analyzer (planted) |
| The candidate verdict stays at ready for approval | Nobody approved the candidate | Approve it in the knowledge diff on the Improve page |
| The finale says "not sent", or Send webhook question is off | A pending promotion, an engaged kill switch, or a lower level | Do the step the message names, then the same trigger |
| The Improve page never moves | The `hill-climbing-runner` service stopped | `make logs NAME=hill-climbing-runner`, then `make up` |
| Anything else | A stale request or an engaged kill switch | `make reset NAME=hill-climbing-loop`, then the same trigger again |
