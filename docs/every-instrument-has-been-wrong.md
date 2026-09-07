# Every instrument in this build has been wrong at least once

**Written:** 2026-09-07, after the third one.
**Scope:** the tools this repository uses to measure itself, not the agent it measures.

This project's thesis is that a rule you declared and a rule something enforces come
apart, and that you cannot tell by looking. It makes that argument about a text-to-SQL
agent. The argument is stronger made about the repository, because here the failures are
documented, dated, and were all found the same way.

**17 instruments have been caught measuring something other than what they
claimed, and one plan has.** Not one was found by reading code. All of them were
green.

*The count above is checked against the numbered entries below by
`tests/test_docs.py`. It said "Twelve" for two entries longer than that was true — a
typed count going stale, in the document about typed things going stale.*

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

**And it exposes a limit of this project's headline guarantee, which is worth stating
on its own.** "Every figure shown in the session is computed during the session"
protects against a stale *number*. It does nothing against a stale *substrate*. A
warehouse built before the vocabulary widened yields figures that are freshly
computed, honestly timestamped, and drawn from the wrong world — the timestamp is
true and the number is meaningless.

Freshness is a property of the computation. Correctness is a property of the
computation *and* everything it read. The preflight now checks the second, because
nothing else in the pipeline could tell the difference.

## 6. `evaluate()` reporting a valid key as invalid

Every LangSmith call in the module goes through `_client()`, which reads the credential
from settings. `evaluate()` does not take that client unless it is handed one — it
builds its own from the environment, and this project's key lives in `.env`, read by
pydantic-settings and never exported to `os.environ`.

So five kinds of call worked and one returned `401 Invalid token`, on an account where
the key was perfectly valid. It was survivable — the arms had already run and written
their results, because LangSmith is advisory — but the diagnosis points at the
credential when the credential is right.

## 7. Four of five charts specified for a session that no longer existed

Not a bug in a running instrument; a bug in a plan. The thesis chart, cost-per-correct
and paired-delta charts were all specified around **C vs D** and **A → C**, and the
measurement killed both — A → C is a null over a mechanism that never fired, and C vs D
has no gap because the frontier model scored 60/60 twice.

Built in the specified order, the session's headline visual would have been a null and
the paired-delta chart would have carried a significance test over a loop that never
ran. Both would have survived to the dress rehearsal and possibly past it, because both
would have rendered correctly. See [the re-spec](charts-respec.md).

**This is the only entry found by changing the ORDER of the work rather than by running
something.** LangSmith was moved ahead of the charts because it was the part that could
not be validated by a test result; what it actually validated was the plan.

## 8. The termination vocabulary, failing the same distinction as the classifier

`TerminationReason` names why a loop stopped. It had no name for a run that
*declined*, so a model naming the input it had not been given fell through to
`max_attempts` — the default terminal state.

On the reference arm at L0 the distribution read `{success: 41, max_attempts: 19}`,
and those nineteen were exactly the nineteen abstentions. **The vocabulary that names
outcomes could not distinguish RAN OUT OF ROAD from REFUSED TO GUESS**, which is the
precise distinction the entire project is about.

This is the same failure as entry 2, one layer down: the classifier scored a refusal
as a crash, and the enum the classifier reads from could not have said otherwise. That
it happened twice, in two modules, says the distinction is genuinely hard to hold —
not that someone was careless once.

## 9. The lint rule, reading a format spec as a display string

Fourth time for this rule. `f"{tick:.0%}"` parses as a `FormattedValue` whose
`format_spec` is a `JoinedStr` holding the constant `".0%"`, which the percentage
pattern matches — so the rule **refused a derived axis label while the entire purpose
of deriving it was to satisfy this rule.**

A format spec is a formatting instruction. It says how to render a value; the value is
interpolated, which was never a Constant and never in scope.

## 10. The Wilson interval excluding its own point estimate

At 60/60 the arithmetic returned `ci_high = 0.9999999999999998` — two ulps below a
value of `1.0`. The interval did not contain the proportion it was an interval for.

Invisible everywhere it had ever been used: both round to the same percentage, so no
rendered string could show it. Fatal the first time something computed
`ci_high - value`, which is the standard error-bar idiom — matplotlib refuses a
negative error bar, and **the first chart to draw an interval on a boundary
observation was the first thing to find out.**

The function already clamped the interval into `[0, 1]`, with a comment explaining
that the clamp catches float error rather than a real excursion. It was right about
the direction it checked and silent about the other one.

## 11. DIAL, broken for any cell that had data

Found by the boundary tests written for entry 10, not by the entry-10 fix.

Removing the stored-measurement path left a dead branch in the bar renderer reading
`row["reference"]` — a key nothing sets any more. So `dial_chart` raised `KeyError`
for **any cell with a value**, and every existing chart test used empty or in-progress
cells, which return before reaching it.

The chart the session has had longest was the one nothing had drawn with real numbers
in it.

## 12. A test asserting the spelling instead of the property, again

`"measured no variance"` failed a substring check on a caption that contained it and
rendered it correctly — the wrapper had inserted a newline at the column width, so the
string was `"measured no\nvariance"`. The assertion was coupled to *where the wrap
landed* rather than to *what the figure said*.

Second time this shape has appeared. Two tests earlier asserted `"n=1" in render()`
and broke when a boundary observation started rendering as `"1 of 1 — at least ..."`
— the metric still carried its n, which is what the tests were named for.

An instrument that checks the spelling passes and fails for reasons unrelated to the
property it is protecting, in both directions. That is the same defect as a checker
that matches nothing, wearing better clothes.

## 13. The confidence scorer, whose failure mode was maximum confidence

`triage.abstain.confidence_of` read `run.get("termination", "")`. Nothing in the function
matches `""`, so a row with no recorded termination fell through every branch to the last
line — `clean_first_try`, the **highest** confidence band, described as "accepted on the
first attempt with no revisions".

A row too malformed to say how its loop ended was scored as the best possible outcome,
inside the one function whose only job is to say how much a result can be trusted, and
that score feeds the abstention curve — the figure about knowing when not to answer.

The defaults were never protecting real data. Every row the sweep and the conditions
write carries all three fields. They were protecting *malformed* data from being noticed.

## 14. The selector that quietly drew a different cell

`render.curve_cell` looked up the cell the abstention curve is computed over and, when it
was absent, returned `max(candidates, key=lambda c: len(c["items"]))`. The key it looked
for named a role that had not existed since the roles were renamed, so the fallback fired
on every run: the curve was drawn from a cell nobody chose, and nothing about the output
said so.

Then the same key turned up again, one module over, in `views/oversight.py` as
`cells.get(CELL_KEY, {}).get("items", [])` — where the default made the view render "not
measured yet — run the sweep first". **OVERSIGHT was telling anyone who opened it to go
and run the sweep they had just run.** Not a wrong number: a wrong instruction, which is
a category this build had not produced before.

The fallback's stated justification was false in both halves. It read: *"the fallbacks
exist so a `smoke` or frontier-only run still gets a curve rather than an empty panel."*
Smoke **does** produce that cell, and no profile is frontier-only — the reference role
never appears without the agent role. It insured against a case no profile can create,
and the one case it ever fired on was the one where it was wrong. The test asserted the
fallback rather than the property, which is how the fallback survived.

That shape — *a guard written against a case that cannot happen, which then fires on the
case where it is wrong, protected by a test asserting the guard rather than the property*
— has now appeared three times: the p10 share-question regex, the retired-model-name
prose ban, and this.

## The rule that came out of it

Three of the entries above are the same defect, and "fail loudly" is not the right
statement of it, because two lookups in this repo degrade on purpose and are correct to.
The general form is:

> **A lookup may degrade if something downstream reports the degradation.**

`diff.paired_map` tolerates a cell with no `items`, and earns it: `keeps_per_item_outcomes`
sets a flag and `unpairable_because` distinguishes *"these arms share no answered items"*
from *"the per-item outcomes were not retained when this was frozen"*. The reader is told
which.

`fingerprint.model_versions` falls back to the requested model id when nothing has been
served yet, and earns it for a different reason: its failure mode is a false **mismatch**,
which is loud. A fallback that can only make the guard fire more often is not this defect.

The abstention selector degraded into a **different measurement** with nothing anywhere to
signal it. That is the line. It is not about how a lookup fails; it is about whether
anything downstream is in a position to say that it did.

The same rule settled a return type. `named_secondary_deltas` emitted a comparison only
when both its cells existed, so a **pre-registered** result whose cell was missing did not
become an empty row — it stopped being a row. The pre-registration is read aloud before
the first cell runs and the room checks the result against it, so a claim with no row at
all is a claim nobody notices went missing. Nothing downstream could report it, because
there was nothing to report on. It renders as a row with no bar now, naming the cell it
needed.

## 15. The same lesson at three depths, in one afternoon

Item 6 produced three failures that are the same shape at increasing distance from
the code, and the third is the one that should worry a reader most.

**The code was wrong.** `run_cell` wrote its summary and then re-raised on Ctrl-C. That
looked careful — the record was safe on disk — but the report never reached
`run_sweep`, so the cell's spend was never counted. A real interrupt nine seconds into
a live sweep printed `spend: est. $0.0000 of $0.05` over a cell that had just cost
$0.0019. On a session that is the spend cap going blind at exactly the moment
something has gone wrong.

**The test was wrong, and green.** The first draft of the interrupt tests raised
`KeyboardInterrupt` from the work function. A real Ctrl-C is delivered to the MAIN
thread, which is blocked in `wait`; an exception from a worker surfaces at
`future.result()` instead. Different path, same `except` clause, so the test passed —
and it could not reach the second-interrupt branch at all, because a worker only
raises once. A test pointed at the wrong code, agreeing with the right answer.

**The VERIFICATION METHOD was wrong.** The first attempt to exercise the interrupt
sent `kill -INT` to a shell background job. A non-interactive shell sets SIGINT to
`SIG_IGN` in the child, so the signal did nothing; the sweep ran happily to
completion. The output was a clean, complete, entirely successful run — and reading it
as "the interrupt was handled" was one glance away.

That third one is new. Every other entry here was found by running the thing and
reading the output, which makes "run it and read the output" the method this whole
document rests on. This is the first time the method itself was the broken instrument,
and it failed in the direction that flatters: not a crash, not a hang, but a green run
that looked like proof.

There is no fix for that beyond the one already in use — knowing what the evidence
should look like BEFORE producing it, and treating an unexpectedly clean result as a
question rather than an answer. The interrupt was supposed to leave a partial cell. It
left a complete one. That mismatch is the only thing that caught it.

## 16. A deleted capability came back through a file format

The stored-measurement render path was removed rather than defended — no stored cell
format, no loader, no flag, no hatching, five guards deleted along with the thing they
guarded. `docs/guards-are-a-tell.md` is the note about it.

Months later, `notebooks/` was added. A Jupyter notebook serialises its **outputs into
the file**. A committed notebook therefore shows a reader tables and figures computed on
somebody else's machine, on some other day, inside a document that looks live and
carries an `In [12]:` prompt to prove it ran.

That is the same defect. Not an analogue of it: the same one. Numbers on screen that
were not computed by the run being looked at, with nothing on screen saying so — and it
arrived without touching a line of the code that was deleted to prevent it, because the
capability was reintroduced by a **serialisation choice** rather than by a feature.

Removing a capability from the data model and the vocabulary does not remove it from
every representation the project may later adopt. The notebooks are committed with every
output cleared and a test asserts it, but the guard had to be written a second time, for
a format, after the first one was thought to have settled the question.

## 17. The taxonomy the sweep computed and discarded

`judge` has always determined which KIND a visible failure is. `verify/batch.py` records
it, `agent/trap.py` records it, `triage/failures.py` exists to sort failures by cause.
`sweep/runner.py` never recorded it — so the most expensive measurement path in the
project wrote cells that could be counted by outcome and never classified by cause.

Every sweep ever run determined the kind of every visible failure, held it for the length
of one function, and dropped it before writing the row. Same sentence as prompt caching:
the instrument was built, the number was computed, and the caller that spends the most
money ignored it.

`VisibleKind` also had no reachability pin, while `TerminationReason` has carried one
since the `declined` gap — and `no_attempts` was in the enum with no test producing it.
Regenerating the record from real failures found the seventh category was a category
nothing had ever demonstrated. See [the failure taxonomy](the-failure-taxonomy.md).

## 18. The taxonomy record's own citation resolved on one machine

Entry 17's fix cited `results/failure_taxonomy_observed.json` by name. The file was
written, committed with `git add -A`, and **silently not added** — `.gitignore` excludes
`results/*.json`. The local suite passed, because the file was sitting there untracked.
CI failed on the clone.

That is the noise-floor defect repeating, three months and one filename later, in the
commit whose subject is citations that resolve to nothing. The existing link check asks
`exists()`, which is true of an untracked file, so it could not see it.

**What caught it was the clean checkout, not the author's laptop** — the first time in
this build that CI found something local testing structurally could not. The guard now
asks whether evidence cited by a design note is TRACKED rather than present, and it is
scoped to `docs/` on purpose: a runbook naming `results/sweep/dial.png` describes output
the reader is about to generate, and requiring that to be committed would invert the
rule this repository is built on.

## A second rule, from the same fix

`named_secondary_deltas` also settled which of two **true** sentences a row should carry.
An absent pre-registered pair is cross-model *and* has a missing cell. Both facts are
correct. `"No p-value: this compares two models"` would have been an honest sentence on
that row — and a reader would have taken it for a measured pair that merely cannot be
tested, rather than one that was never computed.

> **When two true explanations compete for the same row, the one that flatters the
> result loses by default.**

It is a tie-break, not a preference for pessimism. Both branches state something true;
the question is only which the reader is left holding, and the reassuring reading is the
one they will not go back and check. So the absence branch runs first in both `reading()`
and `_delta_row`, and the cross-model refusal — which is still true — is what a formed
pair gets.

The same rule explains two earlier entries. `unpairable_because` reports "the per-item
outcomes were not retained when this was frozen" rather than "these arms share no
answered items", because the second flatters the freeze by blaming the data. And a
deadline-stopped cell renders "stopped at the deadline, final at n=NN" rather than "in
progress", because the second flatters the run by implying more is coming.

## A note on how many of these are self-referential

Four now, and it stopped being funny at the second:

- the lint rule that scanned nothing, then the lint rule that read a format spec as a
  display string — a checker failing at checking
- a test asserting the spelling instead of the property, in a repository whose thesis is
  that declared and enforced come apart
- the citation check, caught by a note about citation checks
- this document opening "Twelve instruments have been caught…" while carrying fourteen
  numbered entries — a typed count going stale, in the document about typed things going
  stale

That is not coincidence and it is not irony. It is what happens when the artifact and its
subject are the same kind of thing: every instrument here measures a codebase, this
codebase is instruments, and so each failure mode has a copy of itself available one level
up. It is also why the fixes generalise — a rule that catches the count in this file is
the same rule that catches a caption on a chart.

## What they have in common

**None was found by reading code.** They were found four different ways: by running
the thing and reading the output; by drawing it; by running the work in a different
order; and — twice — by a library's input validation refusing arithmetic, which then
produced a test that found a dead branch nothing had ever executed. Two were found by a
measurement taken for an unrelated reason, and one by a measurement it had itself
silently ruined.

Each had a plausible reason to look correct:

| instrument | why it looked right |
|---|---|
| the lint rule | it printed a success line every run |
| the classifier | its rule and its enforcement agree everywhere except one case |
| the band subtraction | the arithmetic is correct, for the category set that existed |
| the label map | it was total when it was written |
| the warehouse factory | its docstring argued, correctly, for the check it did have |
| the LangSmith client | five other call sites worked, so the key was obviously fine |
| the chart plan | every chart would have rendered correctly |
| the termination enum | every name in it was accurate for the cases it had |
| the lint rule, again | it was refusing something that looked exactly like the bug |
| the Wilson interval | it clamped the direction it had thought about |
| DIAL | every test of it used cells with no data |
| two assertions | they checked the exact string, which was almost the property |
| the confidence scorer | every real row carries the field it defaulted |
| the curve selector | it always returned a cell, and the cell was always plausible |
| the absent comparison | every comparison it emitted was correct |
| the interrupt accounting | the record on disk was complete and correct |
| notebook outputs | the capability had been deleted, so the question felt settled |
| the failure taxonomy | seven categories, and nothing said which had been seen |
| its own citation | the file was right there, on one machine |
| the interrupt test | it exercised a real path, and passed |
| `kill -INT` on a background job | the run it produced was clean and complete |

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
- every site that subtracts an interval endpoint is exercised at 0 and at n, because
  the arithmetic was wrong only there and only when subtracted
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
It is 18 data points on how instruments fail, in a repository written by someone paying
attention specifically to that failure mode, with tests for it.

The claim the session should make is not "we measured this carefully". It is: *every
instrument we built to measure this has been wrong at least once, we found all of them the
same way — by running it and reading the output — and none of them by review.*

That is a stronger claim, and it is the one the evidence supports.
