# Assignment 4: Hill-climbing loop. Specification

The full requirements for Assignment 4: Hill-climbing loop; the [README](README.md) gives the story
and the steps.

## Inputs

- The complete class system for Section 4: Hill-climbing loop, with its extension points in
  `platform/src/datapilot/loop4_hill_climbing/extension.py`, listed in
  [starter/README.md](starter/README.md).
- The benchmark in `platform/packs/datapilot_us/benchmark/`, and the planted over-broad rule in
  [planted-rule.yaml](planted-rule.yaml), which the check adds to the rule writer's proposals. Its
  evidence becomes your own repeat-customer dev item that failed in the baseline (else your first
  repeat-customer dev item), so your item ids need not match the one in the file.
- Read-only: the frozen contracts in `platform/src/datapilot/contracts/`, the measurement in the
  `evaluation` block of `platform/packs/datapilot_us/pack.yaml`, the gate, and the overfit guard.

## Files you must produce

| Path | What it holds |
|---|---|
| A new file in `platform/packs/datapilot_us/benchmark/` | Six items with `metric_family: repeat_customers` |
| `platform/packs/datapilot_us/pack.yaml` | The family in `autonomy.metric_families`, and the minimum number of holdout items |
| `platform/tests/unit/test_benchmark.py` | The benchmark's composition counts, updated for the new items |
| `platform/src/datapilot/loop4_hill_climbing/extension.py` | `CRITIC_GUIDANCE` and `screen` (hill-climbing-loop-2), and `enough_holdout_items` (hill-climbing-loop-3) |

## Requirements

Deterministic, checked against the real warehouses with no model call; each must pass every run:

1. The benchmark holds 6 items with `metric_family: repeat_customers`, each with a question, a
   gold and a naive Structured Query Language (SQL) query, and a split.
2. At least three of the 6 are in the holdout split.
3. Every gold query returns rows without nulls on both `warehouse` and `warehouse_alt`, and the
   same rows twice. With no repeat-customer item yet, this fails: there is nothing to judge.
4. Every item names the traps it touches, and its naive query gives a different answer from gold
   on both warehouses. With no repeat-customer item yet, this fails too.
5. `repeat_customers` is in `autonomy.metric_families`.
6. A family with fewer than three holdout items is not eligible for the unattended level, whatever
   its results: the check asks the eligibility rule about the real benchmark as if every holdout
   item passed, the most favourable case, and `aov`, with one holdout item, must stay below.
7. A family with at least three holdout items, all passing, is eligible: the check asks the rule
   about every count from 3 up to 10 (or the largest family, if larger), and, again as if every
   holdout item passed, every family of the pack with three or more holdout items (`revenue` and
   `orders` have four) and `repeat_customers` must be eligible. A rule that allows exactly three
   fails here.
8. The gate, the overfit guard, the measurement, and the `evaluation` block are unchanged.

Model-dependent, run live with the class measurement:

9. The analyzer team works on the failed dev items of the baseline experiment as in class: it
   writes `analyzer.candidates` rule sets (two, in pack.yaml), each from its own run, measures each
   on the dev split only, and keeps the one with fewer dev regressions, then more dev passes, then
   fewer rules. In every one of its runs, since any can be kept, the critic's review of the planted
   rule is a drop with a reason, and every accepted rule is one the rule writer proposed.
10. The gate promotes the kept candidate, after the human approval the check gives, with zero
    confirmed regressions on both splits, and the candidate experiment covers the six new items:
    each one is measured. None of them has to pass; the result line says how many holdout items of
    the family passed, for the record.
    The measurement is the class one: holdout items run 3 times and pass on 2; dev items run once;
    every apparent regression is confirmed by re-runs before it counts. An apparent dev regression
    is re-run 2 more times under each version and counts only when the candidate fails both of its
    re-runs and the active version passes both of its own, so an item that is unstable under both
    versions is not a regression; an apparent holdout regression is re-run 3 more times under the
    candidate and counts when 2 of them fail. Afterwards `aov` is not
    eligible for the unattended level. Families are cleared as in class: the minimum number of
    holdout items first, so `aov` is never re-run, then every holdout item of the family at 2 of 3
    runs, an item that fell short counting only if it passes 2 of 3 more runs.

**How often a correct solution passes.** Requirement 10 depends on the rule set the model writes
in that check. In the build's verification and the checks of 23 October, with one candidate per
check, it passed in 6 of 10 checks of correct solutions. Three were blocked by one confirmed dev
regression: a rule the model wrote made one dev item fail under the candidate. The third of them,
measured with the current re-runs of both versions, passed that item in both re-runs under v1 and
failed it in both under the candidate, so it was a real regression of that rule set, not noise in
v1. The fourth candidate was no better than v1 on holdout. The check now writes two candidates and
keeps the one with fewer dev regressions, then more dev passes, as the class does, which targets
the first cause. Measured on 23 October 2026 with two candidates, the reference passed 2 of 2
checks (13.58 and 23.95 cents, 15 and 22 minutes); two checks are a small sample, so a correct
solution may still read FAIL on requirement 10 now and then: run the check again, and the FAIL line
says when the cause is the model's rule set rather than your files. A starter, and a solution that
leaves out a family item or lets `aov` reach the unattended level, still fail it every time.

None of these changes exists in a class code path: the course build's boundary test keeps the
family out of the pack and the extension points inert on the class branch, so the unchanged
starter fails this check. Once your work is in place, those tests fail in your copy by design; the
README lists them under "Tests that pin the starter". Every other test of `make test` still passes.

## Live check

`make check-assignment NAME=hill-climbing-loop` brings up the real stack, checks requirements 1 to
8, prints its estimates (the analyzer team, and the benchmark on its own line), checks your OpenAI
key, and then runs requirements 9 and 10 in this process, against the real Postgres and the real
model. The baseline experiment of the active version is the open live session's: the first check in
a session runs it, and every later check in that session shares it, because the class gate compares
experiments of one live session, unless an item changed since that baseline measured it (its
question, gold SQL, split, or tolerance). Then the check runs a new baseline, and it prints the
reason and the first-check estimate before its first model call. Each live step prints its LangSmith trace link and its live stamp;
at the end the check prints the actual tokens and cost, and puts back the knowledge version that was
active. If the check reaches its spend cap of 1.00 dollar (`assignments.check_cap_usd` in pack.yaml), it stops cleanly: it starts no new run, every requirement it did not reach reads NOT RUN, and it exits 2. A missing or rejected key stops the check with "Live checks need your OpenAI key from the
operations team"; it never falls back to anything offline. When requirement 1 fails, the live
requirements do not run. The command exits 0 when every line reads PASS, 1 on any FAIL, and 2 when
it stopped.

Agent runs: 82 for the candidate experiment, 82 more for the baseline when the live session has
none yet, the re-runs of apparent regressions (4 for a dev item, 2 under each version; 3 for a
holdout item, under the candidate), 3 for each holdout item that falls short when its family is
judged for the unattended level, 28 for each of the two candidates on the dev split, and 3
analyzer team calls for each candidate, 6 in all.

## Evidence to hand in

Nothing is submitted, and there is no hidden grader. Bring these to the Thursday review:

- the output of your live check, with the gate's sentence and the critic's decision;
- one design choice you made, such as how the critic recognises an over-broad rule, and why.

## Limits

- Every model call records its spend in the build-wide ledger under the activity "assignment";
  `make spend` shows the total.
- Each run stays within `budgets.tokens_per_run` in `platform/packs/datapilot_us/pack.yaml`.
- Holdout items run `evaluation.holdout_repeats` times and pass on
  `evaluation.holdout_pass_threshold` runs, at `evaluation.concurrency`, as in class.
