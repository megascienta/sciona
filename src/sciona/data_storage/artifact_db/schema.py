# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

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
    CREATE TABLE IF NOT EXISTS call_sites (
        snapshot_id TEXT NOT NULL,
        caller_id TEXT NOT NULL,
        caller_qname TEXT NOT NULL,
        caller_node_type TEXT NOT NULL,
        identifier TEXT NOT NULL,
        resolution_status TEXT NOT NULL CHECK (resolution_status IN ('accepted', 'dropped')),
        accepted_callee_id TEXT,
        provenance TEXT CHECK (provenance IN ('exact_qname', 'module_scoped', 'import_narrowed') OR provenance IS NULL),
        drop_reason TEXT CHECK (
            drop_reason IN (
                'no_candidates',
                'unique_without_provenance',
                'ambiguous_no_caller_module',
                'ambiguous_no_in_scope_candidate',
                'ambiguous_multiple_in_scope_candidates'
            ) OR drop_reason IS NULL
        ),
        candidate_count INTEGER NOT NULL,
        callee_kind TEXT NOT NULL CHECK (callee_kind IN ('qualified', 'terminal')),
        call_start_byte INTEGER,
        call_end_byte INTEGER,
        call_ordinal INTEGER NOT NULL,
        site_hash TEXT NOT NULL,
        PRIMARY KEY (snapshot_id, caller_id, site_hash)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_call_sites_caller
    ON call_sites(snapshot_id, caller_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_call_sites_status
    ON call_sites(snapshot_id, resolution_status)
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
    """
    CREATE TABLE IF NOT EXISTS diff_overlay_calls (
        snapshot_id TEXT NOT NULL,
        worktree_hash TEXT NOT NULL,
        src_structural_id TEXT NOT NULL,
        dst_structural_id TEXT NOT NULL,
        diff_kind TEXT NOT NULL,
        src_node_type TEXT,
        dst_node_type TEXT,
        src_qualified_name TEXT,
        dst_qualified_name TEXT,
        src_file_path TEXT,
        dst_file_path TEXT,
        created_at TEXT NOT NULL,
        PRIMARY KEY (
            snapshot_id,
            worktree_hash,
            src_structural_id,
            dst_structural_id
        )
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_diff_overlay_calls_snapshot
    ON diff_overlay_calls(snapshot_id, worktree_hash)
    """,
    """
    CREATE TABLE IF NOT EXISTS diff_overlay_summary (
        snapshot_id TEXT NOT NULL,
        worktree_hash TEXT NOT NULL,
        summary_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (snapshot_id, worktree_hash)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_diff_overlay_summary_snapshot
    ON diff_overlay_summary(snapshot_id, worktree_hash)
    """,
]


def ensure_schema(conn: sqlite3.Connection) -> None:
    _ensure_schema(conn, SCHEMA_STATEMENTS)
    _ensure_call_sites_schema(conn)
    _ensure_graph_fk_schema(conn)


def _ensure_call_sites_schema(conn: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(call_sites)").fetchall()
    }
    required = {"callee_kind", "call_ordinal"}
    if not required.issubset(columns):
        conn.execute("DROP TABLE IF EXISTS call_sites")
        conn.execute(SCHEMA_STATEMENTS[3])
        conn.execute(SCHEMA_STATEMENTS[4])
        conn.execute(SCHEMA_STATEMENTS[5])


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
        SCHEMA_STATEMENTS[7],  # graph_edges
        SCHEMA_STATEMENTS[11],  # module_call_edges
        SCHEMA_STATEMENTS[14],  # class_call_edges
        SCHEMA_STATEMENTS[17],  # node_fan_stats
        SCHEMA_STATEMENTS[8],  # idx_graph_edges_src
        SCHEMA_STATEMENTS[9],  # idx_graph_edges_dst
        SCHEMA_STATEMENTS[10],  # idx_graph_edges_kind
        SCHEMA_STATEMENTS[12],  # idx_module_call_edges_src
        SCHEMA_STATEMENTS[13],  # idx_module_call_edges_dst
        SCHEMA_STATEMENTS[15],  # idx_class_call_edges_src
        SCHEMA_STATEMENTS[16],  # idx_class_call_edges_dst
        SCHEMA_STATEMENTS[18],  # idx_node_fan_stats_kind
        SCHEMA_STATEMENTS[19],  # idx_node_fan_stats_node
    ]
    for statement in statements:
        conn.execute(statement)
