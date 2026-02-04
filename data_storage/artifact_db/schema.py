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
        PRIMARY KEY (src_node_id, dst_node_id, edge_kind)
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
        PRIMARY KEY (src_module_id, dst_module_id)
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
        PRIMARY KEY (src_class_id, dst_class_id)
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
        PRIMARY KEY (node_id, edge_kind)
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
]

def ensure_schema(conn: sqlite3.Connection) -> None:
    _ensure_schema(conn, SCHEMA_STATEMENTS)
