# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import sqlite3

import pytest

from sciona.data_storage.core_db.read_ops import hashes as read_hashes
from sciona.data_storage.core_db.read_ops import edges as read_edges
from sciona.data_storage.core_db.read_ops import nodes as read_nodes
from sciona.data_storage.core_db.read_ops import snapshots as read_snapshots
from sciona.data_storage.core_db import write_ops as core_write
from sciona.data_storage.core_db.errors import (
    SnapshotNotFoundError,
    UncommittedSnapshotError,
)
from sciona.data_storage.core_db.schema import ensure_schema


def _conn(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def test_latest_committed_snapshot_orders_by_commit_time(tmp_path) -> None:
    db_path = tmp_path / "core.db"
    conn = _conn(db_path)
    ensure_schema(conn)
    core_write.insert_snapshot(
        conn,
        snapshot_id="snap_old",
        created_at="2024-01-01T00:00:00Z",
        source="test",
        structural_hash="hash-old",
        is_committed=False,
        git_commit_time="2024-01-01T00:00:00Z",
    )
    core_write.insert_snapshot(
        conn,
        snapshot_id="snap_new",
        created_at="2024-01-02T00:00:00Z",
        source="test",
        structural_hash="hash-new",
        is_committed=True,
        git_commit_time="2024-01-02T00:00:00Z",
    )
    conn.commit()

    assert read_snapshots.latest_committed_snapshot_id(conn) == "snap_new"
    assert read_snapshots.list_committed_snapshots(conn) == ["snap_new"]
    conn.close()


def test_validate_snapshot_for_read_requires_committed(tmp_path) -> None:
    db_path = tmp_path / "core.db"
    conn = _conn(db_path)
    ensure_schema(conn)
    core_write.insert_snapshot(
        conn,
        snapshot_id="snap_temp",
        created_at="2024-01-01T00:00:00Z",
        source="test",
        structural_hash="hash-temp",
        is_committed=False,
    )
    conn.commit()

    with pytest.raises(UncommittedSnapshotError):
        read_snapshots.validate_snapshot_for_read(conn, "snap_temp")
    with pytest.raises(SnapshotNotFoundError):
        read_snapshots.validate_snapshot_for_read(conn, "snap_missing")
    conn.close()


def test_node_hashes_for_ids_is_scoped_to_snapshot(tmp_path) -> None:
    db_path = tmp_path / "core.db"
    conn = _conn(db_path)
    ensure_schema(conn)
    core_write.insert_snapshot(
        conn,
        snapshot_id="snap_a",
        created_at="2024-01-01T00:00:00Z",
        source="test",
        structural_hash="hash-a",
        is_committed=False,
    )
    core_write.insert_snapshot(
        conn,
        snapshot_id="snap_b",
        created_at="2024-01-02T00:00:00Z",
        source="test",
        structural_hash="hash-b",
        is_committed=True,
    )
    core_write.insert_structural_node(
        conn,
        structural_id="node_1",
        node_type="function",
        language="python",
        created_snapshot_id="snap_a",
    )
    core_write.insert_node_instance(
        conn,
        instance_id="snap_a:node_1",
        structural_id="node_1",
        snapshot_id="snap_a",
        qualified_name="repo.pkg.fn",
        file_path="pkg/file.py",
        start_line=1,
        end_line=1,
        content_hash="hash-from-a",
    )
    core_write.insert_node_instance(
        conn,
        instance_id="snap_b:node_1",
        structural_id="node_1",
        snapshot_id="snap_b",
        qualified_name="repo.pkg.fn",
        file_path="pkg/file.py",
        start_line=1,
        end_line=1,
        content_hash="hash-from-b",
    )
    conn.commit()

    assert read_hashes.node_hashes_for_ids(conn, "snap_a", ["node_1"]) == {
        "node_1": "hash-from-a"
    }
    assert read_hashes.node_hashes_for_ids(conn, "snap_b", ["node_1"]) == {
        "node_1": "hash-from-b"
    }
    assert read_hashes.node_hashes_for_ids(conn, "snap_a", ["missing"]) == {}
    conn.close()


def test_lookup_structural_id_empty_node_types_returns_none(tmp_path) -> None:
    db_path = tmp_path / "core.db"
    conn = _conn(db_path)
    ensure_schema(conn)
    result = read_nodes.lookup_structural_id(
        conn,
        snapshot_id="snap_any",
        structural_id="any",
        node_types=[],
    )
    assert result is None
    conn.close()


def test_search_node_instances_empty_node_types_returns_empty(tmp_path) -> None:
    db_path = tmp_path / "core.db"
    conn = _conn(db_path)
    ensure_schema(conn)
    result = read_nodes.search_node_instances(
        conn,
        snapshot_id="snap_any",
        node_types=[],
        query="anything",
    )
    assert result == []
    conn.close()


def test_list_nodes_by_types_empty_node_types_returns_empty(tmp_path) -> None:
    db_path = tmp_path / "core.db"
    conn = _conn(db_path)
    ensure_schema(conn)
    result = read_nodes.list_nodes_by_types(
        conn,
        snapshot_id="snap_any",
        node_types=[],
    )
    assert result == []
    conn.close()


def test_node_instances_for_file_paths_is_scoped_to_snapshot(tmp_path) -> None:
    db_path = tmp_path / "core.db"
    conn = _conn(db_path)
    ensure_schema(conn)
    core_write.insert_snapshot(
        conn,
        snapshot_id="snap_a",
        created_at="2024-01-01T00:00:00Z",
        source="test",
        structural_hash="hash-a",
        is_committed=False,
    )
    core_write.insert_snapshot(
        conn,
        snapshot_id="snap_b",
        created_at="2024-01-02T00:00:00Z",
        source="test",
        structural_hash="hash-b",
        is_committed=True,
    )
    core_write.insert_structural_node(
        conn,
        structural_id="node_1",
        node_type="callable",
        language="python",
        created_snapshot_id="snap_a",
    )
    core_write.insert_node_instance(
        conn,
        instance_id="snap_a:node_1",
        structural_id="node_1",
        snapshot_id="snap_a",
        qualified_name="repo.pkg.fn",
        file_path="pkg/file.py",
        start_line=1,
        end_line=1,
        content_hash="hash-a",
    )
    core_write.insert_node_instance(
        conn,
        instance_id="snap_b:node_1",
        structural_id="node_1",
        snapshot_id="snap_b",
        qualified_name="repo.pkg.fn",
        file_path="pkg/file.py",
        start_line=2,
        end_line=2,
        content_hash="hash-b",
    )
    conn.commit()

    rows = read_nodes.node_instances_for_file_paths(conn, "snap_b", ["pkg/file.py"])

    assert rows == [
        {
            "structural_id": "node_1",
            "node_type": "callable",
            "language": "python",
            "qualified_name": "repo.pkg.fn",
            "file_path": "pkg/file.py",
            "start_line": 2,
            "end_line": 2,
            "content_hash": "hash-b",
        }
    ]
    conn.close()


def test_edges_for_source_ids_is_scoped_to_snapshot(tmp_path) -> None:
    db_path = tmp_path / "core.db"
    conn = _conn(db_path)
    ensure_schema(conn)
    for snapshot_id, created_at, committed in (
        ("snap_a", "2024-01-01T00:00:00Z", False),
        ("snap_b", "2024-01-02T00:00:00Z", True),
    ):
        core_write.insert_snapshot(
            conn,
            snapshot_id=snapshot_id,
            created_at=created_at,
            source="test",
            structural_hash=f"hash-{snapshot_id}",
            is_committed=committed,
        )
    for structural_id in ("src", "dst_a", "dst_b"):
        core_write.insert_structural_node(
            conn,
            structural_id=structural_id,
            node_type="callable",
            language="python",
            created_snapshot_id="snap_a",
        )
    core_write.insert_edge(
        conn,
        snapshot_id="snap_a",
        src_structural_id="src",
        dst_structural_id="dst_a",
        edge_type="LEXICALLY_CONTAINS",
    )
    core_write.insert_edge(
        conn,
        snapshot_id="snap_b",
        src_structural_id="src",
        dst_structural_id="dst_b",
        edge_type="LEXICALLY_CONTAINS",
    )
    conn.commit()

    assert read_edges.edges_for_source_ids(conn, "snap_b", ["src"]) == [
        ("src", "dst_b", "LEXICALLY_CONTAINS")
    ]
    conn.close()
