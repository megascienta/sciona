# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CoreDB read/query helpers."""

from __future__ import annotations

import sqlite3
from typing import Iterable, Sequence

from ...common.sql_utils import SQLITE_MAX_VARS, chunked

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
    if not node_types:
        return None
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
    if not node_types:
        return []
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


def snapshot_structural_ids(
    conn: sqlite3.Connection,
    snapshot_id: str,
) -> list[str]:
    rows = conn.execute(
        """
        SELECT DISTINCT structural_id
        FROM node_instances
        WHERE snapshot_id = ?
        """,
        (snapshot_id,),
    ).fetchall()
    return [row["structural_id"] for row in rows]

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
    if not node_types:
        return []
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


def language_file_node_counts(
    conn: sqlite3.Connection,
    snapshot_id: str,
) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT sn.language AS language,
               COUNT(DISTINCT ni.file_path) AS file_count,
               COUNT(DISTINCT ni.structural_id) AS node_count
        FROM node_instances ni
        JOIN structural_nodes sn ON sn.structural_id = ni.structural_id
        WHERE ni.snapshot_id = ?
        GROUP BY sn.language
        """,
        (snapshot_id,),
    ).fetchall()
    return [
        {
            "language": row["language"],
            "file_count": int(row["file_count"] or 0),
            "node_count": int(row["node_count"] or 0),
        }
        for row in rows
    ]


def language_file_node_distribution(
    conn: sqlite3.Connection,
    snapshot_id: str,
) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT sn.language AS language,
               ni.file_path AS file_path,
               COUNT(DISTINCT ni.structural_id) AS node_count
        FROM node_instances ni
        JOIN structural_nodes sn ON sn.structural_id = ni.structural_id
        WHERE ni.snapshot_id = ?
        GROUP BY sn.language, ni.file_path
        """,
        (snapshot_id,),
    ).fetchall()
    return [
        {
            "language": str(row["language"]),
            "file_path": str(row["file_path"]),
            "node_count": int(row["node_count"] or 0),
        }
        for row in rows
    ]


def caller_language_map(
    conn: sqlite3.Connection,
    snapshot_id: str,
) -> dict[str, str]:
    rows = conn.execute(
        """
        SELECT ni.structural_id AS structural_id,
               sn.language AS language
        FROM node_instances ni
        JOIN structural_nodes sn ON sn.structural_id = ni.structural_id
        WHERE ni.snapshot_id = ?
        """,
        (snapshot_id,),
    ).fetchall()
    mapping: dict[str, str] = {}
    for row in rows:
        mapping[str(row["structural_id"])] = str(row["language"])
    return mapping


def caller_node_metadata_map(
    conn: sqlite3.Connection,
    snapshot_id: str,
) -> dict[str, dict[str, object]]:
    rows = conn.execute(
        """
        SELECT ni.structural_id AS structural_id,
               sn.language AS language,
               sn.node_type AS node_type,
               ni.qualified_name AS qualified_name,
               ni.file_path AS file_path,
               ni.start_line AS start_line,
               ni.end_line AS end_line
        FROM node_instances ni
        JOIN structural_nodes sn ON sn.structural_id = ni.structural_id
        WHERE ni.snapshot_id = ?
        """,
        (snapshot_id,),
    ).fetchall()
    mapping: dict[str, dict[str, object]] = {}
    for row in rows:
        structural_id = str(row["structural_id"])
        mapping[structural_id] = {
            "language": str(row["language"]),
            "node_type": str(row["node_type"]),
            "qualified_name": str(row["qualified_name"]),
            "file_path": str(row["file_path"]),
            "start_line": int(row["start_line"]) if row["start_line"] is not None else None,
            "end_line": int(row["end_line"]) if row["end_line"] is not None else None,
        }
    return mapping
