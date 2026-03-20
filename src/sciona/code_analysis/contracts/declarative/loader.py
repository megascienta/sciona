# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Helpers for loading declarative contract data."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


_CONTRACTS_ROOT = Path(__file__).resolve().parent


@lru_cache(maxsize=None)
def load_contract_json(filename: str) -> dict[str, object]:
    path = _CONTRACTS_ROOT / filename
    return json.loads(path.read_text(encoding="utf-8"))
