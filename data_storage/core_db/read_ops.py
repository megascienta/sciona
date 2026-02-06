# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CoreDB read/query helpers."""

from __future__ import annotations

import sqlite3
from typing import Iterable, Sequence

from ..sql_utils import SQLITE_MAX_VARS, chunked
from .errors import SnapshotNotFoundError, UncommittedSnapshotError


def latest_committed_snapshot(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute(
        """
        SELECT snapshot_id, structural_hash, created_at
        FROM snapshots
        WHERE is_committed = 1
        ORDER BY created_at DESC
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
        ORDER BY created_at DESC
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
        ORDER BY created_at DESC
        """
    ).fetchall()
    return [row["snapshot_id"] for row in rows]


def lookup_node_instances(
    conn: sqlite3.Connection,
    *,
    snapshot_id: str,
    node_type: str,
    qualified_name: str,
) -> list[dict[str, str]]:
    rows = conn.execute(
        """
        SELECT sn.structural_id,
               sn.node_type,
               sn.language,
               ni.qualified_name,
               ni.file_path
        FROM node_instances ni
        JOIN structural_nodes sn ON sn.structural_id = ni.structural_id
        WHERE ni.snapshot_id = ?
          AND ni.qualified_name = ?
          AND sn.node_type = ?
        ORDER BY sn.language, ni.file_path
        """,
        (snapshot_id, qualified_name, node_type),
    ).fetchall()
    return [
        {
            "structural_id": row["structural_id"],
            "node_type": row["node_type"],
            "language": row["language"],
            "qualified_name": row["qualified_name"],
            "file_path": row["file_path"],
        }
        for row in rows
    ]


def lookup_structural_id(
    conn: sqlite3.Connection,
    snapshot_id: str,
    structural_id: str,
    node_types: Sequence[str],
) -> dict[str, str] | None:
    placeholders = ", ".join("?" for _ in node_types)
    params: list[str] = [snapshot_id, *node_types, structural_id]
    row = conn.execute(
        f"""
        SELECT sn.structural_id,
               sn.node_type,
               sn.language,
               ni.qualified_name,
               ni.file_path
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type IN ({placeholders})
          AND sn.structural_id = ?
        LIMIT 1
        """,
        tuple(params),
    ).fetchone()
    if not row:
        return None
    return {
        "structural_id": row["structural_id"],
        "node_type": row["node_type"],
        "language": row["language"],
        "qualified_name": row["qualified_name"],
        "file_path": row["file_path"],
    }


def search_node_instances(
    conn: sqlite3.Connection,
    snapshot_id: str,
    node_types: Sequence[str],
    query: str,
    *,
    limit: int = 5,
) -> list[dict[str, str]]:
    lowered = query.lower()
    placeholders = ", ".join("?" for _ in node_types)
    params: list[str] = [snapshot_id, *node_types, f"%{lowered}%", limit]
    rows = conn.execute(
        f"""
        SELECT sn.structural_id,
               sn.node_type,
               sn.language,
               ni.qualified_name,
               ni.file_path
        FROM node_instances ni
        JOIN structural_nodes sn ON sn.structural_id = ni.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type IN ({placeholders})
          AND LOWER(ni.qualified_name) LIKE ?
        ORDER BY ni.qualified_name, sn.language, ni.file_path
        LIMIT ?
        """,
        tuple(params),
    ).fetchall()
    return [
        {
            "structural_id": row["structural_id"],
            "node_type": row["node_type"],
            "language": row["language"],
            "qualified_name": row["qualified_name"],
            "file_path": row["file_path"],
        }
        for row in rows
    ]


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


def snapshot_node_hashes(conn: sqlite3.Connection, snapshot_id: str) -> dict[str, str]:
    rows = conn.execute(
        """
        SELECT structural_id, content_hash
        FROM node_instances
        WHERE snapshot_id = ?
        """,
        (snapshot_id,),
    ).fetchall()
    return {row["structural_id"]: row["content_hash"] for row in rows}


def node_hashes_for_ids(
    conn: sqlite3.Connection, node_ids: Iterable[str]
) -> dict[str, str]:
    if not node_ids:
        return {}
    node_list = list(node_ids)
    if len(node_list) <= SQLITE_MAX_VARS:
        placeholders = ",".join("?" for _ in node_list)
        rows = conn.execute(
            f"""
            SELECT structural_id, content_hash
            FROM node_instances
            WHERE structural_id IN ({placeholders})
            """,
            tuple(node_list),
        ).fetchall()
        return {row[0]: row[1] for row in rows if row[1]}
    result: dict[str, str] = {}
    for batch in chunked(node_list, SQLITE_MAX_VARS):
        placeholders = ",".join("?" for _ in batch)
        rows = conn.execute(
            f"""
            SELECT structural_id, content_hash
            FROM node_instances
            WHERE structural_id IN ({placeholders})
            """,
            tuple(batch),
        ).fetchall()
        for row in rows:
            if row[1]:
                result[row[0]] = row[1]
    return result


def list_structural_nodes(
    conn: sqlite3.Connection,
    snapshot_id: str,
) -> list[tuple[str, str]]:
    rows = conn.execute(
        """
        SELECT sn.structural_id, sn.node_type
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
        """,
        (snapshot_id,),
    ).fetchall()
    return [(row["structural_id"], row["node_type"]) for row in rows]


def list_edges(
    conn: sqlite3.Connection,
    snapshot_id: str,
) -> list[tuple[str, str, str]]:
    rows = conn.execute(
        """
        SELECT src_structural_id, dst_structural_id, edge_type
        FROM edges
        WHERE snapshot_id = ?
        """,
        (snapshot_id,),
    ).fetchall()
    return [
        (row["src_structural_id"], row["dst_structural_id"], row["edge_type"])
        for row in rows
    ]


def list_nodes_with_names(
    conn: sqlite3.Connection,
    snapshot_id: str,
) -> list[tuple[str, str, str]]:
    rows = conn.execute(
        """
        SELECT sn.structural_id, sn.node_type, ni.qualified_name
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
        ORDER BY sn.node_type, ni.qualified_name
        """,
        (snapshot_id,),
    ).fetchall()
    return [
        (row["structural_id"], row["node_type"], row["qualified_name"]) for row in rows
    ]


def list_edges_by_type(
    conn: sqlite3.Connection,
    snapshot_id: str,
    edge_type: str,
) -> list[tuple[str, str]]:
    rows = conn.execute(
        """
        SELECT src_structural_id, dst_structural_id
        FROM edges
        WHERE snapshot_id = ?
          AND edge_type = ?
        """,
        (snapshot_id, edge_type),
    ).fetchall()
    return [(row["src_structural_id"], row["dst_structural_id"]) for row in rows]


def list_nodes_by_types(
    conn: sqlite3.Connection,
    snapshot_id: str,
    node_types: Sequence[str],
) -> list[tuple[str, str, str]]:
    placeholders = ",".join(["?"] * len(node_types))
    rows = conn.execute(
        f"""
        SELECT sn.structural_id, sn.node_type, ni.qualified_name
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
          AND sn.node_type IN ({placeholders})
        """,
        (snapshot_id, *node_types),
    ).fetchall()
    return [(row[0], row[1], row[2]) for row in rows]


def node_instances_for_file_paths(
    conn: sqlite3.Connection,
    snapshot_id: str,
    file_paths: Sequence[str],
) -> list[dict[str, object]]:
    if not file_paths:
        return []
    rows: list[dict[str, object]] = []
    for batch in chunked(list(file_paths), SQLITE_MAX_VARS - 1):
        placeholders = ",".join("?" for _ in batch)
        params = [snapshot_id, *batch]
        batch_rows = conn.execute(
            f"""
            SELECT sn.structural_id,
                   sn.node_type,
                   sn.language,
                   ni.qualified_name,
                   ni.file_path,
                   ni.start_line,
                   ni.end_line,
                   ni.content_hash
            FROM structural_nodes sn
            JOIN node_instances ni ON ni.structural_id = sn.structural_id
            WHERE ni.snapshot_id = ?
              AND ni.file_path IN ({placeholders})
            """,
            params,
        ).fetchall()
        for row in batch_rows:
            rows.append(
                {
                    "structural_id": row["structural_id"],
                    "node_type": row["node_type"],
                    "language": row["language"],
                    "qualified_name": row["qualified_name"],
                    "file_path": row["file_path"],
                    "start_line": row["start_line"],
                    "end_line": row["end_line"],
                    "content_hash": row["content_hash"],
                }
            )
    return rows


def edges_for_source_ids(
    conn: sqlite3.Connection,
    snapshot_id: str,
    src_structural_ids: Sequence[str],
) -> list[tuple[str, str, str]]:
    if not src_structural_ids:
        return []
    edges: list[tuple[str, str, str]] = []
    for batch in chunked(list(src_structural_ids), SQLITE_MAX_VARS - 2):
        placeholders = ",".join("?" for _ in batch)
        params = [snapshot_id, *batch]
        rows = conn.execute(
            f"""
            SELECT src_structural_id, dst_structural_id, edge_type
            FROM edges
            WHERE snapshot_id = ?
              AND src_structural_id IN ({placeholders})
            """,
            params,
        ).fetchall()
        for row in rows:
            edges.append(
                (row["src_structural_id"], row["dst_structural_id"], row["edge_type"])
            )
    return edges


def structural_hash_node_entries(
    conn: sqlite3.Connection, snapshot_id: str
) -> list[str]:
    rows = conn.execute(
        """
        SELECT sn.structural_id,
               sn.node_type,
               sn.language,
               ni.qualified_name,
               ni.file_path,
               ni.start_line,
               ni.end_line,
               ni.content_hash
        FROM structural_nodes sn
        JOIN node_instances ni ON ni.structural_id = sn.structural_id
        WHERE ni.snapshot_id = ?
        ORDER BY sn.structural_id ASC
        """,
        (snapshot_id,),
    ).fetchall()
    return [
        "|".join(
            [
                "N",
                row["structural_id"],
                row["node_type"],
                row["language"],
                row["qualified_name"],
                row["file_path"],
                str(row["start_line"]),
                str(row["end_line"]),
                row["content_hash"],
            ]
        )
        for row in rows
    ]


def structural_hash_edge_entries(
    conn: sqlite3.Connection, snapshot_id: str
) -> list[str]:
    rows = conn.execute(
        """
        SELECT snapshot_id,
               src_structural_id,
               dst_structural_id,
               edge_type
        FROM edges
        WHERE snapshot_id = ?
        ORDER BY src_structural_id ASC, dst_structural_id ASC, edge_type ASC
        """,
        (snapshot_id,),
    ).fetchall()
    return [
        "|".join(
            [
                "E",
                row["src_structural_id"],
                row["dst_structural_id"],
                row["edge_type"],
            ]
        )
        for row in rows
    ]
