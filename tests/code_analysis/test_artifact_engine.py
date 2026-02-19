# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import sqlite3

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
