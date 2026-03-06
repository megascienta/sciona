# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Overlay patching for reducer payloads."""

from __future__ import annotations

import json
from typing import Optional

from ..types import OverlayPayload
from ....runtime import identity as ids
from .fan_utils import (
    _fan_deltas_for_node,
    _match_module_name,
    _module_for_node,
    _node_meta_lookup,
    _patch_fan_table,
)
from .shared import edge_from_value, iter_edge_changes, iter_node_changes, node_from_value

def patch_call_neighbors(
    payload: dict[str, object],
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
) -> dict[str, object]:
    target_id = payload.get("callable_id")
    if not target_id:
        return payload
    callers = {
        entry.get("structural_id"): entry for entry in payload.get("callers", []) or []
    }
    callees = {
        entry.get("structural_id"): entry for entry in payload.get("callees", []) or []
    }
    ids_needed: set[str] = set()
    for change in overlay.calls.get("add", []) + overlay.calls.get("remove", []):
        src_id = change.get("src_structural_id")
        dst_id = change.get("dst_structural_id")
        if src_id == target_id or dst_id == target_id:
            if src_id:
                ids_needed.add(str(src_id))
            if dst_id:
                ids_needed.add(str(dst_id))
    meta_lookup = _node_meta_lookup(conn, snapshot_id, overlay, ids_needed)

    def _entry(node_id: str) -> dict[str, object] | None:
        meta = meta_lookup.get(node_id, {})
        qualified = meta.get("qualified_name")
        node_type = meta.get("node_type")
        if not qualified or not node_type:
            return None
        return {
            "structural_id": node_id,
            "qualified_name": qualified,
            "node_type": node_type,
        }

    for change in overlay.calls.get("add", []):
        src_id = change.get("src_structural_id")
        dst_id = change.get("dst_structural_id")
        if src_id == target_id and dst_id:
            entry = _entry(str(dst_id))
            if entry:
                callees[str(dst_id)] = entry
        if dst_id == target_id and src_id:
            entry = _entry(str(src_id))
            if entry:
                callers[str(src_id)] = entry
    for change in overlay.calls.get("remove", []):
        src_id = change.get("src_structural_id")
        dst_id = change.get("dst_structural_id")
        if src_id == target_id and dst_id:
            callees.pop(str(dst_id), None)
        if dst_id == target_id and src_id:
            callers.pop(str(src_id), None)

    payload["callers"] = sorted(
        callers.values(), key=lambda item: str(item.get("qualified_name"))
    )
    payload["callees"] = sorted(
        callees.values(), key=lambda item: str(item.get("qualified_name"))
    )
    payload["caller_count"] = len(payload["callers"])
    payload["callee_count"] = len(payload["callees"])
    return payload

def patch_callsite_index(
    payload: dict[str, object],
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
) -> dict[str, object]:
    if "callers" in payload or "callees" in payload:
        return patch_call_neighbors(payload, overlay, snapshot_id=snapshot_id, conn=conn)
    target_id = payload.get("callable_id")
    if not target_id:
        return payload
    direction = str(payload.get("direction") or "both").lower()
    edges = list(payload.get("edges", []) or [])
    edge_map: dict[tuple[str, str, str], dict[str, object]] = {}
    for entry in edges:
        key = (
            str(entry.get("caller_id") or ""),
            str(entry.get("callee_id") or ""),
            str(entry.get("edge_kind") or "CALLS"),
        )
        edge_map[key] = entry
    ids_needed: set[str] = set()
    for change in overlay.calls.get("add", []) + overlay.calls.get("remove", []):
        src_id = change.get("src_structural_id")
        dst_id = change.get("dst_structural_id")
        if src_id:
            ids_needed.add(str(src_id))
        if dst_id:
            ids_needed.add(str(dst_id))
    meta_lookup = _node_meta_lookup(conn, snapshot_id, overlay, ids_needed)

    def _module_name(node_id: str) -> str | None:
        meta = meta_lookup.get(node_id, {})
        return _module_for_node(
            str(meta.get("node_type") or ""), str(meta.get("qualified_name") or "")
        )

    def _entry(caller_id: str, callee_id: str, edge_source: str) -> dict[str, object]:
        caller = meta_lookup.get(caller_id, {})
        callee = meta_lookup.get(callee_id, {})
        return {
            "caller_id": caller_id,
            "callee_id": callee_id,
            "caller_qualified_name": caller.get("qualified_name"),
            "callee_qualified_name": callee.get("qualified_name"),
            "caller_file_path": caller.get("file_path"),
            "callee_file_path": callee.get("file_path"),
            "caller_language": caller.get("language"),
            "callee_language": callee.get("language"),
            "caller_node_type": caller.get("node_type"),
            "callee_node_type": callee.get("node_type"),
            "caller_module_qualified_name": _module_name(caller_id),
            "callee_module_qualified_name": _module_name(callee_id),
            "edge_kind": "CALLS",
            "edge_source": edge_source,
            "call_hash": None,
            "line_span": None,
        }

    def _matches_direction(src_id: str, dst_id: str) -> bool:
        if direction == "out":
            return src_id == target_id
        if direction == "in":
            return dst_id == target_id
        return src_id == target_id or dst_id == target_id

    for change in overlay.calls.get("add", []):
        src_id = change.get("src_structural_id")
        dst_id = change.get("dst_structural_id")
        if not src_id or not dst_id:
            continue
        if not _matches_direction(str(src_id), str(dst_id)):
            continue
        key = (str(src_id), str(dst_id), "CALLS")
        edge_map[key] = _entry(str(src_id), str(dst_id), "overlay")

    for change in overlay.calls.get("remove", []):
        src_id = change.get("src_structural_id")
        dst_id = change.get("dst_structural_id")
        if not src_id or not dst_id:
            continue
        if not _matches_direction(str(src_id), str(dst_id)):
            continue
        edge_map.pop((str(src_id), str(dst_id), "CALLS"), None)

    payload["edges"] = sorted(
        edge_map.values(),
        key=lambda item: (
            str(item.get("caller_id")),
            str(item.get("callee_id")),
        ),
    )
    payload["edge_count"] = len(payload["edges"])
    return payload

def patch_module_call_graph_summary(
    payload: dict[str, object],
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
) -> dict[str, object]:
    target_id = payload.get("module_qualified_name")
    if not target_id:
        return payload
    top_k = payload.get("top_k")
    outgoing_map: dict[tuple[str, str], int] = {}
    incoming_map: dict[tuple[str, str], int] = {}
    for entry in payload.get("outgoing", []) or []:
        key = (
            str(entry.get("src_module_qualified_name")),
            str(entry.get("dst_module_qualified_name")),
        )
        outgoing_map[key] = int(entry.get("call_count") or 0)
    for entry in payload.get("incoming", []) or []:
        key = (
            str(entry.get("src_module_qualified_name")),
            str(entry.get("dst_module_qualified_name")),
        )
        incoming_map[key] = int(entry.get("call_count") or 0)
    ids_needed: set[str] = set()
    for change in overlay.calls.get("add", []) + overlay.calls.get("remove", []):
        if change.get("src_structural_id"):
            ids_needed.add(str(change.get("src_structural_id")))
        if change.get("dst_structural_id"):
            ids_needed.add(str(change.get("dst_structural_id")))
    meta_lookup = _node_meta_lookup(conn, snapshot_id, overlay, ids_needed)

    def _module_id(node_id: str) -> str | None:
        meta = meta_lookup.get(node_id, {})
        module_name = _module_for_node(
            str(meta.get("node_type") or ""), str(meta.get("qualified_name") or "")
        )
        language = meta.get("language")
        if not module_name or not language:
            return None
        return ids.structural_id("module", str(language), str(module_name))

    for change in overlay.calls.get("add", []) + overlay.calls.get("remove", []):
        src_id = change.get("src_structural_id")
        dst_id = change.get("dst_structural_id")
        if not src_id or not dst_id:
            continue
        src_module = _module_id(str(src_id))
        dst_module = _module_id(str(dst_id))
        if not src_module or not dst_module:
            continue
        delta = 1 if change.get("diff_kind") == "add" else -1
        if src_module == target_id:
            outgoing_map[(src_module, dst_module)] = max(
                0, outgoing_map.get((src_module, dst_module), 0) + delta
            )
        if dst_module == target_id:
            incoming_map[(src_module, dst_module)] = max(
                0, incoming_map.get((src_module, dst_module), 0) + delta
            )

    def _entries(edge_map: dict[tuple[str, str], int], direction: str) -> list[dict[str, object]]:
        entries = []
        for (src, dst), count in edge_map.items():
            if count <= 0:
                continue
            entries.append(
                {
                    "src_module_qualified_name": src,
                    "dst_module_qualified_name": dst,
                    "direction": direction,
                    "call_count": count,
                }
            )
        entries.sort(
            key=lambda item: (
                -int(item.get("call_count") or 0),
                str(item.get("src_module_qualified_name")),
                str(item.get("dst_module_qualified_name")),
            )
        )
        if top_k is not None:
            try:
                limit = int(top_k)
            except (TypeError, ValueError):
                limit = None
            if limit and limit > 0:
                entries = entries[:limit]
        return entries

    outgoing_all = _entries(outgoing_map, "outgoing")
    incoming_all = _entries(incoming_map, "incoming")
    payload["outgoing"] = outgoing_all
    payload["incoming"] = incoming_all
    payload["outgoing_count"] = len(outgoing_all)
    payload["incoming_count"] = len(incoming_all)
    payload["outgoing_total"] = len(outgoing_all)
    payload["incoming_total"] = len(incoming_all)
    payload["total_edges"] = len(outgoing_all) + len(incoming_all)
    payload["edge_summary"] = {
        "CALLS": {"outgoing": len(outgoing_all), "incoming": len(incoming_all)}
    }
    if outgoing_all:
        payload["outgoing_coverage_ratio"] = 1.0
    if incoming_all:
        payload["incoming_coverage_ratio"] = 1.0
    return payload

def patch_classifier_call_graph_summary(
    payload: dict[str, object],
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
) -> dict[str, object]:
    target_id = payload.get("classifier_id")
    if not target_id:
        return payload
    top_k = payload.get("top_k")
    outgoing_map: dict[tuple[str, str], int] = {}
    incoming_map: dict[tuple[str, str], int] = {}
    for entry in payload.get("outgoing", []) or []:
        key = (
            str(entry.get("src_classifier_id")),
            str(entry.get("dst_classifier_id")),
        )
        outgoing_map[key] = int(entry.get("call_count") or 0)
    for entry in payload.get("incoming", []) or []:
        key = (
            str(entry.get("src_classifier_id")),
            str(entry.get("dst_classifier_id")),
        )
        incoming_map[key] = int(entry.get("call_count") or 0)
    ids_needed: set[str] = set()
    for change in overlay.calls.get("add", []) + overlay.calls.get("remove", []):
        if change.get("src_structural_id"):
            ids_needed.add(str(change.get("src_structural_id")))
        if change.get("dst_structural_id"):
            ids_needed.add(str(change.get("dst_structural_id")))
    meta_lookup = _node_meta_lookup(conn, snapshot_id, overlay, ids_needed)

    def _classifier_id(node_id: str) -> str | None:
        meta = meta_lookup.get(node_id, {})
        if meta.get("node_type") != "callable":
            return None
        qualified = str(meta.get("qualified_name") or "")
        language = meta.get("language")
        parts = qualified.split(".")
        if len(parts) < 2 or not language:
            return None
        classifier_name = ".".join(parts[:-1])
        return ids.structural_id("classifier", str(language), classifier_name)

    for change in overlay.calls.get("add", []) + overlay.calls.get("remove", []):
        src_id = change.get("src_structural_id")
        dst_id = change.get("dst_structural_id")
        if not src_id or not dst_id:
            continue
        src_classifier = _classifier_id(str(src_id))
        dst_classifier = _classifier_id(str(dst_id))
        if not src_classifier or not dst_classifier:
            continue
        delta = 1 if change.get("diff_kind") == "add" else -1
        if src_classifier == target_id:
            outgoing_map[(src_classifier, dst_classifier)] = max(
                0, outgoing_map.get((src_classifier, dst_classifier), 0) + delta
            )
        if dst_classifier == target_id:
            incoming_map[(src_classifier, dst_classifier)] = max(
                0, incoming_map.get((src_classifier, dst_classifier), 0) + delta
            )

    def _entries(edge_map: dict[tuple[str, str], int], direction: str) -> list[dict[str, object]]:
        entries = []
        for (src, dst), count in edge_map.items():
            if count <= 0:
                continue
            entries.append(
                {
                    "src_classifier_id": src,
                    "dst_classifier_id": dst,
                    "direction": direction,
                    "call_count": count,
                }
            )
        entries.sort(
            key=lambda item: (
                -int(item.get("call_count") or 0),
                str(item.get("src_classifier_id")),
                str(item.get("dst_classifier_id")),
            )
        )
        if top_k is not None:
            try:
                limit = int(top_k)
            except (TypeError, ValueError):
                limit = None
            if limit and limit > 0:
                entries = entries[:limit]
        return entries

    outgoing_all = _entries(outgoing_map, "outgoing")
    incoming_all = _entries(incoming_map, "incoming")
    payload["outgoing"] = outgoing_all
    payload["incoming"] = incoming_all
    payload["outgoing_count"] = len(outgoing_all)
    payload["incoming_count"] = len(incoming_all)
    payload["outgoing_total"] = len(outgoing_all)
    payload["incoming_total"] = len(incoming_all)
    payload["total_edges"] = len(outgoing_all) + len(incoming_all)
    payload["edge_summary"] = {
        "CALLS": {"outgoing": len(outgoing_all), "incoming": len(incoming_all)}
    }
    if outgoing_all:
        payload["outgoing_coverage_ratio"] = 1.0
    if incoming_all:
        payload["incoming_coverage_ratio"] = 1.0
    return payload

def patch_fan_summary(
    payload: dict[str, object],
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
) -> dict[str, object]:
    node_id = payload.get("node_id")
    if node_id:
        edge_kinds = dict(payload.get("edge_kinds") or {})
        deltas = _fan_deltas_for_node(overlay, str(node_id))
        for edge_kind, delta_map in deltas.items():
            entry = dict(edge_kinds.get(edge_kind) or {})
            entry["fan_in"] = max(0, int(entry.get("fan_in") or 0) + delta_map.get("fan_in", 0))
            entry["fan_out"] = max(0, int(entry.get("fan_out") or 0) + delta_map.get("fan_out", 0))
            edge_kinds[edge_kind] = entry
        payload["edge_kinds"] = edge_kinds
        payload["edge_summary"] = edge_kinds
        return payload

    calls_table = dict(payload.get("calls") or {})
    imports_table = dict(payload.get("imports") or {})
    payload["calls"] = _patch_fan_table(calls_table, overlay, edge_kind="CALLS")
    payload["imports"] = _patch_fan_table(
        imports_table, overlay, edge_kind="IMPORTS_DECLARED"
    )
    return payload

def patch_hotspot_summary(
    payload: dict[str, object],
    overlay: OverlayPayload,
    *,
    snapshot_id: str,
    conn,
) -> dict[str, object]:
    by_size = list(payload.get("by_size", []) or [])
    size_map = {entry.get("module_qualified_name"): int(entry.get("count") or 0) for entry in by_size}
    module_names = [name for name in size_map.keys() if name]
    for change in iter_node_changes(overlay):
        node = node_from_value(change.get("new_value") or change.get("old_value"))
        if not node:
            continue
        node_type = str(node.get("node_type") or "")
        if node_type not in {"classifier", "callable"}:
            continue
        module_name = _match_module_name(
            str(node.get("qualified_name") or ""), module_names
        )
        if module_name not in size_map:
            continue
        delta = 1 if change.get("diff_kind") == "add" else -1 if change.get("diff_kind") == "remove" else 0
        if delta:
            size_map[module_name] = max(0, size_map.get(module_name, 0) + delta)

    by_size = [
        {"module_qualified_name": name, "count": count}
        for name, count in size_map.items()
    ]
    by_size.sort(key=lambda item: (-int(item.get("count") or 0), str(item.get("module_qualified_name"))))
    payload["by_size"] = by_size[: len(payload.get("by_size", []) or [])]

    fan_in = {entry.get("module_qualified_name"): int(entry.get("count") or 0) for entry in payload.get("by_fan_in", []) or []}
    fan_out = {entry.get("module_qualified_name"): int(entry.get("count") or 0) for entry in payload.get("by_fan_out", []) or []}
    for change in iter_edge_changes(overlay):
        edge = edge_from_value(change.get("new_value") or change.get("old_value"))
        if not edge or edge.get("edge_type") != "IMPORTS_DECLARED":
            continue
        src_name = edge.get("src_qualified_name")
        dst_name = edge.get("dst_qualified_name")
        delta = 1 if change.get("diff_kind") == "add" else -1 if change.get("diff_kind") == "remove" else 0
        if delta:
            if src_name in fan_out:
                fan_out[src_name] = max(0, fan_out.get(src_name, 0) + delta)
            if dst_name in fan_in:
                fan_in[dst_name] = max(0, fan_in.get(dst_name, 0) + delta)
    payload["by_fan_in"] = [
        {"module_qualified_name": name, "count": count}
        for name, count in sorted(fan_in.items(), key=lambda item: (-item[1], str(item[0])))
    ][: len(payload.get("by_fan_in", []) or [])]
    payload["by_fan_out"] = [
        {"module_qualified_name": name, "count": count}
        for name, count in sorted(fan_out.items(), key=lambda item: (-item[1], str(item[0])))
    ][: len(payload.get("by_fan_out", []) or [])]
    return payload
