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
        UNIQUE (structural_id, snapshot_id),
        FOREIGN KEY (structural_id) REFERENCES structural_nodes(structural_id) ON DELETE CASCADE
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
        PRIMARY KEY (snapshot_id, src_structural_id, dst_structural_id, edge_type),
        FOREIGN KEY (src_structural_id) REFERENCES structural_nodes(structural_id) ON DELETE CASCADE,
        FOREIGN KEY (dst_structural_id) REFERENCES structural_nodes(structural_id) ON DELETE CASCADE
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
    conn.execute("PRAGMA foreign_keys=ON")
    _ensure_schema(conn, SCHEMA_STATEMENTS)
    _ensure_fk_schema(conn)


def _ensure_fk_schema(conn: sqlite3.Connection) -> None:
    if (
        _has_foreign_keys(conn, "node_instances")
        and _has_foreign_keys(conn, "edges")
    ):
        return
    conn.execute("PRAGMA foreign_keys=OFF")
    try:
        conn.execute("BEGIN")
        _migrate_node_instances(conn)
        _migrate_edges(conn)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys=ON")


def _has_foreign_keys(conn: sqlite3.Connection, table_name: str) -> bool:
    rows = conn.execute(f"PRAGMA foreign_key_list({table_name})").fetchall()
    return bool(rows)


def _migrate_node_instances(conn: sqlite3.Connection) -> None:
    if _has_foreign_keys(conn, "node_instances"):
        return
    conn.execute("DROP TABLE IF EXISTS node_instances_new")
    conn.execute(
        """
        CREATE TABLE node_instances_new (
            instance_id TEXT PRIMARY KEY,
            structural_id TEXT NOT NULL,
            snapshot_id TEXT NOT NULL,
            qualified_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            start_line INTEGER NOT NULL,
            end_line INTEGER NOT NULL,
            content_hash TEXT NOT NULL,
            UNIQUE (structural_id, snapshot_id),
            FOREIGN KEY (structural_id) REFERENCES structural_nodes(structural_id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        INSERT INTO node_instances_new(
            instance_id,
            structural_id,
            snapshot_id,
            qualified_name,
            file_path,
            start_line,
            end_line,
            content_hash
        )
        SELECT ni.instance_id,
               ni.structural_id,
               ni.snapshot_id,
               ni.qualified_name,
               ni.file_path,
               ni.start_line,
               ni.end_line,
               ni.content_hash
        FROM node_instances ni
        JOIN structural_nodes sn ON sn.structural_id = ni.structural_id
        """
    )
    conn.execute("DROP TABLE node_instances")
    conn.execute("ALTER TABLE node_instances_new RENAME TO node_instances")
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_instances_snapshot
        ON node_instances(snapshot_id)
        """
    )


def _migrate_edges(conn: sqlite3.Connection) -> None:
    if _has_foreign_keys(conn, "edges"):
        return
    conn.execute("DROP TABLE IF EXISTS edges_new")
    conn.execute(
        """
        CREATE TABLE edges_new (
            snapshot_id TEXT NOT NULL,
            src_structural_id TEXT NOT NULL,
            dst_structural_id TEXT NOT NULL,
            edge_type TEXT NOT NULL,
            PRIMARY KEY (snapshot_id, src_structural_id, dst_structural_id, edge_type),
            FOREIGN KEY (src_structural_id) REFERENCES structural_nodes(structural_id) ON DELETE CASCADE,
            FOREIGN KEY (dst_structural_id) REFERENCES structural_nodes(structural_id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        INSERT INTO edges_new(snapshot_id, src_structural_id, dst_structural_id, edge_type)
        SELECT e.snapshot_id,
               e.src_structural_id,
               e.dst_structural_id,
               e.edge_type
        FROM edges e
        JOIN structural_nodes src ON src.structural_id = e.src_structural_id
        JOIN structural_nodes dst ON dst.structural_id = e.dst_structural_id
        """
    )
    conn.execute("DROP TABLE edges")
    conn.execute("ALTER TABLE edges_new RENAME TO edges")
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_edges_snapshot
        ON edges(snapshot_id)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_edges_src
        ON edges(src_structural_id)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_edges_dst
        ON edges(dst_structural_id)
        """
    )
