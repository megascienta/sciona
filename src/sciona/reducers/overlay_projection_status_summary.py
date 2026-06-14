# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Overlay projection support summary reducer."""

from __future__ import annotations

from ..data_storage.artifact_db.overlay import read_overlay as artifact_read_overlay
from ..runtime import git as git_ops
from ..runtime.overlay_profile import OVERLAY_PROFILE
from .helpers.shared.context import current_artifact_connection, fallback_artifact_connection
from .helpers.shared.connection import require_connection
from .helpers.shared.payload import render_json_payload
from .helpers.shared.snapshot_guard import require_latest_committed_snapshot
from .metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="overlay_projection_status_summary",
    category="overlay",
    placeholder="OVERLAY_PROJECTION_STATUS_SUMMARY",
    summary="Shows reducer dirty-worktree overlay metadata status. Use when deciding "
    "how to interpret reducer output on a dirty worktree. ",
)


def render(
    snapshot_id: str,
    conn,
    repo_root,
    **_: object,
) -> str:
    conn = require_connection(conn)
    require_latest_committed_snapshot(
        conn, snapshot_id, reducer_name="overlay_projection_status_summary reducer"
    )
    worktree_dirty = bool(repo_root and git_ops.is_worktree_dirty(repo_root))
    artifact_conn = current_artifact_connection()
    owns_connection = False
    if artifact_conn is None and repo_root is not None:
        artifact_conn = fallback_artifact_connection(repo_root)
        owns_connection = artifact_conn is not None

    overlay_row = None
    if worktree_dirty and artifact_conn is not None:
        overlay_row = artifact_read_overlay.latest_overlay_summary_for_snapshot(
            artifact_conn,
            snapshot_id=snapshot_id,
        )
    if owns_connection and artifact_conn is not None:
        artifact_conn.close()

    overlay_available = overlay_row is not None
    worktree_hash = str(overlay_row["worktree_hash"]) if overlay_row else None
    body = {
        "payload_kind": "summary",
        "overlay_advisory": True,
        "worktree_dirty": worktree_dirty,
        "overlay_available": overlay_available,
        "overlay_reason": "available"
        if overlay_available
        else ("clean_worktree" if not worktree_dirty else "overlay_unavailable"),
        "worktree_hash": worktree_hash,
        "warnings": [],
        "projections": _projection_rows(
            worktree_dirty=worktree_dirty,
            overlay_available=overlay_available,
        ),
    }
    return render_json_payload(body)


def _projection_rows(
    *,
    worktree_dirty: bool,
    overlay_available: bool,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for projection, profile in sorted(OVERLAY_PROFILE.items()):
        overlay_supported = bool(profile.get("overlay_supported", True))
        rows.append(
            {
                "projection": projection,
                "overlay_supported": overlay_supported,
                "payload_state": "committed_snapshot",
                "mode": "metadata_only" if overlay_supported else "unsupported",
                "scope_type": str(profile.get("scope_type") or "unknown"),
                "affected_by": list(profile.get("affected_by") or []),
                "current_state": _current_state(
                    worktree_dirty=worktree_dirty,
                    overlay_available=overlay_available,
                    overlay_supported=overlay_supported,
                ),
            }
        )
    return rows


def _current_state(
    *,
    worktree_dirty: bool,
    overlay_available: bool,
    overlay_supported: bool,
) -> str:
    if not worktree_dirty:
        return "committed_only"
    if not overlay_supported:
        return "unsupported"
    if not overlay_available:
        return "overlay_unavailable"
    return "metadata_only"


__all__ = ["render", "REDUCER_META"]
