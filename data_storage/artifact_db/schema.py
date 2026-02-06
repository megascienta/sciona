"""ArtifactDB schema."""

from __future__ import annotations

import sqlite3

from ..schema_utils import ensure_schema as _ensure_schema

SCHEMA_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS node_calls (
        caller_id TEXT NOT NULL,
        callee_id TEXT NOT NULL,
        valid INTEGER NOT NULL,
        call_hash TEXT NOT NULL,
        PRIMARY KEY (caller_id, callee_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_node_calls_caller
    ON node_calls(caller_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_node_calls_callee
    ON node_calls(callee_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS node_status (
        node_id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_node_status_status
    ON node_status(status)
    """,
    """
    CREATE TABLE IF NOT EXISTS graph_nodes (
        node_id TEXT PRIMARY KEY,
        node_kind TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS graph_edges (
        src_node_id TEXT NOT NULL,
        dst_node_id TEXT NOT NULL,
        edge_kind TEXT NOT NULL,          -- contains/defines/imports/calls/...
        PRIMARY KEY (src_node_id, dst_node_id, edge_kind),
        FOREIGN KEY (src_node_id) REFERENCES graph_nodes(node_id) ON DELETE CASCADE,
        FOREIGN KEY (dst_node_id) REFERENCES graph_nodes(node_id) ON DELETE CASCADE
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_graph_edges_src
    ON graph_edges(src_node_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_graph_edges_dst
    ON graph_edges(dst_node_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_graph_edges_kind
    ON graph_edges(edge_kind)
    """,
    """
    CREATE TABLE IF NOT EXISTS module_call_edges (
        src_module_id TEXT NOT NULL,
        dst_module_id TEXT NOT NULL,
        call_count INTEGER NOT NULL,
        PRIMARY KEY (src_module_id, dst_module_id),
        FOREIGN KEY (src_module_id) REFERENCES graph_nodes(node_id) ON DELETE CASCADE,
        FOREIGN KEY (dst_module_id) REFERENCES graph_nodes(node_id) ON DELETE CASCADE
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_module_call_edges_src
    ON module_call_edges(src_module_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_module_call_edges_dst
    ON module_call_edges(dst_module_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS class_call_edges (
        src_class_id TEXT NOT NULL,
        dst_class_id TEXT NOT NULL,
        call_count INTEGER NOT NULL,
        PRIMARY KEY (src_class_id, dst_class_id),
        FOREIGN KEY (src_class_id) REFERENCES graph_nodes(node_id) ON DELETE CASCADE,
        FOREIGN KEY (dst_class_id) REFERENCES graph_nodes(node_id) ON DELETE CASCADE
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_class_call_edges_src
    ON class_call_edges(src_class_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_class_call_edges_dst
    ON class_call_edges(dst_class_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS node_fan_stats (
        node_id TEXT NOT NULL,
        node_kind TEXT NOT NULL,
        edge_kind TEXT NOT NULL,
        fan_in INTEGER NOT NULL,
        fan_out INTEGER NOT NULL,
        PRIMARY KEY (node_id, edge_kind),
        FOREIGN KEY (node_id) REFERENCES graph_nodes(node_id) ON DELETE CASCADE
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_node_fan_stats_kind
    ON node_fan_stats(edge_kind)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_node_fan_stats_node
    ON node_fan_stats(node_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS rebuild_status (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS diff_overlay (
        snapshot_id TEXT NOT NULL,
        worktree_hash TEXT NOT NULL,
        structural_id TEXT NOT NULL,
        node_type TEXT NOT NULL,
        diff_kind TEXT NOT NULL,
        field TEXT,
        old_value TEXT,
        new_value TEXT,
        created_at TEXT NOT NULL,
        PRIMARY KEY (snapshot_id, worktree_hash, structural_id, field)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_diff_overlay_snapshot
    ON diff_overlay(snapshot_id, worktree_hash)
    """,
]


def ensure_schema(conn: sqlite3.Connection) -> None:
    _ensure_schema(conn, SCHEMA_STATEMENTS)
    _ensure_graph_fk_schema(conn)


def _ensure_graph_fk_schema(conn: sqlite3.Connection) -> None:
    # Graph and rollup tables are fully derived from core data, so rebuilding
    # them during migration is safe and keeps schema upgrades simple.
    fk_rows = conn.execute("PRAGMA foreign_key_list(graph_edges)").fetchall()
    if fk_rows:
        return
    conn.execute("DROP TABLE IF EXISTS graph_edges")
    conn.execute("DROP TABLE IF EXISTS module_call_edges")
    conn.execute("DROP TABLE IF EXISTS class_call_edges")
    conn.execute("DROP TABLE IF EXISTS node_fan_stats")
    statements = [
        SCHEMA_STATEMENTS[6],  # graph_edges
        SCHEMA_STATEMENTS[10],  # module_call_edges
        SCHEMA_STATEMENTS[13],  # class_call_edges
        SCHEMA_STATEMENTS[16],  # node_fan_stats
        SCHEMA_STATEMENTS[7],  # idx_graph_edges_src
        SCHEMA_STATEMENTS[8],  # idx_graph_edges_dst
        SCHEMA_STATEMENTS[9],  # idx_graph_edges_kind
        SCHEMA_STATEMENTS[11],  # idx_module_call_edges_src
        SCHEMA_STATEMENTS[12],  # idx_module_call_edges_dst
        SCHEMA_STATEMENTS[14],  # idx_class_call_edges_src
        SCHEMA_STATEMENTS[15],  # idx_class_call_edges_dst
        SCHEMA_STATEMENTS[17],  # idx_node_fan_stats_kind
        SCHEMA_STATEMENTS[18],  # idx_node_fan_stats_node
    ]
    for statement in statements:
        conn.execute(statement)
