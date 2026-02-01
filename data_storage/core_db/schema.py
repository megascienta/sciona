"""CoreDB schema."""
from __future__ import annotations

import sqlite3

from ..schema_utils import ensure_schema as _ensure_schema

SCHEMA_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS snapshots (
        snapshot_id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        source TEXT NOT NULL,
        is_committed INTEGER NOT NULL,
        structural_hash TEXT NOT NULL,
        git_commit_sha TEXT,
        git_commit_time TEXT,
        git_branch TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_snapshots_committed
    ON snapshots(is_committed, created_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_snapshots_hash
    ON snapshots(structural_hash)
    """,
    """
    CREATE TABLE IF NOT EXISTS structural_nodes (
        structural_id TEXT PRIMARY KEY,
        node_type TEXT NOT NULL,
        language TEXT NOT NULL,
        created_snapshot_id TEXT NOT NULL,
        retired_snapshot_id TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS node_instances (
        instance_id TEXT PRIMARY KEY,
        structural_id TEXT NOT NULL,
        snapshot_id TEXT NOT NULL,
        qualified_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        start_line INTEGER NOT NULL,
        end_line INTEGER NOT NULL,
        content_hash TEXT NOT NULL,
        UNIQUE (structural_id, snapshot_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_instances_snapshot
    ON node_instances(snapshot_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS edges (
        snapshot_id TEXT NOT NULL,
        src_structural_id TEXT NOT NULL,
        dst_structural_id TEXT NOT NULL,
        edge_type TEXT NOT NULL,
        PRIMARY KEY (snapshot_id, src_structural_id, dst_structural_id, edge_type)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_edges_snapshot
    ON edges(snapshot_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_edges_src
    ON edges(src_structural_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_edges_dst
    ON edges(dst_structural_id)
    """,
]

def ensure_schema(conn: sqlite3.Connection) -> None:
    _ensure_schema(conn, SCHEMA_STATEMENTS)
