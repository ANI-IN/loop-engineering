"""Does a killed LangSmith experiment resume, or does it re-run everything?

Phase 3's resume-from-last-completed-cell requirement rests on the answer, and
finding out then is too late. So: run a 5-item experiment, kill it midway, restart
it against the same experiment, and print exactly what happened at every step. The
raw output is the deliverable — "it resumed correctly" is the claim this probe
exists to distrust.

The target deliberately does not call a model. Resumability is a property of
LangSmith's experiment bookkeeping, not of the thing being evaluated, so paying for
inference here would buy nothing. It sleeps instead, which also makes the midpoint
easy to hit with a kill.

It is kept because its output is committed: `results/_resume_first.log` and
`results/_resume_marker.txt` are cited as the evidence behind the resume-from-disk
decision, and evidence with no reproducible provenance is an assertion.

Usage:
    uv run python tools/resumability_probe.py first   <experiment-name>
    uv run python tools/resumability_probe.py resume  <experiment-name>
    uv run python tools/resumability_probe.py inspect <experiment-name>
"""

import sys
import time
from pathlib import Path

from langsmith import Client, evaluate

from loopeng.langsmith_ds import (
    DATASET_NAME,
    LANGSMITH_KEY_VAR,
    credential,
    warn_not_configured,
)

MARKER = Path("results/_resume_marker.txt")
SLEEP_SECONDS = 6.0


def _client() -> Client:
    """The LangSmith client, or a refusal that names the variable.

    This probe is the one place in the repo that genuinely cannot degrade: it measures
    LangSmith's own resume behaviour, so there is nothing to fall back to. It says that
    rather than failing on an attribute of None.
    """
    api_key = credential()
    if api_key is None:
        warn_not_configured("resumability_probe")
        raise SystemExit(
            f"{LANGSMITH_KEY_VAR} is not set, and this probe measures LangSmith itself, "
            f"so there is nothing for it to degrade to.\n"
            f"Add {LANGSMITH_KEY_VAR}=<your key> to .env (see .env.example), or skip "
            f"this probe — nothing else in the repo needs it, and the finding it "
            f"produced is committed at results/_resume_first.log."
        )
    return Client(api_key=api_key)


def target(inputs: dict) -> dict:
    """Slow, deterministic, free. Records every invocation to a local file so we can
    tell what LangSmith actually re-ran, independently of what it reports."""
    question = inputs.get("question", "")
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    with MARKER.open("a", encoding="utf-8") as handle:
        handle.write(f"{time.time():.3f}\tINVOKED\t{question[:70]}\n")
    print(f"  [target] invoked: {question[:70]}", flush=True)
    time.sleep(SLEEP_SECONDS)
    return {"rows": [[0]]}


def _five_examples(client):
    examples = list(client.list_examples(dataset_name=DATASET_NAME, limit=5))
    print(f"  using {len(examples)} examples from {DATASET_NAME}", flush=True)
    return examples


def run_first(experiment_name: str) -> None:
    client = _client()
    print(f"[first] starting experiment {experiment_name!r}", flush=True)
    evaluate(
        target,
        data=_five_examples(client),
        client=client,
        experiment_prefix=experiment_name,
        max_concurrency=1,
        blocking=True,
    )
    print("[first] completed without being killed", flush=True)


def run_resume(experiment_name: str) -> None:
    """Restart against the SAME experiment, which is what a resume would mean."""
    client = _client()
    print(f"[resume] reattaching to experiment {experiment_name!r}", flush=True)
    evaluate(
        target,
        data=_five_examples(client),
        client=client,
        experiment=experiment_name,
        max_concurrency=1,
        blocking=True,
    )
    print("[resume] completed", flush=True)


def inspect(experiment_name: str) -> None:
    """Count what LangSmith holds for this experiment, from its side."""
    client = _client()
    try:
        runs = list(client.list_runs(project_name=experiment_name, is_root=True))
    except Exception as exc:  # noqa: BLE001 - probe output, not control flow
        print(f"[inspect] could not list runs: {type(exc).__name__}: {exc}", flush=True)
        return

    print(f"[inspect] experiment {experiment_name!r}: {len(runs)} root runs", flush=True)
    for run in runs:
        question = (run.inputs or {}).get("question", "")
        if isinstance(question, dict):
            question = question.get("question", "")
        print(
            f"    {run.status:10s} {str(run.start_time)[:19]}  "
            f"err={bool(run.error)}  {str(question)[:52]}",
            flush=True,
        )

    local = MARKER.read_text(encoding="utf-8").splitlines() if MARKER.exists() else []
    print(f"[inspect] local target invocations recorded: {len(local)}", flush=True)
    for line in local:
        print(f"    {line}", flush=True)


if __name__ == "__main__":
    mode, name = sys.argv[1], sys.argv[2]
    {"first": run_first, "resume": run_resume, "inspect": inspect}[mode](name)
