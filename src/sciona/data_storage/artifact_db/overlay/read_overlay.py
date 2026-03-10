# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""ArtifactDB overlay read helpers."""

from __future__ import annotations

import json
import sqlite3


def latest_overlay_summary_for_snapshot(
    conn: sqlite3.Connection,
    *,
    snapshot_id: str,
) -> dict[str, object] | None:
    row = conn.execute(
        """
        SELECT worktree_hash, summary_json, created_at
        FROM diff_overlay_summary
        WHERE snapshot_id = ?
        ORDER BY created_at DESC, worktree_hash DESC
        LIMIT 1
        """,
        (snapshot_id,),
    ).fetchone()
    if row is None:
        return None
    summary = _parse_json_summary(row["summary_json"])
    return {
        "worktree_hash": row["worktree_hash"],
        "created_at": row["created_at"],
        "summary": summary,
    }


def overlay_node_change_count(
    conn: sqlite3.Connection,
    *,
    snapshot_id: str,
    worktree_hash: str,
) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM diff_overlay
        WHERE snapshot_id = ?
          AND worktree_hash = ?
        """,
        (snapshot_id, worktree_hash),
    ).fetchone()
    return int(row["count"] or 0) if row else 0


def overlay_call_change_count(
    conn: sqlite3.Connection,
    *,
    snapshot_id: str,
    worktree_hash: str,
) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM diff_overlay_calls
        WHERE snapshot_id = ?
          AND worktree_hash = ?
        """,
        (snapshot_id, worktree_hash),
    ).fetchone()
    return int(row["count"] or 0) if row else 0


def _parse_json_summary(raw: object) -> dict[str, object] | None:
    if not raw or not isinstance(raw, str):
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


__all__ = [
    "latest_overlay_summary_for_snapshot",
    "overlay_call_change_count",
    "overlay_node_change_count",
]
