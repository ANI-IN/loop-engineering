"""The api contract check, reusable by any client.

`check_console_controls(send)` presses every console control in platform/demos/registry.yaml the
way `trigger.api` names it, builds every request from a datapilot.contracts.api model, and validates
every response against the endpoint table's response model. `send` is the only seam: a callable
(method, path, json body or None) -> (status code, decoded json). The loops track passes one over
FastAPI's TestClient; the console engineer passes one over the console's own api client.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from datapilot.contracts import api as contract
from datapilot.contracts import registries
from datapilot.contracts.registries import Demo
from datapilot.loop3_events import demos

Send = Callable[[str, str, dict[str, Any] | None], tuple[int, Any]]


class ContractError(AssertionError):
    pass


@dataclass
class Checked:
    """Every call the check made: (method, endpoint path, response model name)."""

    calls: list[tuple[str, str, str]] = field(default_factory=list)


class _Reply:
    def __init__(self, status: int, data: Any) -> None:
        self.status_code = status
        self._data = data

    def json(self) -> Any:
        return self._data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise ContractError(f"HTTP {self.status_code}: {self._data}")


class ContractClient:
    """The post/get interface the demo triggers use, validating both sides of every call."""

    def __init__(self, send: Send, checked: Checked) -> None:
        self.send = send
        self.checked = checked

    def call(self, method: str, url: str, body: dict[str, Any] | None = None) -> _Reply:
        entry = contract.endpoint(method, url)
        if entry.request is not None:
            entry.request.model_validate(body or {})
        elif body:
            raise ContractError(f"{method} {entry.path} takes no body, got {body}")
        status, data = self.send(method, url, body if entry.request is not None else None)
        if status < 400:
            entry.response.model_validate(data)
            self.checked.calls.append((method, entry.path, entry.response.__name__))
        return _Reply(status, data)

    def post(self, url: str, json: dict[str, Any] | None = None, **_kw: Any) -> _Reply:
        return self.call("POST", url, json)

    def get(self, url: str, params: dict[str, Any] | None = None, **_kw: Any) -> _Reply:
        query = "&".join(f"{k}={v}" for k, v in (params or {}).items())
        return self.call("GET", f"{url}?{query}" if query else url)


def console_controls() -> list[Demo]:
    """One demo per distinct (console control, api request) pair."""
    seen: dict[tuple[str, str], Demo] = {}
    for demo in registries.demos().demos:
        seen.setdefault((demo.trigger.console, demo.trigger.api or ""), demo)
    return list(seen.values())


def check_console_controls(send: Send) -> dict[str, Checked]:
    """Press every console control once; returns the validated calls per control."""
    results: dict[str, Checked] = {}
    for demo in console_controls():
        checked = Checked()
        client = ContractClient(send, checked)
        done = demos.trigger(client, demo, wait_running_seconds=0)
        for run_id in done.run_ids:
            client.get(f"/runs/{run_id}").raise_for_status()
        if done.request_ids:
            client.get("/improvement/requests").raise_for_status()
        for path in ("/control", "/runs", "/console/settings", "/health"):
            client.get(path).raise_for_status()  # what the status line and the board read
        release = contract.KillSwitchIn(action="release", by="contract test")
        client.post("/control/kill-switch", json=release.model_dump()).raise_for_status()
        results[demo.trigger.console] = checked
    return results
