# docs/

Design notes and pre-committed decisions. Not a runbook — each stage's runbook lives
beside its code in [`demos/`](../demos/), because a runbook kept apart from the thing it
describes drifts, and a runbook that lies at minute forty of a live session is the one
thing this cannot afford.

What lives here is the opposite: decisions that have to be written down **before** the
data lands, and findings about the build itself that no module is the right home for.

| note | what it records |
|---|---|
| [Five guards on one capability is a tell](guards-are-a-tell.md) | why the stored-measurement render path was deleted rather than defended, and what it cost |
| [Our own instrument punished a model for being right](instrument-ranked-honesty-backwards.md) | the classifier ranked a model's honest refusal below a confabulation, silently, with every test green |
| [Every instrument in this build has been wrong at least once](every-instrument-has-been-wrong.md) | 16 of them plus one plan, all green at the time, none found by reading code |
| [The failure taxonomy, regenerated from real failures](the-failure-taxonomy.md) | which of the seven visible-failure kinds real runs have actually produced, and the sweep dropping the field that says |
| [Re-specifying the five charts](charts-respec.md) | what the measurement did to the chart plan, and what each chart is now for |

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
