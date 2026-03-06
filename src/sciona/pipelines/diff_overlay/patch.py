# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Overlay patching for reducer payloads."""

from __future__ import annotations

from .patchers.common import (
    _resolve_projection,
    apply_overlay_to_payload,
    edge_from_value,
    iter_edge_changes,
    iter_node_changes,
    module_for_node,
    module_in_scope,
    node_from_value,
    parse_json_fenced,
    patch_summary_payload,
)
from .patchers.core import (
    patch_callable_overview,
    patch_classifier_overview,
    patch_dependency_edges,
    patch_file_outline,
    patch_module_overview,
    patch_structural_index,
    patch_symbol_lookup,
    patch_symbol_references,
)
from .patchers.analytics import (
    patch_call_neighbors,
    patch_callsite_index,
    patch_classifier_call_graph_summary,
    patch_fan_summary,
    patch_hotspot_summary,
    patch_module_call_graph_summary,
)
from .patchers.fan_utils import (
    _fan_deltas_for_node,
    _match_module_name,
    _module_for_node,
    _node_meta_lookup,
    _patch_fan_table,
)

__all__ = [
    "apply_overlay_to_payload",
    "parse_json_fenced",
    "patch_summary_payload",
]
