# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Overlay bundle storage helpers."""

from __future__ import annotations

import json
from typing import Iterable

from ...data_storage.artifact_db import diff_overlay as overlay_store
from ...data_storage.artifact_db import diff_overlay_calls as overlay_call_store
from ...data_storage.artifact_db import diff_overlay_summary as overlay_summary_store

from .types import OverlayPayload


def overlay_bundle_exists(artifact_conn, snapshot_id: str, worktree_hash: str) -> bool:
    if overlay_store.overlay_exists(artifact_conn, snapshot_id, worktree_hash):
        return True
    if overlay_call_store.overlay_exists(artifact_conn, snapshot_id, worktree_hash):
        return True
    if overlay_summary_store.overlay_exists(artifact_conn, snapshot_id, worktree_hash):
        return True
    return False


def rows_to_payload(
    worktree_hash: str,
    snapshot_commit: str | None,
    base_commit: str | None,
    base_commit_strategy: str | None,
    head_commit: str | None,
    merge_base: str | None,
    rows: Iterable[dict[str, object]],
    call_rows: Iterable[dict[str, object]],
    summary: dict[str, object] | None,
    warnings: list[str],
) -> OverlayPayload:
    nodes = {"add": [], "remove": [], "modify": []}
    edges = {"add": [], "remove": [], "modify": []}
    for row in rows:
        node_type = row["node_type"]
        diff_kind = row["diff_kind"]
        entry = {
            "structural_id": row["structural_id"],
            "field": row.get("field"),
            "old_value": row.get("old_value"),
            "new_value": row.get("new_value"),
        }
        if node_type == "edge":
            if diff_kind in edges:
                edges[diff_kind].append(entry)
            continue
        if diff_kind in nodes:
            nodes[diff_kind].append(entry)
    calls = {"add": [], "remove": [], "modify": []}
    for row in call_rows:
        diff_kind = row.get("diff_kind")
        entry = dict(row)
        entry.pop("diff_kind", None)
        entry.pop("created_at", None)
        entry.pop("snapshot_id", None)
        if diff_kind in calls:
            calls[diff_kind].append(entry)
    _sort_change_entries(nodes, edges, calls)
    return OverlayPayload(
        worktree_hash=worktree_hash,
        snapshot_commit=snapshot_commit,
        base_commit=base_commit,
        base_commit_strategy=base_commit_strategy,
        head_commit=head_commit,
        merge_base=merge_base,
        nodes=nodes,
        edges=edges,
        calls=calls,
        summary=summary,
        warnings=warnings,
    )


def _parse_entry_payload(entry: dict[str, object]) -> dict[str, object]:
    raw = entry.get("new_value") or entry.get("old_value")
    if not isinstance(raw, str) or not raw:
        return {}
    try:
        value = json.loads(raw)
    except Exception:
        return {}
    if isinstance(value, dict):
        return value
    return {}


def _node_sort_key(entry: dict[str, object]) -> tuple[str, str, str]:
    meta = _parse_entry_payload(entry)
    return (
        str(meta.get("file_path") or ""),
        str(meta.get("qualified_name") or ""),
        str(entry.get("structural_id") or ""),
    )


def _edge_sort_key(entry: dict[str, object]) -> tuple[str, str, str, str, str, str]:
    meta = _parse_entry_payload(entry)
    return (
        str(meta.get("src_file_path") or ""),
        str(meta.get("dst_file_path") or ""),
        str(meta.get("src_qualified_name") or ""),
        str(meta.get("dst_qualified_name") or ""),
        str(meta.get("edge_type") or ""),
        str(entry.get("structural_id") or ""),
    )


def _call_sort_key(entry: dict[str, object]) -> tuple[str, str, str, str, str, str]:
    return (
        str(entry.get("src_file_path") or ""),
        str(entry.get("dst_file_path") or ""),
        str(entry.get("src_qualified_name") or ""),
        str(entry.get("dst_qualified_name") or ""),
        str(entry.get("src_structural_id") or ""),
        str(entry.get("dst_structural_id") or ""),
    )


def _sort_change_entries(
    nodes: dict[str, list[dict[str, object]]],
    edges: dict[str, list[dict[str, object]]],
    calls: dict[str, list[dict[str, object]]],
) -> None:
    for entries in nodes.values():
        entries.sort(key=_node_sort_key)
    for entries in edges.values():
        entries.sort(key=_edge_sort_key)
    for entries in calls.values():
        entries.sort(key=_call_sort_key)


__all__ = ["overlay_bundle_exists", "rows_to_payload"]
