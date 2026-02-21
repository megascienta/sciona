# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

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


def delete_module_call_edges_for_nodes(
    conn: sqlite3.Connection,
    *,
    node_ids: Iterable[str],
) -> None:
    ids = list(node_ids)
    if not ids:
        return
    placeholders = ",".join("?" for _ in ids)
    conn.execute(
        f"""
        DELETE FROM module_call_edges
        WHERE src_module_id IN ({placeholders})
           OR dst_module_id IN ({placeholders})
        """,
        tuple(ids + ids),
    )


def delete_class_call_edges_for_nodes(
    conn: sqlite3.Connection,
    *,
    node_ids: Iterable[str],
) -> None:
    ids = list(node_ids)
    if not ids:
        return
    placeholders = ",".join("?" for _ in ids)
    conn.execute(
        f"""
        DELETE FROM class_call_edges
        WHERE src_class_id IN ({placeholders})
           OR dst_class_id IN ({placeholders})
        """,
        tuple(ids + ids),
    )


def delete_node_fan_stats_for_nodes(
    conn: sqlite3.Connection,
    *,
    node_ids: Iterable[str],
) -> None:
    ids = list(node_ids)
    if not ids:
        return
    placeholders = ",".join("?" for _ in ids)
    conn.execute(
        f"DELETE FROM node_fan_stats WHERE node_id IN ({placeholders})",
        tuple(ids),
    )
