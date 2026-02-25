# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from sciona.pipelines.exec.build import build_repo
from sciona.pipelines.domain.repository import RepoState
from sciona.pipelines.policy import build as policy_build
from sciona.pipelines.policy import snapshot as snapshot_policy
from sciona.reducers.analytics import hotspot_summary
from sciona.reducers.core import module_overview, structural_index, symbol_lookup
from sciona.runtime.errors import GitError
from sciona.runtime.paths import get_db_path
from tests.helpers import parse_json_payload


@pytest.fixture(scope="module")
def real_repo_snapshot() -> tuple[Path, str]:
    repo_root = Path(__file__).resolve().parents[2]
    try:
        snapshot_id = snapshot_policy.latest_committed_snapshot_id(repo_root)
    except Exception:
        try:
            repo_state = RepoState.from_repo_root(repo_root)
            policy = policy_build.resolve_build_policy(
                repo_state,
                refresh_artifacts=False,
                refresh_calls=False,
            )
            snapshot_id = build_repo(repo_state, policy).snapshot_id
        except (GitError, Exception) as exc:
            pytest.skip(f"real-repo smoke requires a buildable clean repo: {exc}")
    return repo_root, snapshot_id


@pytest.fixture
def real_repo_conn(real_repo_snapshot):
    repo_root, _snapshot_id = real_repo_snapshot
    conn = sqlite3.connect(get_db_path(repo_root))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def test_real_repo_structural_index_smoke(real_repo_snapshot, real_repo_conn):
    repo_root, snapshot_id = real_repo_snapshot
    payload = structural_index.run(snapshot_id, conn=real_repo_conn, repo_root=repo_root)
    assert payload["projection"] == "structural_index"
    assert payload["payload_kind"] == "summary"
    assert payload["modules"]["count"] > 0
    assert payload["files"]["count"] > 0


def test_real_repo_module_overview_smoke(real_repo_snapshot, real_repo_conn):
    repo_root, snapshot_id = real_repo_snapshot
    module_id = "sciona.src.sciona.runtime.time"
    payload = module_overview.run(
        snapshot_id,
        conn=real_repo_conn,
        repo_root=repo_root,
        module_id=module_id,
    )
    assert payload["payload_kind"] == "summary"
    assert payload["module_qualified_name"] == module_id
    assert payload["file_count"] >= 1
    assert "functions" in payload


def test_real_repo_symbol_lookup_smoke(real_repo_snapshot, real_repo_conn):
    repo_root, snapshot_id = real_repo_snapshot
    payload_text = symbol_lookup.render(
        snapshot_id,
        real_repo_conn,
        repo_root,
        query="sciona.src.sciona.runtime.time.utc_now",
        kind="function",
        limit=5,
    )
    payload = parse_json_payload(payload_text)
    assert payload["payload_kind"] == "summary"
    assert payload["matches"]
    assert any(
        match["qualified_name"] == "sciona.src.sciona.runtime.time.utc_now"
        for match in payload["matches"]
    )


def test_real_repo_hotspot_summary_smoke(real_repo_snapshot, real_repo_conn):
    repo_root, snapshot_id = real_repo_snapshot
    payload_text = hotspot_summary.render(snapshot_id, real_repo_conn, repo_root)
    payload = parse_json_payload(payload_text)
    assert payload["payload_kind"] == "summary"
    assert "by_size" in payload
    assert "by_fan_in" in payload
    assert "by_fan_out" in payload
