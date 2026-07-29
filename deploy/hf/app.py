"""Hugging Face Space entry point. A frozen exhibit that makes zero model calls.

Spaces have an ephemeral filesystem and sleep on the free tier, so the warehouse is
regenerated from the deterministic seed at startup — it takes a fraction of a second,
which keeps *.duckdb out of git — and then its content checksum is asserted against the
one the measurements were taken against. A Space silently serving different data would
make every figure on the page wrong in a way nobody could see.

No API keys are set for this Space. It does not need them, and a public Space holding a
working key means unbounded spend by strangers.

The Space runs on cpu-basic. It has no @spaces.GPU function because it does no
inference at all, and ZeroGPU hardware tears down a container that never declares one.
"""

import os
import sys
from pathlib import Path

# Two layouts share this file. In the repo it lives at deploy/hf/app.py with src/ two
# levels up; on the Space it sits at the root with src/ beside it. Resolve rather than
# assume, because getting it wrong fails at import with a traceback nobody can act on.
HERE = Path(__file__).resolve().parent
ROOT = next(
    (candidate for candidate in (HERE, HERE.parents[1]) if (candidate / "src").is_dir()),
    HERE,
)
sys.path.insert(0, str(ROOT / "src"))

# The exhibit touches no live path, but settings still validate on import, so give them
# something syntactically valid rather than leaving a half-configured process.
os.environ.setdefault("ANTHROPIC_API_KEY", "exhibit-no-live-calls")
os.environ.setdefault("LANGSMITH_API_KEY", "exhibit-no-live-calls")
os.environ.setdefault("LANGSMITH_TRACING", "false")
os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

import gradio as gr  # noqa: E402

from loopeng.gold.build import build_gold  # noqa: E402
from loopeng.views.chrome import CONCURRENCY_LIMIT, MAX_QUEUE_SIZE, PROJECTOR_CSS  # noqa: E402
from loopeng.views.exhibit import build_exhibit_app  # noqa: E402
from loopeng.warehouse.connect import ensure_warehouse  # noqa: E402
from loopeng.warehouse.expected import assert_matches  # noqa: E402

WAREHOUSE = Path(os.environ.get("LOOPENG_WAREHOUSE", "/tmp/loopeng_warehouse.duckdb"))
SEED = int(os.environ.get("WAREHOUSE_SEED", "20260729"))


def build() -> "gr.Blocks":
    print("regenerating the warehouse from seed…", flush=True)
    ensure_warehouse(WAREHOUSE, seed=SEED)
    checksum = assert_matches(WAREHOUSE)
    print(f"warehouse verified: {checksum[:16]}…", flush=True)

    items = build_gold(WAREHOUSE)
    print(f"gold set rebuilt: {len(items)} items", flush=True)

    # There is deliberately no results/sweep on the Space: live cell output never
    # ships, so DIAL renders reference cells only and nothing can pass for fresh.
    app = build_exhibit_app(ROOT / "results" / "sweep", items, WAREHOUSE)
    app.queue(default_concurrency_limit=CONCURRENCY_LIMIT, max_size=MAX_QUEUE_SIZE)
    return app


# Spaces looks for a module-level `demo` and launches it itself. Building at import
# rather than under __main__ is what the platform expects; without it the log says
# "Launching demo not found in __main__" and the process is torn down.
demo = build()

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, css=PROJECTOR_CSS)
