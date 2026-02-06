import sqlite3
from pathlib import Path

from sciona.data_storage.core_db.schema import ensure_schema
from sciona.code_analysis.core.extract.analyzer import ASTAnalyzer
from sciona.code_analysis.core.engine import BuildEngine
from sciona.data_storage.core_db import write_ops as core_write
from sciona.runtime import config as core_config
from sciona.code_analysis.core.extract import registry
from sciona.code_analysis.core.snapshot import Snapshot


def test_engine_records_nodes_for_failed_parse(tmp_path, monkeypatch):
    class FailingAnalyzer(ASTAnalyzer):
        language = "python"

        def analyze(self, snapshot, module_name):
            raise ValueError("boom")

        def module_name(self, repo_root, snapshot):
            return "pkg.mod"

    repo_root = tmp_path
    (repo_root / "pkg").mkdir()
    file_path = repo_root / "pkg" / "mod.py"
    file_path.write_text("def x(:\n", encoding="utf-8")

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)

    snapshot_id = "snap"
    conn.execute(
        """
        INSERT INTO snapshots(snapshot_id, created_at, source, is_committed, structural_hash)
        VALUES (?, ?, ?, ?, ?)
        """,
        (snapshot_id, "2024-01-01T00:00:00Z", "scan", 0, "hash"),
    )
    conn.commit()

    languages = {
        "python": core_config.LanguageSettings(
            name="python",
            enabled=True,
        )
    }

    monkeypatch.setattr(registry, "get_analyzer", lambda language: FailingAnalyzer())
    monkeypatch.setattr(
        registry,
        "get_analyzer_for_path",
        lambda path, analyzers: analyzers.get("python"),
    )
    monkeypatch.setattr(
        "sciona.runtime.git.tracked_paths",
        lambda _root: {Path("pkg/mod.py").as_posix()},
    )
    monkeypatch.setattr(
        "sciona.runtime.git.blob_sha_batch",
        lambda _root, paths: {path: "hash" for path in paths},
    )
    monkeypatch.setattr(
        "sciona.runtime.git.blob_sha",
        lambda _root, _path: "hash",
    )

    discovery = core_config.DiscoverySettings(exclude_globs=[])
    engine = BuildEngine(
        repo_root, conn, core_write, languages=languages, discovery=discovery
    )
    conn.execute("BEGIN")
    engine.run(
        snapshot=Snapshot(
            snapshot_id=snapshot_id,
            created_at="2024-01-01T00:00:00Z",
            source="scan",
            git_commit_sha="",
            git_commit_time="",
            git_branch="",
        )
    )
    conn.commit()

    row = conn.execute(
        "SELECT structural_id FROM node_instances WHERE qualified_name = ?",
        ("pkg.mod",),
    ).fetchone()
    assert row is not None


def test_engine_warns_on_empty_language_matches(tmp_path, monkeypatch):
    repo_root = tmp_path
    (repo_root / "src").mkdir()
    file_path = repo_root / "src" / "mod.py"
    file_path.write_text("print('hi')\n", encoding="utf-8")

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)

    snapshot_id = "snap"
    conn.execute(
        """
        INSERT INTO snapshots(snapshot_id, created_at, source, is_committed, structural_hash)
        VALUES (?, ?, ?, ?, ?)
        """,
        (snapshot_id, "2024-01-01T00:00:00Z", "scan", 0, "hash"),
    )
    conn.commit()

    languages = {
        "python": core_config.LanguageSettings(
            name="python",
            enabled=True,
        )
    }
    discovery = core_config.DiscoverySettings(exclude_globs=["**/*.py"])

    monkeypatch.setattr(
        "sciona.runtime.git.tracked_paths",
        lambda _root: {Path("src/mod.py").as_posix()},
    )
    monkeypatch.setattr(
        "sciona.runtime.git.blob_sha_batch",
        lambda _root, paths: {path: "hash" for path in paths},
    )
    monkeypatch.setattr(
        "sciona.runtime.git.blob_sha",
        lambda _root, _path: "hash",
    )

    engine = BuildEngine(
        repo_root, conn, core_write, languages=languages, discovery=discovery
    )
    conn.execute("BEGIN")
    engine.run(
        snapshot=Snapshot(
            snapshot_id=snapshot_id,
            created_at="2024-01-01T00:00:00Z",
            source="scan",
            git_commit_sha="",
            git_commit_time="",
            git_branch="",
        )
    )
    conn.commit()

    warning_text = "\n".join(engine.warnings)
    assert "Discovery warning:" in warning_text
    assert "python: 1 tracked by extension, 0 discovered" in warning_text
