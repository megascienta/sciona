# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CoreDB read/query helpers."""

from __future__ import annotations

import sqlite3
from typing import Iterable, Sequence

from ..sql_utils import SQLITE_MAX_VARS, chunked
from .errors import SnapshotNotFoundError, UncommittedSnapshotError

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
