# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import sqlite3

import pytest

from sciona.data_storage.core_db.schema import ensure_schema


def _conn(tmp_path):
    conn = sqlite3.connect(tmp_path / "sciona.db")
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    return conn


def test_node_instances_require_existing_snapshot_and_node(tmp_path):
    conn = _conn(tmp_path)
    try:
        conn.execute(
            """
            INSERT INTO snapshots(
                snapshot_id, created_at, source, is_committed, structural_hash
            ) VALUES ('snap_1', '2026-01-01T00:00:00Z', 'test', 1, 'hash')
            """
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO node_instances(
                    instance_id, structural_id, snapshot_id, qualified_name, file_path,
                    start_line, end_line, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "inst_1",
                    "missing_node",
                    "snap_1",
                    "pkg.mod",
                    "pkg/mod.py",
                    1,
                    1,
                    "h1",
                ),
            )
    finally:
        conn.close()


def test_edges_require_existing_snapshot_and_nodes(tmp_path):
    conn = _conn(tmp_path)
    try:
        conn.execute(
            """
            INSERT INTO snapshots(
                snapshot_id, created_at, source, is_committed, structural_hash
            ) VALUES ('snap_1', '2026-01-01T00:00:00Z', 'test', 1, 'hash')
            """
        )
        conn.execute(
            """
            INSERT INTO structural_nodes(
                structural_id, node_type, language, created_snapshot_id, retired_snapshot_id
            ) VALUES ('node_a', 'module', 'python', 'snap_1', NULL)
            """
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO edges(snapshot_id, src_structural_id, dst_structural_id, edge_type)
                VALUES (?, ?, ?, ?)
                """,
                ("snap_1", "node_a", "missing_node", "CONTAINS"),
            )
    finally:
        conn.close()
