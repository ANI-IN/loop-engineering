# docs/

Design notes and pre-committed decisions. Not a runbook — each stage's runbook lives
beside its code in [`demos/`](../demos/), because a runbook kept apart from the thing it
describes drifts, and a runbook that lies at minute forty of a live session is the one
thing this cannot afford.

What lives here is the opposite: decisions that have to be written down **before** the
data lands, and findings about the build itself that no module is the right home for.

## Reading order

**If you have twenty minutes and want the argument**, read these two, in this order:

1. **[Our own instrument punished a model for being right](instrument-ranked-honesty-backwards.md)**
   — one model invented a conversion rate it had not been given; the other named the
   input it was missing. Our classifier scored the honest one as a crash and the
   confabulation as a near miss. On the single axis this project exists to teach, our
   instrument ranked the two behaviours backwards, silently, with every test green.
2. **[Every instrument in this build has been wrong at least once](every-instrument-has-been-wrong.md)**
   — the same failure nineteen times, dated, none of them found by reading code. Start
   at "What they have in common" if you want the conclusion before the evidence.

Everything else is reference for a specific decision.

## The notes

**Session material** — the argument a room is shown, or the reasoning behind what it is
shown:

| note | what it records |
|---|---|
| [Our own instrument punished a model for being right](instrument-ranked-honesty-backwards.md) | the classifier ranked an honest refusal below a confabulation. The full write-up behind §2 of the instruments note |
| [Every instrument in this build has been wrong at least once](every-instrument-has-been-wrong.md) | 17 instruments, one plan and one author, all green at the time, none found by reading code |
| [Re-specifying the five charts](charts-respec.md) | what the measurement did to the chart plan — including the two charts specified for a session that stopped existing |

**Build history** — why the code is shaped the way it is, for whoever changes it next:

| note | what it records |
|---|---|
| [Five guards on one capability is a tell](guards-are-a-tell.md) | why the stored-measurement render path was deleted rather than defended, and what it cost |
| [The failure taxonomy, regenerated from real failures](the-failure-taxonomy.md) | which of the seven visible-failure kinds real runs have actually produced, and the sweep dropping the field that says |

**Nothing here is a runbook.** Each stage's runbook lives beside its code in
[`demos/`](../demos/), the notebooks are in [`notebooks/`](../notebooks/), and the
loop-to-notebook map is [`notebooks/README.md`](../notebooks/README.md). A runbook kept
apart from the thing it describes drifts, and a runbook that lies at minute forty of a
live session is the one thing this cannot afford.

## What is deliberately NOT here

- **Measured numbers in prose.** Every figure belongs in a chart that carries its own
  `n` and interval, or in a record under `results/` that a test proves is tracked. A
  number typed into a design note is a number nothing can invalidate.
- **A "what you should expect" table.** It is owed, and it comes from the dress
  rehearsal rather than from this build's exercises — see *Still owed* below.

## Two spec items superseded by findings

Both were written before the measurement that invalidated them, and both were caught
because the instruction was **read rather than executed**. Recording them here so the
pattern is visible, and so the next stale instruction gets the same treatment.

**`TerminationReason.DEADLINE`.** The spec asked for a `deadline` member alongside
`budget` and `max_attempts`. Writing it made the mistake visible: that enum names why
ONE AGENT LOOP stopped on ONE ITEM, and the deadline stops the RUNNER between items — so
an item that never started has no run, no attempts and no reason, and the member could
never be produced. `test_every_termination_reason_is_reachable` would have caught it as
a dead branch. Checking the clock inside the loop instead is worse and not because it is
harder: an item cut off after attempt 1 of 3 did not run under the condition it is
reported under, so scoring it puts a handicapped item in the accuracy figure. An item
runs fully or not at all.

**"Cut views to agent, verify, dial."** Written when A→C was the headline and the trap
was a supporting demo. That inverted: A→C measured as a null, and the trap — rules
withheld against rules given, a 73-point gap — became the session's primary result.
Cutting `trap` would have deleted the visual the whole session rests on. `oversight`
stays too: it was to go for live-surface reasons, and it is now the only view showing
the abstention machinery, which the 19–0 confabulate-versus-signal finding made a bigger
part of the session than it was. Five views, and the spec is amended rather than the
code bent to fit it.

The common shape is worth naming: **a spec is a measurement of what was known when it
was written.** Executing a stale one literally produces code that is correct against the
instruction and wrong against the world, and the only place that gets caught is at the
moment of writing it, by someone asking what would make the instruction true.

## Still owed

**`reference/` has to be rebuilt, not inherited as a deletion.** The old
`results/reference/` was removed because it held measurements of Anthropic models this
build no longer contains — it described a system that does not exist. The *purpose* it
served is unchanged and still required: a cloner should be able to see what a run
produces before spending anything.

So `reference/` returns from the dress rehearsal, against the current models, holding
the run's JSONL, its rendered charts and a summary table, each stamped with the date,
the models, the profile, the `n` and the account tier. The one structural difference is
that nothing under `src/loopeng/` may import it, and a test asserts that.

Until that run happens there is no "What you should expect" table in the README, and
there should not be one: a section promising numbers that do not exist yet is the
citation-that-resolves-to-nothing defect this repository has already been bitten by
three times.
