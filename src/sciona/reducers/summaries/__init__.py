# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Summary reducers."""

from __future__ import annotations

from . import (
    call_neighbors,
    callsite_index,
    class_call_graph_summary,
    fan_summary,
    hotspot_summary,
    importers_index,
    module_call_graph_summary,
)

__all__ = [
    "call_neighbors",
    "callsite_index",
    "class_call_graph_summary",
    "fan_summary",
    "hotspot_summary",
    "importers_index",
    "module_call_graph_summary",
]
