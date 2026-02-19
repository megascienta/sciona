# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Overlay patching for reducer payloads."""

from __future__ import annotations

import json
from typing import Optional

from ..types import OverlayPayload
from ....runtime import identity as ids
from .shared import edge_from_value, iter_node_changes, node_from_value

def _node_meta_lookup(
    conn,
    snapshot_id: str,
    overlay: OverlayPayload,
    node_ids: set[str],
) -> dict[str, dict[str, object]]:
    lookup: dict[str, dict[str, object]] = {}
    for change in iter_node_changes(overlay):
        node = node_from_value(change.get("new_value") or change.get("old_value"))
        if not node:
            continue
        structural_id = node.get("structural_id")
        if not structural_id:
            continue
        lookup[str(structural_id)] = {
            "qualified_name": node.get("qualified_name"),
            "file_path": node.get("file_path"),
            "node_type": node.get("node_type"),
            "language": node.get("language"),
        }
    if not node_ids:
        return lookup
    missing = [node_id for node_id in node_ids if node_id not in lookup]
    if not missing:
        return lookup
    placeholders = ",".join("?" for _ in missing)
    rows = conn.execute(
        f"""
        SELECT sn.structural_id, sn.node_type, sn.language, ni.qualified_name, ni.file_path
        FROM structural_nodes sn
        JOIN node_instances ni
            ON ni.structural_id = sn.structural_id
           AND ni.snapshot_id = ?
        WHERE sn.structural_id IN ({placeholders})
        """,
        (snapshot_id, *missing),
    ).fetchall()
    for row in rows:
        lookup[str(row["structural_id"])] = {
            "qualified_name": row["qualified_name"],
            "file_path": row["file_path"],
            "node_type": row["node_type"],
            "language": row["language"],
        }
    return lookup

def _module_for_node(node_type: str, qualified_name: str) -> str | None:
    if not qualified_name:
        return None
    if node_type == "module":
        return qualified_name
    parts = qualified_name.split(".")
    if not parts:
        return None
    if node_type == "method":
        if len(parts) >= 3:
            return ".".join(parts[:-2])
        return None
    if len(parts) >= 2:
        return ".".join(parts[:-1])
    return None

def _match_module_name(qualified_name: str, module_names: list[str]) -> str | None:
    if not qualified_name or not module_names:
        return None
    best = None
    best_len = -1
    q_parts = qualified_name.split(".")
    for name in module_names:
        n_parts = name.split(".")
        if len(n_parts) > len(q_parts):
            continue
        for idx in range(len(q_parts) - len(n_parts) + 1):
            if q_parts[idx : idx + len(n_parts)] == n_parts:
                if len(n_parts) > best_len:
                    best = name
                    best_len = len(n_parts)
                break
    return best

def _fan_deltas_for_node(overlay: OverlayPayload, node_id: str) -> dict[str, dict[str, int]]:
    deltas: dict[str, dict[str, int]] = {
        "CALLS": {"fan_in": 0, "fan_out": 0},
        "IMPORTS_DECLARED": {"fan_in": 0, "fan_out": 0},
    }
    for change in overlay.calls.get("add", []):
        if change.get("src_structural_id") == node_id:
            deltas["CALLS"]["fan_out"] += 1
        if change.get("dst_structural_id") == node_id:
            deltas["CALLS"]["fan_in"] += 1
    for change in overlay.calls.get("remove", []):
        if change.get("src_structural_id") == node_id:
            deltas["CALLS"]["fan_out"] -= 1
        if change.get("dst_structural_id") == node_id:
            deltas["CALLS"]["fan_in"] -= 1
    for change in overlay.edges.get("add", []):
        edge = edge_from_value(change.get("new_value") or change.get("old_value"))
        if not edge or edge.get("edge_type") != "IMPORTS_DECLARED":
            continue
        if edge.get("src_structural_id") == node_id:
            deltas["IMPORTS_DECLARED"]["fan_out"] += 1
        if edge.get("dst_structural_id") == node_id:
            deltas["IMPORTS_DECLARED"]["fan_in"] += 1
    for change in overlay.edges.get("remove", []):
        edge = edge_from_value(change.get("new_value") or change.get("old_value"))
        if not edge or edge.get("edge_type") != "IMPORTS_DECLARED":
            continue
        if edge.get("src_structural_id") == node_id:
            deltas["IMPORTS_DECLARED"]["fan_out"] -= 1
        if edge.get("dst_structural_id") == node_id:
            deltas["IMPORTS_DECLARED"]["fan_in"] -= 1
    return deltas

def _patch_fan_table(
    table: dict[str, object],
    overlay: OverlayPayload,
    *,
    edge_kind: str,
) -> dict[str, object]:
    by_in = {entry.get("node_id"): int(entry.get("count") or 0) for entry in table.get("by_fan_in", []) or []}
    by_out = {entry.get("node_id"): int(entry.get("count") or 0) for entry in table.get("by_fan_out", []) or []}
    if edge_kind == "CALLS":
        for change in overlay.calls.get("add", []) + overlay.calls.get("remove", []):
            delta = 1 if change.get("diff_kind") == "add" else -1
            src_id = change.get("src_structural_id")
            dst_id = change.get("dst_structural_id")
            if src_id in by_out:
                by_out[src_id] = max(0, by_out.get(src_id, 0) + delta)
            if dst_id in by_in:
                by_in[dst_id] = max(0, by_in.get(dst_id, 0) + delta)
    if edge_kind == "IMPORTS_DECLARED":
        for change in overlay.edges.get("add", []) + overlay.edges.get("remove", []):
            edge = edge_from_value(change.get("new_value") or change.get("old_value"))
            if not edge or edge.get("edge_type") != "IMPORTS_DECLARED":
                continue
            delta = 1 if change.get("diff_kind") == "add" else -1
            src_id = edge.get("src_structural_id")
            dst_id = edge.get("dst_structural_id")
            if src_id in by_out:
                by_out[src_id] = max(0, by_out.get(src_id, 0) + delta)
            if dst_id in by_in:
                by_in[dst_id] = max(0, by_in.get(dst_id, 0) + delta)
    table["by_fan_in"] = [
        {"node_id": node_id, "count": count}
        for node_id, count in sorted(by_in.items(), key=lambda item: (-item[1], str(item[0])))
    ]
    table["by_fan_out"] = [
        {"node_id": node_id, "count": count}
        for node_id, count in sorted(by_out.items(), key=lambda item: (-item[1], str(item[0])))
    ]
    return table
