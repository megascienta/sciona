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


def reset_rollup_temp_tables(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS temp.module_lookup")
    conn.execute("DROP TABLE IF EXISTS temp.method_to_class")


def load_module_lookup(
    conn: sqlite3.Connection,
    *,
    rows: Iterable[tuple[str, str]],
) -> None:
    conn.execute(
        """
        CREATE TEMP TABLE module_lookup (
            node_id TEXT PRIMARY KEY,
            module_id TEXT NOT NULL
        )
        """
    )
    conn.executemany(
        "INSERT INTO module_lookup(node_id, module_id) VALUES (?, ?)",
        rows,
    )


def load_method_to_class(
    conn: sqlite3.Connection,
    *,
    rows: Iterable[tuple[str, str]],
) -> None:
    conn.execute(
        """
        CREATE TEMP TABLE method_to_class (
            callable_id TEXT PRIMARY KEY,
            class_id TEXT NOT NULL
        )
        """
    )
    conn.executemany(
        "INSERT INTO method_to_class(callable_id, class_id) VALUES (?, ?)",
        rows,
    )


def insert_module_call_edges_from_graph(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO module_call_edges(src_module_id, dst_module_id, call_count)
        SELECT ml_src.module_id, ml_dst.module_id, COUNT(*) AS call_count
        FROM graph_edges ge
        JOIN module_lookup ml_src ON ml_src.node_id = ge.src_node_id
        JOIN module_lookup ml_dst ON ml_dst.node_id = ge.dst_node_id
        WHERE ge.edge_kind = 'CALLS'
        GROUP BY ml_src.module_id, ml_dst.module_id
        """
    )


def insert_class_call_edges_from_graph(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO class_call_edges(src_class_id, dst_class_id, call_count)
        SELECT mtc_src.class_id, mtc_dst.class_id, COUNT(*) AS call_count
        FROM graph_edges ge
        JOIN method_to_class mtc_src ON mtc_src.callable_id = ge.src_node_id
        JOIN method_to_class mtc_dst ON mtc_dst.callable_id = ge.dst_node_id
        WHERE ge.edge_kind = 'CALLS'
        GROUP BY mtc_src.class_id, mtc_dst.class_id
        """
    )


def insert_node_fan_stats_from_graph(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO node_fan_stats(node_id, node_kind, edge_kind, fan_in, fan_out)
        WITH edge_totals AS (
            SELECT
                ge.src_node_id AS node_id,
                ge.edge_kind AS edge_kind,
                0 AS fan_in,
                COUNT(*) AS fan_out
            FROM graph_edges ge
            GROUP BY ge.src_node_id, ge.edge_kind
            UNION ALL
            SELECT
                ge.dst_node_id AS node_id,
                ge.edge_kind AS edge_kind,
                COUNT(*) AS fan_in,
                0 AS fan_out
            FROM graph_edges ge
            GROUP BY ge.dst_node_id, ge.edge_kind
        )
        SELECT
            et.node_id,
            gn.node_kind,
            et.edge_kind,
            SUM(et.fan_in) AS fan_in,
            SUM(et.fan_out) AS fan_out
        FROM edge_totals et
        JOIN graph_nodes gn ON gn.node_id = et.node_id
        GROUP BY et.node_id, gn.node_kind, et.edge_kind
        """
    )
