# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CoreDB write/maintenance helpers."""

from __future__ import annotations

import sqlite3

from ..encoding import bool_to_int


def insert_snapshot(
    conn: sqlite3.Connection,
    *,
    snapshot_id: str,
    created_at: str,
    source: str,
    structural_hash: str,
    is_committed: bool,
    git_commit_sha: str | None = None,
    git_commit_time: str | None = None,
    git_branch: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO snapshots(
            snapshot_id,
            created_at,
            source,
            is_committed,
            structural_hash,
            git_commit_sha,
            git_commit_time,
            git_branch
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            snapshot_id,
            created_at,
            source,
            bool_to_int(is_committed),
            structural_hash,
            git_commit_sha,
            git_commit_time,
            git_branch,
        ),
    )


def insert_structural_node(
    conn: sqlite3.Connection,
    *,
    structural_id: str,
    node_type: str,
    language: str,
    created_snapshot_id: str,
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO structural_nodes(
            structural_id, node_type, language, created_snapshot_id
        ) VALUES (?, ?, ?, ?)
        """,
        (
            structural_id,
            node_type,
            language,
            created_snapshot_id,
        ),
    )


def upsert_node_instance(
    conn: sqlite3.Connection,
    *,
    instance_id: str,
    structural_id: str,
    snapshot_id: str,
    qualified_name: str,
    file_path: str,
    start_line: int,
    end_line: int,
    content_hash: str,
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO node_instances(
            instance_id,
            structural_id,
            snapshot_id,
            qualified_name,
            file_path,
            start_line,
            end_line,
            content_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            instance_id,
            structural_id,
            snapshot_id,
            qualified_name,
            file_path,
            start_line,
            end_line,
            content_hash,
        ),
    )


def insert_node_instance(
    conn: sqlite3.Connection,
    *,
    instance_id: str,
    structural_id: str,
    snapshot_id: str,
    qualified_name: str,
    file_path: str,
    start_line: int,
    end_line: int,
    content_hash: str,
) -> None:
    upsert_node_instance(
        conn,
        instance_id=instance_id,
        structural_id=structural_id,
        snapshot_id=snapshot_id,
        qualified_name=qualified_name,
        file_path=file_path,
        start_line=start_line,
        end_line=end_line,
        content_hash=content_hash,
    )


def insert_edge(
    conn: sqlite3.Connection,
    *,
    snapshot_id: str,
    src_structural_id: str,
    dst_structural_id: str,
    edge_type: str,
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO edges(
            snapshot_id, src_structural_id, dst_structural_id, edge_type
        ) VALUES (?, ?, ?, ?)
        """,
        (
            snapshot_id,
            src_structural_id,
            dst_structural_id,
            edge_type,
        ),
    )


def delete_snapshot_tree(conn: sqlite3.Connection, snapshot_id: str) -> None:
    """Remove a snapshot and all derived artifacts."""
    conn.execute("DELETE FROM node_instances WHERE snapshot_id = ?", (snapshot_id,))
    conn.execute("DELETE FROM edges WHERE snapshot_id = ?", (snapshot_id,))
    conn.execute("DELETE FROM snapshots WHERE snapshot_id = ?", (snapshot_id,))


def rekey_snapshot_id(
    conn: sqlite3.Connection,
    *,
    from_snapshot_id: str,
    to_snapshot_id: str,
) -> None:
    """Replace snapshot identifiers across CoreDB tables."""
    if from_snapshot_id == to_snapshot_id:
        return
    conn.execute(
        "UPDATE snapshots SET snapshot_id = ? WHERE snapshot_id = ?",
        (to_snapshot_id, from_snapshot_id),
    )
    conn.execute(
        "UPDATE node_instances SET snapshot_id = ? WHERE snapshot_id = ?",
        (to_snapshot_id, from_snapshot_id),
    )
    conn.execute(
        "UPDATE edges SET snapshot_id = ? WHERE snapshot_id = ?",
        (to_snapshot_id, from_snapshot_id),
    )
    conn.execute(
        "UPDATE structural_nodes SET created_snapshot_id = ? WHERE created_snapshot_id = ?",
        (to_snapshot_id, from_snapshot_id),
    )


def purge_uncommitted_snapshots(
    conn: sqlite3.Connection, exclude: str | None = None
) -> list[str]:
    """Delete temporary snapshots that were never committed."""
    rows = conn.execute(
        "SELECT snapshot_id FROM snapshots WHERE is_committed = 0"
    ).fetchall()
    purged: list[str] = []
    for row in rows:
        snapshot_id = row["snapshot_id"]
        if exclude and snapshot_id == exclude:
            continue
        delete_snapshot_tree(conn, snapshot_id)
        purged.append(snapshot_id)
    return purged


def delete_committed_snapshots_except(
    conn: sqlite3.Connection, keep_snapshot_id: str
) -> list[str]:
    """Delete committed snapshots except the provided snapshot id."""
    rows = conn.execute(
        """
        SELECT snapshot_id
        FROM snapshots
        WHERE is_committed = 1
          AND snapshot_id != ?
        """,
        (keep_snapshot_id,),
    ).fetchall()
    removed: list[str] = []
    for row in rows:
        snapshot_id = row["snapshot_id"]
        delete_snapshot_tree(conn, snapshot_id)
        removed.append(snapshot_id)
    return removed


def prune_orphan_structural_nodes(conn: sqlite3.Connection) -> int:
    """Drop structural nodes that have no node_instances in the database."""
    cursor = conn.execute(
        """
        DELETE FROM structural_nodes
        WHERE structural_id NOT IN (
            SELECT DISTINCT structural_id
            FROM node_instances
        )
        """
    )
    return int(cursor.rowcount or 0)
