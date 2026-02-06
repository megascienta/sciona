"""Diff overlay summary storage for dirty-worktree payload augmentation."""

from __future__ import annotations

import json
import sqlite3
from typing import Optional


def overlay_exists(
    conn: sqlite3.Connection, snapshot_id: str, worktree_hash: str
) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM diff_overlay_summary
        WHERE snapshot_id = ?
          AND worktree_hash = ?
        LIMIT 1
        """,
        (snapshot_id, worktree_hash),
    ).fetchone()
    return bool(row)


def fetch_summary(
    conn: sqlite3.Connection,
    snapshot_id: str,
    worktree_hash: str,
) -> Optional[dict[str, object]]:
    row = conn.execute(
        """
        SELECT summary_json
        FROM diff_overlay_summary
        WHERE snapshot_id = ?
          AND worktree_hash = ?
        LIMIT 1
        """,
        (snapshot_id, worktree_hash),
    ).fetchone()
    if not row or not row["summary_json"]:
        return None
    try:
        return json.loads(row["summary_json"])
    except json.JSONDecodeError:
        return None


def clear_overlay(
    conn: sqlite3.Connection,
    snapshot_id: str,
    worktree_hash: str,
) -> None:
    conn.execute(
        """
        DELETE FROM diff_overlay_summary
        WHERE snapshot_id = ?
          AND worktree_hash = ?
        """,
        (snapshot_id, worktree_hash),
    )


def clear_all(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM diff_overlay_summary")


def insert_summary(
    conn: sqlite3.Connection,
    *,
    snapshot_id: str,
    worktree_hash: str,
    summary: dict[str, object],
    created_at: str,
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO diff_overlay_summary(
            snapshot_id,
            worktree_hash,
            summary_json,
            created_at
        ) VALUES (?, ?, ?, ?)
        """,
        (
            snapshot_id,
            worktree_hash,
            json.dumps(summary, sort_keys=True),
            created_at,
        ),
    )


__all__ = [
    "clear_all",
    "clear_overlay",
    "fetch_summary",
    "insert_summary",
    "overlay_exists",
]
