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
