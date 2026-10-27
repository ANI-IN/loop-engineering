"""The api and datapilot.contracts.api agree: every route is in ENDPOINTS with the same models, and
no request or response model is defined anywhere else (no database, zero tokens)."""

from __future__ import annotations

import ast

import pytest
from fastapi.routing import APIRoute
from pydantic import ValidationError

from datapilot.contracts import api as contract
from datapilot.loop3_events.api import control, demo, events, improve, runs
from datapilot.loop3_events.api.app import app
from datapilot.settings import PLATFORM


def _routes() -> dict[tuple[str, str], APIRoute]:
    found = {}
    routers = (events.api, runs.api, control.api, improve.api, demo.api)
    for route in [*app.routes, *(r for router in routers for r in router.routes)]:
        if isinstance(route, APIRoute) and not route.path.startswith(("/docs", "/openapi")):
            for method in route.methods - {"HEAD", "OPTIONS"}:
                found[(method, route.path)] = route
    return found


def _request_model(route: APIRoute) -> type | None:
    params = route.dependant.body_params
    return params[0].field_info.annotation if params else None


def test_every_route_is_in_the_endpoint_table_with_its_models() -> None:
    routes = _routes()
    table = {(e.method, e.path): e for e in contract.ENDPOINTS}
    assert set(routes) == set(table)
    for key, route in routes.items():
        assert route.response_model is table[key].response, key
        assert _request_model(route) is table[key].request, key


def test_endpoint_lookup_resolves_concrete_paths() -> None:
    assert contract.endpoint("GET", "/runs/123e4567-e89b-12d3-a456-426614174000").response is (
        contract.RunDetail
    )
    assert contract.endpoint("get", "/runs?limit=5").response is contract.RunList
    assert (
        contract.endpoint("POST", "/knowledge/v2/approve").request is contract.KnowledgeApprovalIn
    )


def test_no_api_model_is_defined_outside_the_contract() -> None:
    defined = []
    for path in (PLATFORM / "src" / "datapilot" / "loop3_events").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = {getattr(b, "id", getattr(b, "attr", "")) for b in node.bases}
                if "BaseModel" in bases:
                    defined.append(f"{path.name}: {node.name}")
    assert defined == []


def test_every_model_in_the_table_is_documented_in_the_module() -> None:
    doc = contract.__doc__ or ""
    for entry in contract.ENDPOINTS:
        assert f"| {entry.method} | {entry.path} |" in doc, entry.path
        assert entry.response.__name__ in doc
        if entry.request is not None:
            assert entry.request.__name__ in doc


@pytest.mark.parametrize("name", ["", "   ", "console", "CONSOLE"])
def test_a_knowledge_approval_needs_a_persons_name(name: str) -> None:
    """Owner's decision, 27 October 2026: no default approver; an empty name or "console" is
    refused before anything is stored (the api answers 422)."""
    with pytest.raises(ValidationError, match="a person's name"):
        contract.KnowledgeApprovalIn(approved_by=name)
    with pytest.raises(ValidationError):
        contract.KnowledgeApprovalIn()


def test_a_knowledge_approval_keeps_the_name_as_given_without_its_spaces() -> None:
    assert contract.KnowledgeApprovalIn(approved_by=" Priya ").approved_by == "Priya"
