import sqlite3
from pathlib import Path

import pytest

from sciona.data_storage.core_db.schema import ensure_schema
from sciona.reducers import registry as reducer_registry


def _setup_latest_snapshot_db(tmp_path: Path) -> tuple[Path, Path, str, str]:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    sciona_dir = repo_root / ".sciona"
    sciona_dir.mkdir()
    db_path = sciona_dir / "sciona.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    _insert_snapshot(conn, "snap_old", created_at="2024-01-01T00:00:00Z")
    _insert_snapshot(conn, "snap_new", created_at="2024-01-02T00:00:00Z")
    conn.commit()
    conn.close()
    return repo_root, db_path, "snap_old", "snap_new"


def _insert_snapshot(conn, snapshot_id: str, *, created_at: str) -> None:
    conn.execute(
        """
        INSERT INTO snapshots(
            snapshot_id,
            created_at,
            source,
            is_committed,
            structural_hash,
            git_commit_sha,
            git_commit_time,
            git_branch
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            snapshot_id,
            created_at,
            "test",
            1,
            f"hash-{snapshot_id}",
            f"commit-{snapshot_id}",
            created_at,
            "main",
        ),
    )


def test_reducers_require_single_committed_snapshot_state(tmp_path: Path) -> None:
    repo_root, db_path, old_snapshot, _latest_snapshot = _setup_latest_snapshot_db(tmp_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        reducers = reducer_registry.get_reducers()
        for reducer_id, entry in reducers.items():
            reducer = entry.module
            if reducer_id in {"callable_overview", "class_overview", "module_overview", "structural_index"}:
                with pytest.raises(ValueError, match="exactly one committed snapshot"):
                    reducer.run(old_snapshot, conn=conn, repo_root=repo_root)
                continue
            with pytest.raises(ValueError, match="exactly one committed snapshot"):
                reducer.render(old_snapshot, conn, repo_root)
    finally:
        conn.close()
