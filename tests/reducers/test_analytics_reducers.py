# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import pytest
import json

from sciona.reducers.analytics import (
    call_resolution_quality,
    callsite_index,
    class_call_graph_summary,
    fan_summary,
    hotspot_summary,
    module_call_graph_summary,
    resolution_trace,
    structural_integrity_summary,
)
from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.data_storage.artifact_db import write_index as artifact_write
from sciona.runtime import constants as setup_config
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


def test_call_resolution_quality_returns_payload(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = core_conn(repo_root)
    try:
        payload_text = call_resolution_quality.render(snapshot_id, conn, repo_root)
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["payload_kind"] == "summary"
    assert "totals" in payload
    assert "by_language" in payload
    assert "by_module" in payload
    assert "by_caller" in payload


def test_call_resolution_quality_aggregates_callsite_rows(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    artifact_db = repo_root / ".sciona" / setup_config.ARTIFACT_DB_FILENAME
    conn = artifact_connect(artifact_db, repo_root=repo_root)
    try:
        artifact_write.upsert_call_sites(
            conn,
            snapshot_id=snapshot_id,
            caller_id="func_alpha",
            caller_qname=qualify_repo_name(repo_root, "pkg.alpha.service.helper"),
            caller_node_type="callable",
            rows=[
                (
                    "pkg.beta.worker",
                    "accepted",
                    "func_beta",
                    "exact_qname",
                    None,
                    1,
                    "qualified",
                    1,
                    5,
                    0,
                ),
                (
                    "pkg.unknown.missing",
                    "dropped",
                    None,
                    None,
                    "no_candidates",
                    1,
                    "qualified",
                    6,
                    10,
                    1,
                ),
            ],
        )
        conn.commit()
    finally:
        conn.close()

    core = core_conn(repo_root)
    try:
        payload_text = call_resolution_quality.render(snapshot_id, core, repo_root)
    finally:
        core.close()
    payload = parse_json_payload(payload_text)
    assert payload["totals"]["eligible"] == 2
    assert payload["totals"]["accepted"] == 1
    assert payload["totals"]["dropped"] == 1
    assert payload["drop_reason_counts"][0]["name"] == "no_candidates"
    assert payload["drop_reason_counts"][0]["count"] == 1


def test_resolution_trace_returns_payload(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = core_conn(repo_root)
    function_id = qualify_repo_name(repo_root, "pkg.alpha.service.helper")
    try:
        payload_text = resolution_trace.render(
            snapshot_id,
            conn,
            repo_root,
            function_id=function_id,
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["payload_kind"] == "summary"
    assert payload["callable_id"]
    assert "resolution_pipeline_stages" in payload
    assert "accepted_samples" in payload
    assert "dropped_samples" in payload


def test_resolution_trace_uses_callsite_and_diagnostics(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    artifact_db = repo_root / ".sciona" / setup_config.ARTIFACT_DB_FILENAME
    conn = artifact_connect(artifact_db, repo_root=repo_root)
    try:
        artifact_write.upsert_call_sites(
            conn,
            snapshot_id=snapshot_id,
            caller_id="func_alpha",
            caller_qname=qualify_repo_name(repo_root, "pkg.alpha.service.helper"),
            caller_node_type="callable",
            rows=[
                (
                    "pkg.beta.worker",
                    "accepted",
                    "func_beta",
                    "exact_qname",
                    None,
                    1,
                    "qualified",
                    1,
                    5,
                    0,
                ),
                (
                    "pkg.unknown.missing",
                    "dropped",
                    None,
                    None,
                    "no_candidates",
                    2,
                    "qualified",
                    6,
                    10,
                    1,
                ),
            ],
        )
        artifact_write.set_rebuild_metadata(
            conn,
            key=f"call_resolution_diagnostics:{snapshot_id}",
            value=json.dumps(
                {
                    "version": 1,
                    "by_caller": {
                        "func_alpha": {
                            "identifiers_total": 2,
                            "accepted_identifiers": 1,
                            "dropped_identifiers": 1,
                            "accepted_by_provenance": {"exact_qname": 1},
                            "dropped_by_reason": {"no_candidates": 1},
                            "candidate_count_histogram": {"1": 1, "2": 1},
                            "record_drops": {},
                            "assembler_accepted_artifact_dropped": 0,
                        }
                    },
                },
                sort_keys=True,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    core = core_conn(repo_root)
    try:
        payload_text = resolution_trace.render(
            snapshot_id,
            core,
            repo_root,
            function_id=qualify_repo_name(repo_root, "pkg.alpha.service.helper"),
        )
    finally:
        core.close()
    payload = parse_json_payload(payload_text)
    assert payload["totals"] == {"eligible": 2, "accepted": 1, "dropped": 1}
    assert payload["accepted_by_provenance"][0] == {"name": "exact_qname", "count": 1}
    assert payload["dropped_by_reason"][0] == {"name": "no_candidates", "count": 1}
    assert payload["accepted_samples"][0]["identifier"] == "pkg.beta.worker"
    assert payload["dropped_samples"][0]["identifier"] == "pkg.unknown.missing"
    assert payload["dropped_samples"][0]["drop_reason"] == "no_candidates"


def test_structural_integrity_summary_returns_payload(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = core_conn(repo_root)
    try:
        payload_text = structural_integrity_summary.render(snapshot_id, conn, repo_root)
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["payload_kind"] == "summary"
    assert "integrity_ok" in payload
    assert "duplicate_qualified_names" in payload
    assert "lexical_orphans" in payload
    assert "inheritance_cycles" in payload


def test_structural_integrity_summary_detects_duplicates_and_orphans(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = core_conn(repo_root)
    try:
        conn.execute(
            """
            INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
            VALUES (?, ?, ?, ?)
            """,
            ("func_dup", "callable", "python", snapshot_id),
        )
        conn.execute(
            """
            INSERT INTO node_instances(
                instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{snapshot_id}:func_dup",
                "func_dup",
                snapshot_id,
                qualify_repo_name(repo_root, "pkg.alpha.service.helper"),
                "pkg/alpha/other.py",
                1,
                2,
                "hash-func_dup",
            ),
        )
        conn.execute(
            """
            INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
            VALUES (?, ?, ?, ?)
            """,
            ("func_orphan", "callable", "python", snapshot_id),
        )
        conn.execute(
            """
            INSERT INTO node_instances(
                instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{snapshot_id}:func_orphan",
                "func_orphan",
                snapshot_id,
                qualify_repo_name(repo_root, "pkg.alpha.orphan"),
                "pkg/alpha/orphan.py",
                1,
                2,
                "hash-func_orphan",
            ),
        )
        conn.commit()
        payload_text = structural_integrity_summary.render(snapshot_id, conn, repo_root)
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    duplicate_names = {
        entry["qualified_name"] for entry in payload["duplicate_qualified_names"]
    }
    orphan_ids = {entry["structural_id"] for entry in payload["lexical_orphans"]}
    assert qualify_repo_name(repo_root, "pkg.alpha.service.helper") in duplicate_names
    assert "func_orphan" in orphan_ids
    assert payload["integrity_ok"] is False


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
