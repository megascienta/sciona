# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

import pytest
import json

from sciona.pipelines.diff_overlay.types import OverlayPayload
from sciona.reducers import (
    classifier_call_graph_summary,
    fan_summary,
    hotspot_summary,
    module_call_graph_summary,
    structural_integrity_summary,
)
from sciona.reducers.helpers.shared.context import use_overlay_payload
from sciona.data_storage.artifact_db import connect as artifact_connect
from sciona.data_storage.artifact_db.writes import write_index as artifact_write
from sciona.runtime.common import constants as setup_config
from tests.helpers import core_conn, parse_json_payload, qualify_repo_name, seed_repo_with_snapshot


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


def test_structural_integrity_summary_excludes_classifier_contained_methods(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = core_conn(repo_root)
    try:
        conn.execute(
            """
            INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
            VALUES (?, ?, ?, ?)
            """,
            ("cls_extra", "classifier", "python", snapshot_id),
        )
        conn.execute(
            """
            INSERT INTO node_instances(
                instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{snapshot_id}:cls_extra",
                "cls_extra",
                snapshot_id,
                qualify_repo_name(repo_root, "pkg.alpha.extra.Extra"),
                "pkg/alpha/extra.py",
                1,
                10,
                "hash-cls-extra",
            ),
        )
        conn.execute(
            """
            INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
            VALUES (?, ?, ?, ?)
            """,
            ("meth_extra", "callable", "python", snapshot_id),
        )
        conn.execute(
            """
            INSERT INTO node_instances(
                instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{snapshot_id}:meth_extra",
                "meth_extra",
                snapshot_id,
                qualify_repo_name(repo_root, "pkg.alpha.extra.Extra.run"),
                "pkg/alpha/extra.py",
                2,
                4,
                "hash-meth-extra",
            ),
        )
        conn.execute(
            """
            INSERT INTO edges(snapshot_id, src_structural_id, dst_structural_id, edge_type)
            VALUES (?, ?, ?, ?)
            """,
            (snapshot_id, "cls_extra", "meth_extra", "LEXICALLY_CONTAINS"),
        )
        conn.commit()
        payload_text = structural_integrity_summary.render(snapshot_id, conn, repo_root)
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    orphan_ids = {entry["structural_id"] for entry in payload["lexical_orphans"]}
    assert "meth_extra" not in orphan_ids


def test_structural_integrity_summary_excludes_callable_contained_callables(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = core_conn(repo_root)
    try:
        conn.execute(
            """
            INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
            VALUES (?, ?, ?, ?)
            """,
            ("func_parent", "callable", "python", snapshot_id),
        )
        conn.execute(
            """
            INSERT INTO node_instances(
                instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{snapshot_id}:func_parent",
                "func_parent",
                snapshot_id,
                qualify_repo_name(repo_root, "pkg.alpha.outer"),
                "pkg/alpha/outer.py",
                1,
                10,
                "hash-func-parent",
            ),
        )
        conn.execute(
            """
            INSERT INTO structural_nodes(structural_id, node_type, language, created_snapshot_id)
            VALUES (?, ?, ?, ?)
            """,
            ("func_child", "callable", "python", snapshot_id),
        )
        conn.execute(
            """
            INSERT INTO node_instances(
                instance_id, structural_id, snapshot_id, qualified_name, file_path, start_line, end_line, content_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{snapshot_id}:func_child",
                "func_child",
                snapshot_id,
                qualify_repo_name(repo_root, "pkg.alpha.outer.inner"),
                "pkg/alpha/outer.py",
                2,
                4,
                "hash-func-child",
            ),
        )
        conn.execute(
            """
            INSERT INTO edges(snapshot_id, src_structural_id, dst_structural_id, edge_type)
            VALUES (?, ?, ?, ?)
            """,
            (snapshot_id, "func_parent", "func_child", "LEXICALLY_CONTAINS"),
        )
        conn.commit()
        payload_text = structural_integrity_summary.render(snapshot_id, conn, repo_root)
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    orphan_ids = {entry["structural_id"] for entry in payload["lexical_orphans"]}
    assert "func_child" not in orphan_ids


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
    if payload["calls"]["by_fan_in"]:
        assert payload["calls"]["by_fan_in"][0]["delta_count"] == 0


def test_fan_summary_compact_mode_returns_previews(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    conn = core_conn(repo_root)
    try:
        payload_text = fan_summary.render(
            snapshot_id,
            conn,
            repo_root,
            compact=True,
            top_k=3,
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["payload_kind"] == "compact_summary"
    assert "calls" not in payload
    assert "imports" not in payload
    assert "calls_preview" in payload
    assert "imports_preview" in payload


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


def test_fan_summary_applies_overlay_during_render(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    artifact_db = repo_root / ".sciona" / setup_config.ARTIFACT_DB_FILENAME
    artifact_conn = artifact_connect(artifact_db, repo_root=repo_root)
    try:
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

    overlay = OverlayPayload(
        worktree_hash="hash",
        snapshot_commit="commit",
        base_commit="base",
        base_commit_strategy="snapshot",
        head_commit="head",
        merge_base=None,
        nodes={"add": [], "remove": [], "update": []},
        edges={"add": [], "remove": [], "update": []},
        calls={
            "add": [
                {
                    "src_structural_id": "func_alpha",
                    "dst_structural_id": "func_alpha",
                    "diff_kind": "add",
                }
            ],
            "remove": [],
            "update": [],
        },
        summary=None,
        warnings=[],
    )
    conn = core_conn(repo_root)
    try:
        with use_overlay_payload(overlay):
            payload_text = fan_summary.render(
                snapshot_id,
                conn,
                repo_root,
                edge_kind="CALLS",
                node_kind="callable",
                top_k=5,
            )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["_overlay_applied_by_reducer"] is True
    assert payload["calls"]["by_fan_in"][0]["count"] == 2
    assert payload["calls"]["by_fan_in"][0]["delta_count"] == 1
    assert payload["calls"]["by_fan_in"][0]["row_origin"] == "overlay_changed"
    assert payload["calls"]["by_fan_out"][0]["count"] == 2
    assert payload["calls"]["by_fan_out"][0]["delta_count"] == 1
    assert payload["calls"]["by_fan_out"][0]["row_origin"] == "overlay_changed"


def test_fan_summary_materializes_overlay_only_rows_during_render(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    overlay = OverlayPayload(
        worktree_hash="hash",
        snapshot_commit="commit",
        base_commit="base",
        base_commit_strategy="snapshot",
        head_commit="head",
        merge_base=None,
        nodes={"add": [], "remove": [], "update": []},
        edges={"add": [], "remove": [], "update": []},
        calls={
            "add": [
                {
                    "src_structural_id": "func_alpha",
                    "dst_structural_id": "meth_alpha",
                    "src_qualified_name": qualify_repo_name(
                        repo_root, "pkg.alpha.service.helper"
                    ),
                    "dst_qualified_name": qualify_repo_name(
                        repo_root, "pkg.alpha.Service.run"
                    ),
                    "diff_kind": "add",
                }
            ],
            "remove": [],
            "update": [],
        },
        summary=None,
        warnings=[],
    )
    conn = core_conn(repo_root)
    try:
        with use_overlay_payload(overlay):
            payload_text = fan_summary.render(
                snapshot_id,
                conn,
                repo_root,
                edge_kind="CALLS",
                node_kind="callable",
                top_k=5,
            )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["_overlay_applied_by_reducer"] is True
    assert payload["calls"]["total"] >= 2
    fan_in_ids = {entry["node_id"] for entry in payload["calls"]["by_fan_in"]}
    fan_out_ids = {entry["node_id"] for entry in payload["calls"]["by_fan_out"]}
    assert "meth_alpha" in fan_in_ids
    assert "func_alpha" in fan_out_ids


def test_fan_summary_node_view_applies_overlay_during_render(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    callable_id = qualify_repo_name(repo_root, "pkg.alpha.service.helper")
    overlay = OverlayPayload(
        worktree_hash="hash",
        snapshot_commit="commit",
        base_commit="base",
        base_commit_strategy="snapshot",
        head_commit="head",
        merge_base=None,
        nodes={"add": [], "remove": [], "update": []},
        edges={"add": [], "remove": [], "update": []},
        calls={
            "add": [
                {
                    "src_structural_id": "func_alpha",
                    "dst_structural_id": "func_alpha",
                    "diff_kind": "add",
                }
            ],
            "remove": [],
            "update": [],
        },
        summary=None,
        warnings=[],
    )
    conn = core_conn(repo_root)
    try:
        with use_overlay_payload(overlay):
            payload_text = fan_summary.render(
                snapshot_id,
                conn,
                repo_root,
                callable_id=callable_id,
                edge_kind="CALLS",
            )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["_overlay_applied_by_reducer"] is True
    assert payload["edge_kinds"]["CALLS"]["fan_in"] == 1
    assert payload["edge_kinds"]["CALLS"]["fan_out"] == 1
    assert payload["edge_kinds"]["CALLS"]["delta_fan_in"] == 1
    assert payload["edge_kinds"]["CALLS"]["delta_fan_out"] == 1


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
    assert payload["by_fan_in"][0]["module_qualified_name"] == qualify_repo_name(
        repo_root, "pkg.alpha"
    )
    assert payload["by_fan_in"][0]["count"] == 3
    assert payload["by_fan_out"][0]["module_qualified_name"] == qualify_repo_name(
        repo_root, "pkg.alpha"
    )
    assert payload["by_fan_out"][0]["count"] == 8
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


def test_module_call_graph_summary_applies_overlay_during_render(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    module_id = qualify_repo_name(repo_root, "pkg.alpha")
    overlay = OverlayPayload(
        worktree_hash="hash",
        snapshot_commit="commit",
        base_commit="base",
        base_commit_strategy="snapshot",
        head_commit="head",
        merge_base=None,
        nodes={"add": [], "remove": [], "update": []},
        edges={"add": [], "remove": [], "update": []},
        calls={
            "add": [
                {
                    "src_structural_id": "func_alpha",
                    "dst_structural_id": "func_alpha",
                    "src_node_type": "callable",
                    "dst_node_type": "callable",
                    "src_qualified_name": qualify_repo_name(
                        repo_root, "pkg.alpha.service.helper"
                    ),
                    "dst_qualified_name": qualify_repo_name(
                        repo_root, "pkg.alpha.service.helper"
                    ),
                    "src_file_path": "pkg/alpha/service.py",
                    "dst_file_path": "pkg/alpha/service.py",
                    "diff_kind": "add",
                }
            ],
            "remove": [],
            "update": [],
        },
        summary=None,
        warnings=[],
    )
    conn = core_conn(repo_root)
    try:
        with use_overlay_payload(overlay):
            payload_text = module_call_graph_summary.render(
                snapshot_id, conn, repo_root, module_id=module_id, top_k=5
            )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["_overlay_applied_by_reducer"] is True
    assert payload["changed_edge_count"] >= 1
    assert payload["added_edge_count"] >= 1
    assert payload["outgoing"]
    assert payload["outgoing"][0]["delta_call_count"] == 1


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


def test_classifier_call_graph_summary_applies_overlay_during_render(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    classifier_id = qualify_repo_name(repo_root, "pkg.alpha.Service")
    overlay = OverlayPayload(
        worktree_hash="hash",
        snapshot_commit="commit",
        base_commit="base",
        base_commit_strategy="snapshot",
        head_commit="head",
        merge_base=None,
        nodes={"add": [], "remove": [], "update": []},
        edges={"add": [], "remove": [], "update": []},
        calls={
            "add": [
                {
                    "src_structural_id": "meth_alpha",
                    "dst_structural_id": "meth_alpha",
                    "src_node_type": "callable",
                    "dst_node_type": "callable",
                    "src_qualified_name": qualify_repo_name(
                        repo_root, "pkg.alpha.Service.run"
                    ),
                    "dst_qualified_name": qualify_repo_name(
                        repo_root, "pkg.alpha.Service.run"
                    ),
                    "src_file_path": "pkg/alpha/service.py",
                    "dst_file_path": "pkg/alpha/service.py",
                    "diff_kind": "add",
                }
            ],
            "remove": [],
            "update": [],
        },
        summary=None,
        warnings=[],
    )
    conn = core_conn(repo_root)
    try:
        with use_overlay_payload(overlay):
            payload_text = classifier_call_graph_summary.render(
                snapshot_id, conn, repo_root, classifier_id=classifier_id, top_k=5
            )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["_overlay_applied_by_reducer"] is True
    assert payload["changed_edge_count"] >= 1
    assert payload["added_edge_count"] >= 1
    assert payload["outgoing"]
    assert payload["outgoing"][0]["delta_call_count"] == 1


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


def test_module_call_graph_summary_compact_mode_returns_previews(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    module_id = qualify_repo_name(repo_root, "pkg.alpha")
    conn = core_conn(repo_root)
    try:
        payload_text = module_call_graph_summary.render(
            snapshot_id,
            conn,
            repo_root,
            module_id=module_id,
            compact=True,
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["payload_kind"] == "compact_summary"
    assert payload["preview_limit"] == 10
    assert "outgoing" not in payload
    assert "incoming" not in payload
    assert payload["outgoing_preview"]["total"] == payload["outgoing_total"]
    assert payload["incoming_preview"]["total"] == payload["incoming_total"]


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


def test_classifier_call_graph_summary_compact_mode_returns_previews(tmp_path):
    repo_root, snapshot_id = seed_repo_with_snapshot(tmp_path)
    classifier_id = qualify_repo_name(repo_root, "pkg.alpha.Service")
    conn = core_conn(repo_root)
    try:
        payload_text = classifier_call_graph_summary.render(
            snapshot_id,
            conn,
            repo_root,
            classifier_id=classifier_id,
            compact=True,
        )
    finally:
        conn.close()
    payload = parse_json_payload(payload_text)
    assert payload["payload_kind"] == "compact_summary"
    assert payload["preview_limit"] == 10
    assert "outgoing" not in payload
    assert "incoming" not in payload
    assert payload["outgoing_preview"]["total"] == payload["outgoing_total"]
    assert payload["incoming_preview"]["total"] == payload["incoming_total"]
