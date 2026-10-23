"""Puts the unit test folder on sys.path, so integration tests share its support modules
(loops_support, security_cases). Import it before them."""

from __future__ import annotations

import sys
from pathlib import Path

UNIT = str(Path(__file__).resolve().parents[1] / "unit")
if UNIT not in sys.path:
    sys.path.insert(0, UNIT)
