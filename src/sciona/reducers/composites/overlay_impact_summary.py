# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Overlay impact summary reducer."""

from __future__ import annotations

from ...data_storage.artifact_db import read_overlay as artifact_read_overlay
from ..helpers.context import current_artifact_connection, fallback_artifact_connection
from ..helpers.render import render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot
from ..metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="overlay_impact_summary",
    category="metrics",
    risk_tier="elevated",
    stage="diagnostics_metrics",
    placeholder="OVERLAY_IMPACT_SUMMARY",
    summary="Advisory summary of dirty-worktree diff overlay impact for the committed snapshot. "
    "Use when triaging uncommitted changes; output is non-authoritative. ",
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="overlay_impact_summary reducer"
    )
    artifact_conn = current_artifact_connection()
    owns_connection = False
    if artifact_conn is None:
        artifact_conn = fallback_artifact_connection(repo_root)
        owns_connection = artifact_conn is not None
    body = {
        "payload_kind": "summary",
        "overlay_advisory": True,
        "snapshot_id": snapshot_id,
        "overlay_available": False,
        "worktree_hash": None,
        "created_at": None,
        "summary": None,
        "node_change_count": 0,
        "call_change_count": 0,
    }
    if artifact_conn is not None:
        row = artifact_read_overlay.latest_overlay_summary_for_snapshot(
            artifact_conn,
            snapshot_id=snapshot_id,
        )
        if row is not None:
            worktree_hash = str(row["worktree_hash"])
            body["overlay_available"] = True
            body["worktree_hash"] = worktree_hash
            body["created_at"] = row["created_at"]
            body["summary"] = row["summary"]
            body["node_change_count"] = artifact_read_overlay.overlay_node_change_count(
                artifact_conn,
                snapshot_id=snapshot_id,
                worktree_hash=worktree_hash,
            )
            body["call_change_count"] = artifact_read_overlay.overlay_call_change_count(
                artifact_conn,
                snapshot_id=snapshot_id,
                worktree_hash=worktree_hash,
            )
    if owns_connection and artifact_conn is not None:
        artifact_conn.close()
    return render_json_payload(body)


__all__ = ["render", "REDUCER_META"]
