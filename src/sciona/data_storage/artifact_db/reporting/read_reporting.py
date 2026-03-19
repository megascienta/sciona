# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""ArtifactDB reporting reads."""

from __future__ import annotations

import sqlite3


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
    "graph_edge_source_counts",
    "node_call_caller_counts",
]
