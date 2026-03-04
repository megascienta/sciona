# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Structural index reducer."""

from __future__ import annotations

from ._internal.structural_index_main import REDUCER_META, render, run
from ._internal.structural_index_entries import (
    TYPE_NODE_TYPES,
    CALLABLE_NODE_TYPES,
    _module_summaries,
    _file_entries,
    _class_entries,
    _callable_stats,
    _count_to_entries,
)
from ._internal.structural_index_graph import (
    _ModuleGraph,
    _build_module_graph,
    _import_edges,
    _import_cycles,
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
