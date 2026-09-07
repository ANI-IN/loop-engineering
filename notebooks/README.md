# notebooks/

Three notebooks, in the order they are worth opening. **The filename says whether it
spends** — `_free` makes no API call at all, `_live` does — because that is what you see
in a directory listing, before you have opened anything.

| notebook | cost | what it is for |
|---|---|---|
| [`01_the_rules_free.ipynb`](01_the_rules_free.ipynb) | nothing | The business rules as declared, the two prompt levels, the rule-surface probes, and the gold set. Start here even with a key: if this runs clean your checkout is sound, and if it does not, nothing you measure later means anything. |
| [`02_one_question_live.ipynb`](02_one_question_live.ipynb) | a fraction of a cent | One question through Level 1 and Level 2, with the attempt timeline, the verifier's rejections and the cost. The teaching beat: verification does not mainly make an agent right, it makes it stop being confidently wrong. |
| [`03_read_a_sweep_free.ipynb`](03_read_a_sweep_free.ipynb) | nothing | Read a sweep you have already run: the pre-registration, every cell, the figures, the comparisons and what may not be said about them. |

```bash
uv sync --extra notebooks
uv run --extra notebooks jupyter lab notebooks/
```

## THE NUMBERS ARE SESSION ORDER, NOT LOOP LEVELS

`01`, `02`, `03` are the order to read them in. They are **not** Levels 1, 2 and 3.

This warning exists because the mistake has already been made once here. `demos/` used
to be `01_agent_loop`, `02_verification_loop`, `03_event_driven_loop`,
`04_hill_climbing_loop`, where the numbers *did* mean the levels — and readers kept
carrying that convention into every other numbered thing in the repository. The numbers
were reworked to stop it, and they have now returned in a different directory with a
different meaning, which is exactly how the confusion got in the first time.

So: `02_one_question_live` covers Levels **1 and 2**. `03_read_a_sweep_free` covers
Level **4**. Nothing here covers Level 3.

## Where each loop lives

| loop | what it is | where to see it |
|---|---|---|
| **Level 1** — the agent loop | Ask, run the SQL, retry when it **fails to execute**. Sees crashes only. | [`02_one_question_live.ipynb`](02_one_question_live.ipynb), first half |
| **Level 2** — the verification loop | Level 1 plus verifiers that read a query which **ran** and reject it for breaking a declared rule. | [`02_one_question_live.ipynb`](02_one_question_live.ipynb), second half |
| **Level 3** — the event-driven loop | A queue and a worker: claim a question, run Level 2, write the answer back, with nobody watching. | **`demos/03_event_driven_loop/`, terminal only.** See below. |
| **Level 4** — the hill-climbing loop | The loop around the loop: a sweep across configurations, measuring which is better. | [`03_read_a_sweep_free.ipynb`](03_read_a_sweep_free.ipynb) |
| the rules, the levels, the gold set | What all four loops are measured against, and the L0/L3 split the session turns on. | [`01_the_rules_free.ipynb`](01_the_rules_free.ipynb) |

### Why Level 3 has no notebook, and that is the point

**A notebook is a supervised surface. Level 3 is the stage that denies supervision.**

The whole claim of the event-driven loop is that nobody is watching: a question is
enqueued, a worker claims it, runs the verification loop and writes the answer back,
and no human is in the path. Putting that in a notebook — a cell you run, whose output
you read, in a browser tab you are looking at — would stage a demonstration of
unsupervised operation under supervision, and the reader would take the wrong thing
from it. The same reasoning is why Level 3 has no Gradio view either.

It runs in a terminal, in two commands, and you are meant to be able to walk away
between them:

```bash
uv run python demos/03_event_driven_loop/enqueue.py "your question"
uv run python demos/03_event_driven_loop/worker.py --drain
```

Its absence here is a design decision, not a gap in the notebooks.

The kernel is an **optional** dependency. Nothing else in this repository needs it, and
CI installs the default set only — so the offline job's zero-key, zero-network property
is not weakened by a notebook a reader may never open.

## The two rules these are held to

**They import from `loopeng` and contain no loop logic.** A notebook cell is the easiest
place in the world to paste something that works. A second implementation of the retry
policy, the budget check or the verifier feedback living in a cell would be exactly the
defect this project is about — declared in one place, enforced in another — and nothing
would fail. `tests/test_notebooks.py` bans function and class definitions, `while` loops,
and direct imports of a vendor SDK.

That rule earned its keep while these were being written. `02` originally called
`judge(l2, item)` on a verified run and raised `AttributeError: 'VerifiedAttempt' object
has no attribute 'model_call_failed'` — because verified runs go through `as_agent_run`
first, so that ONE judge scores both arms. The notebook was skipping an adapter that
exists precisely so two scoring paths cannot drift. It failed loudly, which is the point.

**They are committed with every output cleared.** A notebook carrying stored outputs
shows a reader numbers computed on somebody else's machine on some other day, in a
document that looks live. That is the stored-measurement-passing-as-fresh defect with an
`In [12]:` prompt in front of it — the thing this repository deleted an entire render
path to be rid of — and it must not come back through a file format. The test asserts
every code cell has empty `outputs` and a null `execution_count`.

Clear them before committing:

```bash
uv run --extra notebooks jupyter nbconvert --clear-output --inplace notebooks/*.ipynb
```
