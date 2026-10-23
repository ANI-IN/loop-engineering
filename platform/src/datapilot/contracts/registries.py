"""Schemas and loaders for the two registries that drive generated docs, make targets, and the
console: platform/demos/registry.yaml and platform/planted/registry.yaml."""

from __future__ import annotations

import re
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from datapilot.names import SECTIONS_BY_SLUG
from datapilot.settings import PLATFORM

DEMOS_FILE = PLATFORM / "demos" / "registry.yaml"
PLANTED_FILE = PLATFORM / "planted" / "registry.yaml"

_SLUG = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)+$")
_FLAG = re.compile(r"^BUG_[A-Z0-9_]+$")


class Tier(StrEnum):
    CORE = "core"
    OPTIONAL = "optional"


class CodeRef(BaseModel):
    path: str
    lines: str = Field(pattern=r"^\d+-\d+$")


class Trigger(BaseModel):
    console: str  # "<page> > <control label>"
    make: str
    api: str | None = None


class Demo(BaseModel):
    id: str
    section: str
    title: str
    tier: Tier
    trigger: Trigger
    planted: list[str] = Field(default_factory=list)
    guaranteed_moment: str
    expected_outcome: str
    can_vary: list[str]
    target_minutes: float = Field(gt=0)
    code: list[CodeRef] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _slug(cls, value: str) -> str:
        if not _SLUG.match(value):
            raise ValueError(
                f"demo id {value!r} must be a readable slug, such as agent-simple-question"
            )
        return value

    @field_validator("section")
    @classmethod
    def _section(cls, value: str) -> str:
        if value not in SECTIONS_BY_SLUG:
            raise ValueError(f"unknown section {value!r}; use one of {sorted(SECTIONS_BY_SLUG)}")
        return value

    @model_validator(mode="after")
    def _make_matches_id(self) -> Demo:
        if self.trigger.make != f"make demo NAME={self.id}":
            raise ValueError(f"{self.id}: trigger.make must be 'make demo NAME={self.id}'")
        return self

    @property
    def reset(self) -> str:
        return f"make reset NAME={self.section}"


class PlantedKind(StrEnum):
    CODE_BUG = "code_bug"
    HARNESS_WEAKNESS = "harness_weakness"
    DATA_CONDITION = "data_condition"
    DEMO_AID = "demo_aid"


class PlantedItem(BaseModel):
    id: str  # an env var for code bugs and demo aids; a slug for the others
    name: str  # the prose name, such as "the naive guard"
    chip: str  # the console chip label, sentence case, such as "Naive guard"
    kind: PlantedKind
    section: str
    location: str
    trigger: str
    symptom: str
    fix: str
    demos: list[str] = Field(default_factory=list)
    optional: bool = False

    @model_validator(mode="after")
    def _id_form(self) -> PlantedItem:
        if self.kind is PlantedKind.CODE_BUG and not _FLAG.match(self.id):
            raise ValueError(f"code bug {self.id!r} must be a BUG_* environment variable")
        if self.section not in SECTIONS_BY_SLUG:
            raise ValueError(f"{self.id}: unknown section {self.section!r}")
        return self


class DemoRegistry(BaseModel):
    demos: list[Demo]

    @model_validator(mode="after")
    def _unique(self) -> DemoRegistry:
        ids = [d.id for d in self.demos]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            raise ValueError(f"duplicate demo ids: {duplicates}")
        return self

    def by_id(self, demo_id: str) -> Demo:
        for demo in self.demos:
            if demo.id == demo_id:
                return demo
        raise KeyError(f"no demo named {demo_id!r}; `make demos` lists them")

    def for_section(self, slug: str) -> list[Demo]:
        return [d for d in self.demos if d.section == slug]


class PlantedRegistry(BaseModel):
    items: list[PlantedItem]

    def by_id(self, item_id: str) -> PlantedItem:
        for item in self.items:
            if item.id == item_id:
                return item
        raise KeyError(f"no planted item {item_id!r} in {PLANTED_FILE.name}")

    @property
    def flags(self) -> list[str]:
        return [i.id for i in self.items if _FLAG.match(i.id)]


def _read(path: Path) -> object:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def demos(path: Path = DEMOS_FILE) -> DemoRegistry:
    return DemoRegistry.model_validate({"demos": _read(path)})


@lru_cache(maxsize=1)
def planted(path: Path = PLANTED_FILE) -> PlantedRegistry:
    return PlantedRegistry.model_validate({"items": _read(path)})


def cross_check(demo_registry: DemoRegistry, planted_registry: PlantedRegistry) -> list[str]:
    """Every planted id a demo names exists, and every demo a planted item names exists."""
    problems = []
    demo_ids = {d.id for d in demo_registry.demos}
    planted_ids = {i.id for i in planted_registry.items}
    for demo in demo_registry.demos:
        problems += [
            f"{demo.id}: unknown planted item {p}" for p in demo.planted if p not in planted_ids
        ]
    for item in planted_registry.items:
        problems += [f"{item.id}: unknown demo {d}" for d in item.demos if d not in demo_ids]
    return problems
