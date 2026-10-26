# Section 4: Hill-climbing loop. Concepts

Reading time: about 10 minutes.

## The problem

**Illustrative scenario.** Take the pasted fixes from the [section page](README.md#the-problem).
The question that breaks is about orders, and nobody can say which pasted line caused it.

> **Terms on this page**
>
> - **Hill-climbing loop**: Experiments find failures, an analyzer team proposes rules, and a gate decides.
> - **Knowledge version**: A numbered set of business rules given to the agent in its prompt.
> - **Development split**: The benchmark questions the analyzer team may learn from.
> - **Holdout split**: The benchmark questions the analyzer team never sees; the gate decides on them.
> - **Promotion gate**: The check that a new knowledge version must pass before it becomes active.
> - **Regression**: An item that passed under the active version and fails under the candidate, confirmed by re-runs.
>
> All terms: [glossary](../docs/glossary.md).

## The idea in one sentence

Let an analyzer team learn rules from failures on one split, and let a deterministic gate promote
them only on questions the team never saw, with zero regressions and human approval.

## How it works

If the development score goes up, should you promote the new rules? No: rules written from the
development items fit them. Only the holdout questions decide.

[MAGIC](https://arxiv.org/abs/2406.12692) turns training-set failures into a self-correction
guideline and reports gains on two benchmarks. A [table agents survey](https://arxiv.org/html/2507.10281)
re-ran it and found small gains, and drops with one large language model (LLM). Failure-derived rules do not reliably
transfer, which is the argument for a holdout gate.

### Measure by execution, on two databases

An experiment runs each benchmark question and compares results, never Structured Query Language
(SQL) text. Results are
normalized and checked on both `warehouse` and `warehouse_alt`. One database can agree with a wrong
query by accident; [Semantic Evaluation for Text-to-SQL with Distilled Test Suites](https://arxiv.org/abs/2010.02840)
measures that false-positive effect and fixes it with more databases. The SQL text evaluator
(`BUG_SQL_TEXT_EVAL`) compares query text and marks correct answers wrong.

The benchmark has 40 questions, 25 in the development split (`benchmark/dev.yaml`) and 15 in the
holdout split (`benchmark/holdout.yaml`), with no ambiguous category.

Key idea: compare results, not query text.

### The analyzer team

Three agents split the work, each with one structured output in
`platform/src/datapilot/contracts/agents.py`:

| Agent | Reads | Returns |
|---|---|---|
| the failure analyst | One failed development item | `Diagnosis`: what went wrong and the likely cause, no rules |
| the rule writer | The diagnoses | `ProposedRule`: a general rule and when it applies |
| the critic | Each proposed rule | `CriticReview`: keep, narrow, or drop; never add |

The analyzer model is set separately with `OPENAI_ANALYZER_MODEL`. A rule's SQL guidance must run
over the schema, or the critic gets it back. The team writes two candidates and keeps the better one
on the development split. The naive analyzer (`BUG_NAIVE_ANALYZER`) quotes each failed question in a
rule and skips the critic and the guard.

Key idea: split diagnosis, proposal, and criticism so no agent grades its own work.

### The overfit guard and the promotion gate

The overfit guard is deterministic code, not an agent. It rejects any rule that shares 6
consecutive words with a benchmark question or 20 consecutive SQL tokens with a gold query
(`evaluation.overfit_question_words` and `evaluation.overfit_sql_tokens`). The candidate then
runs on both splits, measured like the active version (`platform/packs/datapilot_us/pack.yaml`):

- Each holdout item runs 3 times per version and passes on 2 of 3 (`evaluation.holdout_repeats`,
  `evaluation.holdout_pass_threshold`).
- Each development item runs once. A development item that passed under the active version and fails
  under the candidate is re-run twice more under each version (`evaluation.dev_regression_reruns`).
  It is a regression only if the candidate fails both of its re-runs and the active version passes
  both of its own (`evaluation.dev_regression_threshold`), so an item unstable under both versions
  never counts.
- An apparent holdout regression is confirmed under the candidate only: 3 more runs, and 2 of 3
  must fail again. The active version is not re-run, because its holdout result already passed 2
  of 3 runs. The ledger shows "Apparent regression: confirming with 3 more runs".
- Calibration keeps only stable holdout items: each runs 5 times under the starting and the
  promoted version and stays only at 4 or 5 of 5, or 0 or 1 of 5, under each. Calibration
  replaced 3 unstable items, found others unstable on the next run, and restored the original 15.
- Runs go 8 at a time (`evaluation.concurrency`).

The gate passes the candidate when it passes more holdout items than the active version, there are
zero regressions on both splits, its new rules pass the overfit guard, and a person approves the
knowledge diff. The over-broad version `v2-overbroad`, "exclude discounted orders from revenue",
breaks items, and the gate blocks it.

Key idea: the gate decides on questions the analyzer never saw.

![The benchmark, 25 development and 15 holdout items, and two databases feed the experiment runner; failed development items go to the analyzer team of three agents, then the overfit guard, then a candidate knowledge version; the promotion gate, with its confirming runs and a person's approval, makes the active version; a band below explains autonomy per metric family](diagrams/hill-climbing-loop.svg)

*Notice that the agents only propose: code decides whether a rule overfits and whether a version is better, and a person approves the promotion.*

### Earned autonomy per metric family

A promoted version clears a metric family, from `autonomy.metric_families` in `pack.yaml`, for
the unattended level on the gate's own confirmed standard, not on one lucky experiment:

- Every holdout item of the family must pass 2 of 3 runs in the candidate experiment
  (`evaluation.holdout_repeats`, `evaluation.holdout_pass_threshold`).
- An item that falls short gets the confirming re-run, 3 more runs
  (`evaluation.holdout_regression_reruns`), and counts as passing if it passes 2 of 3 of them.
- A family stays at the assisted level when one of its items falls short twice.

The fiscal year 2025 revenue question then arrives as a webhook, and the correct answer posts at the
level its family has earned. The revenue metric family has 4 holdout questions in
`benchmark/holdout.yaml`. Calibration showed why one experiment is not enough: all 4 revenue items
passed together in only one of four measurements. The rule that a family needs at least three
holdout questions before the unattended level is not in class code. Assignment 4: Hill-climbing loop
builds it, and it applies before the confirmed standard: a family with too few holdout questions is
never re-run.

Key idea: autonomy is granted per metric family, from holdout evidence.

That leaves an open question for you. "We just granted the unattended level from 4 holdout
questions for revenue and 1 for average order value. Is that enough evidence?"

Experiments are scored locally, and the console's holdout ledger is the source of truth.
Experiment runs are traced as a sample, about 1 in 5 (`tracing.experiment_sample_rate`), in
`datapilot-experiments`, tagged with knowledge version, split, item, and repetition. A ledger row
with no traced run reads "Not traced". Every other run is traced in full, with a live stamp. The baseline is the one started in this session, at the poll.

### Before and after

Before: someone pastes fixes into the prompt, the score on the fixed questions rises, and a
question that used to pass breaks unnoticed. After: the critic drops a rule that quotes a question,
the gate blocks a version with one regression, and a version that flips holdout items with zero
regressions waits for human approval.

The loop combines five pieces: a holdout split, zero regressions on both splits, human approval
of a versioned knowledge artefact, a deterministic overfit guard, and autonomy per metric family.

## How DataPilot does it

The evaluator scores one benchmark item. These lines run the agent's SQL and the gold SQL on both
warehouses and pass the item only when the results match on each:

```python
# platform/src/datapilot/loop4_hill_climbing/evaluator.py (lines 88-119)
    def evaluate(self, item: BenchmarkItem, answer: AnswerEnvelope) -> ItemResult:
        if item.expected_status is AnswerStatus.NEEDS_CLARIFICATION:
            passed = answer.status is AnswerStatus.NEEDS_CLARIFICATION
            reason = "asked for clarification" if passed else f"status {answer.status.value}"
            return ItemResult(item_id=item.id, passed=passed, reason=reason)
        if answer.status is not AnswerStatus.ANSWERED or not answer.final_sql:
            reason = f"status {answer.status.value}, no SQL to execute"
            return ItemResult(item_id=item.id, passed=False, reason=reason)
        labels = labels_for(answer.final_sql, item.traps)
        if not item.gold_sql:
            raise ValueError(f"{item.id}: an answered item needs gold_sql")
        if planted("BUG_SQL_TEXT_EVAL"):
            # planted: compares SQL text, so a correct query written differently fails
            same = _sql_text(answer.final_sql) == _sql_text(item.gold_sql)
            reason = "SQL text matches gold" if same else "SQL text differs from gold"
            return ItemResult(
                item_id=item.id, passed=same, reason=reason, trap_labels=[] if same else labels
            )
        for warehouse in WAREHOUSES:
            passed, reason = self._match_on(item, answer.final_sql, warehouse)
            if not passed:
                return ItemResult(
                    item_id=item.id,
                    passed=False,
                    reason=f"{warehouse}: {reason}",
                    trap_labels=labels,
                )
        return ItemResult(
            item_id=item.id,
            passed=True,
            reason="matches gold on both warehouses",
        )
```

The gold SQL runs live every time; the trap labels name the traps a failed answer's SQL hit. The
other parts live beside it in `platform/src/datapilot/loop4_hill_climbing/`: `analyzer.py` runs the
failure analyst, the rule writer, and the critic in order; `sql_guidance.py` checks SQL
guidance; `overfit_guard.py` checks every proposed rule; `candidates.py` keeps one candidate;
`gate.py` and `measurement.py` apply the repeat and threshold settings from `pack.yaml`.

## What we measured

| Check | Result |
|---|---|
| Holdout items passed, version 1 of the knowledge (the starting version) | 2 of 15, in every baseline experiment |
| Holdout items passed, promoted candidate | 12 to 14 of 15 in 7 promotions with two candidates; 3 to 12 with one |
| Regressions on both splits | 0 for every promoted version |
| Naive analyzer verdict | Blocked in 6 of 6 runs; 2 of 15 holdout items passed in five, 0 of 15 in one |

The runs are on the [evidence page for this section](../docs/evidence/section-4-hill-climbing-loop.md).

## When it helps, and when it does not

It helps when:

- You have a benchmark with gold answers and can hold part of it back.
- Failures share causes that a general rule can fix, such as the fiscal year or cancelled orders.
- You want to grant autonomy for one metric family at a time, from evidence.

It does not help when:

- The benchmark is too small to hold back enough questions per metric family.
- The failure is in the tools or the graders, not in missing knowledge; fix those in
  Section 1: Agent loop or Section 2: Verification loop.
- The data changes faster than you can re-run the experiments.

## Key takeaways

- Measure by execution on two databases, and let the gate decide only on the holdout split.
- Split the analyzer into a failure analyst, a rule writer, and a critic, then a deterministic overfit guard.
- Grant the unattended level per metric family, only after a gated promotion and human approval.

## Check your understanding

1. Why can a higher score on the development split still mean a worse version?

<details><summary>Answer</summary>

The rules were written from the development items, so they fit them. A rule can also break questions that
passed before. Only the holdout split and the regression check show whether it generalises.

</details>

2. Why does each holdout item run 3 times, and the same way for both versions?

<details><summary>Answer</summary>

Model runs vary. Passing on 2 of 3 keeps noise from looking like a flip or a regression, and the
same scheme for both versions keeps the comparison fair.

</details>

3. What does the critic do that the rule writer cannot?

<details><summary>Answer</summary>

It judges each rule it did not write, and may keep, narrow, or drop it, never add one. That keeps
any agent from grading its own proposal.

</details>

4. Why is the overfit guard deterministic code and not another agent?

<details><summary>Answer</summary>

Whether a rule quotes a benchmark question is a text check with one right answer. Code gives the
same answer every time and costs nothing.

</details>

## Further reading

- [Reading list for this section](post-class-reading/README.md)

## Sources

- Source 1: MAGIC: Generating Self-Correction Guideline for In-Context Text-to-SQL, <https://arxiv.org/abs/2406.12692>, Arian Askari et al., 2024-06-18
- Source 2: Toward Real-World Table Agents: Capabilities, Workflows, and Design Principles for LLM-based Table Intelligence, <https://arxiv.org/html/2507.10281>, Jiaming Tian et al., 2025-07-14
- Source 3: Semantic Evaluation for Text-to-SQL with Distilled Test Suites, <https://arxiv.org/abs/2010.02840>, Ruiqi Zhong et al., 2020-10-06
