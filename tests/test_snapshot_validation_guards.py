import sqlite3

import pytest

from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.data_storage.artifact_db.maintenance import rebuild_graph_index
from sciona.data_storage.core_db import errors as core_errors
from sciona.data_storage.core_db.schema import ensure_schema
from sciona.runtime.paths import get_artifact_db_path


def test_rebuild_graph_rejects_uncommitted_snapshot(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".sciona").mkdir()

    core_conn = sqlite3.connect(tmp_path / "core.db")
    core_conn.row_factory = sqlite3.Row
    ensure_schema(core_conn)
    core_conn.execute(
        """
        INSERT INTO snapshots(
            snapshot_id, created_at, source, is_committed, structural_hash
        ) VALUES ('snap_temp', '2026-01-01T00:00:00Z', 'test', 0, 'hash')
        """
    )
    core_conn.commit()

    artifact_conn = artifact_connect(
        get_artifact_db_path(repo_root), repo_root=repo_root
    )
    try:
        with pytest.raises(core_errors.UncommittedSnapshotError):
            rebuild_graph_index(
                artifact_conn, core_conn=core_conn, snapshot_id="snap_temp"
            )
    finally:
        artifact_conn.close()
        core_conn.close()
