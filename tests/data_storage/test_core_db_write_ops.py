# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import sqlite3

import pytest

from sciona.data_storage.core_db import write_ops as core_write
from sciona.data_storage.core_db.schema import ensure_schema


def _conn(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def test_insert_snapshot_rejects_duplicate_ids(tmp_path) -> None:
    db_path = tmp_path / "core.db"
    conn = _conn(db_path)
    ensure_schema(conn)
    core_write.insert_snapshot(
        conn,
        snapshot_id="snap",
        created_at="2024-01-01T00:00:00Z",
        source="test",
        structural_hash="hash",
        is_committed=True,
    )
    with pytest.raises(sqlite3.IntegrityError):
        core_write.insert_snapshot(
            conn,
            snapshot_id="snap",
            created_at="2024-01-01T00:00:00Z",
            source="test",
            structural_hash="hash",
            is_committed=True,
        )
    conn.close()


def test_insert_edge_ignores_duplicates(tmp_path) -> None:
    db_path = tmp_path / "core.db"
    conn = _conn(db_path)
    ensure_schema(conn)
    core_write.insert_snapshot(
        conn,
        snapshot_id="snap",
        created_at="2024-01-01T00:00:00Z",
        source="test",
        structural_hash="hash",
        is_committed=True,
    )
    conn.execute(
        """
        INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
        VALUES ('node_a', 'module', 'python', 'snap')
        """
    )
    conn.execute(
        """
        INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
        VALUES ('node_b', 'module', 'python', 'snap')
        """
    )
    conn.execute(
        """
        INSERT INTO node_instances(
            instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
        ) VALUES ('snap:node_a', 'node_a', 'snap', 'pkg.a', 'pkg/a.py', 1, 1, 'hash-a')
        """
    )
    conn.execute(
        """
        INSERT INTO node_instances(
            instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
        ) VALUES ('snap:node_b', 'node_b', 'snap', 'pkg.b', 'pkg/b.py', 1, 1, 'hash-b')
        """
    )
    conn.commit()

    core_write.insert_edge(
        conn,
        snapshot_id="snap",
        src_structural_id="node_a",
        dst_structural_id="node_b",
        edge_type="IMPORTS_DECLARED",
    )
    core_write.insert_edge(
        conn,
        snapshot_id="snap",
        src_structural_id="node_a",
        dst_structural_id="node_b",
        edge_type="IMPORTS_DECLARED",
    )
    conn.commit()

    count = conn.execute("SELECT COUNT(*) AS count FROM edges").fetchone()["count"]
    assert count == 1
    conn.close()
