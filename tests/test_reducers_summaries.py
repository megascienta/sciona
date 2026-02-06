# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import json
import sqlite3

from sciona.reducers.summaries import callsite_index, importers_index

from tests.helpers import seed_repo_with_snapshot


def _strip_json_fence(text: str) -> str:
    trimmed = text.strip()
    if trimmed.startswith("```json") and trimmed.endswith("```"):
        lines = trimmed.splitlines()
        return "\n".join(lines[1:-1])
    return trimmed


def _core_conn(repo_root):
    conn = sqlite3.connect(repo_root / ".sciona" / "sciona.db")
    conn.row_factory = sqlite3.Row
    return conn


def test_importers_index_returns_importers(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        payload_text = importers_index.render(
            snapshot_id,
            conn,
            repo_root,
            module_id="pkg.alpha",
        )
    finally:
        conn.close()
    payload = json.loads(_strip_json_fence(payload_text))
    assert payload["importers"]
    assert any(
        entry["module_qualified_name"] == "pkg.beta" for entry in payload["importers"]
    )


def test_callsite_index_reducer_returns_payload(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        payload_text = callsite_index.render(
            snapshot_id,
            conn,
            repo_root,
            function_id="pkg.alpha.service.helper",
        )
    finally:
        conn.close()
    payload = json.loads(_strip_json_fence(payload_text))
    assert payload["callable_id"]
    assert "edges" in payload
    assert "artifact_available" in payload
    assert "edge_source" in payload
    if payload["edges"]:
        edge = payload["edges"][0]
        assert "caller_node_type" in edge
        assert "callee_node_type" in edge
