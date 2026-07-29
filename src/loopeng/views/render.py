"""Every pure string renderer a view uses. No `gr.Blocks` in this file, ever.

ONE RULE, APPLIED
-----------------

**`views/` owns all Gradio composition. `*/ui.py` modules own none.** Before this file
there was no boundary at all, only two half-boundaries pointing at each other:

  - `build_trap_app` existed twice — `agent/ui.py` and `views/trap.py` — and the two had
    already drifted. Different outcome labels, different withheld-scores wording, one
    checking `len(state.arms) == 2` and the other `PAIRED_ARM_COUNT`, one rendering a
    null metric through a helper and the other inline.
  - `render_attempts` also existed twice, in `agent/ui.py` and `triage/ui.py`, as two
    genuinely DIFFERENT functions sharing a name — one takes an `AgentRun`, the other a
    recorded-run dict.
  - and `views/agent.py` imported from `agent/ui.py` while `views/oversight.py` imported
    from `triage/ui.py`, so the boundary was crossed in both directions.

Two copies of a renderer is two places for the wording of a disclosure to diverge, and
the trap's scoreboard is the screen where that matters most.

THE LABELS THAT SURVIVED, AND WHY
---------------------------------

The plain (non-emoji) variant won. `agent/ui.py` used `✅ correct` and
`🟥 **silently wrong**`; `views/trap.py` used `correct` and `**SILENTLY WRONG**`. Emoji
render at the mercy of whichever font the projector's browser resolves, and a missing
glyph in the cell that is supposed to read "silently wrong" is the single worst place in
this project for a rendering failure. Weight and capitals work everywhere.

The withheld-scores line is `views/trap.py`'s: *"Scores are already computed. They are
withheld, not deferred."* It states the property. The other version described the button.

The two `render_attempts` are now `render_attempt_timeline` (an AgentRun, for AGENT and
the Level 1 view) and `render_declined_run` (a recorded dict, for OVERSIGHT). Different
functions get different names.
"""

from loopeng.agent.classify import Outcome
from loopeng.agent.trap import TrapState, arm_key, arm_label
from loopeng.metric import Metric
from loopeng.paired import PAIRED_ARM_COUNT
from loopeng.triage.abstain import CONFIDENCE, decide, operating_point
from loopeng.views.chrome import NOT_MEASURED

# Identical for every landed cell, whatever happened inside it. A cell reading "query
# failed" before the reveal hands the room a free answer key for that row.
PENDING, LANDED = "·", "▪"

# Non-emoji, deliberately. See the module docstring.
OUTCOME_LABELS = {
    Outcome.CORRECT: "correct",
    Outcome.SILENT_ERROR: "**SILENTLY WRONG**",
    Outcome.VISIBLE_FAILURE: "visible failure",
}

WITHHELD = "_Scores are already computed. They are withheld, not deferred._"

NO_RUN_YET = "_no run yet_"


# ---- metrics and money -------------------------------------------------------


def render_metric(metric: Metric | None) -> str:
    """A missing measurement renders "not yet measured", never zero, never blank."""
    return metric.render() if metric else NOT_MEASURED


def render_cost(ledger) -> str:
    """Always the est. prefix. Tokens are measured; dollars are a price table."""
    total = ledger.cost_usd()
    tokens = ledger.totals()
    return (
        f"est. ${total:.4f} · {tokens['n_calls']} calls · "
        f"{tokens['total_tokens']} tokens (in {tokens['input_tokens']}, "
        f"out {tokens['output_tokens']}, cache-w {tokens['cache_creation_input_tokens']}, "
        f"cache-r {tokens['cache_read_input_tokens']})"
    )


# ---- the attempt timeline ----------------------------------------------------

ROWS_SHOWN = 5        # layout: rows of a result printed inline
SQL_SHOWN = 300       # layout: characters of a recorded result printed inline


def render_attempt_timeline(run) -> str:
    """One row per attempt, for an `AgentRun`.

    **A failed model call is never labelled `database said`.** It used to be: a typo'd
    API key rendered three attempts reading `database said: AuthenticationError`, which
    blames the warehouse for a credential problem and sends the reader to the wrong file.
    The two are told apart by `Attempt.model_call_failed`, which reads the recorded call
    outcome rather than guessing from an empty SQL string.
    """
    if run is None:
        return NO_RUN_YET
    lines = [f"**termination:** `{run.termination}` · **model:** `{run.model_id}`", ""]
    for attempt in run.attempts:
        if attempt.model_call_failed:
            lines.append(f"### Attempt {attempt.n} — the model call failed")
            lines.append(f"**the API said:** `{attempt.error}`")
            lines.append("")
            continue
        status = "ran" if attempt.executed else "failed to execute"
        lines.append(f"### Attempt {attempt.n} — {status}")
        lines.append(f"```sql\n{attempt.sql or '(no SQL returned)'}\n```")
        if attempt.error:
            lines.append(f"**database said:** `{attempt.error}`")
        elif attempt.rows is not None:
            lines.append(f"**returned:** `{attempt.rows[:ROWS_SHOWN]}`")
        lines.append("")
    return "\n".join(lines)


# ---- the trap grid and scoreboard --------------------------------------------


def grid(state: TrapState, item_ids: list[str]) -> str:
    labels = [arm_label(role, level) for role, level in state.arms]
    lines = ["| item | " + " | ".join(labels) + " |",
             "|---|" + "---|" * len(labels)]
    for item_id in item_ids:
        cells = []
        for role, level in state.arms:
            cell = state.cells.get((item_id, arm_key(role, level)))
            if not cell or not cell.done:
                cells.append(PENDING)
            elif not state.revealed:
                cells.append(LANDED)  # successes and failures look the same
            else:
                cells.append(OUTCOME_LABELS[cell.judgement.outcome])
        lines.append(f"| `{item_id}` | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def scoreboard(state: TrapState) -> str:
    if not state.revealed:
        return WITHHELD
    lines = []
    for role, level in state.arms:
        arm = arm_key(role, level)
        summary = state.summary(arm)
        lines.append(
            f"**{arm_label(role, level)}** — silent-error rate "
            f"{render_metric(state.silent_error_rate(arm))} over "
            f"{summary['n_ran_and_returned']} that ran · "
            f"visible failures {summary['n_visible_failures']} · "
            f"unclassified {summary['n_unclassified']}"
        )
    # McNemar is defined on exactly two arms. Named rather than a bare `== 2`, which at a
    # call site reads as an arbitrary arity check.
    if len(state.arms) == PAIRED_ARM_COUNT:
        paired = state.paired_comparison(arm_key(*state.arms[0]), arm_key(*state.arms[1]))
        lines.append(f"**Paired (McNemar exact):** {paired.render()}")
    return "\n\n".join(lines)


# ---- abstention and intervention ---------------------------------------------


def _threshold_label(threshold: float) -> str:
    names = [name for name, value in CONFIDENCE.items() if value >= threshold]
    return ", ".join(sorted(names)) or "nothing"


def render_declined(runs: list[dict], threshold: float) -> str:
    point = operating_point(runs, threshold)
    if not point["declined"]:
        return (
            f"**Nothing declined at threshold {threshold:.2f}.** "
            f"All {point['n_total']} questions were answered."
        )
    lines = [
        f"### {point['n_declined']} of {point['n_total']} questions declined",
        f"*Answered only when the run ends as: {_threshold_label(threshold)}*",
        "",
    ]
    for entry in point["declined"]:
        lines.append(f"**`{entry['item_id']}`** — {entry['reason']}")
        lines.append("")
    return "\n".join(lines)


def render_declined_run(run: dict) -> str:
    """What the operator inspects to decide whether a decline was fair.

    Named apart from `render_attempt_timeline` because it is a different function over a
    different input. The two shared the name `render_attempts` in two modules, which is
    how `views/agent.py` and `views/oversight.py` ended up importing "the same" helper
    from two different places.
    """
    if not run:
        return "_select a declined question_"
    decision = decide(run, 1.0)
    return "\n".join([
        f"### `{run['item_id']}`",
        f"**Why it was declined:** {decision.reason}",
        "",
        f"- ended as `{run.get('termination')}` after {run.get('n_attempts')} attempt(s)",
        f"- the verifier sent it back {run.get('rejections', 0)} time(s)",
        f"- confidence band: {decision.confidence:.2f}",
        "",
        "**Last query the model wrote:**",
        f"```sql\n{run.get('sql') or '(no SQL recorded)'}\n```",
        "",
        f"**What it returned:** `{str(run.get('rows'))[:SQL_SHOWN]}`",
        "",
        "_The gold answer is deliberately not shown here. An operator judging whether a "
        "decline was fair should be looking at the query and the reason, not at the "
        "answer key._",
    ])
