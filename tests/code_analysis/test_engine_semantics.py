# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import sqlite3
from pathlib import Path

from sciona.data_storage.core_db.schema import ensure_schema
from sciona.code_analysis.core.extract.analyzer import ASTAnalyzer
from sciona.code_analysis.core.engine import BuildEngine
from sciona.code_analysis.core.normalize.model import AnalysisResult, CallRecord
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
        "sciona.runtime.git.ignored_tracked_paths",
        lambda _root: set(),
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
        "sciona.runtime.git.ignored_tracked_paths",
        lambda _root: set(),
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


def test_entry_points_are_written_to_synthetic_tables(tmp_path, monkeypatch):
    class MinimalAnalyzer(ASTAnalyzer):
        language = "python"

        def analyze(self, snapshot, module_name):
            return AnalysisResult(nodes=[], edges=[], call_records=[])

        def module_name(self, repo_root, snapshot):
            return "pkg.sub.mod"

    repo_root = tmp_path
    (repo_root / "pkg" / "sub").mkdir(parents=True)
    file_path = repo_root / "pkg" / "sub" / "mod.py"
    file_path.write_text("pass\n", encoding="utf-8")

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
    monkeypatch.setattr(registry, "get_analyzer", lambda language: MinimalAnalyzer())
    monkeypatch.setattr(
        registry,
        "get_analyzer_for_path",
        lambda path, analyzers: analyzers.get("python"),
    )
    monkeypatch.setattr(
        "sciona.runtime.git.tracked_paths",
        lambda _root: {Path("pkg/sub/mod.py").as_posix()},
    )
    monkeypatch.setattr(
        "sciona.runtime.git.ignored_tracked_paths",
        lambda _root: set(),
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

    synthetic_rows = conn.execute(
        """
        SELECT qualified_name
        FROM synthetic_node_instances
        WHERE snapshot_id = ?
        ORDER BY qualified_name
        """,
        (snapshot_id,),
    ).fetchall()
    names = [row["qualified_name"] for row in synthetic_rows]
    assert len(names) == 2
    assert names[0].endswith(".pkg")
    assert names[1].endswith(".pkg.sub")

    entry_point_rows = conn.execute(
        "SELECT COUNT(*) AS count FROM structural_nodes WHERE node_type = 'entry_point'"
    ).fetchone()
    assert entry_point_rows is not None
    assert entry_point_rows["count"] == 0
    conn.close()


def test_engine_applies_max_file_bytes_guardrail(tmp_path, monkeypatch):
    class MinimalAnalyzer(ASTAnalyzer):
        language = "python"

        def analyze(self, snapshot, module_name):
            return AnalysisResult(nodes=[], edges=[], call_records=[])

        def module_name(self, repo_root, snapshot):
            return "pkg.mod"

    repo_root = tmp_path
    (repo_root / "pkg").mkdir(parents=True)
    file_path = repo_root / "pkg" / "mod.py"
    file_path.write_text("print('too-large')\n", encoding="utf-8")

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

    languages = {"python": core_config.LanguageSettings(name="python", enabled=True)}
    monkeypatch.setattr(registry, "get_analyzer", lambda language: MinimalAnalyzer())
    monkeypatch.setattr(
        registry, "get_analyzer_for_path", lambda path, analyzers: analyzers.get("python")
    )
    monkeypatch.setattr(
        "sciona.runtime.git.tracked_paths", lambda _root: {Path("pkg/mod.py").as_posix()}
    )
    monkeypatch.setattr("sciona.runtime.git.ignored_tracked_paths", lambda _root: set())
    monkeypatch.setattr(
        "sciona.runtime.git.blob_sha_batch", lambda _root, paths: {path: "hash" for path in paths}
    )
    monkeypatch.setattr("sciona.runtime.git.blob_sha", lambda _root, _path: "hash")

    engine = BuildEngine(
        repo_root,
        conn,
        core_write,
        languages=languages,
        discovery=core_config.DiscoverySettings(exclude_globs=[]),
        max_file_bytes=1,
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

    assert engine.parse_failures == 1
    assert any("max_file_bytes=1" in warning for warning in engine.warnings)
    conn.close()


def test_engine_applies_max_call_identifiers_guardrail(tmp_path, monkeypatch):
    class CallHeavyAnalyzer(ASTAnalyzer):
        language = "python"

        def analyze(self, snapshot, module_name):
            return AnalysisResult(
                nodes=[],
                edges=[],
                call_records=[
                    CallRecord(
                        qualified_name="pkg.mod.fn",
                        node_type="function",
                        callee_identifiers=["a", "b", "c"],
                    )
                ],
            )

        def module_name(self, repo_root, snapshot):
            return "pkg.mod"

    repo_root = tmp_path
    (repo_root / "pkg").mkdir(parents=True)
    file_path = repo_root / "pkg" / "mod.py"
    file_path.write_text("def fn():\n    pass\n", encoding="utf-8")

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

    languages = {"python": core_config.LanguageSettings(name="python", enabled=True)}
    monkeypatch.setattr(registry, "get_analyzer", lambda language: CallHeavyAnalyzer())
    monkeypatch.setattr(
        registry, "get_analyzer_for_path", lambda path, analyzers: analyzers.get("python")
    )
    monkeypatch.setattr(
        "sciona.runtime.git.tracked_paths", lambda _root: {Path("pkg/mod.py").as_posix()}
    )
    monkeypatch.setattr("sciona.runtime.git.ignored_tracked_paths", lambda _root: set())
    monkeypatch.setattr(
        "sciona.runtime.git.blob_sha_batch", lambda _root, paths: {path: "hash" for path in paths}
    )
    monkeypatch.setattr("sciona.runtime.git.blob_sha", lambda _root, _path: "hash")

    engine = BuildEngine(
        repo_root,
        conn,
        core_write,
        languages=languages,
        discovery=core_config.DiscoverySettings(exclude_globs=[]),
        max_call_identifiers_per_file=2,
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

    assert engine.parse_failures == 1
    assert any(
        "max_call_identifiers_per_file=2" in warning for warning in engine.warnings
    )
    conn.close()


def test_engine_accumulates_name_collision_and_residual_containment_diagnostics(
    tmp_path, monkeypatch
):
    class DiagnosticAnalyzer(ASTAnalyzer):
        language = "python"

        def analyze(self, snapshot, module_name):
            rel = snapshot.record.relative_path.as_posix()
            if rel.endswith("bad.py"):
                raise ValueError(
                    "Lexical containment span invariant violated: parent does not enclose child"
                )
            return AnalysisResult(
                nodes=[],
                edges=[],
                call_records=[],
                diagnostics={
                    "name_collisions_detected": 2,
                    "name_collisions_disambiguated": 2,
                    "imports_seen": 5,
                    "imports_internal": 3,
                    "imports_filtered_not_internal": 2,
                },
            )

        def module_name(self, repo_root, snapshot):
            rel = snapshot.record.relative_path.as_posix()
            if rel.endswith("good.py"):
                return "pkg.good"
            return "pkg.bad"

    repo_root = tmp_path
    pkg = repo_root / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "good.py").write_text("def ok():\n    pass\n", encoding="utf-8")
    (pkg / "bad.py").write_text("def bad():\n    pass\n", encoding="utf-8")

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

    languages = {"python": core_config.LanguageSettings(name="python", enabled=True)}
    monkeypatch.setattr(registry, "get_analyzer", lambda language: DiagnosticAnalyzer())
    monkeypatch.setattr(
        registry, "get_analyzer_for_path", lambda path, analyzers: analyzers.get("python")
    )
    monkeypatch.setattr(
        "sciona.runtime.git.tracked_paths",
        lambda _root: {Path("pkg/good.py").as_posix(), Path("pkg/bad.py").as_posix()},
    )
    monkeypatch.setattr("sciona.runtime.git.ignored_tracked_paths", lambda _root: set())
    monkeypatch.setattr(
        "sciona.runtime.git.blob_sha_batch", lambda _root, paths: {path: "hash" for path in paths}
    )
    monkeypatch.setattr("sciona.runtime.git.blob_sha", lambda _root, _path: "hash")

    engine = BuildEngine(
        repo_root,
        conn,
        core_write,
        languages=languages,
        discovery=core_config.DiscoverySettings(exclude_globs=[]),
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

    assert engine.name_collisions_detected == 2
    assert engine.name_collisions_disambiguated == 2
    assert engine.residual_containment_failures == 1
    assert engine.name_collisions_by_language["python"]["name_collisions_detected"] == 2
    assert engine.name_collisions_by_language["python"]["name_collisions_disambiguated"] == 2
    assert engine.imports_seen == 5
    assert engine.imports_internal == 3
    assert engine.imports_filtered_not_internal == 2
    assert engine.imports_by_language["python"]["imports_seen"] == 5
    assert engine.imports_by_language["python"]["imports_internal"] == 3
    assert (
        engine.imports_by_language["python"]["imports_filtered_not_internal"] == 2
    )
    conn.close()
