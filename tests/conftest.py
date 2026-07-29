"""Suite-wide guarantees.

The offline suite must make zero network calls. The LangSmith SDK does not ask —
it enables itself from environment variables, so a developer machine (or a CI
runner, or a laptop that ran the sweep yesterday) with LANGSMITH_TRACING exported
would have every ordinary pytest run attempting background sends. That failure is
quiet: tests still pass, the network traffic is asynchronous, and the zero-network
property is gone without anything saying so.

So tracing is forced off for every test that is not marked `live`.
"""

import os

import pytest

# Both the current name and the LangChain-era one. The SDK honours either.
_TRACING_VARS = (
    "LANGSMITH_TRACING",
    "LANGSMITH_TRACING_V2",
    "LANGCHAIN_TRACING_V2",
    "LANGCHAIN_TRACING",
)


@pytest.fixture(autouse=True)
def _tracing_off_unless_live(request, monkeypatch):
    if request.node.get_closest_marker("live"):
        return
    for var in _TRACING_VARS:
        monkeypatch.setenv(var, "false")
    # LANGSMITH_ENDPOINT pointing somewhere real is harmless with tracing off, but
    # unsetting it removes the last way a stray client could reach the network.
    monkeypatch.delenv("LANGSMITH_ENDPOINT", raising=False)


@pytest.fixture
def tracing_env_snapshot():
    return {var: os.environ.get(var) for var in _TRACING_VARS}
