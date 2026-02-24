# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

from .connections import open_core_db
from .reducer_queries import (
    get_call_edges,
    get_callable_overview,
    get_callsite_index_payload,
    get_class_methods,
    get_class_overview,
    get_dependency_edges,
    get_dependency_edges_payload,
    get_module_overview,
    get_module_overview_payload,
    get_snapshot_id,
    get_structural_index_hash,
    get_structural_index_payload,
    render_reducer_json as _render_json,
    strip_json_fence as _strip_json_fence,
)

__all__ = [
    "_render_json",
    "_strip_json_fence",
    "get_call_edges",
    "get_callable_overview",
    "get_callsite_index_payload",
    "get_class_methods",
    "get_class_overview",
    "get_dependency_edges",
    "get_dependency_edges_payload",
    "get_module_overview",
    "get_module_overview_payload",
    "get_snapshot_id",
    "get_structural_index_hash",
    "get_structural_index_payload",
    "open_core_db",
]
