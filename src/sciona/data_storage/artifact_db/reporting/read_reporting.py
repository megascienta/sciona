# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""ArtifactDB reporting reads."""

from __future__ import annotations

import sqlite3


def callsite_pair_caller_counts(
    conn: sqlite3.Connection,
    *,
    snapshot_id: str,
) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT caller_id,
               COUNT(*) AS pair_count
        FROM callsite_pairs
        WHERE snapshot_id = ?
        GROUP BY caller_id
        """,
        (snapshot_id,),
    ).fetchall()
    return [
        {
            "caller_id": row["caller_id"],
            "pair_count": int(row["pair_count"] or 0),
        }
        for row in rows
    ]


def node_call_caller_counts(
    conn: sqlite3.Connection,
) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT caller_id,
               COUNT(*) AS edge_count
        FROM node_calls
        GROUP BY caller_id
        """
    ).fetchall()
    return [
        {
            "caller_id": row["caller_id"],
            "edge_count": int(row["edge_count"] or 0),
        }
        for row in rows
    ]


def graph_edge_source_counts(
    conn: sqlite3.Connection,
) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT src_node_id,
               COUNT(*) AS edge_count
        FROM graph_edges
        GROUP BY src_node_id
        """
    ).fetchall()
    return [
        {
            "src_node_id": row["src_node_id"],
            "edge_count": int(row["edge_count"] or 0),
        }
        for row in rows
    ]


__all__ = [
    "callsite_pair_caller_counts",
    "graph_edge_source_counts",
    "node_call_caller_counts",
]
