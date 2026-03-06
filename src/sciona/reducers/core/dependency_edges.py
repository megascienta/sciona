# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Compatibility shim for dependency_edges reducer."""

from __future__ import annotations

from ..dependency_edges import (
    REDUCER_META,
    _fetch_dependency_edges,
    _fetch_edges,
    _node_lookup,
    _normalize_direction,
    _normalize_edge_type,
    _normalize_limit,
    _resolve_module_ids,
    _resolve_module_query,
    render,
)

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
