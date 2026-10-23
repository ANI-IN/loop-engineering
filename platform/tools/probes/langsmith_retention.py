"""LangSmith retention test: does an evaluate() experiment use extended (billed) traces?

Runs a 2-example experiment whose target is a plain function (no model call, no OpenAI spend),
adds one feedback with extend_trace_retention=False, then reads each run's trace tier back from
the API. Afterwards, compare with the usage page in LangSmith (Settings > Usage and billing).

    uv run python platform/tools/probes/langsmith_retention.py
"""

from __future__ import annotations

import time
import uuid

import httpx
from langsmith import Client, evaluate
from langsmith.run_helpers import get_current_run_tree

from datapilot.settings import get_settings

DATASET = "datapilot-retention-test"


def target(inputs: dict) -> dict:
    run = get_current_run_tree()
    return {"answer": inputs["question"].upper(), "run_id": str(run.id) if run else None}


def exact(outputs: dict, reference_outputs: dict) -> bool:
    return outputs["answer"] == reference_outputs["answer"]


def main() -> None:
    settings = get_settings()
    client = Client(
        api_key=settings.langsmith_api_key.get_secret_value(), api_url=settings.langsmith_endpoint
    )
    if client.has_dataset(dataset_name=DATASET):
        dataset = client.read_dataset(dataset_name=DATASET)
    else:
        dataset = client.create_dataset(DATASET, description="Retention test, two examples")
    if not list(client.list_examples(dataset_id=dataset.id, limit=1)):
        # The pinned langsmith 0.14.5 names reference outputs "outputs" in create_examples.
        client.create_examples(
            dataset_id=dataset.id,
            examples=[
                {"inputs": {"question": "one"}, "outputs": {"answer": "ONE"}},
                {"inputs": {"question": "two"}, "outputs": {"answer": "TWO"}},
            ],
        )
    prefix = f"retention-test-{uuid.uuid4().hex[:6]}"
    results = evaluate(
        target,
        data=DATASET,
        evaluators=[exact],
        experiment_prefix=prefix,
        max_concurrency=2,
        client=client,
    )
    rows = list(results)
    run_ids = [row["run"].id for row in rows]
    client.create_feedback(run_ids[0], key="retention-test", score=1, extend_trace_retention=False)
    time.sleep(10)  # let ingestion settle before reading the runs back
    # The SDK's run model does not expose the tier; the REST response does.
    headers = {"x-api-key": settings.langsmith_api_key.get_secret_value()}
    for run_id in run_ids:
        body = httpx.get(
            f"{settings.langsmith_endpoint}/api/v1/runs/{run_id}", headers=headers, timeout=30
        ).json()
        print(
            f"run {run_id}: trace_tier={body.get('trace_tier')} "
            f"ttl_seconds={body.get('ttl_seconds')} trace_upgrade={body.get('trace_upgrade')}"
        )
    print(f"experiment: {results.experiment_name} ({len(run_ids)} traces)")


if __name__ == "__main__":
    main()
