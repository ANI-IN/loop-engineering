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

---

# Second act: the instrument could not tell luck from knowledge

Found the same day, one level deeper, by asking what happens when a guess is *right*.

## The condition, which is structural rather than probabilistic

The conversion factors live in `semantic_model.yaml` and reach the model only through
the L3 prompt. There is no rates table in the schema, and nothing in the warehouse from
which a rate could be derived — it stores an amount in minor units and a currency code.

So on an item requiring the currency rules, **at a level that withholds them, a correct
answer is a guess that landed.** That is not a heuristic and it needs no threshold; it
follows from what was in the prompt. `Outcome.UNEARNED_CORRECT` is that condition, and
`_could_not_have_known` decides it from the item's rules and the prompt level.

It is deliberately narrow. It does not fire for `soft_delete` or `internal_accounts`: a
model that writes `deleted_at IS NULL` at L0 has plausibly reasoned it from a column
called `deleted_at`, and inference from the schema earns the answer. Only an arbitrary
constant conjured from nothing does not.

## What the data says, and why it is not reassuring

Re-scoring the measured arms with the outcome live:

| arm | n | correct | of which unearned | currency items |
|---|---|---|---|---|
| luna L0 | 20 | 2 | **0** | 8 |
| astra L0 | 20 | 4 | **0** | 8 |

Zero. Every L0 correct answer was `p01_product_count`, which requires no rules, or
`p03_customers_in_region`, whose rules are inferable from column names. **The trap
matrix is unchanged.**

Then the reason why:

| item | rate luna invented | JPY exact? | EUR exact? | scored |
|---|---|---|---|---|
| `p04_gross_revenue__00` | 0.0064 | no | no | silent error |
| `p05_net_revenue__00` | 0.0068 | no | no | silent error |
| `p07_aov_by_region__00` | **0.0067** | **yes** | no | silent error |
| `p08_revenue_by_category__00` | **0.0067** | **yes** | no | silent error |
| `p04_gross_revenue__01` | 0.0066 | no | no | silent error |
| `p05_net_revenue__01` | 0.0066 | no | no | silent error |
| `p07_aov_by_region__01` | **0.0067** | **yes** | no | silent error |
| `p08_revenue_by_category__01` | **0.0067** | **yes** | no | silent error |

**Luna guessed the JPY factor exactly, on four of eight items.** It never guessed the
EUR one. Every currency item is scoped to `currency IN ('EUR', 'JPY')` and therefore
needs *both* factors, and the EUR miss is the only thing that kept those four out of the
correct column.

Had any of those items been JPY-only, a guessed rate would have scored as knowledge,
four times out of eight.

## Why that is the same defect again

The EUR+JPY scoping was not chosen to prevent this. `gold/patterns.py` says why it was
chosen: *"EUR is included so the multi-currency rule is exercised as mixing and not only
as JPY's zero decimal places."* It is about rule coverage. That it also happens to
require two independent guesses, and so protects the score, is a coincidence.

Which is [the guards argument](guards-are-a-tell.md) from the other direction. A property
holding by accident looks exactly like a property holding by design, right up until the
accident stops.

**State the counterfactual plainly, because it is the whole reason this outcome exists.**
Had the warehouse been single-currency — JPY only, which is the obvious simplification and
was very nearly the design — four of eight L0 currency items would have scored as correct
on a rate the model invented. The bottom-left cell of the trap matrix would have read 30%
instead of 10%. The headline gap would have compressed from 60 points to 40, in the
direction that makes the session's central claim look weaker than it is, and **every test
in this repository would have been green.** Nothing would have said so, because there was
nothing that could.

That gold set would not have been careless. It would have been simpler, and simpler in a
way that looks like good taste.

So the outcome exists even though it currently fires zero times. The alternative is a
metric that will silently start scoring confabulation as knowledge the first time the
item mix changes, with nothing to say it happened.

## What this buys the Level 2 argument

An accuracy metric cannot separate these two cases. It compares the answer to gold, and
both answers equal gold; there is nothing further to look at.

A verifier can, because it reads the query rather than the result. *Did this rate come
from anywhere?* is a structural question about the SQL — is the factor joined from a
source, or is it a literal the model produced — and it is answerable without knowing the
right answer.

That is the clearest statement of what verification adds that measurement cannot, and it
was found by measuring rather than by arguing.

---

# Postscript: it fires on the real set

Everything above was written when the outcome had fired zero times. On the 60-item
held-out set it fires twice, on the first live run:

| | items matching gold | scored correct | scored unearned |
|---|---|---|---|
| L0 · rules withheld | 8 | 6 | **2** |
| L3 · rules given | 50 | 50 | 0 |

Both are currency items — `p07_aov_by_region__04` and `p08_revenue_by_category__04` —
where a guessed conversion rate landed on an item needing both factors, which is the
case the earlier measurement narrowly missed.

**Without the category, L0 would have read 13.3% instead of 10.0%,** and the headline
gap would have been 70.0 points instead of 73.3. The category moves the headline by
3.3 points, in the direction that makes the claim *stronger* — which is the direction
that matters, because a metric that flatters the arm you are arguing against is the
only kind you can trust.

The six genuinely correct L0 answers are all `p01_product_count`, the pattern that
requires no rules. That is the L0 floor doing exactly its job: without it, L0 would sit
at zero by construction and the whole comparison would be rigged.

## What it does not fix

The eight L0 currency items remain unanswerable. Scoring an abstention correctly does
not make the question answerable, and the L0 arm still contains items where no model
can succeed. That is a property of the trap and is disclosed as one; what changed is
that a model behaving well on an impossible question is no longer recorded as having
crashed.
