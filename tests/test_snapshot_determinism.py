import sqlite3
import subprocess
from pathlib import Path

from sciona.data_storage.core_db.schema import ensure_schema
from sciona.code_analysis.core.engine import BuildEngine
from sciona.data_storage.core_db import store as core_store
from sciona.code_analysis.core.snapshot import create_snapshot
from sciona.code_analysis.analysis.structural_hash import compute_structural_hash


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


def test_snapshot_structural_hash_is_deterministic(tmp_path):
    repo_root = tmp_path / "repo"
    _init_repo(repo_root)
    _write_config(repo_root)

    db_path = repo_root / ".sciona" / "sciona.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)

    engine = BuildEngine(repo_root, conn, core_store)

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
