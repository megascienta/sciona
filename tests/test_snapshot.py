import sqlite3
import subprocess
from pathlib import Path

from sciona.runtime import constants as setup_config
from sciona.data_storage.core_db.schema import ensure_schema
from sciona.data_storage.core_db import store as core_store
from sciona.code_analysis.core import snapshot
from sciona.data_storage.core_db import store as snapshot_storage
from tests.helpers import insert_snapshot


def _git(args, cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


def test_create_snapshot_captures_git_metadata(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["git", "init"], repo)
    _git(["git", "config", "user.name", "Test User"], repo)
    _git(["git", "config", "user.email", "test@example.com"], repo)
    (repo / "file.txt").write_text("hello\n", encoding="utf-8")
    _git(["git", "add", "file.txt"], repo)
    _git(["git", "commit", "-m", "init"], repo)

    db_path = repo / "sciona.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)

    snap = snapshot.create_snapshot(repo, source="scan")
    structural_hash = "hash-integration"
    snapshot.persist_snapshot(
        conn,
        snap,
        structural_hash=structural_hash,
        is_committed=True,
        store=core_store,
    )
    row = conn.execute(
        """
        SELECT snapshot_id, source, is_committed, structural_hash, git_commit_sha
        FROM snapshots
        """
    ).fetchone()
    assert row is not None
    assert row["snapshot_id"] == snap.snapshot_id
    assert row["source"] == "scan"
    assert row["is_committed"] == 1
    assert row["structural_hash"] == structural_hash
    head_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()
    assert row["git_commit_sha"] == head_sha
    conn.close()


def test_delete_snapshot_tree_removes_rows(tmp_path):
    db_path = tmp_path / "cleanup.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    snapshot_id = "snap_cleanup"
    insert_snapshot(conn, snapshot_id, is_committed=False)
    conn.execute(
        """
        INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id, retired_snapshot_id)
        VALUES ('node_one', 'module', 'python', ?, ?)
        """,
        (snapshot_id, setup_config.ACTIVE_RETIREMENT_FLAG),
    )
    conn.execute(
        """
        INSERT INTO node_instances(
            instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
        ) VALUES ('inst', 'node_one', ?, 'pkg.module', 'pkg/module.py', 1, 5, 'hash')
        """,
        (snapshot_id,),
    )
    conn.execute(
        """
        INSERT INTO edges(snapshot_id, src_structural_id, dst_structural_id, edge_type)
        VALUES (?, 'node_one', 'node_one', 'CONTAINS')
        """,
        (snapshot_id,),
    )
    conn.commit()

    snapshot_storage.delete_snapshot_tree(conn, snapshot_id)
    assert conn.execute("SELECT 1 FROM snapshots").fetchone() is None
    assert conn.execute("SELECT 1 FROM node_instances").fetchone() is None
    assert conn.execute("SELECT 1 FROM edges").fetchone() is None
    conn.close()
