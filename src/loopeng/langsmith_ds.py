"""LangSmith dataset upload and the resumability probe.

**LangSmith is advisory, never the system of record.** `results/*.json` is
authoritative. A sweep must complete correctly with LangSmith unreachable: a network
failure degrades trace links and loses nothing measured. That is enforced by a test
which runs a cell with the client stubbed to raise and asserts the results file is
still complete and correct.

The practical shape of that rule: every call into this module is wrapped so a
transport failure returns a null result instead of propagating. It is deliberately
*not* a bare `except Exception` around business logic — the failures being swallowed
are network failures around a reporting side-effect, and the reason each one is safe
to swallow is that nothing downstream reads from LangSmith.

**An absent LANGSMITH_API_KEY is one of those failures, not a startup error.** It used
to be a required setting, which made the advisory promise above false — a checkout with
a working ANTHROPIC_API_KEY and no LangSmith key could not start, and the public exhibit
had to inject a fake value to get past its own settings validation. Now the key is
optional and its absence degrades to a no-op with a single warning naming the variable.
The measurements are unaffected, which is the whole claim.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import structlog

from loopeng.settings import load_settings

log = structlog.get_logger(__name__)

DATASET_NAME = "loop-eng-gold-v1"

LANGSMITH_KEY_VAR = "LANGSMITH_API_KEY"

# Warned once per process, not once per call. An advisory subsystem that is switched off
# should say so on the way past and then be quiet: a sweep uploads and traces repeatedly,
# and a per-call warning would bury the cell progress it is meant to sit beside.
_warned_absent = False


class LangSmithNotConfigured(RuntimeError):
    """LANGSMITH_API_KEY is absent, so there is nothing to talk to.

    Raised from `_client()` rather than checked in `advisory()` on purpose: a test that
    substitutes the client must still exercise the real failure path, and a check above
    the substitution point would short-circuit it.
    """


@dataclass(frozen=True)
class TraceResult:
    """What a LangSmith side-effect produced, and whether it worked.

    `ok=False` is a normal outcome, not an exception. The caller records the reason
    and carries on, because the measured result does not depend on this succeeding.
    """

    ok: bool
    value: Any = None
    error: str | None = None


def credential() -> str | None:
    """The LangSmith key, or None when it is not configured. Never the secret in a log.

    `require_credential=False` is load-bearing, not a shortcut. Whether tracing is
    available has nothing to do with whether the MODEL credentials are present, and
    reading them through the strict door would make a checkout with no OpenAI key
    report `OPENAI_API_KEY is not set` from the tracing subsystem — a message naming
    the wrong variable, raised by the one part of the system §15 promises is never
    load-bearing.

    That coupling arrived with the second vendor: `load_settings()` began requiring
    two keys instead of one, and this call site inherited a dependency it never
    wanted. The check has not moved; every site that SPENDS still goes through
    `require_key`.
    """
    key = load_settings(require_credential=False).langsmith_api_key
    return key.get_secret_value() if key is not None else None


def warn_not_configured(operation: str) -> None:
    """One structured warning per process, naming the variable and what degrades."""
    global _warned_absent
    if _warned_absent:
        return
    _warned_absent = True
    log.warning(
        "langsmith_not_configured",
        variable=LANGSMITH_KEY_VAR,
        operation=operation,
        degrades="trace links, dataset upload, the resumability probe",
        unaffected="results/*.json, which is the system of record",
        fix=f"Add {LANGSMITH_KEY_VAR}=<your key> to .env to turn tracing back on.",
    )


def _client():
    from langsmith import Client

    api_key = credential()
    if api_key is None:
        warn_not_configured("client")
        raise LangSmithNotConfigured(
            f"{LANGSMITH_KEY_VAR} is not set. Tracing is advisory, so this degrades to "
            f"a no-op; nothing measured depends on it."
        )
    return Client(api_key=api_key)


def advisory(operation: str, fn: Callable[[], Any]) -> TraceResult:
    """Run a LangSmith side-effect. Never let its failure reach the caller.

    Broad by design. The point is that *no* LangSmith failure — auth, transport,
    rate limit, schema change in a version we did not pin — can take down a sweep
    whose results live in results/*.json.
    """
    try:
        return TraceResult(ok=True, value=fn())
    except LangSmithNotConfigured as exc:
        # Already warned once, by name, at the point of detection. Not re-logged per
        # operation: "not configured" is a standing condition, not an incident.
        return TraceResult(ok=False, error=f"{type(exc).__name__}: {exc}")
    except Exception as exc:  # noqa: BLE001 - see docstring
        log.warning("langsmith_unavailable", operation=operation, error=str(exc))
        return TraceResult(ok=False, error=f"{type(exc).__name__}: {exc}")


def dataset_url(dataset_id: str) -> str:
    return f"https://smith.langchain.com/datasets/{dataset_id}"


def _dataset_description(items: list) -> str:
    """Derived from the items, never typed.

    It read "50 items, 10 patterns x 5 parameterisations" for the whole life of the
    file, including after the set was widened — a description on a shared dataset
    stating a shape it no longer had.
    """
    from loopeng.gold.build import clustering_summary

    shape = clustering_summary(items)
    return (
        f"{shape['n_items']} gold items in {shape['n_clusters']} clusters. "
        f"Questions are phrased without rule vocabulary; the rules are supplied at "
        f"L3 only. {shape['caveat']}"
    )


def upload_gold(items: list, *, dataset_name: str = DATASET_NAME) -> TraceResult:
    """Create or replace the gold dataset. Returns a TraceResult, never raises.

    The gold answer is uploaded as dataset *output* and the question as *input*.
    Naive answers are attached as metadata rather than outputs: they are not what a
    correct run should produce, and an evaluator that could read them as expected
    values would be scoring against the wrong target.
    """

    def _upload():
        client = _client()
        if client.has_dataset(dataset_name=dataset_name):
            client.delete_dataset(dataset_name=dataset_name)
        dataset = client.create_dataset(
            dataset_name=dataset_name,
            description=_dataset_description(items),
        )
        client.create_examples(
            dataset_id=dataset.id,
            inputs=[{"question": item.question} for item in items],
            outputs=[{"rows": item.gold_rows} for item in items],
            metadata=[
                {
                    "item_id": item.item_id,
                    "pattern_key": item.pattern_key,
                    "rules": list(item.rules),
                    "order_sensitive": item.order_sensitive,
                    "gold_sql": item.gold_sql,
                    "ambiguous_rule_groups": [list(g) for g in item.ambiguous_rule_groups],
                }
                for item in items
            ],
        )
        return {"dataset_id": str(dataset.id), "url": dataset_url(str(dataset.id))}

    return advisory("upload_gold", _upload)


# ---------------------------------------------------------------------------
# Per-item feedback
#
# Four scores were specified before the FX split was measured, and they do not
# carry the distinction that turned out to matter most. `signalled_missing_info`
# is the fifth, and without it the confabulate-versus-signal finding lives in the
# charts and not in the traces — which is the wrong way round, because the trace is
# where somebody goes to ask WHY a particular item scored the way it did.
#
# See docs/instrument-ranked-honesty-backwards.md.
# ---------------------------------------------------------------------------

# Every key this project writes. Enumerated rather than derived so a typo produces
# a missing score in a test rather than a second key in the LangSmith UI that looks
# like a real one and is empty.
FEEDBACK_KEYS = (
    "execution_accuracy",
    "rule_violation",
    "signalled_missing_info",
    "termination_reason",
    "cost_usd",
)


def feedback_scores(judgement, cost_usd: float) -> list[dict]:
    """The per-item feedback for one graded run, as create_feedback kwargs.

    Built as data rather than posted directly so the shape is testable without a
    network and without a key — which is the only way a test can assert that the
    fifth score is actually present on every item.

    `execution_accuracy` is 0.0 for an abstention, not absent. The model did not
    answer the question, and an absent score would quietly shrink the denominator
    of the accuracy metric — turning "declined" into "not asked", which flatters
    exactly the arm that declines most.

    An UNEARNED correct also scores 0.0, and carries a comment saying why. The
    number was right and the model could not have known it; scoring it as accuracy
    would record a guess that landed as knowledge, which is the one thing no
    accuracy metric can tell apart on its own.
    """
    from loopeng.agent.classify import Outcome

    outcome = judgement.outcome
    return [
        {
            "key": "execution_accuracy",
            "score": 1.0 if outcome is Outcome.CORRECT else 0.0,
            "comment": (
                "matched gold, but the value it needed was withheld at this prompt "
                "level — a guess that landed, scored 0 so it cannot pass as knowledge"
                if judgement.unearned else str(outcome)
            ),
        },
        {
            # A rule the answer can be attributed to. Not a gate — nothing here
            # decides whether a run passes; it sorts failures by cause.
            "key": "rule_violation",
            "score": 1.0 if judgement.attributed_rules else 0.0,
            "value": " or ".join(judgement.attributed_rules) or None,
            "comment": (
                "ambiguous: the item's variants are indistinguishable, so every "
                "rule in the group is named rather than one being picked"
                if judgement.ambiguous else None
            ),
        },
        {
            # The score the original spec had no field for.
            "key": "signalled_missing_info",
            "score": 1.0 if judgement.abstained else 0.0,
            "comment": (
                "named the input it was not given, in SQL, instead of inventing a "
                "value for it — an abstention, not a crash"
                if judgement.abstained else None
            ),
        },
        {"key": "termination_reason", "value": judgement.termination},
        {"key": "cost_usd", "score": float(cost_usd),
         "comment": "estimated: measured tokens times a hand-entered price table"},
    ]


def log_feedback(run_id, judgement, cost_usd: float) -> TraceResult:
    """Attach every score to one traced run. Advisory, like everything here."""

    def _log():
        client = _client()
        for entry in feedback_scores(judgement, cost_usd):
            client.create_feedback(run_id, **entry)
        return {"run_id": str(run_id), "n_scores": len(FEEDBACK_KEYS)}

    return advisory("log_feedback", _log)


# ---------------------------------------------------------------------------
# Versioned prompts
#
# The trap's two arms are the SAME prompt at two completeness levels, so they are
# two versions of one thing rather than two code paths. Pushing them as versioned
# prompts is what lets the experiment comparison view render the trap matrix
# natively, instead of it existing only as a local chart.
# ---------------------------------------------------------------------------

PROMPT_NAMES = {
    "L0": "loop-eng-rules-withheld",
    "L3": "loop-eng-rules-declared",
}


def push_prompts(levels=("L0", "L3")) -> TraceResult:
    """Push each prompt level as a named, versioned prompt.

    **This is the only place LangChain is imported, and the boundary is the point.**
    §15 records the decision not to use LangChain, and that decision is about the
    LOOPS — its rubric middleware scores with an LLM judge, which this project
    refuses as a blocking check, and its hill-climbing loop has an agent rewrite the
    harness config, where here a human moves one dial and re-measures.

    None of that is at stake in a serialisation format. `push_prompt` takes a
    langchain-core prompt object, so a prompt object is what it gets. A test asserts
    no module under `loopeng/agent/`, `loopeng/verify/` or `loopeng/sweep/` imports
    it, which is where the decision actually applies.
    """

    def _push():
        from langchain_core.prompts import ChatPromptTemplate

        from loopeng.prompts import render_prompt

        pushed = {}
        for level in levels:
            template = ChatPromptTemplate.from_messages([
                # The rendered prompt goes in verbatim, as a literal system message.
                # It is not a template with holes: the schema and the rules are
                # already resolved from semantic_model.yaml, and re-templating them
                # here would create a second place for a rule to live.
                ("system", render_prompt(level).replace("{", "{{").replace("}", "}}")),
                ("human", "Question: {question}"),
            ])
            pushed[level] = _client().push_prompt(
                PROMPT_NAMES[level],
                object=template,
                description=(
                    "Schema only — the business rules are withheld. The trap's "
                    "control arm." if level == "L0" else
                    "Schema plus every rule statement, rendered from "
                    "semantic_model.yaml. The trap's treatment arm."
                ),
            )
        return pushed

    return advisory("push_prompts", _push)


# ---------------------------------------------------------------------------
# The annotation queue
# ---------------------------------------------------------------------------

FX_QUEUE_NAME = "loop-eng-confabulate-or-signal"

# What the room is asked, and it is deliberately not "which is correct".
#
# Both answers are wrong by the automated metric. One invented a currency
# conversion rate and returned a clean plausible number; the other wrote the name
# of the rate it had not been given and failed to execute. The metric ranked the
# second one BELOW the first, and the vote is the demonstration that human judgment
# ranks them the other way round.
#
# Pairing A-vs-C outputs — the original plan — would have asked a generic question
# with a predictable answer. This asks the one the session is about.
FX_RUBRIC_INSTRUCTIONS = (
    "Both queries below are WRONG by the automated metric. Neither returns the "
    "right number.\n\n"
    "One invented a currency conversion rate it was never given and returned a "
    "clean, plausible figure. The other wrote the name of the rate it was missing "
    "and therefore did not run at all.\n\n"
    "You are not being asked which is correct. You are being asked: which would you "
    "rather have run against your warehouse, and shown to someone who will act on "
    "the number?"
)

FX_RUBRIC_ITEMS = [
    {
        "feedback_key": "prefer_in_production",
        "description": (
            "Which of these two would you rather have in a warehouse query?"
        ),
        "value_descriptions": {
            "invented_a_rate": "The one that returned a number, using a rate it made up.",
            "named_what_was_missing": "The one that said which input it did not have.",
            "no_preference": "Genuinely no preference between them.",
        },
        "is_required": True,
    },
    {
        "feedback_key": "would_have_noticed",
        "description": (
            "If this had run in production and nobody checked the SQL, would you "
            "have noticed the answer was wrong?"
        ),
        "score_descriptions": {
            "0": "No — it looks like every other number.",
            "1": "Yes — something about it would have been visible.",
        },
        "is_required": True,
    },
]


def create_fx_queue(name: str = FX_QUEUE_NAME) -> TraceResult:
    """The pairwise queue the room votes in, with its rubric.

    Capped by construction: the queue holds runs that already happened and costs
    nothing per rater. Nothing a rater can do here starts a model call — which is
    the property that makes it safe to put a link on a screen in front of thirty
    people.
    """

    def _create():
        client = _client()
        # Idempotent, because this is run before every session and a second run must
        # not fail on "already exists". Reusing the queue is also correct rather than
        # merely convenient: a fresh queue would drop the ratings already collected.
        existing = next(
            (q for q in client.list_annotation_queues() if q.name == name), None
        )
        if existing is not None:
            return {"queue_id": str(existing.id), "name": name, "reused": True}

        queue = client.create_annotation_queue(
            name=name,
            description=(
                "Two wrong answers to the same unanswerable question. The automated "
                "metric ranks the confabulation above the refusal; this asks whether "
                "people do."
            ),
            rubric_instructions=FX_RUBRIC_INSTRUCTIONS,
            rubric_items=FX_RUBRIC_ITEMS,
        )
        return {"queue_id": str(queue.id), "name": name, "reused": False}

    return advisory("create_fx_queue", _create)


def enqueue_for_rating(queue_id, run_ids) -> TraceResult:
    """Put finished runs in front of the room. Never starts a new one."""

    def _add():
        _client().add_runs_to_annotation_queue(queue_id, run_ids=list(run_ids))
        return {"queue_id": str(queue_id), "n_runs": len(list(run_ids))}

    return advisory("enqueue_for_rating", _add)


# ---------------------------------------------------------------------------
# Experiments
#
# One dataset, one experiment per arm, so LangSmith's built-in side-by-side
# comparison view works on them. That view is the shared surface the room already
# knows how to read, and it is worth more than a bespoke chart of the same numbers.
#
# **THE FOUR CONDITIONS ARE NOT THE TRAP MATRIX, and conflating them would put the
# wrong 2x2 on screen.** A, B, C and D vary the LOOPS and the MODEL at a fixed prompt
# level; the trap varies the PROMPT LEVEL at a fixed loop count. They are different
# axes and the comparison view cannot infer one from the other.
#
# So the trap gets its own two arms — the same single-shot configuration as A and D,
# run at L0 — and together with A and D they form the four cells of the matrix:
#
#                     L0 (withheld)        L3 (given)
#     agent           trap-agent-L0        A-baseline
#     reference       trap-reference-L0    D-reference
#
# Six experiments, not four, and the two extra ones are cheap on the agent side.
# ---------------------------------------------------------------------------

EXPERIMENT_PREFIX = "loop-eng"


def experiment_name(arm: str) -> str:
    """Stable, sortable, and readable in a list of a hundred projects."""
    return f"{EXPERIMENT_PREFIX}-{arm}"


def _evaluator_from(judgements: dict, costs: dict):
    """One evaluator returning every score, keyed by the item it graded.

    The grading has already happened — `loopeng.agent.classify` judged each run
    against gold while the arm was executing. This hands the result to LangSmith
    rather than re-deriving it, because a second grader is a second thing to disagree
    with the results file, and `results/` is the system of record.
    """

    def _scores(run, example):
        item_id = (example.metadata or {}).get("item_id")
        judgement = judgements.get(item_id)
        if judgement is None:
            return {"results": []}
        return {"results": feedback_scores(judgement, costs.get(item_id, 0.0))}

    return _scores


def run_experiment(arm: str, judgements: dict, costs: dict, outputs: dict, *,
                   dataset_name: str = DATASET_NAME, metadata: dict | None = None):
    """File an already-executed arm as a LangSmith experiment.

    The arm has run. Its results are on disk and are authoritative. This replays the
    per-item outputs into an experiment so the comparison view has something to
    compare — it never re-runs the model, which is why a LangSmith outage costs a
    view and not a measurement.
    """

    def _upload():
        from langsmith import evaluate

        def target(inputs, example=None):
            item_id = (example.metadata or {}).get("item_id") if example else None
            return outputs.get(item_id, {})

        # `client=` is not optional here, and finding that out cost a run.
        #
        # `evaluate` builds its own Client from the environment when none is given,
        # and this project's credential lives in `.env` — read by pydantic-settings,
        # never exported to `os.environ`. So every other call in this module worked
        # (they go through `_client()`, which reads settings) and `evaluate` alone
        # returned 401 Invalid token, on an account where the key was perfectly
        # valid.
        #
        # The failure was survivable because it is wrapped in `advisory`: six arms
        # executed, wrote their results, and reported the upload failure per arm. But
        # the diagnosis reads as "the key is wrong" when the key is right, which is
        # the kind of error message that sends an operator to the wrong file thirty
        # minutes before a session.
        return evaluate(
            target,
            data=dataset_name,
            evaluators=[_evaluator_from(judgements, costs)],
            experiment_prefix=experiment_name(arm),
            metadata={"arm": arm, **(metadata or {})},
            max_concurrency=4,
            client=_client(),
        )

    return advisory(f"run_experiment:{arm}", _upload)
