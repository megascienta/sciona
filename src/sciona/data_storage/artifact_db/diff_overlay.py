# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Diff overlay storage for dirty-worktree payload augmentation."""

from __future__ import annotations

import sqlite3
from typing import Iterable, List


def overlay_exists(
    conn: sqlite3.Connection, snapshot_id: str, worktree_hash: str
) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM diff_overlay
        WHERE snapshot_id = ?
          AND worktree_hash = ?
        LIMIT 1
        """,
        (snapshot_id, worktree_hash),
    ).fetchone()
    return bool(row)


def fetch_overlay_rows(
    conn: sqlite3.Connection,
    snapshot_id: str,
    worktree_hash: str,
) -> List[dict[str, str | None]]:
    rows = conn.execute(
        """
        SELECT structural_id,
               node_type,
               diff_kind,
               field,
               old_value,
               new_value
        FROM diff_overlay
        WHERE snapshot_id = ?
          AND worktree_hash = ?
        ORDER BY node_type, structural_id, field
        """,
        (snapshot_id, worktree_hash),
    ).fetchall()
    return [
        {
            "structural_id": row["structural_id"],
            "node_type": row["node_type"],
            "diff_kind": row["diff_kind"],
            "field": row["field"],
            "old_value": row["old_value"],
            "new_value": row["new_value"],
        }
        for row in rows
    ]


def clear_overlay(
    conn: sqlite3.Connection,
    snapshot_id: str,
    worktree_hash: str,
) -> None:
    conn.execute(
        """
        DELETE FROM diff_overlay
        WHERE snapshot_id = ?
          AND worktree_hash = ?
        """,
        (snapshot_id, worktree_hash),
    )


def clear_all(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM diff_overlay")


def insert_overlay_rows(
    conn: sqlite3.Connection,
    rows: Iterable[dict[str, str | None]],
) -> None:
    payload = [
        (
            row["snapshot_id"],
            row["worktree_hash"],
            row["structural_id"],
            row["node_type"],
            row["diff_kind"],
            row.get("field"),
            row.get("old_value"),
            row.get("new_value"),
            row["created_at"],
        )
        for row in rows
    ]
    if not payload:
        return
    conn.executemany(
        """
        INSERT OR REPLACE INTO diff_overlay(
            snapshot_id,
            worktree_hash,
            structural_id,
            node_type,
            diff_kind,
            field,
            old_value,
            new_value,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        payload,
    )


__all__ = [
    "clear_all",
    "clear_overlay",
    "fetch_overlay_rows",
    "insert_overlay_rows",
    "overlay_exists",
]
