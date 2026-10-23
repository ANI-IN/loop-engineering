"""The pack configuration (platform/packs/<pack>/pack.yaml): limits, prices, budgets, models.

The pack is the DATAPILOT_PACK setting (datapilot_us when unset). Every component reads it through
`active_pack`, so one .env line moves the whole platform to another pack.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from datapilot.settings import PLATFORM, get_settings

PACKS = PLATFORM / "packs"


class UnknownPack(RuntimeError):
    pass


def active_pack() -> str:
    """The folder name under platform/packs/ of the selected pack."""
    return get_settings().datapilot_pack


def pack_config(pack: str | None = None, root: Path = PACKS) -> dict[str, Any]:
    return _load(pack or active_pack(), root)


@lru_cache(maxsize=8)
def _load(pack: str, root: Path) -> dict[str, Any]:
    path = root / pack / "pack.yaml"
    if not path.is_file():
        raise UnknownPack(f"no pack {pack!r}: {path} does not exist (check DATAPILOT_PACK)")
    return yaml.safe_load(path.read_text(encoding="utf-8"))
