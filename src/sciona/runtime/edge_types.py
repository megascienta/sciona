# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Canonical edge-kind definitions shared across storage and reducers."""

from __future__ import annotations


CORE_STRUCTURAL_EDGE_TYPES = frozenset(
    {
        "CONTAINS",
        "DEFINES_METHOD",
        "IMPORTS_DECLARED",
        "CALLS",
        "NESTS",
        "EXTENDS",
        "IMPLEMENTS",
    }
)

MODULE_DEPENDENCY_EDGE_TYPES = frozenset({"IMPORTS_DECLARED"})


__all__ = ["CORE_STRUCTURAL_EDGE_TYPES", "MODULE_DEPENDENCY_EDGE_TYPES"]
