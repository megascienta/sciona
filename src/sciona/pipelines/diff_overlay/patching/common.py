# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Overlay patching for reducer payloads."""

from __future__ import annotations

from ..types import OverlayPayload
from ....runtime.common import identity as ids
from .analytics import (
    patch_call_neighbors,
    patch_call_resolution_drop_summary,
    patch_call_resolution_quality,
    patch_callsite_pairs_index,
    patch_classifier_call_graph_summary,
    patch_fan_summary,
    patch_hotspot_summary,
    patch_module_call_graph_summary,
)
from .core import (
    patch_callable_overview,
    patch_classifier_overview,
    patch_dependency_edges,
    patch_file_outline,
    patch_module_overview,
    patch_structural_index,
    patch_symbol_lookup,
    patch_symbol_references,
)
from .shared import (
    edge_from_value,
    iter_edge_changes,
    iter_node_changes,
    module_for_node,
    module_in_scope,
    node_from_value,
)

def apply_overlay_to_payload(
    payload: dict[str, object],
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
    reducer_id: str | None = None,
) -> tuple[dict[str, object], bool]:
    projection = _resolve_projection(payload, reducer_id)
    if projection == "structural_index":
        return patch_structural_index(payload, overlay), True
    if projection == "module_overview":
        return patch_module_overview(payload, overlay), True
    if projection == "callable_overview":
        return patch_callable_overview(payload, overlay), True
    if projection == "classifier_overview":
        return patch_classifier_overview(
            payload, overlay, snapshot_id=snapshot_id, conn=conn
        ), True
    if projection == "file_outline":
        return patch_file_outline(payload, overlay), True
    if projection == "dependency_edges":
        return patch_dependency_edges(payload, overlay), True
    if projection == "symbol_lookup":
        return patch_symbol_lookup(payload, overlay), True
    if projection == "symbol_references":
        return patch_symbol_references(payload, overlay), True
    if projection == "callsite_pairs_index":
        return patch_callsite_pairs_index(
            payload, overlay, snapshot_id=snapshot_id, conn=conn
        ), True
    if projection == "classifier_call_graph_summary":
        return patch_classifier_call_graph_summary(
            payload, overlay, snapshot_id=snapshot_id, conn=conn
        ), True
    if projection == "module_call_graph_summary":
        return patch_module_call_graph_summary(
            payload, overlay, snapshot_id=snapshot_id, conn=conn
        ), True
    if projection == "call_resolution_quality":
        return patch_call_resolution_quality(
            payload, overlay, snapshot_id=snapshot_id, conn=conn
        ), True
    if projection == "call_resolution_drop_summary":
        return patch_call_resolution_drop_summary(
            payload, overlay, snapshot_id=snapshot_id, conn=conn
        ), True
    if projection == "fan_summary":
        return patch_fan_summary(payload, overlay, snapshot_id=snapshot_id, conn=conn), True
    if projection == "hotspot_summary":
        return patch_hotspot_summary(payload, overlay, snapshot_id=snapshot_id, conn=conn), True
    return payload, False

def _resolve_projection(payload: dict[str, object], reducer_id: str | None) -> str:
    projection = str(payload.get("projection", "")).strip().lower()
    if projection:
        return projection
    return str(reducer_id or "").strip().lower()

def patch_summary_payload(
    payload: dict[str, object], overlay: OverlayPayload
) -> dict[str, object]:
    if overlay.summary is None:
        return payload
    payload["diff_summary"] = overlay.summary
    return payload
