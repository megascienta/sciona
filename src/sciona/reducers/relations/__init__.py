# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Relations reducer namespace."""

from __future__ import annotations

from .. import callsite_index
from .. import classifier_call_graph_summary
from .. import dependency_edges
from .. import module_call_graph_summary
from .. import symbol_references

__all__ = [
    "callsite_index",
    "classifier_call_graph_summary",
    "dependency_edges",
    "module_call_graph_summary",
    "symbol_references",
]
