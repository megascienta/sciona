# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from pathlib import Path
import hashlib

from sciona.pipelines.domain.repository import RepoState
from sciona.pipelines.exec.build import build_repo
from sciona.pipelines.policy import build as policy_build
from sciona.runtime.config import io as config_io
from sciona.runtime.common import constants as setup_config
import sqlite3

from sciona.data_storage.core_db.read_ops import snapshots as read_snapshots
from tests.helpers import commit_all, init_git_repo


def _write_config(repo_root: Path) -> None:
    sciona_dir = repo_root / setup_config.SCIONA_DIR_NAME
    sciona_dir.mkdir(exist_ok=True)
    config_io.write_config_text(
        repo_root,
        """languages:\n  python:\n    enabled: true\n\ndiscovery:\n  exclude_globs: []\n""",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_build_repo_creates_committed_snapshot(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root, commit=False)
    (repo_root / "src").mkdir()
    (repo_root / "src" / "mod.py").write_text("print('hi')\n", encoding="utf-8")
    commit_all(repo_root)
    _write_config(repo_root)

    repo_state = RepoState.from_repo_root(repo_root)
    policy = policy_build.resolve_build_policy(
        repo_state, refresh_artifacts=False, refresh_calls=False
    )
    result = build_repo(repo_state, policy)

    conn = sqlite3.connect(repo_state.db_path)
    conn.row_factory = sqlite3.Row
    try:
        assert read_snapshots.count_committed_snapshots(conn) == 1
        assert read_snapshots.snapshot_exists(conn, result.snapshot_id)
    finally:
        conn.close()


def test_build_repo_keeps_single_committed_snapshot_across_rebuilds(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root, commit=False)
    (repo_root / "src").mkdir()
    mod_path = repo_root / "src" / "mod.py"
    mod_path.write_text("print('v1')\n", encoding="utf-8")
    commit_all(repo_root)
    _write_config(repo_root)

    repo_state = RepoState.from_repo_root(repo_root)
    policy = policy_build.resolve_build_policy(
        repo_state, refresh_artifacts=False, refresh_calls=False
    )
    first = build_repo(repo_state, policy)

    mod_path.write_text("print('v2')\n", encoding="utf-8")
    commit_all(repo_root)
    second = build_repo(repo_state, policy)

    conn = sqlite3.connect(repo_state.db_path)
    conn.row_factory = sqlite3.Row
    try:
        assert read_snapshots.count_committed_snapshots(conn) == 1
        assert read_snapshots.snapshot_exists(conn, second.snapshot_id)
        assert not read_snapshots.snapshot_exists(conn, first.snapshot_id)
    finally:
        conn.close()


def test_build_repo_is_deterministic_across_three_runs(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root, commit=False)
    (repo_root / "src").mkdir()
    (repo_root / "src" / "mod.py").write_text("print('stable')\n", encoding="utf-8")
    commit_all(repo_root)
    _write_config(repo_root)

    repo_state = RepoState.from_repo_root(repo_root)
    policy = policy_build.resolve_build_policy(
        repo_state, refresh_artifacts=False, refresh_calls=False
    )

    results = [build_repo(repo_state, policy) for _ in range(3)]
    snapshot_ids = [result.snapshot_id for result in results]

    conn = sqlite3.connect(repo_state.db_path)
    conn.row_factory = sqlite3.Row
    try:
        hashes = [
            conn.execute(
                "SELECT structural_hash FROM snapshots WHERE snapshot_id = ?",
                (snapshot_id,),
            ).fetchone()["structural_hash"]
            for snapshot_id in snapshot_ids
        ]
        assert len(set(snapshot_ids)) == 1
        assert len(set(hashes)) == 1
    finally:
        conn.close()


def test_build_repo_reuses_cached_result_when_fingerprint_matches(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root, commit=False)
    (repo_root / "src").mkdir()
    (repo_root / "src" / "mod.py").write_text("print('stable')\n", encoding="utf-8")
    commit_all(repo_root)
    _write_config(repo_root)

    repo_state = RepoState.from_repo_root(repo_root)
    policy = policy_build.resolve_build_policy(
        repo_state, refresh_artifacts=False, refresh_calls=False
    )

    first = build_repo(repo_state, policy)
    core_hash_before = _sha256(repo_state.db_path)
    cache_path = repo_state.sciona_dir / ".build_fingerprint.json"
    cache_before = cache_path.read_text(encoding="utf-8")

    second = build_repo(repo_state, policy)
    core_hash_after = _sha256(repo_state.db_path)
    cache_after = cache_path.read_text(encoding="utf-8")

    assert first.snapshot_id == second.snapshot_id
    assert second.status == "reused"
    assert cache_before == cache_after
    assert core_hash_before == core_hash_after


def test_build_repo_force_rebuild_keeps_committed_replace_semantics(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root, commit=False)
    (repo_root / "src").mkdir()
    (repo_root / "src" / "mod.py").write_text("print('stable')\n", encoding="utf-8")
    commit_all(repo_root)
    _write_config(repo_root)

    repo_state = RepoState.from_repo_root(repo_root)
    base_policy = policy_build.resolve_build_policy(
        repo_state, refresh_artifacts=False, refresh_calls=False
    )
    build_repo(repo_state, base_policy)
    cache_path = repo_state.sciona_dir / ".build_fingerprint.json"
    cache_before = cache_path.read_text(encoding="utf-8")

    force_policy = policy_build.resolve_build_policy(
        repo_state,
        refresh_artifacts=False,
        refresh_calls=False,
        force_rebuild=True,
    )
    forced = build_repo(repo_state, force_policy)
    cache_after = cache_path.read_text(encoding="utf-8")

    assert forced.status == "committed"
    assert cache_before != cache_after


def test_build_repo_diagnostic_workspace_is_removed(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    init_git_repo(repo_root, commit=False)
    (repo_root / "src").mkdir()
    (repo_root / "src" / "mod.py").write_text("print('stable')\n", encoding="utf-8")
    commit_all(repo_root)
    _write_config(repo_root)

    repo_state = RepoState.from_repo_root(repo_root)
    policy = policy_build.resolve_build_policy(
        repo_state, refresh_artifacts=False, refresh_calls=False
    )

    result = build_repo(repo_state, policy, diagnostic=True)

    assert result.status == "committed"
    assert not (repo_root / ".sciona" / ".diagnostic_rejected_calls").exists()
