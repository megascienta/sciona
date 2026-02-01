"""ArtifactDB rollup persistence helpers."""
from __future__ import annotations

import sqlite3
from typing import Iterable


def reset_graph_rollups(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM module_call_edges")
    conn.execute("DELETE FROM class_call_edges")
    conn.execute("DELETE FROM node_fan_stats")


def insert_module_call_edges(
    conn: sqlite3.Connection,
    *,
    rows: Iterable[tuple[str, str, int]],
) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO module_call_edges(src_module_id, dst_module_id, call_count)
        VALUES (?, ?, ?)
        """,
        list(rows),
    )


def insert_class_call_edges(
    conn: sqlite3.Connection,
    *,
    rows: Iterable[tuple[str, str, int]],
) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO class_call_edges(src_class_id, dst_class_id, call_count)
        VALUES (?, ?, ?)
        """,
        list(rows),
    )


def insert_node_fan_stats(
    conn: sqlite3.Connection,
    *,
    rows: Iterable[tuple[str, str, str, int, int]],
) -> None:
    conn.executemany(
        """
        INSERT OR REPLACE INTO node_fan_stats(node_id, node_kind, edge_kind, fan_in, fan_out)
        VALUES (?, ?, ?, ?, ?)
        """,
        list(rows),
    )
