"""ArtifactDB graph write helpers."""

from __future__ import annotations

import sqlite3
from typing import Iterable


def reset_graph_index(conn: sqlite3.Connection) -> None:
    """Clear graph tables. Build pipeline should call this before rebuilding index."""
    conn.execute("DELETE FROM graph_edges")
    conn.execute("DELETE FROM graph_nodes")


def insert_graph_nodes(
    conn: sqlite3.Connection, *, rows: Iterable[tuple[str, str]]
) -> None:
    """rows: (node_id, node_kind)"""
    conn.executemany(
        "INSERT OR REPLACE INTO graph_nodes(node_id, node_kind) VALUES (?, ?)",
        list(rows),
    )


def insert_graph_edges(
    conn: sqlite3.Connection,
    *,
    rows: Iterable[tuple[str, str, str]],
) -> None:
    """rows: (src_node_id, dst_node_id, edge_kind)"""
    conn.executemany(
        """
        INSERT OR IGNORE INTO graph_edges(src_node_id, dst_node_id, edge_kind)
        VALUES (?, ?, ?)
        """,
        list(rows),
    )
