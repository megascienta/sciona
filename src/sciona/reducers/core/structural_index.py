# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Compatibility shim for structural_index reducer."""

from __future__ import annotations

from ..structural_index import (
    CALLABLE_NODE_TYPES,
    REDUCER_META,
    TYPE_NODE_TYPES,
    _ModuleGraph,
    _build_module_graph,
    _callable_stats,
    _class_entries,
    _count_to_entries,
    _file_entries,
    _import_cycles,
    _import_edges,
    _module_summaries,
    render,
    run,
)

__all__ = [
    "REDUCER_META",
    "render",
    "run",
    "TYPE_NODE_TYPES",
    "CALLABLE_NODE_TYPES",
    "_module_summaries",
    "_file_entries",
    "_class_entries",
    "_callable_stats",
    "_count_to_entries",
    "_ModuleGraph",
    "_build_module_graph",
    "_import_edges",
    "_import_cycles",
]
