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
| [Every instrument in this build has been wrong at least once](every-instrument-has-been-wrong.md) | four of them, all green at the time, none found by reading code |

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
