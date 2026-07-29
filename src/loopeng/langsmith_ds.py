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
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import structlog

from loopeng.settings import load_settings

log = structlog.get_logger(__name__)

DATASET_NAME = "loop-eng-gold-v1"


@dataclass(frozen=True)
class TraceResult:
    """What a LangSmith side-effect produced, and whether it worked.

    `ok=False` is a normal outcome, not an exception. The caller records the reason
    and carries on, because the measured result does not depend on this succeeding.
    """

    ok: bool
    value: Any = None
    error: str | None = None


def _client():
    from langsmith import Client

    settings = load_settings()
    return Client(api_key=settings.langsmith_api_key.get_secret_value())


def advisory(operation: str, fn: Callable[[], Any]) -> TraceResult:
    """Run a LangSmith side-effect. Never let its failure reach the caller.

    Broad by design. The point is that *no* LangSmith failure — auth, transport,
    rate limit, schema change in a version we did not pin — can take down a sweep
    whose results live in results/*.json.
    """
    try:
        return TraceResult(ok=True, value=fn())
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
