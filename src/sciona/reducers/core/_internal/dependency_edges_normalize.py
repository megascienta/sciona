# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Dependency edge reducer."""

from __future__ import annotations

from typing import Dict, List, Optional

from ...helpers.render import render_json_payload, require_connection
from ...helpers.utils import require_latest_committed_snapshot
from ...metadata import ReducerMeta
from ....runtime.edge_types import MODULE_DEPENDENCY_EDGE_TYPES

def _normalize_edge_type(edge_type: str | None) -> str | None:
    if edge_type is None:
        return "IMPORTS_DECLARED"
    normalized = str(edge_type).strip()
    if not normalized:
        return "IMPORTS_DECLARED"
    if normalized.lower() in {"any", "*"}:
        return None
    if normalized not in MODULE_DEPENDENCY_EDGE_TYPES:
        allowed = ", ".join(sorted(MODULE_DEPENDENCY_EDGE_TYPES))
        raise ValueError(
            f"dependency_edges edge_type must be one of: {allowed}, any, *."
        )
    return normalized

def _normalize_direction(direction: str | None) -> str:
    if not direction:
        return "both"
    value = str(direction).strip().lower()
    if value in {"in", "out", "both"}:
        return value
    raise ValueError("dependency_edges direction must be one of: in, out, both.")

def _normalize_limit(limit: int | str | None) -> int | None:
    if limit is None:
        return None
    try:
        value = int(limit)
    except (TypeError, ValueError):
        raise ValueError("dependency_edges limit must be an integer.")
    if value <= 0:
        raise ValueError("dependency_edges limit must be positive.")
    return min(value, 10000)
