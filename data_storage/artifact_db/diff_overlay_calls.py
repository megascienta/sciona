"""Diff overlay call-edge storage for dirty-worktree payload augmentation."""

from __future__ import annotations

import sqlite3
from typing import Iterable, List


def overlay_exists(
    conn: sqlite3.Connection, snapshot_id: str, worktree_hash: str
) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM diff_overlay_calls
        WHERE snapshot_id = ?
          AND worktree_hash = ?
        LIMIT 1
        """,
        (snapshot_id, worktree_hash),
    ).fetchone()
    return bool(row)


def fetch_call_rows(
    conn: sqlite3.Connection,
    snapshot_id: str,
    worktree_hash: str,
) -> List[dict[str, str | None]]:
    rows = conn.execute(
        """
        SELECT src_structural_id,
               dst_structural_id,
               diff_kind,
               src_node_type,
               dst_node_type,
               src_qualified_name,
               dst_qualified_name,
               src_file_path,
               dst_file_path
        FROM diff_overlay_calls
        WHERE snapshot_id = ?
          AND worktree_hash = ?
        ORDER BY src_structural_id, dst_structural_id
        """,
        (snapshot_id, worktree_hash),
    ).fetchall()
    return [
        {
            "src_structural_id": row["src_structural_id"],
            "dst_structural_id": row["dst_structural_id"],
            "diff_kind": row["diff_kind"],
            "src_node_type": row["src_node_type"],
            "dst_node_type": row["dst_node_type"],
            "src_qualified_name": row["src_qualified_name"],
            "dst_qualified_name": row["dst_qualified_name"],
            "src_file_path": row["src_file_path"],
            "dst_file_path": row["dst_file_path"],
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
        DELETE FROM diff_overlay_calls
        WHERE snapshot_id = ?
          AND worktree_hash = ?
        """,
        (snapshot_id, worktree_hash),
    )


def clear_all(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM diff_overlay_calls")


def insert_call_rows(
    conn: sqlite3.Connection,
    rows: Iterable[dict[str, str | None]],
) -> None:
    payload = [
        (
            row["snapshot_id"],
            row["worktree_hash"],
            row["src_structural_id"],
            row["dst_structural_id"],
            row["diff_kind"],
            row.get("src_node_type"),
            row.get("dst_node_type"),
            row.get("src_qualified_name"),
            row.get("dst_qualified_name"),
            row.get("src_file_path"),
            row.get("dst_file_path"),
            row["created_at"],
        )
        for row in rows
    ]
    if not payload:
        return
    conn.executemany(
        """
        INSERT OR REPLACE INTO diff_overlay_calls(
            snapshot_id,
            worktree_hash,
            src_structural_id,
            dst_structural_id,
            diff_kind,
            src_node_type,
            dst_node_type,
            src_qualified_name,
            dst_qualified_name,
            src_file_path,
            dst_file_path,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        payload,
    )


__all__ = [
    "clear_all",
    "clear_overlay",
    "fetch_call_rows",
    "insert_call_rows",
    "overlay_exists",
]
