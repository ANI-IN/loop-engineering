"""Load a pack's Python folder (such as data_generator/) as a package, and its benchmark.

Every function reads the selected pack (DATAPILOT_PACK) unless it is given another pack's name.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import yaml

from datapilot.config import PACKS, active_pack
from datapilot.contracts import BenchmarkItem, KnowledgeVersion


def pack_root(pack: str | None = None) -> Path:
    return PACKS / (pack or active_pack())


def load_package(folder: str, pack: str | None = None) -> ModuleType:
    """Import platform/packs/<pack>/<folder>/ under the name datapilot_pack_<pack>_<folder>."""
    pack = pack or active_pack()
    name = f"datapilot_pack_{pack}_{folder}"
    if name in sys.modules:
        return sys.modules[name]
    init = pack_root(pack) / folder / "__init__.py"
    if not init.is_file():
        raise ImportError(f"the pack {pack} has no {folder}/ folder ({init} does not exist)")
    spec = importlib.util.spec_from_file_location(
        name, init, submodule_search_locations=[str(init.parent)]
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {init}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_submodule(folder: str, submodule: str, pack: str | None = None) -> ModuleType:
    package = load_package(folder, pack)
    return importlib.import_module(f"{package.__name__}.{submodule}")


def load_benchmark(pack: str | None = None) -> list[BenchmarkItem]:
    """Every item in benchmark/*.yaml, in file order then item order."""
    items: list[BenchmarkItem] = []
    for path in sorted((pack_root(pack) / "benchmark").glob("*.yaml")):
        for raw in yaml.safe_load(path.read_text(encoding="utf-8")) or []:
            items.append(BenchmarkItem.model_validate(raw))
    return items


def load_knowledge(version: str, pack: str | None = None) -> KnowledgeVersion:
    path = pack_root(pack) / "knowledge" / f"{version}.yaml"
    return KnowledgeVersion.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
