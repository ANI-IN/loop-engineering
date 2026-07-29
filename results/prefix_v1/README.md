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
