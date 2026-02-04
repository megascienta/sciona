from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.data_storage.artifact_db import store as artifact_store
from sciona.runtime.paths import get_artifact_db_path


def test_rebuild_status_consistency_complete(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".sciona").mkdir()
    conn = artifact_connect(get_artifact_db_path(repo_root), repo_root=repo_root)
    try:
        artifact_store.mark_rebuild_started(conn, snapshot_id="snap_1")
        artifact_store.mark_rebuild_completed(conn, snapshot_id="snap_1")
        conn.commit()
        assert artifact_store.rebuild_consistent_for_snapshot(conn, snapshot_id="snap_1")
    finally:
        conn.close()


def test_rebuild_status_consistency_failed(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".sciona").mkdir()
    conn = artifact_connect(get_artifact_db_path(repo_root), repo_root=repo_root)
    try:
        artifact_store.mark_rebuild_started(conn, snapshot_id="snap_2")
        artifact_store.mark_rebuild_failed(conn, snapshot_id="snap_2")
        conn.commit()
        assert not artifact_store.rebuild_consistent_for_snapshot(conn, snapshot_id="snap_2")
    finally:
        conn.close()
