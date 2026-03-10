# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CoreDB read/query helpers."""

from __future__ import annotations

import sqlite3
from typing import Iterable, Sequence

from ..common.sql_utils import SQLITE_MAX_VARS, chunked
from .errors import SnapshotNotFoundError, UncommittedSnapshotError

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
    conn: sqlite3.Connection, snapshot_id: str, node_ids: Iterable[str]
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
            WHERE snapshot_id = ?
              AND structural_id IN ({placeholders})
            """,
            (snapshot_id, *node_list),
        ).fetchall()
        return {row[0]: row[1] for row in rows if row[1]}
    result: dict[str, str] = {}
    for batch in chunked(node_list, SQLITE_MAX_VARS):
        placeholders = ",".join("?" for _ in batch)
        rows = conn.execute(
            f"""
            SELECT structural_id, content_hash
            FROM node_instances
            WHERE snapshot_id = ?
              AND structural_id IN ({placeholders})
            """,
            (snapshot_id, *batch),
        ).fetchall()
        for row in rows:
            if row[1]:
                result[row[0]] = row[1]
    return result

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
