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
> - **Dev split**: The benchmark questions the analyzer team may learn from.
> - **Holdout split**: The benchmark questions the analyzer team never sees; the gate decides on them.
> - **Promotion gate**: The check that a new knowledge version must pass before it becomes active.
> - **Regression**: An item that passed under the active version and fails under the candidate.
>
> All terms: [glossary](../docs/glossary.md).

## Why it happens

- Rules written from failures do not reliably transfer.
  [MAGIC](https://arxiv.org/html/2406.12692) turns training failures into a self-correction
  guideline; a [table agents survey](https://arxiv.org/html/2507.10281) re-ran it and found small
  gains, and drops with one large language model (LLM).
- Knowledge given to the model is evidence, and evidence can be missing or wrong
  ([SEED](https://arxiv.org/html/2506.07423)).
- Comparing Structured Query Language (SQL) text, or results on one database, marks answers wrong or right by accident
  ([Semantic Evaluation for Text-to-SQL with Distilled Test Suites](https://arxiv.org/abs/2010.02840)).

## How this section fixes it

An experiment runs the benchmark by execution on two databases. The analyzer team reads the
failed dev items: the failure analyst diagnoses, the rule writer proposes, and the critic keeps,
narrows, or drops each rule. A deterministic overfit guard and the promotion gate follow. The gate
decides on the holdout split, with zero regressions, every new rule passing the overfit guard, and
human approval.

![The benchmark, 25 dev and 15 holdout items, and two databases feed the experiment runner; failed dev items go to the analyzer team of three agents, then the overfit guard, then a candidate knowledge version; the promotion gate, with its confirming runs and a person's approval, makes the active version; a band below explains autonomy per metric family](diagrams/hill-climbing-loop.svg)

*Notice that the agents only propose: code decides whether a rule overfits and whether a version is better, and a person approves the promotion.*

A promoted version clears a metric family for the unattended level on the gate's own confirmed
standard: every holdout item of the family passes 2 of 3 runs, and an item that falls short counts
only if it passes 2 of 3 more runs. The pieces exist in other
systems; their combination is one we have not seen documented. What the course measured is on the
[evidence page](../docs/evidence/section-4-hill-climbing-loop.md). <!-- provisional: results come from the calibration and class runs -->

## How to work through this section

| Part | What it gives you | In class |
|---|---|---|
| [concepts.md](concepts.md) | Execution match, the analyzer team, the gate, earned autonomy | Minutes 0-20 |
| [demo/](demo/README.md) | Five live demos, from the baseline experiment to the unattended level | Minutes 20-35 |
| [demo/walkthrough.md](demo/walkthrough.md) | The evaluator, the critic, the overfit guard, the gate | Minutes 35-40 |
| [assignment/](assignment/README.md) | Add a metric family, improve the critic, add the minimum-holdout rule | After class |
| [post-class-reading/](post-class-reading/README.md) | Readings on evidence, evaluation, and self-correction | After class |
| [session-notes.md](session-notes.md) | What class showed, questions, what to try next | After class |

In class, every demo result on the console shows a live stamp: its run's start time in the
viewer's local time and its LangSmith trace link. The `demo/expected/` folder is for you
after class; it is never opened in class.

The baseline experiment starts at the poll before the second break, so it finishes during it.

## Where next

- First time here? Install everything with [setup/](../setup/README.md), then run the
  [demos](demo/README.md).
- Already set up? Start with [concepts.md](concepts.md).
- Previous section: [Section 3: Event loop](../section-3-event-loop/README.md).
- Put it together: the [final project](../final-project/README.md), then
  [use it in your repository](../use-in-your-repo/README.md).

## Sources

- Source 1: MAGIC: Generating Self-Correction Guideline for In-Context Text-to-SQL, <https://arxiv.org/html/2406.12692>, Askari et al., 2024
- Source 2: Toward Real-World Table Agents: Capabilities, Workflows, and Design Principles for LLM-based Table Intelligence, <https://arxiv.org/html/2507.10281>, Jiaming Tian et al., 2025-07-14
- Source 3: SEED: Enhancing Text-to-SQL Performance and Practical Usability Through Automatic Evidence Generation, <https://arxiv.org/html/2506.07423>, Janghyeon Yun et al., 2025-06-09
- Source 4: Semantic Evaluation for Text-to-SQL with Distilled Test Suites, <https://arxiv.org/abs/2010.02840>, Ruiqi Zhong et al., 2020-10-06
