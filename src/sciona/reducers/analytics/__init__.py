# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Analytics reducers."""

from __future__ import annotations

from . import (
    call_resolution_quality,
    callsite_index,
    class_call_graph_summary,
    fan_summary,
    hotspot_summary,
    module_call_graph_summary,
    resolution_trace,
)

__all__ = [
    "callsite_index",
    "call_resolution_quality",
    "class_call_graph_summary",
    "fan_summary",
    "hotspot_summary",
    "module_call_graph_summary",
    "resolution_trace",
]
