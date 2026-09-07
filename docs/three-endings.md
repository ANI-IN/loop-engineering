# Three endings, committed before the run that will be shown

**Written:** 2026-09-08, before the dress rehearsal.
**Selected by:** `src/loopeng/sweep/endings.py :: select()`, not by a person reading a chart.

The session's **named secondary** asks one question: does a budget model with loops
around it close the distance to a frontier model with nothing around it?

There are three ways that can come out. All three are written here, with their criteria,
before the run the room will see. Which one gets said out loud is then arithmetic.

## The readings

| ending | when it is selected |
|---|---|
| **No gap to close** | The frontier model bare was **not ahead** of the budget model bare. |
| **Reached** | There was a gap, and with loops the budget model was **not behind** the frontier. |
| **Approached but short** | There was a gap, and with loops the budget model was **still behind**. |

Checked in that order, and the order matters. "No gap to close" is first because it is
the result most easily dropped: it makes the comparison uninteresting rather than lost,
and a finding nobody wants to present is a finding that quietly does not get presented.
If the frontier model bare is not ahead, then whether loops close a distance is a
question about a quantity that does not exist, and both other readings would be claims
about it.

## The criteria carry no p-value, and that is not a loophole

`sweep/diff.py` refuses a p-value across models — in code, not in a caption — because a
cross-model pair differs in model, price and training at once, and a significance claim
over it attributes a confounded difference to whichever axis the chart is about.

A pre-commitment that turned on significance would therefore be a rule the rest of the
project forbids anyone to evaluate. So the criteria are stated in **discordant pairs**:
of the items both arms answered, how many did each get that the other did not. That is
what a paired comparison can honestly report between two different models.

Items an arm **declined** are excluded from the pairing rather than scored as wrong.
Counting an abstention as a failure would rank a model that knew what it was missing
below one that invented a number, which is the mistake this project spent an entire
outcome category fixing.

## What the pilot already says, recorded now so it cannot be chosen later

The four conditions have been run once, on the 60 held-out items, before this note. **So
for that data this is not a pre-commitment**, and saying otherwise would be the exact
move the pre-registration exists to prevent. What it is instead: the pilot's reading,
written down and dated *before* the rehearsal, so a different reading on the day is a
visible change rather than a quiet selection.

The pilot selects **approached but short**. The verdict is one sentence and the
decomposition is the finding, so both get said, **in that order**:

- **The verdict.** The frontier model bare beat the budget model bare on 8 discordant
  items to 0 — a gap existed — and with the loops the budget model did not catch it.
  By accuracy over all 60 items: 52 correct against 60, a gap of 8.
- **The decomposition.** Over the 54 items **both arms answered**, the deficit is **2
  discordant items**, not 8. The other 6 are items the looped arm did not answer at
  all: it declined, or failed visibly.
- **Why that matters.** An arm wrong on 2 and visibly failing on 6 is not an arm
  quietly wrong on 8. Six of those failures are in the band a reader of the answer can
  see, and only the other two are in the band this session exists for.

**The order is load-bearing in both directions.** Leading with the decomposition would
be the post-hoc reframing this whole note exists to prevent — picking a kinder
description of a result after seeing it. Stopping at the verdict would understate the
result, because the raw gap and the paired deficit are different sizes and the
difference between them is made of a different kind of failure.

`Selection.render()` prints them in that order for the same reason, so what gets said
out loud cannot drift from what is written here.

## What would change the reading

Stated in advance so the rehearsal cannot be re-run until it agrees:

- **Fewer visible failures in the looped arm** would move items out of "did not answer"
  and into the pairing, which could push the ending either way.
- **Any discordant item won by the budget arm** narrows the margin directly.
- **The frontier arm failing to beat the bare budget arm** selects "no gap to close",
  and that is a legitimate outcome of a rehearsal, not a broken run.

**The rehearsal is run once and its ending is the one reported.** If it disagrees with
the pilot, both are shown, with their dates and their discordant counts, and the
disagreement is the finding — a run-to-run difference on a comparison this design is
already documented as underpowered for.
