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
    """The LangSmith key, or None when it is not configured. Never the secret in a log."""
    key = load_settings().langsmith_api_key
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
            description=(
                "Phase 0 gold set: 50 items, 10 patterns x 5 parameterisations. "
                "Questions are phrased without rule vocabulary; the rules are "
                "supplied at L3 only."
            ),
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
