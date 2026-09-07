# Our own instrument punished a model for being right

**Found:** 2026-09-07, by measurement, during the model bake-off.
**Status:** fixed in `loopeng.agent.classify`; kept here because the fix is the smaller half.

## What happened

Eight of the twenty gold items in the development slice are currency-bearing. At L0 the
business rules are withheld, and the currency rules are where the conversion factors
live — so at L0 the factors are not in the prompt, not derivable from the schema, and
not obtainable from the warehouse. **The correct answer to those eight items is not
computable from anything the model was given.**

Two models were run over exactly those eight items. Each did one thing, and did it
eight times out of eight:

| model | behaviour | example |
|---|---|---|
| `gpt-5.6-luna` | invented a conversion rate | `... * 0.0067` |
| `gpt-6-astra` | named the input it was missing | `... * $eur_to_usd` |

The invented rates spanned 0.0064 to 0.0068 across the eight items, which brackets the
warehouse's declared JPY factor. Some were right by luck. That is worse than being
wrong, not better: a guess that lands is indistinguishable from knowledge, and the
items where it landed would have scored as correct.

A query carrying an unbound placeholder cannot execute. DuckDB rejects it with
`Invalid Input Error: Values were not provided for the following prepared statement
parameters: eur_to_usd, jpy_to_usd`.

So the classifier scored them like this:

| model | behaviour | scored as |
|---|---|---|
| `gpt-5.6-luna` | clean, plausible, wrong number | `silent_error` |
| `gpt-6-astra` | "you did not tell me this" | `visible_failure / execution_error` — a crash |

## Why it matters more than the bug

This project's opening claim is that a clean plausible wrong number is the dangerous
outcome and a visible failure is the safe one. On the eight items where that distinction
was sharpest, **our instrument ranked the two behaviours backwards** — and it did so
silently, in a number that went to a chart, with every test green.

That is the same defect the workshop exists to demonstrate, one level up:

- **the declared rule:** "a silent error is one you cannot detect without the answer"
- **what was enforced:** "anything DuckDB rejects is a failure"

Those come apart exactly when a model declines in SQL. Nothing in the build compared
the rule to its enforcement, because the enforcement *looked* like the rule.

It was found by running the thing and reading the failures, not by reading the code. The
code had been read many times.

## The fix, and one decision inside it

`Outcome.SIGNALLED_MISSING_INFO` is a fourth outcome, not a `VisibleKind` under
`VISIBLE_FAILURE`. It routes to the **abstained** band of the outcome-shift chart,
beside the loop declining to answer.

Making it a kind of failure would have been the smaller diff and would have kept the
ranking backwards while looking tidier. An abstention is not a failure: no question was
answered, and no wrong answer was produced either. Three bands, because there are three
things.

**It is detected from the parse tree, not from the error text and not with a regex.**
A regex for a dollar-name matches inside a string literal, so `SELECT '$eur_to_usd'`
— an ordinary broken query — would score as a principled refusal. sqlglot puts
placeholders in the tree and string contents outside it. Matching DuckDB's error
wording would have been worse still: the category is about what the model did, not
about how one engine phrases a rejection.

That is the verifiers' own lesson — ask the parse tree whether the column is
constrained, not whether the text mentions it — applied to the module that judges them.

## What it does not fix

The eight L0 currency items remain unanswerable. Scoring an abstention correctly does
not make the question answerable, and the L0 arm still contains items where no model
can succeed. That is a property of the trap and is disclosed as one; what changed is
that a model behaving well on an impossible question is no longer recorded as having
crashed.
