# Every instrument in this build has been wrong at least once

**Written:** 2026-09-07, after the third one.
**Scope:** the tools this repository uses to measure itself, not the agent it measures.

This project's thesis is that a rule you declared and a rule something enforces come
apart, and that you cannot tell by looking. It makes that argument about a text-to-SQL
agent. The argument is stronger made about the repository, because here the failures are
documented, dated, and were all found the same way.

**Five instruments have been caught measuring something other than what they claimed.
Not one was found by reading the code.** All five were green.

## 1. The lint rule that scanned nothing

`tools/lint_no_numbers.py` bans typed numbers in the modules that render to a projector.
It named a views module under the old top-level `app/` package. That file had moved to
`src/loopeng/views/` during a restructure, so the rule walked a path that did not exist,
found nothing, and exited 0.

(Writing that sentence tripped `test_no_markdown_points_at_a_file_in_a_deleted_directory`,
which refuses a markdown citation to a file in a removed directory — including one being
quoted as history. Fifth data point, and the shortest-lived: the check that exists because
a rule cited a dead path caught a note about a rule citing a dead path.)

The test written to prevent exactly that planted its violation by *writing* the target
file — which created the missing path. It proved the AST walker worked while never once
checking the target was real.

And when the target was fixed, the rule still caught nothing that mattered: it inspected
numeric literals, and a number inside a *string* is a string constant. The single
most-quoted screen in the session carried two hardcoded p-values, in a file the rule had
always scanned, and the build was green.

**Three failures, one instrument, and all three left it reporting success.**

## 2. The classifier that ranked a refusal below a confabulation

On items whose required value was withheld, one model invented a number and one model
named the input it was missing. The second cannot execute, so the classifier scored the
confabulation as a `silent_error` and the refusal as a crash.

On the single axis this project exists to teach — a clean plausible wrong number is the
dangerous outcome — our own instrument ranked the two behaviours backwards. Full write-up:
[the instrument note](instrument-ranked-honesty-backwards.md).

Then the same instrument, one level deeper: a guess that *lands* was scored as knowledge,
because an accuracy metric compares the answer to gold and both answers equal gold.

## 3. The band that swallowed whatever was added next

`silent = len(ran) - correct` derives one category by subtracting the categories somebody
remembered from the total. It is right exactly while the enumeration in the author's head
matches the enum.

Two categories were added. Both landed in `silent_errors`, in two separate modules — so a
*right* answer was counted as a wrong one, on the headline metric, twice.

## 4. The label map that would have crashed on stage

The trap's reveal grid looks up an outcome label with a bare `[]`. The map had three
entries; the enum had five. The grid would have raised `KeyError` on the first currency
item of the reveal — in front of the room, on the headline visual.

Louder than a silent default, and worse than either.

## 5. The warehouse factory that used a warehouse the gold set could not index into

`ensure_warehouse` generated the file when absent and returned it otherwise. Its
docstring said the missing check was deliberate: silently regenerating someone's
warehouse mid-session because a seed argument drifted would be worse than using the
file that is there.

That reasoning is correct, and it is about the **seed**. It does not cover the
schema's *vocabulary* changing. When the categories and regions were widened to build
the 84-item gold set, a warehouse generated before the widening contained none of the
new slices — so gold answers referencing them came back empty, and a 120-call
measurement scored exactly zero on every arm, including the pattern that requires no
rules at all.

Zero everywhere is at least loud, and it is why this was caught in one run. **A partial
overlap would have been worse:** some items right, some wrong, and a plausible number
on a chart.

The fix keeps the original reasoning intact. It refuses rather than regenerates, and it
asks about the content the gold set indexes into rather than about the seed.

## What they have in common

**None was found by reading code. All five were found by running the thing and looking at
what came out.** Two were found by a measurement taken for an unrelated reason, and one
by a measurement it had itself silently ruined.

Each had a plausible reason to look correct:

| instrument | why it looked right |
|---|---|
| the lint rule | it printed a success line every run |
| the classifier | its rule and its enforcement agree everywhere except one case |
| the band subtraction | the arithmetic is correct, for the category set that existed |
| the label map | it was total when it was written |
| the warehouse factory | its docstring argued, correctly, for the check it did have |

The last two are the most uncomfortable, because **both were correct when written.** They
did not decay through neglect. They decayed because a category was added somewhere else,
and nothing connected the two facts. Correctness that depends on a set staying frozen is
not correctness. It is a deadline.

## What was done differently each time

The fix is never the interesting part. What changed is what makes the *next* one loud:

- a declared lint target that does not resolve is now a build failure
- every `Outcome` must have a band, and `band_of` raises rather than defaulting
- every dict keyed on `Outcome` must be total, checked by walking the AST of `src/`
- the grep that bans band-subtraction has its own test proving it matches the two lines
  it was written for
- a warehouse that cannot represent the declared vocabulary is refused, with the fix
  named, rather than silently used

That last one is the pattern worth naming. **A checker that silently matches nothing is
indistinguishable from a checker that passes**, so every checker added here now carries a
test that it fires on the bug it was written for. The lint rule failed that way twice
before anyone noticed the shape.

The convention paid immediately. Asked whether the AST walker also caught a map built by
comprehension or by `dict(zip(...))`, the answer was no — it matches `ast.Dict` and both
of those are different nodes. Rather than document the gap and stop, the check moved to
the built objects: importing each module and inspecting what it actually holds sees every
construction form, because by then a dict is a dict. Its meta-test plants all three and
requires the detector to fire on each.

One residual gap is documented rather than papered over: a dict built inside a *function*
by comprehension is invisible to both halves — the runtime check cannot see it because it
is not a module attribute, and the AST check cannot see it because it is not a literal. A
checker with a known blind spot is usable. A checker with an undocumented one is this
list's recurring entry.

## The honest reading

This is not a list of things that went wrong on the way to a build that is now correct.
It is four data points on how instruments fail, in a repository written by someone paying
attention specifically to that failure mode, with tests for it.

The claim the session should make is not "we measured this carefully". It is: *every
instrument we built to measure this has been wrong at least once, we found all of them the
same way — by running it and reading the output — and none of them by review.*

That is a stronger claim, and it is the one the evidence supports.
