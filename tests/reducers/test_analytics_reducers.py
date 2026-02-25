# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import pytest

from sciona.reducers.analytics import (
    callsite_index,
    class_call_graph_summary,
    fan_summary,
    hotspot_summary,
    module_call_graph_summary,
)
from tests.helpers import core_conn, parse_json_payload, qualify_repo_name, seed_repo_with_snapshot


def test_callsite_index_reducer_returns_payload(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    function_id = qualify_repo_name(repo_root, "pkg.alpha.service.helper")
    conn = core_conn(repo_root)
    try:
        payload_text = callsite_index.render(
            snapshot_id,
            conn,
            repo_root,
            function_id=function_id,
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["callable_id"]
    assert "edges" in payload
    assert "artifact_available" in payload
    assert "edge_source" in payload
    assert "resolution_diagnostics" in payload
    if payload["edges"]:
        edge = payload["edges"][0]
        assert "caller_node_type" in edge
        assert "callee_node_type" in edge


def test_callsite_index_neighbors_detail_level(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    function_id = qualify_repo_name(repo_root, "pkg.alpha.service.helper")
    conn = core_conn(repo_root)
    try:
        payload_text = callsite_index.render(
            snapshot_id,
            conn,
            repo_root,
            function_id=function_id,
            detail_level="neighbors",
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["callable_id"]
    assert "callers" in payload
    assert "callees" in payload


def test_fan_summary_returns_payload(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = core_conn(repo_root)
    try:
        payload_text = fan_summary.render(snapshot_id, conn, repo_root, top_k=3)
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["payload_kind"] == "summary"
    assert "calls" in payload
    assert "imports" in payload


def test_hotspot_summary_returns_payload(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = core_conn(repo_root)
    try:
        payload_text = hotspot_summary.render(snapshot_id, conn, repo_root)
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["payload_kind"] == "summary"
    assert "by_size" in payload
    assert "by_fan_in" in payload
    assert "by_fan_out" in payload


def test_module_call_graph_summary_returns_payload(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    module_id = qualify_repo_name(repo_root, "pkg.alpha")
    conn = core_conn(repo_root)
    try:
        payload_text = module_call_graph_summary.render(
            snapshot_id, conn, repo_root, module_id=module_id, top_k=5
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["payload_kind"] == "summary"
    assert payload["module_qualified_name"] == module_id
    assert "outgoing" in payload
    assert "incoming" in payload


def test_class_call_graph_summary_returns_payload(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    class_id = qualify_repo_name(repo_root, "pkg.alpha.Service")
    conn = core_conn(repo_root)
    try:
        payload_text = class_call_graph_summary.render(
            snapshot_id, conn, repo_root, class_id=class_id, top_k=5
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["payload_kind"] == "summary"
    assert payload["class_id"] == class_id
    assert "outgoing" in payload
    assert "incoming" in payload


def test_callsite_index_rejects_invalid_detail_level(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    function_id = qualify_repo_name(repo_root, "pkg.alpha.service.helper")
    conn = core_conn(repo_root)
    try:
        with pytest.raises(ValueError, match="detail_level must be"):
            callsite_index.render(
                snapshot_id,
                conn,
                repo_root,
                function_id=function_id,
                detail_level="verbose",
            )
    finally:
        conn.close()


def test_callsite_index_rejects_invalid_direction(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    function_id = qualify_repo_name(repo_root, "pkg.alpha.service.helper")
    conn = core_conn(repo_root)
    try:
        with pytest.raises(ValueError, match="direction must be one of"):
            callsite_index.render(
                snapshot_id,
                conn,
                repo_root,
                function_id=function_id,
                direction="up",
            )
    finally:
        conn.close()
