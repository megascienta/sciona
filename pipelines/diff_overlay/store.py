# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Overlay bundle storage helpers."""

from __future__ import annotations

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
    head_commit: str | None,
    merge_base: str | None,
    rows: Iterable[dict[str, object]],
    call_rows: Iterable[dict[str, object]],
    summary: dict[str, object] | None,
    warnings: list[str],
) -> OverlayPayload:
    nodes = {"add": [], "remove": [], "modify": []}
    edges = {"add": [], "remove": []}
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
    calls = {"add": [], "remove": []}
    for row in call_rows:
        diff_kind = row.get("diff_kind")
        entry = dict(row)
        entry.pop("diff_kind", None)
        entry.pop("created_at", None)
        if diff_kind in calls:
            calls[diff_kind].append(entry)
    return OverlayPayload(
        worktree_hash=worktree_hash,
        snapshot_commit=snapshot_commit,
        base_commit=base_commit,
        head_commit=head_commit,
        merge_base=merge_base,
        nodes=nodes,
        edges=edges,
        calls=calls,
        summary=summary,
        warnings=warnings,
    )


__all__ = ["overlay_bundle_exists", "rows_to_payload"]
