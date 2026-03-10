# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.data_storage.artifact_db.reporting import read_status as artifact_read
from sciona.data_storage.artifact_db.writes import write_index as artifact_write
from sciona.runtime.paths import get_artifact_db_path


def test_rebuild_status_consistency_complete(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".sciona").mkdir()
    conn = artifact_connect(get_artifact_db_path(repo_root), repo_root=repo_root)
    try:
        artifact_write.mark_rebuild_started(conn, snapshot_id="snap_1")
        artifact_write.mark_rebuild_completed(conn, snapshot_id="snap_1")
        conn.commit()
        assert artifact_read.rebuild_consistent_for_snapshot(conn, snapshot_id="snap_1")
    finally:
        conn.close()


def test_rebuild_status_consistency_failed(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".sciona").mkdir()
    conn = artifact_connect(get_artifact_db_path(repo_root), repo_root=repo_root)
    try:
        artifact_write.mark_rebuild_started(conn, snapshot_id="snap_2")
        artifact_write.mark_rebuild_failed(conn, snapshot_id="snap_2")
        conn.commit()
        assert not artifact_read.rebuild_consistent_for_snapshot(
            conn, snapshot_id="snap_2"
        )
    finally:
        conn.close()


def test_build_total_seconds_for_snapshot(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".sciona").mkdir()
    conn = artifact_connect(get_artifact_db_path(repo_root), repo_root=repo_root)
    try:
        artifact_write.set_rebuild_metadata(
            conn,
            key="build_total_seconds:snap_3",
            value="2.500000",
        )
        conn.commit()
        assert artifact_read.build_total_seconds_for_snapshot(
            conn,
            snapshot_id="snap_3",
        ) == 2.5
    finally:
        conn.close()
