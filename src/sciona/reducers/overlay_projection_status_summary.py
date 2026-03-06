# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Overlay projection support summary reducer."""

from __future__ import annotations

from ..overlay_access import load_overlay
from ..runtime import git as git_ops
from ..runtime.overlay_profile import OVERLAY_PROFILE
from .helpers.context import current_artifact_connection, fallback_artifact_connection
from .helpers.render import render_json_payload, require_connection
from .helpers.utils import require_latest_committed_snapshot
from .metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="overlay_projection_status_summary",
    category="metrics",
    risk_tier="normal",
    stage="diagnostics_metrics",
    placeholder="OVERLAY_PROJECTION_STATUS_SUMMARY",
    summary="Summarize dirty-worktree overlay support by reducer projection, "
    "including patchable versus metadata-only behavior. ",
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

    overlay = None
    if worktree_dirty and artifact_conn is not None and repo_root is not None:
        overlay = load_overlay(
            repo_root=repo_root,
            snapshot_id=snapshot_id,
            core_conn=conn,
            artifact_conn=artifact_conn,
        )
    if owns_connection and artifact_conn is not None:
        artifact_conn.close()

    overlay_available = overlay is not None
    body = {
        "payload_kind": "summary",
        "overlay_advisory": True,
        "worktree_dirty": worktree_dirty,
        "overlay_available": overlay_available,
        "overlay_reason": "available"
        if overlay_available
        else ("clean_worktree" if not worktree_dirty else "overlay_unavailable"),
        "worktree_hash": overlay.worktree_hash if overlay else None,
        "warnings": list(overlay.warnings) if overlay else [],
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
        supports_patch = bool(profile.get("supports_patch"))
        rows.append(
            {
                "projection": projection,
                "supports_patch": supports_patch,
                "mode": "patchable" if supports_patch else "metadata_only",
                "scope_type": str(profile.get("scope_type") or "unknown"),
                "affected_by": list(profile.get("affected_by") or []),
                "current_state": _current_state(
                    worktree_dirty=worktree_dirty,
                    overlay_available=overlay_available,
                    supports_patch=supports_patch,
                ),
            }
        )
    return rows


def _current_state(
    *,
    worktree_dirty: bool,
    overlay_available: bool,
    supports_patch: bool,
) -> str:
    if not worktree_dirty:
        return "committed_only"
    if not overlay_available:
        return "overlay_unavailable"
    if supports_patch:
        return "patchable"
    return "metadata_only"


__all__ = ["render", "REDUCER_META"]
