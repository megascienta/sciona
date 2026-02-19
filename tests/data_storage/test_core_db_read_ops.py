# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import sqlite3

import pytest

from sciona.data_storage.core_db import read_ops_snapshots as read_snapshots
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
        is_committed=True,
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
    assert read_snapshots.list_committed_snapshots(conn) == ["snap_new", "snap_old"]
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
