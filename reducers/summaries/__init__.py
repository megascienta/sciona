# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Summary reducers."""

from __future__ import annotations

from . import (
    call_graph,
    callsite_index,
    class_call_graph,
    fan_summary,
    hotspot_summary,
    importers_index,
    module_call_graph,
)

__all__ = [
    "call_graph",
    "callsite_index",
    "class_call_graph",
    "fan_summary",
    "hotspot_summary",
    "importers_index",
    "module_call_graph",
]
