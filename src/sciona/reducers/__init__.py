# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Reducer root package."""

from __future__ import annotations

from . import callable_overview
from . import callable_source
from . import classifier_call_graph_summary
from . import classifier_inheritance
from . import classifier_overview
from . import concatenated_source
from . import dependency_edges
from . import fan_summary
from . import file_outline
from . import hotspot_summary
from . import module_call_graph_summary
from . import module_overview
from . import ownership_summary
from . import overlay_impact_summary
from . import overlay_projection_status_summary
from . import snapshot_provenance
from . import structural_index
from . import structural_integrity_summary
from . import symbol_lookup
from . import symbol_references

__all__ = [
    "callable_overview",
    "callable_source",
    "classifier_call_graph_summary",
    "classifier_inheritance",
    "classifier_overview",
    "concatenated_source",
    "dependency_edges",
    "fan_summary",
    "file_outline",
    "hotspot_summary",
    "module_call_graph_summary",
    "module_overview",
    "ownership_summary",
    "overlay_impact_summary",
    "overlay_projection_status_summary",
    "snapshot_provenance",
    "structural_index",
    "structural_integrity_summary",
    "symbol_lookup",
    "symbol_references",
]
