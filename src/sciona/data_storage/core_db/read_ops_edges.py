# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""CoreDB read/query helpers."""

from __future__ import annotations

import sqlite3
from typing import Iterable, Sequence

from ..sql_utils import SQLITE_MAX_VARS, chunked
from .errors import SnapshotNotFoundError, UncommittedSnapshotError

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


def language_edge_counts(
    conn: sqlite3.Connection,
    snapshot_id: str,
) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT src.language AS language,
               COUNT(*) AS edge_count
        FROM edges e
        JOIN structural_nodes src ON src.structural_id = e.src_structural_id
        WHERE e.snapshot_id = ?
        GROUP BY src.language
        """,
        (snapshot_id,),
    ).fetchall()
    return [
        {
            "language": row["language"],
            "edge_count": int(row["edge_count"] or 0),
        }
        for row in rows
    ]
