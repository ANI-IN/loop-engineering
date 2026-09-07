# Re-specifying the five charts against what was actually measured

**Written:** 2026-09-07, after the six-arm run on the 60 held-out items.
**Status:** chart 1 built. Charts 2–5 specified here and not yet built.

Four of the five charts were specified for a session that no longer exists. The thesis
chart, cost-per-correct and paired deltas were all built around **C vs D** and
**A → C**, and both of those comparisons are now dead:

- **A → C is a null.** Condition A terminated `success` 60/60, so retry had nothing to
  retry and B fired zero retries; C's verifiers rejected 2 of 60. Five runs of the
  cheap arm at L3 scored 46, 51, 52, 52, 52 — the six-item "uplift" is the arm's own
  spread. McNemar returns p=0.031 over a mechanism that never fired.
- **C vs D has no gap to close.** The frontier model scored 60/60 twice.

Building them as specified and repurposing afterwards would keep their shape and lose
their argument. Each is re-specified below against the data that exists.

---

## 1. OUTCOME SHIFT — built

The L0 arms, five bands. See the commit; nothing further is owed.

## 2. THESIS → the trap matrix

**Was:** four conditions side by side on accuracy, C and D adjacent so the room can see
whether cheap-plus-loops reached frontier-bare.

**Now:** the 2×2 that is the whole argument.

|  | L0 · rules withheld | L3 · rules given |
|---|---|---|
| **gpt-5.6-luna** | 7/60 | ~50/60 |
| **gpt-6-astra** | 9/60 | 60/60 |

The reading is the **diagonal**: cheap-with-spec beats frontier-without-spec by roughly
forty items, at a fraction of the cost. The columns are the trap; the rows are the model
upgrade; the diagonal is the session.

Two things this chart must not do:

- **It must not plot a single cheap-L3 run as if it were the value.** That cell moved
  46 → 52 across five runs. The bar carries a Wilson interval for sampling error *and*
  a separately-styled marker for the measured run-to-run spread, because they are
  different uncertainties and one of them is invisible to the other. A single interval
  covering both would imply we know which is which.
- **It must not put a significance star on the row comparison.** Rows are cross-model
  and `diff.py` already refuses a p-value across that; the columns are where the
  paired test lives, and that is chart 4.

## 3. COST PER CORRECT ANSWER — survives, with a different comparison

**Was:** all four conditions, C dramatically below D.

**Now:** the same chart, and the number it exists for is unchanged — it just comes from
a different pair.

| arm | correct | total cost | per correct |
|---|---|---|---|
| cheap · L3 | 52/60 | $0.0176 | **$0.00034** |
| frontier · L3 | 60/60 | $0.7901 | **$0.01317** |
| cheap · L0 | 7/60 | $0.0134 | $0.00191 |
| frontier · L0 | 9/60 | $0.9657 | **$0.10730** |

**39× the cost per correct answer for 15% more accuracy** — or 45× the total bill.
That is a business number and it survives the collapse of everything around it.

The L0 bars are what make it an argument rather than a price list: the frontier model
*without* the spec costs **$0.107 per correct answer**, three hundred times the cheap
model *with* it. Spending on the model instead of on the spec is the expensive way to
be wrong.

Failed calls are included, via `usage.py`. Every figure keeps `est.`.

## 4. PAIRED DELTAS — only the comparison that is still paired and still real

**Was:** A→B, A→C, C vs D, each with an interval, a McNemar p-value and a discordant
count.

**Now:** L0 → L3, within each model. Two rows, and both are enormous:

| comparison | discordant | against | McNemar |
|---|---|---|---|
| agent: L0 → L3 | 39 | 0 | p < 0.0001 |
| reference: L0 → L3 | 51 | 0 | p < 0.0001 |

**A→B, A→C and B→C are removed rather than drawn as nulls.** Drawing a null with a
significance test attached is worse than not drawing it: the p-value is real arithmetic
and the mechanism never fired, so the chart would be honest about its statistics and
wrong about its subject. If they appear at all they appear as a caption sentence saying
the loops had nothing to do at L3, which is the finding.

Cross-model rows stay refused in code.

## 5. TERMINATION REASONS — keep, but fix a label first

**Was:** distribution across conditions, by name.

**Now:** the same, and the measurement exposed a defect that has to be fixed before the
chart is worth drawing.

Measured terminations:

    trap-agent-L0        {success: 60}
    A-baseline           {success: 60}
    C-verified           {success: 59, no_progress: 1}
    trap-reference-L0    {success: 41, max_attempts: 19}
    D-reference          {success: 60}

At L3 every arm is `success` and the chart says nothing. The one interesting column is
`max_attempts: 19` on the reference L0 arm — and **it is exactly the 19 abstentions.**

That is a mislabel. Those runs did not exhaust their attempts failing; they declined, by
naming the input they had not been given, on a single-shot arm where "the one attempt
did not succeed" collapses to `max_attempts` by default. The termination vocabulary
cannot currently distinguish *ran out of road* from *refused to guess*, which is the
distinction the session is about.

**Prerequisite:** a termination reason for a run that declined. Done —
`TerminationReason.DECLINED`, verified live: 15 declined terminations against 15
abstained outcomes, agreeing exactly.

**And with that done, the chart is CUT.** Its full contents across 360 runs:

    success 340 · max_attempts 19 · no_progress 1

Five of six arms are a single solid `success` block. The one real column is the
reference arm's declined count at L0 — which the outcome-shift chart already renders,
better, as its blue band. Drawing the same fact twice weakens both.

It becomes three lines in the L0 discussion: *15 declined, 41 success, 2 max_attempts
on the reference arm at L0 — the only place in the session where a termination reason
other than `success` appears in quantity.*

The honest reading is that the termination distribution is evidence a policy branch
fired, and at L3 the answer is that none of them did, because nothing went wrong. That
is the loops-had-nothing-to-do finding again, and the DELTA caption already carries
it.

---

## What this cost, and what it bought

Reordering LangSmith ahead of the charts is what surfaced all of it. Building the five
charts in the specified order would have produced a headline visual around a null and a
paired-delta chart carrying a significance test over a mechanism that never fired —
both of which would have survived to the dress rehearsal, and possibly past it.

It is the eighth entry in [the instruments list](every-instrument-has-been-wrong.md),
and the only one found by changing the order of the work rather than by running
something.
