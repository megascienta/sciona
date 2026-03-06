# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import pytest
import json

from sciona.reducers import (
    call_resolution_drop_summary,
    call_resolution_quality,
    callsite_index,
    classifier_call_graph_summary,
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
    callable_id = qualify_repo_name(repo_root, "pkg.alpha.service.helper")
    conn = core_conn(repo_root)
    try:
        payload_text = callsite_index.render(
            snapshot_id,
            conn,
            repo_root,
            callable_id=callable_id,
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["callable_id"]
    assert "edges" in payload
    assert "artifact_available" in payload
    assert "edge_source" in payload
    assert "resolution_diagnostics" in payload
    assert "edge_transition_summary" in payload
    if payload["edges"]:
        edge = payload["edges"][0]
        assert "caller_node_type" in edge
        assert "callee_node_type" in edge
        assert edge["row_origin"] == "committed"
        assert edge["transition"] == "unchanged"


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
    assert "committed_totals" in payload
    assert "overlay_adjusted_totals" in payload
    assert "overlay_delta_totals" in payload
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


def test_call_resolution_drop_summary_aggregates_dropped_callsites(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = core_conn(repo_root)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
            VALUES (?, ?, ?, ?)
            """,
            ("mod_pkg_tests", "module", "python", snapshot_id),
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO node_instances(
                instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{snapshot_id}:mod_pkg_tests",
                "mod_pkg_tests",
                snapshot_id,
                qualify_repo_name(repo_root, "pkg.tests"),
                "tests/test_case.py",
                1,
                12,
                "hash-mod-pkg-tests",
            ),
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
            VALUES (?, ?, ?, ?)
            """,
            ("func_test_case", "callable", "python", snapshot_id),
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO node_instances(
                instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{snapshot_id}:func_test_case",
                "func_test_case",
                snapshot_id,
                qualify_repo_name(repo_root, "pkg.tests.test_case.helper"),
                "tests/test_case.py",
                1,
                12,
                "hash-func-test-case",
            ),
        )
        conn.execute(
            """
            INSERT INTO edges(snapshot_id, src_structural_id, dst_structural_id, edge_type)
            VALUES (?, ?, ?, ?)
            """,
            (snapshot_id, "mod_pkg_tests", "func_test_case", "LEXICALLY_CONTAINS"),
        )
        conn.commit()
    finally:
        conn.close()

    artifact_db = repo_root / ".sciona" / setup_config.ARTIFACT_DB_FILENAME
    artifact_conn = artifact_connect(artifact_db, repo_root=repo_root)
    try:
        artifact_write.upsert_call_sites(
            artifact_conn,
            snapshot_id=snapshot_id,
            caller_id="func_alpha",
            caller_qname=qualify_repo_name(repo_root, "pkg.alpha.service.helper"),
            caller_node_type="callable",
            rows=[
                (
                    "helper",
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
                    "missing_helper",
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
        artifact_write.upsert_call_sites(
            artifact_conn,
            snapshot_id=snapshot_id,
            caller_id="func_test_case",
            caller_qname=qualify_repo_name(repo_root, "pkg.tests.test_case.helper"),
            caller_node_type="callable",
            rows=[
                (
                    "pkg.external.helper",
                    "dropped",
                    None,
                    None,
                    "ambiguous_no_in_scope_candidate",
                    3,
                    "qualified",
                    11,
                    15,
                    0,
                ),
            ],
        )
        artifact_conn.commit()
    finally:
        artifact_conn.close()

    conn = core_conn(repo_root)
    try:
        payload_text = call_resolution_drop_summary.render(
            snapshot_id,
            conn,
            repo_root,
            limit=5,
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["payload_kind"] == "summary"
    assert payload["artifact_available"] is True
    assert payload["totals"]["eligible"] == 3
    assert payload["totals"]["accepted"] == 1
    assert payload["totals"]["dropped"] == 2
    assert payload["dropped_by_reason"] == [
        {"name": "ambiguous_no_in_scope_candidate", "count": 1},
        {"name": "no_candidates", "count": 1},
    ]
    assert payload["dropped_by_reason_by_language"] == [
        {
            "language": "python",
            "dropped": 2,
            "drop_reasons": [
                {"name": "ambiguous_no_in_scope_candidate", "count": 1},
                {"name": "no_candidates", "count": 1},
            ],
        }
    ]
    assert payload["dropped_by_reason_by_scope"]["non_tests"] == [
        {"name": "no_candidates", "count": 1}
    ]
    assert payload["dropped_by_reason_by_scope"]["tests"] == [
        {"name": "ambiguous_no_in_scope_candidate", "count": 1}
    ]
    assert payload["top_callers_by_drop_count"][0]["caller_id"] == "func_alpha"
    assert payload["top_callers_by_drop_count"][1]["caller_id"] == "func_test_case"
    assert payload["committed_totals"] == payload["totals"]
    assert payload["overlay_adjusted_totals"] == payload["totals"]
    assert payload["overlay_delta_totals"] == {
        "eligible": 0,
        "accepted": 0,
        "dropped": 0,
    }


def test_resolution_trace_returns_payload(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = core_conn(repo_root)
    callable_id = qualify_repo_name(repo_root, "pkg.alpha.service.helper")
    try:
        payload_text = resolution_trace.render(
            snapshot_id,
            conn,
            repo_root,
            callable_id=callable_id,
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["payload_kind"] == "summary"
    assert payload["callable_id"]
    assert "resolution_pipeline_stages" in payload
    assert "accepted_samples" in payload
    assert "dropped_samples" in payload


def test_call_resolution_drop_summary_rejects_invalid_limit(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = core_conn(repo_root)
    try:
        with pytest.raises(ValueError, match="positive integer"):
            call_resolution_drop_summary.render(
                snapshot_id,
                conn,
                repo_root,
                limit=0,
            )
    finally:
        conn.close()


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
            callable_id=qualify_repo_name(repo_root, "pkg.alpha.service.helper"),
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
    assert "low_node_file_diagnostics" in payload
    totals = payload["low_node_file_diagnostics"]["totals"]
    assert totals["files"] >= 1
    assert totals["inflation_warning"] is False
    reconciliation = payload["low_node_file_diagnostics"]["discovery_reconciliation"]
    assert "totals" in reconciliation
    assert "inferred_zero_node_files" in reconciliation["totals"]


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
    assert "low_node_file_diagnostics" in payload
    assert "discovery_reconciliation" in payload["low_node_file_diagnostics"]


def test_callsite_index_neighbors_detail_level(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    callable_id = qualify_repo_name(repo_root, "pkg.alpha.service.helper")
    conn = core_conn(repo_root)
    try:
        payload_text = callsite_index.render(
            snapshot_id,
            conn,
            repo_root,
            callable_id=callable_id,
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


def test_fan_summary_filters_by_edge_kind_node_kind_and_min_fan(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    artifact_db = repo_root / ".sciona" / setup_config.ARTIFACT_DB_FILENAME
    artifact_conn = artifact_connect(artifact_db, repo_root=repo_root)
    try:
        artifact_conn.execute(
            """
            INSERT OR REPLACE INTO node_fan_stats(node_id, node_kind, edge_kind, fan_in, fan_out)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("meth_alpha", "callable", "CALLS", 3, 1),
        )
        artifact_conn.execute(
            """
            INSERT OR REPLACE INTO node_fan_stats(node_id, node_kind, edge_kind, fan_in, fan_out)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("func_alpha", "callable", "CALLS", 1, 1),
        )
        artifact_conn.commit()
    finally:
        artifact_conn.close()
    conn = core_conn(repo_root)
    try:
        payload_text = fan_summary.render(
            snapshot_id,
            conn,
            repo_root,
            edge_kind="CALLS",
            node_kind="callable",
            min_fan=2,
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["filters"]["edge_kind"] == "CALLS"
    assert payload["filters"]["node_kind"] == "callable"
    assert payload["filters"]["min_fan"] == 2
    assert payload["imports"]["total"] == 0
    assert payload["calls"]["total"] >= 1
    assert all(entry["count"] >= 2 for entry in payload["calls"]["by_fan_in"])


def test_hotspot_summary_returns_payload(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = core_conn(repo_root)
    try:
        payload_text = hotspot_summary.render(snapshot_id, conn, repo_root)
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["payload_kind"] == "summary"
    assert payload["version"] == 2
    assert "by_size" in payload
    assert "by_fan_in" in payload
    assert "by_fan_out" in payload
    assert "by_call_fan_in" in payload
    assert "by_call_fan_out" in payload
    assert "by_import_fan_in" in payload
    assert "by_import_fan_out" in payload


def test_hotspot_summary_v2_uses_rollup_fan_stats(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    artifact_db = repo_root / ".sciona" / setup_config.ARTIFACT_DB_FILENAME
    conn = artifact_connect(artifact_db, repo_root=repo_root)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO node_fan_stats(node_id, node_kind, edge_kind, fan_in, fan_out)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("mod_alpha", "module", "CALLS", 5, 2),
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO node_fan_stats(node_id, node_kind, edge_kind, fan_in, fan_out)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("mod_beta", "module", "CALLS", 1, 7),
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO node_fan_stats(node_id, node_kind, edge_kind, fan_in, fan_out)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("mod_alpha", "module", "IMPORTS_DECLARED", 3, 8),
        )
        conn.commit()
    finally:
        conn.close()

    core = core_conn(repo_root)
    try:
        payload_text = hotspot_summary.render(snapshot_id, core, repo_root)
    finally:
        core.close()
    payload = parse_json_payload(payload_text)
    assert payload["by_call_fan_in"][0]["module_id"] == "mod_alpha"
    assert payload["by_call_fan_out"][0]["module_id"] == "mod_beta"
    assert payload["by_import_fan_out"][0]["module_id"] == "mod_alpha"


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
    assert payload["changed_edge_count"] == 0
    if payload["outgoing"]:
        assert payload["outgoing"][0]["row_origin"] == "committed"
        assert payload["outgoing"][0]["delta_call_count"] == 0


def test_class_call_graph_summary_returns_payload(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    classifier_id = qualify_repo_name(repo_root, "pkg.alpha.Service")
    conn = core_conn(repo_root)
    try:
        payload_text = classifier_call_graph_summary.render(
            snapshot_id, conn, repo_root, classifier_id=classifier_id, top_k=5
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["payload_kind"] == "summary"
    assert payload["classifier_id"] == classifier_id
    assert "outgoing" in payload
    assert "incoming" in payload
    assert payload["changed_edge_count"] == 0
    if payload["outgoing"]:
        assert payload["outgoing"][0]["row_origin"] == "committed"
        assert payload["outgoing"][0]["delta_call_count"] == 0


def test_module_call_graph_summary_can_narrow_by_peer_modules(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    module_id = qualify_repo_name(repo_root, "pkg.alpha")
    other_module_id = qualify_repo_name(repo_root, "pkg.beta")
    artifact_db = repo_root / ".sciona" / setup_config.ARTIFACT_DB_FILENAME
    artifact_conn = artifact_connect(artifact_db, repo_root=repo_root)
    try:
        artifact_conn.execute(
            """
            INSERT OR REPLACE INTO module_call_edges(src_module_id, dst_module_id, call_count)
            VALUES (?, ?, ?)
            """,
            ("mod_alpha", "mod_beta", 5),
        )
        artifact_conn.execute(
            """
            INSERT OR REPLACE INTO module_call_edges(src_module_id, dst_module_id, call_count)
            VALUES (?, ?, ?)
            """,
            ("mod_beta", "mod_alpha", 4),
        )
        artifact_conn.commit()
    finally:
        artifact_conn.close()
    conn = core_conn(repo_root)
    try:
        payload_text = module_call_graph_summary.render(
            snapshot_id,
            conn,
            repo_root,
            module_id=module_id,
            from_module_id=other_module_id,
            to_module_id=other_module_id,
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["module_qualified_name"] == module_id
    assert payload["from_module_id"] == other_module_id
    assert payload["to_module_id"] == other_module_id
    assert payload["outgoing_total"] == 1
    assert payload["incoming_total"] == 1
    assert payload["outgoing"][0]["dst_module_qualified_name"] == other_module_id
    assert payload["incoming"][0]["src_module_qualified_name"] == other_module_id


def test_classifier_call_graph_summary_can_narrow_by_peer_classifiers(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    artifact_db = repo_root / ".sciona" / setup_config.ARTIFACT_DB_FILENAME
    conn = core_conn(repo_root)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
            VALUES (?, ?, ?, ?)
            """,
            ("cls_other", "classifier", "python", snapshot_id),
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO node_instances(
                instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{snapshot_id}:cls_other",
                "cls_other",
                snapshot_id,
                qualify_repo_name(repo_root, "pkg.beta.Other"),
                "pkg/beta/other.py",
                1,
                10,
                "hash-cls-other",
            ),
        )
        conn.commit()
    finally:
        conn.close()
    artifact_conn = artifact_connect(artifact_db, repo_root=repo_root)
    try:
        artifact_conn.execute(
            """
            INSERT OR REPLACE INTO graph_nodes(node_id, node_kind)
            VALUES (?, ?)
            """,
            ("cls_other", "classifier"),
        )
        artifact_conn.execute(
            """
            INSERT OR REPLACE INTO class_call_edges(src_class_id, dst_class_id, call_count)
            VALUES (?, ?, ?)
            """,
            ("cls_alpha", "cls_other", 4),
        )
        artifact_conn.execute(
            """
            INSERT OR REPLACE INTO class_call_edges(src_class_id, dst_class_id, call_count)
            VALUES (?, ?, ?)
            """,
            ("cls_other", "cls_alpha", 3),
        )
        artifact_conn.commit()
    finally:
        artifact_conn.close()
    conn = core_conn(repo_root)
    try:
        payload_text = classifier_call_graph_summary.render(
            snapshot_id,
            conn,
            repo_root,
            classifier_id=qualify_repo_name(repo_root, "pkg.alpha.Service"),
            caller_id=qualify_repo_name(repo_root, "pkg.beta.Other"),
            callee_id=qualify_repo_name(repo_root, "pkg.beta.Other"),
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    other_id = qualify_repo_name(repo_root, "pkg.beta.Other")
    assert payload["classifier_id"] == qualify_repo_name(repo_root, "pkg.alpha.Service")
    assert payload["caller_id"] == other_id
    assert payload["callee_id"] == other_id
    assert payload["outgoing_total"] == 1
    assert payload["incoming_total"] == 1
    assert payload["outgoing"][0]["dst_classifier_id"] == "cls_other"
    assert payload["incoming"][0]["src_classifier_id"] == "cls_other"


def test_callsite_index_rejects_invalid_detail_level(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    callable_id = qualify_repo_name(repo_root, "pkg.alpha.service.helper")
    conn = core_conn(repo_root)
    try:
        with pytest.raises(ValueError, match="detail_level must be"):
            callsite_index.render(
                snapshot_id,
                conn,
                repo_root,
                callable_id=callable_id,
                detail_level="verbose",
            )
    finally:
        conn.close()


def test_callsite_index_rejects_invalid_direction(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    callable_id = qualify_repo_name(repo_root, "pkg.alpha.service.helper")
    conn = core_conn(repo_root)
    try:
        with pytest.raises(ValueError, match="direction must be one of"):
            callsite_index.render(
                snapshot_id,
                conn,
                repo_root,
                callable_id=callable_id,
                direction="up",
            )
    finally:
        conn.close()
