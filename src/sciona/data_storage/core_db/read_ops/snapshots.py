# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CoreDB read/query helpers."""

from __future__ import annotations

import sqlite3
from typing import Iterable, Sequence

from ..errors import SnapshotNotFoundError, UncommittedSnapshotError

def latest_committed_snapshot(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute(
        """
        SELECT snapshot_id, structural_hash, created_at
        FROM snapshots
        WHERE is_committed = 1
        ORDER BY COALESCE(git_commit_time, created_at) DESC, snapshot_id DESC
        LIMIT 1
        """
    ).fetchone()
    if not row:
        return None
    return {
        "snapshot_id": row["snapshot_id"],
        "structural_hash": row["structural_hash"],
        "created_at": row["created_at"],
    }

def latest_committed_snapshot_id(conn: sqlite3.Connection) -> str | None:
    """Return the latest committed snapshot id or None."""
    row = conn.execute(
        """
        SELECT snapshot_id
        FROM snapshots
        WHERE is_committed = 1
        ORDER BY COALESCE(git_commit_time, created_at) DESC, snapshot_id DESC
        LIMIT 1
        """
    ).fetchone()
    if row:
        return row["snapshot_id"]
    return None

def snapshot_git_commit_sha(conn: sqlite3.Connection, snapshot_id: str) -> str | None:
    row = conn.execute(
        """
        SELECT git_commit_sha
        FROM snapshots
        WHERE snapshot_id = ?
        """,
        (snapshot_id,),
    ).fetchone()
    if not row:
        return None
    return row["git_commit_sha"]


def snapshot_created_at(conn: sqlite3.Connection, snapshot_id: str) -> str | None:
    row = conn.execute(
        """
        SELECT created_at
        FROM snapshots
        WHERE snapshot_id = ?
        LIMIT 1
        """,
        (snapshot_id,),
    ).fetchone()
    if not row:
        return None
    return row["created_at"]

def count_committed_snapshots(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS count FROM snapshots WHERE is_committed = 1"
    ).fetchone()
    if not row or row["count"] is None:
        return 0
    return int(row["count"])

def list_committed_snapshots(conn: sqlite3.Connection) -> list[str]:
    """Return committed snapshot IDs ordered by newest first."""
    rows = conn.execute(
        """
        SELECT snapshot_id
        FROM snapshots
        WHERE is_committed = 1
        ORDER BY COALESCE(git_commit_time, created_at) DESC, snapshot_id DESC
        """
    ).fetchall()
    return [row["snapshot_id"] for row in rows]

def snapshot_is_committed(conn: sqlite3.Connection, snapshot_id: str) -> bool:
    row = conn.execute(
        "SELECT is_committed FROM snapshots WHERE snapshot_id = ?",
        (snapshot_id,),
    ).fetchone()
    if not row:
        return False
    try:
        return bool(row["is_committed"])
    except (TypeError, KeyError, IndexError):
        return bool(row[0])

def snapshot_exists(conn: sqlite3.Connection, snapshot_id: str) -> bool:
    """Return True when a snapshot id is present."""
    row = conn.execute(
        "SELECT 1 FROM snapshots WHERE snapshot_id = ? LIMIT 1",
        (snapshot_id,),
    ).fetchone()
    return bool(row)

def validate_snapshot_for_read(
    conn: sqlite3.Connection,
    snapshot_id: str,
    *,
    require_committed: bool = True,
) -> str:
    """Validate a snapshot id before read operations."""
    if not snapshot_exists(conn, snapshot_id):
        raise SnapshotNotFoundError(f"Snapshot '{snapshot_id}' was not found.")
    if require_committed and not snapshot_is_committed(conn, snapshot_id):
        raise UncommittedSnapshotError(
            f"Snapshot '{snapshot_id}' is not committed; latest committed snapshot is required."
        )
    return snapshot_id
