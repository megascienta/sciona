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


def test_build_wall_seconds_and_phase_timings_for_snapshot(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".sciona").mkdir()
    conn = artifact_connect(get_artifact_db_path(repo_root), repo_root=repo_root)
    try:
        artifact_write.set_rebuild_metadata(
            conn,
            key="build_wall_seconds:snap_4",
            value="4.750000",
        )
        artifact_write.set_rebuild_metadata(
            conn,
            key="build_phase_timings:snap_4",
            value='{"build_structural_index": 3.5, "rebuild_graph_rollups": 0.2}',
        )
        conn.commit()
        assert artifact_read.build_wall_seconds_for_snapshot(
            conn,
            snapshot_id="snap_4",
        ) == 4.75
        assert artifact_read.build_phase_timings_for_snapshot(
            conn,
            snapshot_id="snap_4",
        ) == {
            "build_structural_index": 3.5,
            "rebuild_graph_rollups": 0.2,
        }
    finally:
        conn.close()


def test_snapshot_summary_for_snapshot(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".sciona").mkdir()
    conn = artifact_connect(get_artifact_db_path(repo_root), repo_root=repo_root)
    try:
        artifact_write.set_snapshot_summary(
            conn,
            snapshot_id="snap_5",
            value='{"timing": {"build_total_seconds": 1.5}, "totals": {"callsites": {"accepted_callsites": 2}}}',
        )
        conn.commit()
        assert artifact_read.snapshot_summary_for_snapshot(
            conn,
            snapshot_id="snap_5",
        ) == {
            "timing": {"build_total_seconds": 1.5},
            "totals": {"callsites": {"accepted_callsites": 2}},
        }
    finally:
        conn.close()
