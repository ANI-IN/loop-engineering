"""The only module that reads planted-item flags. Every flag must be in the planted registry."""

from __future__ import annotations

import os

from datapilot.contracts import registries

_ON = {"1", "true", "yes", "on"}


def planted(flag: str) -> bool:
    """True when a planted code bug or demo aid is switched on. An unknown flag is a bug here,
    not a silent False, so a typo cannot hide a planted branch."""
    known = set(registries.planted().flags) | {"DEMO_PACING"}
    if flag not in known:
        raise KeyError(f"{flag} is not in platform/planted/registry.yaml")
    return os.environ.get(flag, "0").strip().lower() in _ON


def active() -> list[str]:
    """The flags that are on now, for run metadata and the console chips."""
    return [flag for flag in [*registries.planted().flags, "DEMO_PACING"] if planted(flag)]
