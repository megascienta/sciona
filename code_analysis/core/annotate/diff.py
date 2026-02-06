"""Snapshot diff helpers for incremental ingestion."""

from __future__ import annotations

from typing import Optional


def previous_snapshot_id(conn, current_snapshot_id: str) -> Optional[str]:
    current = conn.execute(
        "SELECT created_at FROM snapshots WHERE snapshot_id = ?",
        (current_snapshot_id,),
    ).fetchone()
    if not current:
        return None
    current_created_at = current["created_at"]
    if current_created_at:
        row = conn.execute(
            """
            SELECT snapshot_id FROM snapshots
            WHERE snapshot_id != ?
              AND is_committed = 1
              AND (
                created_at < ?
                OR (created_at = ? AND snapshot_id < ?)
              )
            ORDER BY created_at DESC, snapshot_id DESC
            LIMIT 1
            """,
            (
                current_snapshot_id,
                current_created_at,
                current_created_at,
                current_snapshot_id,
            ),
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT snapshot_id FROM snapshots
            WHERE snapshot_id != ? AND is_committed = 1
            ORDER BY created_at DESC, snapshot_id DESC
            LIMIT 1
            """,
            (current_snapshot_id,),
        ).fetchone()
    if row:
        return row["snapshot_id"]
    return None
