# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from sciona.code_analysis.artifacts.engine import ArtifactEngine

from tests.helpers import seed_repo_with_snapshot


def test_artifact_engine_runs_without_shadowing_error(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    db_path = repo_root / ".sciona" / "sciona.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        config_dir = repo_root / ".sciona"
        config_dir.mkdir(exist_ok=True)
        (config_dir / "config.yaml").write_text(
            "languages:\n  python:\n    enabled: true\n",
            encoding="utf-8",
        )
        engine = ArtifactEngine(repo_root, conn, config_root=repo_root)
        results = engine.run(snapshot_id)
    finally:
        conn.close()
    assert isinstance(results, list)


@dataclass
class _FakeAnalysisRecord:
    qualified_name: str
    node_type: str
    callee_identifiers: tuple[str, ...]


@dataclass
class _FakeAnalysis:
    call_records: list[_FakeAnalysisRecord]


@dataclass
class _FakeFileRecord:
    language: str
    relative_path: str


@dataclass
class _FakeFileSnapshot:
    record: _FakeFileRecord


class _FakeAnalyzer:
    module_index = None

    def module_name(self, workspace_root: Path, file_snapshot: _FakeFileSnapshot) -> str:
        del workspace_root, file_snapshot
        return "repo.pkg.alpha"

    def analyze(
        self, file_snapshot: _FakeFileSnapshot, module_name: str
    ) -> _FakeAnalysis:
        del file_snapshot, module_name
        return _FakeAnalysis(
            call_records=[
                _FakeAnalysisRecord(
                    qualified_name="repo.pkg.alpha.Service.run",
                    node_type="callable",
                    callee_identifiers=("foo", "bar"),
                ),
                _FakeAnalysisRecord(
                    qualified_name="repo.pkg.alpha.Service.run",
                    node_type="callable",
                    callee_identifiers=("bar", "baz"),
                ),
            ]
        )


class _ConflictingAnalyzer(_FakeAnalyzer):
    def analyze(
        self, file_snapshot: _FakeFileSnapshot, module_name: str
    ) -> _FakeAnalysis:
        del file_snapshot, module_name
        return _FakeAnalysis(
            call_records=[
                _FakeAnalysisRecord(
                    qualified_name="repo.pkg.alpha.Service.run",
                    node_type="callable",
                    callee_identifiers=("foo",),
                ),
                _FakeAnalysisRecord(
                    qualified_name="repo.pkg.alpha.Service.execute",
                    node_type="callable",
                    callee_identifiers=("bar",),
                ),
            ]
        )


def _configure_fake_engine(monkeypatch, analyzer) -> None:
    from sciona.code_analysis.artifacts import engine as engine_module

    monkeypatch.setattr(engine_module.git_ops, "tracked_paths", lambda _root: set())
    monkeypatch.setattr(
        engine_module.git_ops, "ignored_tracked_paths", lambda _root: set()
    )
    monkeypatch.setattr(
        engine_module.walker,
        "collect_files",
        lambda *args, **kwargs: [_FakeFileRecord("python", "pkg/alpha/service.py")],
    )
    monkeypatch.setattr(
        engine_module.snapshots,
        "prepare_file_snapshots",
        lambda *args, **kwargs: [_FakeFileSnapshot(_FakeFileRecord("python", "pkg/alpha/service.py"))],
    )
    monkeypatch.setattr(engine_module, "_load_node_map", lambda *args: {
        ("repo.pkg.alpha.Service.run", "callable"): "caller-1",
        ("repo.pkg.alpha.Service.execute", "callable"): "caller-1",
    })
    monkeypatch.setattr(engine_module, "_load_module_index", lambda *args: {"repo.pkg.alpha"})
    monkeypatch.setattr(engine_module.routing, "resolve_analyzer", lambda *args: analyzer)


def _write_test_config(repo_root: Path) -> None:
    config_dir = repo_root / ".sciona"
    config_dir.mkdir(exist_ok=True)
    (config_dir / "config.yaml").write_text(
        "languages:\n  python:\n    enabled: true\n",
        encoding="utf-8",
    )


def test_artifact_engine_merges_duplicate_caller_records(monkeypatch, tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    _write_test_config(repo_root)
    db_path = repo_root / ".sciona" / "sciona.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        _configure_fake_engine(monkeypatch, _FakeAnalyzer())
        engine = ArtifactEngine(repo_root, conn, config_root=repo_root)
        results = engine.run(snapshot_id)
    finally:
        conn.close()

    assert len(results) == 1
    assert results[0].caller_structural_id == "caller-1"
    assert results[0].caller_qualified_name == "repo.pkg.alpha.Service.run"
    assert results[0].callee_identifiers == ("foo", "bar", "baz")


def test_artifact_engine_rejects_conflicting_duplicate_caller_metadata(
    monkeypatch, tmp_path
):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    _write_test_config(repo_root)
    db_path = repo_root / ".sciona" / "sciona.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        _configure_fake_engine(monkeypatch, _ConflictingAnalyzer())
        engine = ArtifactEngine(repo_root, conn, config_root=repo_root)
        try:
            engine.run(snapshot_id)
        except RuntimeError as exc:
            assert "Conflicting caller metadata" in str(exc)
        else:
            raise AssertionError("Expected conflicting caller metadata to raise")
    finally:
        conn.close()
