# Pre-fix measurements (kept deliberately)

These are the measurements taken BEFORE the p07/p08 wording was corrected. They are
kept, not deleted, because the defect and what it cost are part of the record.

Two of the ten gold patterns never said whether refunds were netted. The model
frequently netted; the gold answers were gross. Triage found it, and the split showed
it was not neutral: **100% of L3 failures on those patterns subtracted refunds against
30% at L0**, because the L3 prompt renders the refunds rule and the model then netted
on a question that never asked. It penalised the arm with the more complete spec, and
it cost **15.1pp on the L3 arm** (26.8% all patterns vs 11.8% excluding them).

The fix states the MEASURE without stating the RULE — "before refunds" — which is the
same line the question-leakage test polices.

This directory is the evidence for the Stage 3 triage beat: we found our own
under-specification by triaging failures, measured what it cost, and fixed it.

## One rendered string was re-stamped; no measured value changed

Every raw cell here was written by `Metric.render()`, which bakes `computed HH:MM
today` into its string. On a file kept as a record that sentence is false, and it is
false in the exact way `sweep/reference.py` exists to prevent — it makes a stored number
look like a fresh one. Fifteen files here said it, every day anyone opened them.

`silent_error_rate` now reads `measured 2026-07-29`, applied through
`reference.as_measured`, the same helper `_freeze` uses. The date is not inferred: this
directory's own `measurements.json` was frozen from these cells and already carries it.

**Nothing else moved.** `rate_value`, `rate_ci_low`, `rate_ci_high`, `rate_n`, the
per-item rows and every count are byte-for-byte what was measured — the diff is one line
per file. A test scans every committed JSON under `results/` for the pattern, so this is
enforced rather than remembered.
