# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Overlay impact summary reducer."""

from __future__ import annotations

import json

from ..helpers.context import current_artifact_connection, fallback_artifact_connection
from ..helpers.render import render_json_payload, require_connection
from ..helpers.utils import require_latest_committed_snapshot
from ..metadata import ReducerMeta

REDUCER_META = ReducerMeta(
    reducer_id="overlay_impact_summary",
    category="composites",
    scope="codebase",
    placeholders=("OVERLAY_IMPACT_SUMMARY",),
    determinism="conditional",
    payload_size_stats=None,
    summary="Advisory summary of dirty-worktree diff overlay impact for the committed snapshot. "
    "Use when triaging uncommitted changes; output is non-authoritative. "
    "Scope: codebase-level overlay synthesis. Payload kind: summary.",
    lossy=True,
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
        row = artifact_conn.execute(
            """
            SELECT worktree_hash, summary_json, created_at
            FROM diff_overlay_summary
            WHERE snapshot_id = ?
            ORDER BY created_at DESC, worktree_hash DESC
            LIMIT 1
            """,
            (snapshot_id,),
        ).fetchone()
        if row:
            summary_payload = _parse_summary(row["summary_json"])
            worktree_hash = row["worktree_hash"]
            body["overlay_available"] = True
            body["worktree_hash"] = worktree_hash
            body["created_at"] = row["created_at"]
            body["summary"] = summary_payload
            body["node_change_count"] = _count_node_changes(
                artifact_conn,
                snapshot_id=snapshot_id,
                worktree_hash=worktree_hash,
            )
            body["call_change_count"] = _count_call_changes(
                artifact_conn,
                snapshot_id=snapshot_id,
                worktree_hash=worktree_hash,
            )
    if owns_connection and artifact_conn is not None:
        artifact_conn.close()
    return render_json_payload(body)


def _parse_summary(raw: object) -> dict[str, object] | None:
    if not raw or not isinstance(raw, str):
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _count_node_changes(artifact_conn, *, snapshot_id: str, worktree_hash: str) -> int:
    row = artifact_conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM diff_overlay
        WHERE snapshot_id = ?
          AND worktree_hash = ?
        """,
        (snapshot_id, worktree_hash),
    ).fetchone()
    return int(row["count"] or 0) if row else 0


def _count_call_changes(artifact_conn, *, snapshot_id: str, worktree_hash: str) -> int:
    row = artifact_conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM diff_overlay_calls
        WHERE snapshot_id = ?
          AND worktree_hash = ?
        """,
        (snapshot_id, worktree_hash),
    ).fetchone()
    return int(row["count"] or 0) if row else 0


__all__ = ["render", "REDUCER_META"]
