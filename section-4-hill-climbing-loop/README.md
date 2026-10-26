# Module: Loop Engineering - Section 4: Hill-climbing loop

How DataPilot gets better without fooling itself: experiments find failures, an analyzer team
proposes rules, and a gate decides on questions the team never saw.

## The problem

**Illustrative scenario.** An analyst at Harbor & Pine Outfitters pastes a fix for every failed
benchmark question into the prompt. The score on those questions jumps, and the change ships.
Next month's questions are still wrong, and one question that used to be right now breaks.

> **Terms on this page**
>
> - **Hill-climbing loop**: Experiments find failures, an analyzer team proposes rules, and a gate decides.
> - **Development split**: The benchmark questions the analyzer team may learn from.
> - **Holdout split**: The benchmark questions the analyzer team never sees; the gate decides on them.
> - **Promotion gate**: The check that a new knowledge version must pass before it becomes active.
> - **Regression**: An item that passed under the active version and fails under the candidate, confirmed by re-runs.
>
> All terms: [glossary](../docs/glossary.md).

## Why it happens

- Rules written from failures do not reliably transfer.
  [MAGIC](https://arxiv.org/abs/2406.12692) turns training failures into a self-correction
  guideline; a [table agents survey](https://arxiv.org/html/2507.10281) re-ran it and found small
  gains, and drops with one large language model (LLM).
- Knowledge given to the model is evidence, and evidence can be missing or wrong
  ([SEED](https://arxiv.org/abs/2506.07423)).
- Comparing Structured Query Language (SQL) text, or results on one database, marks answers wrong or right by accident
  ([Semantic Evaluation for Text-to-SQL with Distilled Test Suites](https://arxiv.org/abs/2010.02840)).

## How this section fixes it

An experiment runs the benchmark by execution on two databases. The analyzer team reads the
failed development items: the failure analyst diagnoses, the rule writer proposes, and the critic
keeps, narrows, or drops each rule. The team writes two candidates; the runner keeps the one with
fewer regressions on the development split, then more development items passed, then fewer rules,
and the holdout split never takes part.
A deterministic overfit guard and the promotion gate follow. The gate
decides on the holdout split, with zero regressions, every new rule passing the overfit guard, and
human approval.

![The hill-climbing cycle: the benchmark, 25 development and 15 holdout questions, feeds an experiment that measures execution match on two databases; the analyzer team of three agents reads only the failed development questions; the overfit guard rejects a rule that copies a question or a gold query; of two candidates the better one is kept; the promotion gate needs all four conditions, more holdout passes than the active version, zero confirmed regressions on both splits, human approval, and every new rule passing the overfit guard; the promoted version becomes the active knowledge version and the next baseline](diagrams/hill-climbing-loop.svg)

*Notice that the agents only propose: code decides whether a rule overfits and whether a version is better, and a person approves the promotion.*

A promoted version clears a metric family for the unattended level on the gate's own confirmed
standard: every holdout item of the family passes 2 of 3 runs, and an item that falls short counts
only if it passes 2 of 3 more runs. The full idea is in [concepts.md](concepts.md) (in class,
minutes 0 to 20).

## How to work through this section

### How it works in the code

- [`ExperimentRunner`](../platform/src/datapilot/loop4_hill_climbing/experiment.py) runs the
  benchmark, and [`ExecutionEvaluator`](../platform/src/datapilot/loop4_hill_climbing/evaluator.py)
  scores each answer by its result on both warehouses.
- [`AnalyzerTeam`](../platform/src/datapilot/loop4_hill_climbing/analyzer.py) runs the failure
  analyst, the rule writer, and the critic; `choose` in
  [`candidates.py`](../platform/src/datapilot/loop4_hill_climbing/candidates.py) keeps one candidate.
- [`OverfitGuard`](../platform/src/datapilot/loop4_hill_climbing/overfit_guard.py) rejects a rule
  that copies a benchmark question or gold query.
- [`decide`](../platform/src/datapilot/loop4_hill_climbing/gate.py) applies the gate's four
  conditions, and `find_regressions` confirms each apparent regression by re-runs.
- [`gate`](../platform/src/datapilot/loop4_hill_climbing/runner.py) records the baseline it
  compared with, and a later approval promotes against that same experiment.

The [walkthrough](demo/walkthrough.md) explains these lines (minutes 35 to 40).

### The demo

Five core demos, live, in minutes 20 to 35: the baseline experiment, the naive analyzer blocked,
the analyzer team and approval, the candidate experiment, and cleared for the unattended level
(`improve-baseline-experiment` to `improve-cleared-unattended`). The baseline starts at the poll
before the second break, so it finishes during it. Experiment runs are traced as a sample, about
1 in 5, so a holdout ledger row may read "Not traced". Run them with the
[demo page](demo/README.md); the measured runs are on the
[evidence page](../docs/evidence/section-4-hill-climbing-loop.md).

### The assignment

[Assignment 4: Hill-climbing loop](assignment/README.md) adds a repeat-customer metric family, a
critic that drops an over-broad rule, and a rule that a family needs at least three holdout items
before the unattended level. It is done when `make check-assignment NAME=hill-climbing-loop` reads
PASS on every line. Effort: about 2 to 2.5 hours; it runs the benchmark, so it is the costly
check ([costs page](../docs/costs.md#assignments)).

### Apply it in a real system

- Keep a holdout split that the improvement process never reads, and decide only on it.
- Confirm an apparent regression with re-runs before it counts, and accept zero.
- Let code decide and a person approve: agents propose rules; a guard and a gate judge them.
  Grant autonomy per metric family, from measured results.

### Further reading

The [reading list](post-class-reading/README.md) has three: rules learned from failures, evidence
written by a machine, and the post that names the four loops.

## Where next

- First time here? Install everything with [setup/](../setup/README.md), then run the
  [demos](demo/README.md).
- Already set up? Start with [concepts.md](concepts.md).
- Previous section: [Section 3: Event loop](../section-3-event-loop/README.md).
- Put it together: the [final project](../final-project/README.md), then
  [use it in your repository](../use-in-your-repo/README.md).

## Sources

- Source 1: MAGIC: Generating Self-Correction Guideline for In-Context Text-to-SQL, <https://arxiv.org/abs/2406.12692>, Arian Askari et al., 2024-06-18
- Source 2: Toward Real-World Table Agents: Capabilities, Workflows, and Design Principles for LLM-based Table Intelligence, <https://arxiv.org/html/2507.10281>, Jiaming Tian et al., 2025-07-14
- Source 3: SEED: Enhancing Text-to-SQL Performance and Practical Usability Through Automatic Evidence Generation, <https://arxiv.org/abs/2506.07423>, Janghyeon Yun et al., 2025-06-09
- Source 4: Semantic Evaluation for Text-to-SQL with Distilled Test Suites, <https://arxiv.org/abs/2010.02840>, Ruiqi Zhong et al., 2020-10-06
