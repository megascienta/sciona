# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Core reducers."""

from __future__ import annotations

from . import (
    callable_overview,
    class_overview,
    class_inheritance,
    dependency_edges,
    file_outline,
    module_overview,
    snapshot_provenance,
    structural_index,
    symbol_lookup,
    symbol_references,
)

__all__ = [
    "callable_overview",
    "class_overview",
    "class_inheritance",
    "dependency_edges",
    "file_outline",
    "module_overview",
    "snapshot_provenance",
    "structural_index",
    "symbol_lookup",
    "symbol_references",
]
