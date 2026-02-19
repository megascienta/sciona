# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Dependency edge reducer."""

from __future__ import annotations

from ._internal.dependency_edges_main import REDUCER_META, render
from ._internal.dependency_edges_normalize import (
    _normalize_direction,
    _normalize_edge_type,
    _normalize_limit,
)
from ._internal.dependency_edges_resolve import (
    _node_lookup,
    _resolve_module_ids,
    _resolve_module_query,
)
from ._internal.dependency_edges_fetch import _fetch_dependency_edges, _fetch_edges

__all__ = [
    "REDUCER_META",
    "render",
    "_normalize_direction",
    "_normalize_edge_type",
    "_normalize_limit",
    "_node_lookup",
    "_resolve_module_ids",
    "_resolve_module_query",
    "_fetch_dependency_edges",
    "_fetch_edges",
]
