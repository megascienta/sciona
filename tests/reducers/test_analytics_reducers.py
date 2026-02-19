# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import json
import sqlite3

from sciona.reducers.analytics import (
    callsite_index,
    class_call_graph_summary,
    fan_summary,
    hotspot_summary,
    module_call_graph_summary,
)
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


def test_callsite_index_neighbors_detail_level(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        payload_text = callsite_index.render(
            snapshot_id,
            conn,
            repo_root,
            function_id="pkg.alpha.service.helper",
            detail_level="neighbors",
        )
    finally:
        conn.close()
    payload = json.loads(_strip_json_fence(payload_text))
    assert payload["callable_id"]
    assert "callers" in payload
    assert "callees" in payload


def test_fan_summary_returns_payload(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        payload_text = fan_summary.render(snapshot_id, conn, repo_root, top_k=3)
    finally:
        conn.close()
    payload = json.loads(_strip_json_fence(payload_text))
    assert payload["payload_kind"] == "summary"
    assert "calls" in payload
    assert "imports" in payload


def test_hotspot_summary_returns_payload(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        payload_text = hotspot_summary.render(snapshot_id, conn, repo_root)
    finally:
        conn.close()
    payload = json.loads(_strip_json_fence(payload_text))
    assert payload["payload_kind"] == "summary"
    assert "by_size" in payload
    assert "by_fan_in" in payload
    assert "by_fan_out" in payload


def test_module_call_graph_summary_returns_payload(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        payload_text = module_call_graph_summary.render(
            snapshot_id, conn, repo_root, module_id="pkg.alpha", top_k=5
        )
    finally:
        conn.close()
    payload = json.loads(_strip_json_fence(payload_text))
    assert payload["payload_kind"] == "summary"
    assert payload["module_qualified_name"] == "pkg.alpha"
    assert "outgoing" in payload
    assert "incoming" in payload


def test_class_call_graph_summary_returns_payload(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = _core_conn(repo_root)
    try:
        payload_text = class_call_graph_summary.render(
            snapshot_id, conn, repo_root, class_id="pkg.alpha.Service", top_k=5
        )
    finally:
        conn.close()
    payload = json.loads(_strip_json_fence(payload_text))
    assert payload["payload_kind"] == "summary"
    assert payload["class_id"] == "pkg.alpha.Service"
    assert "outgoing" in payload
    assert "incoming" in payload
