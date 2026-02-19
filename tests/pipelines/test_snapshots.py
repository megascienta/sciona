# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import sqlite3
import subprocess
from pathlib import Path

import pytest

from sciona.code_analysis.analysis.structural_hash import compute_structural_hash
from sciona.code_analysis.core.engine import BuildEngine
from sciona.code_analysis.core.snapshot import create_snapshot
from sciona.code_analysis.core import snapshot
from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.data_storage.artifact_db.maintenance import rebuild_graph_index
from sciona.data_storage.core_db import errors as core_errors
from sciona.data_storage.core_db import write_ops as core_write
from sciona.data_storage.core_db import write_ops as snapshot_storage
from sciona.data_storage.core_db.schema import ensure_schema
from sciona.pipelines.domain.repository import RepoState
from sciona.pipelines.exec.build import build_repo
from sciona.pipelines.policy import build as policy_build
from sciona.reducers import registry as reducer_registry
from sciona.runtime.paths import get_artifact_db_path
from tests.helpers import insert_snapshot


def _git(args, cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


def _init_repo(repo_root: Path) -> None:
    repo_root.mkdir()
    _git(["git", "init"], repo_root)
    _git(["git", "config", "user.name", "Test User"], repo_root)
    _git(["git", "config", "user.email", "test@example.com"], repo_root)
    src_dir = repo_root / "src"
    src_dir.mkdir()
    (src_dir / "mod.py").write_text("print('hi')\n", encoding="utf-8")
    _git(["git", "add", "src/mod.py"], repo_root)
    _git(["git", "commit", "-m", "init"], repo_root)


def _write_config(repo_root: Path) -> None:
    sciona_dir = repo_root / ".sciona"
    sciona_dir.mkdir()
    (sciona_dir / "config.yaml").write_text(
        """languages:\n  python:\n    enabled: true\n\ndiscovery:\n  exclude_globs: []\n""",
        encoding="utf-8",
    )


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
        store=core_write,
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
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
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
        INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
        VALUES ('node_one', 'module', 'python', ?)
        """,
        (snapshot_id,),
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


def test_delete_committed_snapshots_except_keeps_only_target(tmp_path):
    db_path = tmp_path / "single.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    insert_snapshot(conn, "snap_old", is_committed=True)
    insert_snapshot(conn, "snap_keep", is_committed=True)
    conn.commit()

    removed = snapshot_storage.delete_committed_snapshots_except(conn, "snap_keep")
    remaining = conn.execute(
        "SELECT snapshot_id FROM snapshots WHERE is_committed = 1 ORDER BY snapshot_id"
    ).fetchall()

    assert removed == ["snap_old"]
    assert [row["snapshot_id"] for row in remaining] == ["snap_keep"]
    conn.close()


def test_reducers_require_single_committed_snapshot_state(tmp_path: Path) -> None:
    repo_root, db_path, old_snapshot, _latest_snapshot = _setup_latest_snapshot_db(
        tmp_path
    )
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        reducers = reducer_registry.get_reducers()
        for reducer_id, entry in reducers.items():
            reducer = entry.module
            if reducer_id in {
                "callable_overview",
                "class_overview",
                "module_overview",
                "structural_index",
            }:
                with pytest.raises(ValueError, match="exactly one committed snapshot"):
                    reducer.run(old_snapshot, conn=conn, repo_root=repo_root)
                continue
            with pytest.raises(ValueError, match="exactly one committed snapshot"):
                reducer.render(old_snapshot, conn, repo_root)
    finally:
        conn.close()


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


def test_snapshot_structural_hash_is_deterministic(tmp_path):
    repo_root = tmp_path / "repo"
    _init_repo(repo_root)
    _write_config(repo_root)

    db_path = repo_root / ".sciona" / "sciona.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)

    engine = BuildEngine(repo_root, conn, core_write)

    snap_a = create_snapshot(repo_root, source="scan")
    conn.execute("BEGIN")
    engine.run(snap_a)
    conn.commit()
    hash_a = compute_structural_hash(conn, snap_a.snapshot_id)

    snap_b = create_snapshot(repo_root, source="scan")
    conn.execute("BEGIN")
    engine.run(snap_b)
    conn.commit()
    hash_b = compute_structural_hash(conn, snap_b.snapshot_id)

    conn.close()

    assert hash_a == hash_b


def test_committed_snapshot_id_is_deterministic(tmp_path):
    repo_root = tmp_path / "repo"
    _init_repo(repo_root)
    _write_config(repo_root)

    repo_state = RepoState.from_repo_root(repo_root)
    policy = policy_build.resolve_build_policy(
        repo_state, refresh_artifacts=False, refresh_calls=False
    )

    result_a = build_repo(repo_state, policy)
    result_b = build_repo(repo_state, policy)

    assert result_a.snapshot_id == result_b.snapshot_id
