# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Symbol reference reducer."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from ...helpers.artifact_graph_edges import artifact_db_available, load_artifact_edges
from ...helpers.render import render_json_payload, require_connection
from ...helpers.utils import require_latest_committed_snapshot
from ...metadata import ReducerMeta

_NODE_TYPES = {"module", "classifier", "callable"}

def _normalize_kind(kind: Optional[str]) -> Sequence[str]:
    if not kind:
        return tuple(sorted(_NODE_TYPES))
    normalized = str(kind).strip().lower()
    if normalized in {"any", "all"}:
        return tuple(sorted(_NODE_TYPES))
    if normalized == "callable":
        return ("callable",)
    if normalized in {"function", "method"}:
        return ("callable",)
    if normalized == "class":
        return ("classifier",)
    if normalized in _NODE_TYPES:
        return (normalized,)
    raise ValueError(f"Unknown kind '{kind}'.")

def _normalize_limit(limit: int | str | None) -> int:
    if limit is None:
        return 20
    try:
        value = int(limit)
    except (TypeError, ValueError):
        raise ValueError("symbol_references limit must be an integer.")
    if value <= 0:
        raise ValueError("symbol_references limit must be positive.")
    return min(value, 200)
