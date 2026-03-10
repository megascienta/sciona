# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json
from pathlib import Path

from sciona.pipelines.reducers import emit
from sciona.reducers import overlay_projection_status_summary
from sciona.pipelines.diff_overlay.patchers.analytics import patch_callsite_index
from sciona.pipelines.diff_overlay.patchers.analytics import (
    patch_call_resolution_drop_summary,
    patch_call_resolution_quality,
    patch_classifier_call_graph_summary,
    patch_fan_summary,
    patch_module_call_graph_summary,
)
from sciona.pipelines.diff_overlay.patchers.core import (
    patch_file_outline,
    patch_symbol_lookup,
)
from sciona.pipelines.diff_overlay.patchers.core import patch_dependency_edges
from sciona.pipelines.diff_overlay.ops_get import _OVERLAY_PROFILE
from sciona.pipelines.diff_overlay.ops_patch import apply_overlay_to_payload_object
from sciona.pipelines.diff_overlay.types import OverlayPayload
from tests.helpers import core_conn, parse_json_payload, qualify_repo_name


def test_dirty_overlay_adds_node(repo_with_snapshot):
    repo_root, _snapshot_id = repo_with_snapshot
    service_path = repo_root / "pkg/alpha/service.py"
    service_path.write_text(
        "def helper():\n    return 1\n\n\ndef helper2():\n    return 2\n",
        encoding="utf-8",
    )

    text, _, _ = emit(
        "module_overview",
        repo_root=repo_root,
        module_id=qualify_repo_name(repo_root, "pkg.alpha"),
    )
    payload = parse_json_payload(text)
    diff = payload.get("_diff")
    assert diff, "Expected diff overlay in reducer payload"
    assert diff["version"] == 3
    assert diff["overlay_available"] is True
    assert diff["worktree_hash"]
    assert diff.get("affected") is True
    assert "nodes" in diff.get("affected_by", [])
    assert "projection_not_patched" not in (diff.get("warnings") or [])


def test_dirty_overlay_calls_and_summary(repo_with_snapshot):
    repo_root, _snapshot_id = repo_with_snapshot
    service_path = repo_root / "pkg/alpha/service.py"
    service_path.write_text(
        "def helper():\n    return 1\n\n\ndef caller():\n    return helper()\n",
        encoding="utf-8",
    )

    text, _, _ = emit(
        "fan_summary",
        repo_root=repo_root,
    )
    payload = parse_json_payload(text)
    diff = payload.get("_diff")
    assert diff, "Expected diff overlay in reducer payload"
    assert diff.get("affected") is True
    assert "calls" in diff.get("affected_by", [])


def test_dirty_overlay_callsite_index_applies_reducer_overlay(repo_with_snapshot):
    repo_root, _snapshot_id = repo_with_snapshot
    service_path = repo_root / "pkg/alpha/service.py"
    service_path.write_text(
        "def helper():\n    return helper()\n",
        encoding="utf-8",
    )

    text, _, _ = emit(
        "callsite_index",
        repo_root=repo_root,
        callable_id=qualify_repo_name(repo_root, "pkg.alpha.service.helper"),
    )
    payload = parse_json_payload(text)
    diff = payload.get("_diff")
    assert diff, "Expected diff overlay in reducer payload"
    assert diff.get("affected") is True
    assert "projection_not_patched" not in (diff.get("warnings") or [])
    assert any(
        edge.get("transition") == "dropped_to_accepted"
        for edge in payload.get("edges", [])
    )


def test_dirty_overlay_summary_mode(repo_with_snapshot):
    repo_root, _snapshot_id = repo_with_snapshot
    service_path = repo_root / "pkg/alpha/service.py"
    service_path.write_text(
        "def helper():\n    return 1\n\n\ndef helper3():\n    return 3\n",
        encoding="utf-8",
    )

    text, _, _ = emit(
        "module_overview",
        repo_root=repo_root,
        module_id=qualify_repo_name(repo_root, "pkg.alpha"),
        diff_mode="summary",
    )
    payload = parse_json_payload(text)
    diff = payload.get("_diff")
    assert diff, "Expected diff overlay in reducer payload"
    assert diff["overlay_available"] is True
    assert diff["worktree_hash"]
    assert diff.get("affected") is True
    assert "nodes" in diff.get("affected_by", [])


def test_apply_overlay_skips_duplicate_patch_when_reducer_already_applied():
    overlay = OverlayPayload(
        worktree_hash="hash",
        snapshot_commit="snap",
        base_commit="base",
        base_commit_strategy="head",
        head_commit="head",
        merge_base="merge",
        nodes={"add": [], "remove": []},
        edges={"add": [], "remove": []},
        calls={"add": [], "remove": []},
        summary=None,
        warnings=[],
    )
    payload = {
        "projection": "fan_summary",
        "_overlay_applied_by_reducer": True,
        "calls": {
            "total": 1,
            "committed_total": 1,
            "adjusted_total": 2,
            "delta_total": 1,
        },
    }

    patched = apply_overlay_to_payload_object(
        payload,
        overlay,
        repo_root=Path("."),
        snapshot_id="snap",
        conn=None,
        reducer_id="fan_summary",
    )

    assert "_overlay_applied_by_reducer" not in patched
    assert patched["calls"]["adjusted_total"] == 2
    assert patched["_diff"]["overlay_available"] is True
    assert "projection_not_patched" not in (patched["_diff"].get("warnings") or [])


def test_patch_dependency_edges_marks_overlay_added_and_removed():
    payload = {
        "module_filter": "pkg.alpha",
        "from_module_filter": None,
        "to_module_filter": None,
        "direction": "both",
        "edge_count": 1,
        "listed_edge_count": 1,
        "committed_count": 1,
        "overlay_added_count": 0,
        "overlay_removed_count": 0,
        "edges": [
            {
                "from_module_structural_id": "mod_alpha",
                "to_module_structural_id": "mod_beta",
                "from_module_qualified_name": "pkg.alpha",
                "to_module_qualified_name": "pkg.beta",
                "from_file_path": "pkg/alpha/__init__.py",
                "to_file_path": "pkg/beta/__init__.py",
                "edge_type": "IMPORTS_DECLARED",
                "edge_source": "sci",
                "row_origin": "committed",
            }
        ],
    }
    overlay = OverlayPayload(
        worktree_hash="hash",
        snapshot_commit="commit",
        base_commit="base",
        base_commit_strategy="snapshot",
        head_commit="head",
        merge_base=None,
        nodes={"add": [], "remove": [], "update": []},
        edges={
            "add": [
                {
                    "new_value": json.dumps(
                        {
                            "src_structural_id": "mod_alpha",
                            "dst_structural_id": "mod_gamma",
                            "src_qualified_name": "pkg.alpha",
                            "dst_qualified_name": "pkg.gamma",
                            "src_file_path": "pkg/alpha/__init__.py",
                            "dst_file_path": "pkg/gamma/__init__.py",
                            "edge_type": "IMPORTS_DECLARED",
                        }
                    )
                }
            ],
            "remove": [
                {
                    "old_value": json.dumps(
                        {
                            "src_structural_id": "mod_alpha",
                            "dst_structural_id": "mod_beta",
                            "src_qualified_name": "pkg.alpha",
                            "dst_qualified_name": "pkg.beta",
                            "src_file_path": "pkg/alpha/__init__.py",
                            "dst_file_path": "pkg/beta/__init__.py",
                            "edge_type": "IMPORTS_DECLARED",
                        }
                    )
                }
            ],
            "update": [],
        },
        calls={"add": [], "remove": [], "update": []},
        summary=None,
        warnings=[],
    )

    patched = patch_dependency_edges(payload, overlay)
    assert patched["edge_count"] == 1
    assert patched["listed_edge_count"] == 2
    assert patched["committed_count"] == 0
    assert patched["overlay_added_count"] == 1
    assert patched["overlay_removed_count"] == 1
    origins = {
        (edge["from_module_structural_id"], edge["to_module_structural_id"]): edge[
            "row_origin"
        ]
        for edge in patched["edges"]
    }
    assert origins[("mod_alpha", "mod_beta")] == "overlay_removed"
    assert origins[("mod_alpha", "mod_gamma")] == "overlay_added"


def test_patch_callsite_index_marks_edge_transitions(repo_with_snapshot):
    repo_root, snapshot_id = repo_with_snapshot
    payload = {
        "callable_id": "func_alpha",
        "direction": "both",
        "edge_count": 1,
        "edges": [
            {
                "caller_id": "func_alpha",
                "callee_id": "func_beta",
                "caller_qualified_name": "pkg.alpha.helper",
                "callee_qualified_name": "pkg.beta.worker",
                "caller_file_path": "pkg/alpha/service.py",
                "callee_file_path": "pkg/beta/worker.py",
                "caller_language": "python",
                "callee_language": "python",
                "caller_node_type": "callable",
                "callee_node_type": "callable",
                "caller_module_qualified_name": "pkg.alpha",
                "callee_module_qualified_name": "pkg.beta",
                "edge_kind": "CALLS",
                "edge_source": "artifact_db",
                "call_hash": None,
                "line_span": None,
                "row_origin": "committed",
                "transition": "unchanged",
            }
        ],
        "call_sites": [],
        "edge_transition_summary": {
            "unchanged": 1,
            "accepted_to_dropped": 0,
            "dropped_to_accepted": 0,
            "provenance_changed": 0,
        },
    }
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
                    "dst_structural_id": "func_gamma",
                    "src_node_type": "callable",
                    "dst_node_type": "callable",
                    "src_qualified_name": "pkg.alpha.helper",
                    "dst_qualified_name": "pkg.gamma.worker",
                    "src_file_path": "pkg/alpha/service.py",
                    "dst_file_path": "pkg/gamma/worker.py",
                }
            ],
            "remove": [
                {
                    "src_structural_id": "func_alpha",
                    "dst_structural_id": "func_beta",
                    "src_node_type": "callable",
                    "dst_node_type": "callable",
                    "src_qualified_name": "pkg.alpha.helper",
                    "dst_qualified_name": "pkg.beta.worker",
                    "src_file_path": "pkg/alpha/service.py",
                    "dst_file_path": "pkg/beta/worker.py",
                }
            ],
            "update": [],
        },
        summary=None,
        warnings=[],
    )
    conn = core_conn(repo_root)
    try:
        patched = patch_callsite_index(
            payload,
            overlay,
            snapshot_id=snapshot_id,
            conn=conn,
        )
    finally:
        conn.close()
    assert patched["edge_count"] == 1
    assert patched["edge_transition_summary"] == {
        "unchanged": 0,
        "accepted_to_dropped": 1,
        "dropped_to_accepted": 1,
        "provenance_changed": 0,
    }
    transitions = {
        (edge["caller_id"], edge["callee_id"]): edge["transition"]
        for edge in patched["edges"]
    }
    assert transitions[("func_alpha", "func_beta")] == "accepted_to_dropped"
    assert transitions[("func_alpha", "func_gamma")] == "dropped_to_accepted"


def test_patch_module_call_graph_summary_marks_edge_deltas(repo_with_snapshot):
    repo_root, snapshot_id = repo_with_snapshot
    payload = {
        "module_qualified_name": qualify_repo_name(repo_root, "pkg.alpha"),
        "module_structural_id": "mod_alpha",
        "top_k": None,
        "outgoing": [
            {
                "src_module_structural_id": "mod_alpha",
                "dst_module_structural_id": "mod_beta",
                "src_module_qualified_name": qualify_repo_name(repo_root, "pkg.alpha"),
                "dst_module_qualified_name": qualify_repo_name(repo_root, "pkg.beta"),
                "direction": "outgoing",
                "call_count": 1,
                "committed_call_count": 1,
                "overlay_call_count": 1,
                "delta_call_count": 0,
                "row_origin": "committed",
                "is_active": True,
            }
        ],
        "incoming": [],
        "outgoing_total": 1,
        "incoming_total": 0,
    }
    overlay = OverlayPayload(
        worktree_hash="hash",
        snapshot_commit="commit",
        base_commit="base",
        base_commit_strategy="snapshot",
        head_commit="head",
        merge_base=None,
        nodes={
            "add": [
                {
                    "new_value": json.dumps(
                        {
                            "structural_id": "func_beta",
                            "node_type": "callable",
                            "language": "python",
                            "qualified_name": qualify_repo_name(repo_root, "pkg.beta.worker.helper"),
                            "file_path": "pkg/beta/worker.py",
                        }
                    )
                }
            ],
            "remove": [],
            "update": [],
        },
        edges={"add": [], "remove": [], "update": []},
        calls={
            "add": [
                {
                    "src_structural_id": "func_alpha",
                    "dst_structural_id": "meth_alpha",
                    "src_node_type": "callable",
                    "dst_node_type": "callable",
                    "src_qualified_name": qualify_repo_name(repo_root, "pkg.alpha.service.helper"),
                    "dst_qualified_name": qualify_repo_name(repo_root, "pkg.alpha.Service.run"),
                    "src_file_path": "pkg/alpha/service.py",
                    "dst_file_path": "pkg/alpha/service.py",
                    "diff_kind": "add",
                }
            ],
            "remove": [
                    {
                        "src_structural_id": "func_alpha",
                        "dst_structural_id": "func_beta",
                        "src_node_type": "callable",
                        "dst_node_type": "callable",
                        "src_qualified_name": qualify_repo_name(repo_root, "pkg.alpha.service.helper"),
                        "dst_qualified_name": qualify_repo_name(repo_root, "pkg.beta.worker.helper"),
                        "src_file_path": "pkg/alpha/service.py",
                        "dst_file_path": "pkg/beta/worker.py",
                        "diff_kind": "remove",
                    }
                ],
            "update": [],
        },
        summary=None,
        warnings=[],
    )
    conn = core_conn(repo_root)
    try:
        patched = patch_module_call_graph_summary(
            payload,
            overlay,
            snapshot_id=snapshot_id,
            conn=conn,
        )
    finally:
        conn.close()
    assert patched["added_edge_count"] == 1
    assert patched["removed_edge_count"] == 1
    assert patched["changed_edge_count"] == 2
    origins = {
        (edge["src_module_structural_id"], edge["dst_module_structural_id"]): edge[
            "row_origin"
        ]
        for edge in patched["outgoing"]
    }
    assert origins[("mod_alpha", "mod_beta")] == "overlay_removed"
    assert origins[("mod_alpha", "mod_alpha")] == "overlay_added"


def test_patch_classifier_call_graph_summary_marks_edge_deltas(repo_with_snapshot):
    repo_root, snapshot_id = repo_with_snapshot
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
                12,
                "hash-cls-other",
            ),
        )
        conn.commit()
    finally:
        conn.close()
    payload = {
        "classifier_id": qualify_repo_name(repo_root, "pkg.alpha.Service"),
        "classifier_structural_id": "cls_alpha",
        "top_k": None,
        "outgoing": [
            {
                "src_classifier_id": "cls_alpha",
                "dst_classifier_id": "cls_other",
                "src_classifier_qualified_name": qualify_repo_name(repo_root, "pkg.alpha.Service"),
                "dst_classifier_qualified_name": qualify_repo_name(repo_root, "pkg.beta.Other"),
                "direction": "outgoing",
                "call_count": 1,
                "committed_call_count": 1,
                "overlay_call_count": 1,
                "delta_call_count": 0,
                "row_origin": "committed",
                "is_active": True,
            }
        ],
        "incoming": [],
        "outgoing_total": 1,
        "incoming_total": 0,
    }
    overlay = OverlayPayload(
        worktree_hash="hash",
        snapshot_commit="commit",
        base_commit="base",
        base_commit_strategy="snapshot",
        head_commit="head",
        merge_base=None,
        nodes={
            "add": [
                {
                    "new_value": json.dumps(
                        {
                            "structural_id": "meth_other",
                            "node_type": "callable",
                            "language": "python",
                            "qualified_name": qualify_repo_name(repo_root, "pkg.beta.Other.run"),
                            "file_path": "pkg/beta/other.py",
                        }
                    )
                }
            ],
            "remove": [],
            "update": [],
        },
        edges={"add": [], "remove": [], "update": []},
        calls={
            "add": [
                {
                    "src_structural_id": "meth_alpha",
                    "dst_structural_id": "meth_alpha",
                    "src_node_type": "callable",
                    "dst_node_type": "callable",
                    "src_qualified_name": qualify_repo_name(repo_root, "pkg.alpha.Service.run"),
                    "dst_qualified_name": qualify_repo_name(repo_root, "pkg.alpha.Service.run"),
                    "src_file_path": "pkg/alpha/service.py",
                    "dst_file_path": "pkg/alpha/service.py",
                    "diff_kind": "add",
                }
            ],
            "remove": [
                {
                    "src_structural_id": "meth_alpha",
                    "dst_structural_id": "meth_other",
                    "src_node_type": "callable",
                    "dst_node_type": "callable",
                    "src_qualified_name": qualify_repo_name(repo_root, "pkg.alpha.Service.run"),
                    "dst_qualified_name": qualify_repo_name(repo_root, "pkg.beta.Other.run"),
                    "src_file_path": "pkg/alpha/service.py",
                    "dst_file_path": "pkg/beta/other.py",
                    "diff_kind": "remove",
                }
            ],
            "update": [],
        },
        summary=None,
        warnings=[],
    )
    conn = core_conn(repo_root)
    try:
        patched = patch_classifier_call_graph_summary(
            payload,
            overlay,
            snapshot_id=snapshot_id,
            conn=conn,
        )
    finally:
        conn.close()
    assert patched["added_edge_count"] == 1
    assert patched["removed_edge_count"] == 1
    assert patched["changed_edge_count"] == 2
    origins = {
        (edge["src_classifier_id"], edge["dst_classifier_id"]): edge["row_origin"]
        for edge in patched["outgoing"]
    }
    assert origins[("cls_alpha", "cls_other")] == "overlay_removed"
    assert origins[("cls_alpha", "cls_alpha")] == "overlay_added"


def test_patch_call_resolution_quality_adjusts_overlay_totals(repo_with_snapshot):
    repo_root, snapshot_id = repo_with_snapshot
    payload = {
        "totals": {"eligible": 4, "accepted": 3, "dropped": 1, "acceptance_rate": 0.75},
        "committed_totals": {
            "eligible": 4,
            "accepted": 3,
            "dropped": 1,
            "acceptance_rate": 0.75,
        },
        "overlay_adjusted_totals": {
            "eligible": 4,
            "accepted": 3,
            "dropped": 1,
            "acceptance_rate": 0.75,
        },
        "overlay_delta_totals": {"eligible": 0, "accepted": 0, "dropped": 0},
        "overlay_transition_counts": {
            "accepted_to_dropped": 0,
            "dropped_to_accepted": 0,
        },
        "by_caller": [
            {
                "caller_id": "func_alpha",
                "qualified_name": qualify_repo_name(repo_root, "pkg.alpha.service.helper"),
                "language": "python",
                "module_qualified_name": qualify_repo_name(repo_root, "pkg.alpha"),
                "file_path": "pkg/alpha/service.py",
                "eligible": 4,
                "accepted": 3,
                "dropped": 1,
                "acceptance_rate": 0.75,
            }
        ],
    }
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
            "add": [{"src_structural_id": "func_alpha", "dst_structural_id": "meth_alpha"}],
            "remove": [{"src_structural_id": "func_alpha", "dst_structural_id": "meth_alpha"}],
            "update": [],
        },
        summary=None,
        warnings=[],
    )
    conn = core_conn(repo_root)
    try:
        patched = patch_call_resolution_quality(
            payload,
            overlay,
            snapshot_id=snapshot_id,
            conn=conn,
        )
    finally:
        conn.close()
    assert patched["overlay_transition_counts"] == {
        "accepted_to_dropped": 1,
        "dropped_to_accepted": 1,
    }
    assert patched["overlay_delta_totals"] == {
        "eligible": 0,
        "accepted": 0,
        "dropped": 0,
    }
    assert patched["overlay_adjusted_totals"]["accepted"] == 3
    assert patched["overlay_adjusted_totals"]["dropped"] == 1


def test_patch_call_resolution_drop_summary_adjusts_overlay_totals(repo_with_snapshot):
    repo_root, snapshot_id = repo_with_snapshot
    payload = {
        "limit": 10,
        "totals": {"eligible": 4, "accepted": 2, "dropped": 2, "drop_rate": 0.5},
        "committed_totals": {
            "eligible": 4,
            "accepted": 2,
            "dropped": 2,
            "drop_rate": 0.5,
        },
        "overlay_adjusted_totals": {
            "eligible": 4,
            "accepted": 2,
            "dropped": 2,
            "drop_rate": 0.5,
        },
        "overlay_delta_totals": {"eligible": 0, "accepted": 0, "dropped": 0},
        "overlay_transition_counts": {
            "accepted_to_dropped": 0,
            "dropped_to_accepted": 0,
        },
        "overlay_drop_reason_delta": [],
    }
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
            "add": [{"src_structural_id": "func_alpha", "dst_structural_id": "meth_alpha"}],
            "remove": [],
            "update": [],
        },
        summary=None,
        warnings=[],
    )
    conn = core_conn(repo_root)
    try:
        patched = patch_call_resolution_drop_summary(
            payload,
            overlay,
            snapshot_id=snapshot_id,
            conn=conn,
        )
    finally:
        conn.close()
    assert patched["overlay_transition_counts"] == {
        "accepted_to_dropped": 0,
        "dropped_to_accepted": 1,
    }
    assert patched["overlay_delta_totals"] == {
        "eligible": 0,
        "accepted": 1,
        "dropped": -1,
    }
    assert patched["overlay_adjusted_totals"]["accepted"] == 3
    assert patched["overlay_adjusted_totals"]["dropped"] == 1
    assert patched["overlay_drop_reason_delta"] == [
        {"name": "overlay_unclassified_resolution", "delta_count": -1}
    ]


def test_patch_file_outline_marks_overlay_row_origins():
    payload = {
        "file_path": None,
        "module_filter": None,
        "files": [
            {
                "file_path": "pkg/alpha/service.py",
                "language": "python",
                "nodes": [
                    {
                        "structural_id": "func_alpha",
                        "qualified_name": "pkg.alpha.service.helper",
                        "node_type": "callable",
                        "module_qualified_name": "pkg.alpha",
                        "line_span": [1, 2],
                        "row_origin": "committed",
                    }
                ],
            }
        ],
    }
    overlay = OverlayPayload(
        worktree_hash="hash",
        snapshot_commit="commit",
        base_commit="base",
        base_commit_strategy="snapshot",
        head_commit="head",
        merge_base=None,
        nodes={
            "add": [
                {
                    "new_value": json.dumps(
                        {
                            "structural_id": "meth_alpha",
                            "qualified_name": "pkg.alpha.Service.run",
                            "node_type": "callable",
                            "language": "python",
                            "file_path": "pkg/alpha/service.py",
                            "start_line": 5,
                            "end_line": 8,
                        }
                    )
                }
            ],
            "remove": [
                {
                    "old_value": json.dumps(
                        {
                            "structural_id": "func_alpha",
                            "qualified_name": "pkg.alpha.service.helper",
                            "node_type": "callable",
                            "language": "python",
                            "file_path": "pkg/alpha/service.py",
                            "start_line": 1,
                            "end_line": 2,
                        }
                    )
                }
            ],
            "update": [],
        },
        edges={"add": [], "remove": [], "update": []},
        calls={"add": [], "remove": [], "update": []},
        summary=None,
        warnings=[],
    )
    patched = patch_file_outline(payload, overlay)
    origins = {
        node["structural_id"]: node["row_origin"]
        for node in patched["files"][0]["nodes"]
    }
    assert origins["func_alpha"] == "overlay_removed"
    assert origins["meth_alpha"] == "overlay_added"


def test_patch_symbol_lookup_marks_overlay_match_status():
    payload = {
        "limit": 10,
        "matches": [
            {
                "structural_id": "func_alpha",
                "node_type": "callable",
                "language": "python",
                "qualified_name": "pkg.alpha.service.helper",
                "file_path": "pkg/alpha/service.py",
                "score": 0.9,
                "row_origin": "committed",
                "match_status": "active",
            }
        ],
    }
    overlay = OverlayPayload(
        worktree_hash="hash",
        snapshot_commit="commit",
        base_commit="base",
        base_commit_strategy="snapshot",
        head_commit="head",
        merge_base=None,
        nodes={
            "add": [
                {
                    "new_value": json.dumps(
                        {
                            "structural_id": "meth_alpha",
                            "node_type": "callable",
                            "language": "python",
                            "qualified_name": "pkg.alpha.Service.run",
                            "file_path": "pkg/alpha/service.py",
                        }
                    )
                }
            ],
            "remove": [
                {
                    "old_value": json.dumps(
                        {
                            "structural_id": "func_alpha",
                            "node_type": "callable",
                            "language": "python",
                            "qualified_name": "pkg.alpha.service.helper",
                            "file_path": "pkg/alpha/service.py",
                        }
                    )
                }
            ],
            "update": [],
        },
        edges={"add": [], "remove": [], "update": []},
        calls={"add": [], "remove": [], "update": []},
        summary=None,
        warnings=[],
    )
    patched = patch_symbol_lookup(payload, overlay)
    states = {
        row["structural_id"]: (row["row_origin"], row["match_status"])
        for row in patched["matches"]
    }
    assert states["func_alpha"] == ("overlay_removed", "stale")
    assert states["meth_alpha"] == ("overlay_added", "active")


def test_patch_fan_summary_adds_delta_counts(repo_with_snapshot):
    repo_root, snapshot_id = repo_with_snapshot
    payload = {
        "calls": {
            "total": 1,
            "committed_total": 1,
            "adjusted_total": 1,
            "delta_total": 0,
            "by_fan_in": [
                {
                    "node_id": "meth_alpha",
                    "qualified_name": qualify_repo_name(repo_root, "pkg.alpha.Service.run"),
                    "count": 1,
                    "committed_count": 1,
                    "adjusted_count": 1,
                    "delta_count": 0,
                }
            ],
            "by_fan_out": [
                {
                    "node_id": "func_alpha",
                    "qualified_name": qualify_repo_name(repo_root, "pkg.alpha.service.helper"),
                    "count": 1,
                    "committed_count": 1,
                    "adjusted_count": 1,
                    "delta_count": 0,
                }
            ],
        },
        "imports": {"total": 0, "committed_total": 0, "adjusted_total": 0, "delta_total": 0, "by_fan_in": [], "by_fan_out": []},
    }
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
            "add": [{"src_structural_id": "func_alpha", "dst_structural_id": "meth_alpha", "diff_kind": "add"}],
            "remove": [],
            "update": [],
        },
        summary=None,
        warnings=[],
    )
    conn = core_conn(repo_root)
    try:
        patched = patch_fan_summary(
            payload,
            overlay,
            snapshot_id=snapshot_id,
            conn=conn,
        )
    finally:
        conn.close()
    assert patched["calls"]["by_fan_in"][0]["delta_count"] == 1
    assert patched["calls"]["by_fan_out"][0]["delta_count"] == 1


def test_dirty_overlay_fan_summary_node_id_updates(repo_with_snapshot):
    repo_root, _snapshot_id = repo_with_snapshot
    service_path = repo_root / "pkg/alpha/service.py"
    service_path.write_text(
        "def helper():\n    return 1\n\n\ndef caller():\n    return helper()\n",
        encoding="utf-8",
    )

    text, _, _ = emit(
        "fan_summary",
        repo_root=repo_root,
        callable_id=qualify_repo_name(repo_root, "pkg.alpha.service.helper"),
    )
    payload = parse_json_payload(text)
    edge_kinds = payload.get("edge_kinds") or {}
    calls = edge_kinds.get("CALLS") or {}
    assert calls.get("fan_in") == 1


def test_dirty_overlay_hotspot_summary_size_updates(repo_with_snapshot):
    repo_root, _snapshot_id = repo_with_snapshot
    text, _, _ = emit(
        "hotspot_summary",
        repo_root=repo_root,
    )
    payload = parse_json_payload(text)
    baseline = {
        entry.get("module_qualified_name"): entry.get("count")
        for entry in payload.get("by_size", [])
    }

    service_path = repo_root / "pkg/alpha/service.py"
    service_path.write_text(
        "def helper():\n    return 1\n\n\ndef helper2():\n    return 2\n",
        encoding="utf-8",
    )

    text, _, _ = emit(
        "hotspot_summary",
        repo_root=repo_root,
    )
    payload = parse_json_payload(text)
    updated = {
        entry.get("module_qualified_name"): entry.get("count")
        for entry in payload.get("by_size", [])
    }
    module_id = qualify_repo_name(repo_root, "pkg.alpha")
    baseline_count = baseline.get(module_id) or 0
    assert updated.get(module_id) == baseline_count - 1


def test_non_indexed_dirty_does_not_attach_overlay_warning(repo_with_snapshot):
    repo_root, _snapshot_id = repo_with_snapshot
    (repo_root / "README.md").write_text("dirty docs\n", encoding="utf-8")

    text, _, _ = emit(
        "module_overview",
        repo_root=repo_root,
        module_id=qualify_repo_name(repo_root, "pkg.alpha"),
    )
    payload = parse_json_payload(text)
    assert payload.get("_diff") is None
    assert payload.get("snapshot_warning") is None


def test_out_of_scope_indexed_dirty_marks_diff_not_affected(repo_with_snapshot):
    repo_root, _snapshot_id = repo_with_snapshot
    (repo_root / "pkg/beta/__init__.py").write_text("x = 1\n", encoding="utf-8")

    text, _, _ = emit(
        "module_overview",
        repo_root=repo_root,
        module_id=qualify_repo_name(repo_root, "pkg.alpha"),
    )
    payload = parse_json_payload(text)
    diff = payload.get("_diff")
    assert diff, "Expected diff overlay in reducer payload"
    assert diff["overlay_available"] is True
    assert diff.get("affected") is False


def test_overlay_profile_support_matrix_includes_supported_and_metadata_only_cases():
    assert _OVERLAY_PROFILE["structural_index"]["supports_patch"] is True
    assert _OVERLAY_PROFILE["module_overview"]["supports_patch"] is True
    assert _OVERLAY_PROFILE["snapshot_provenance"]["supports_patch"] is False
    assert _OVERLAY_PROFILE["callable_source"]["supports_patch"] is False


def test_dirty_overlay_snapshot_provenance_marks_projection_not_supported(
    repo_with_snapshot,
):
    repo_root, _snapshot_id = repo_with_snapshot
    service_path = repo_root / "pkg/alpha/service.py"
    service_path.write_text(
        "def helper():\n    return 1\n\n\ndef helper2():\n    return 2\n",
        encoding="utf-8",
    )

    text, _, _ = emit(
        "snapshot_provenance",
        repo_root=repo_root,
    )
    payload = parse_json_payload(text)
    diff = payload.get("_diff")
    assert diff, "Expected diff overlay in reducer payload"
    assert diff["overlay_available"] is True
    assert diff.get("affected") is None
    warnings = diff.get("warnings") or []
    assert "projection_not_supported" in warnings
    assert "projection_not_patched" not in warnings
    warning = payload.get("snapshot_warning") or {}
    assert warning.get("code") == "DIRTY_OVERLAY_METADATA_ONLY"
    assert "committed-snapshot only" in str(warning.get("message") or "")


def test_overlay_projection_status_summary_reports_clean_worktree(
    repo_with_snapshot,
    monkeypatch,
):
    repo_root, snapshot_id = repo_with_snapshot
    monkeypatch.setattr(
        overlay_projection_status_summary.git_ops,
        "is_worktree_dirty",
        lambda _repo_root: False,
    )
    conn = core_conn(repo_root)
    try:
        payload = parse_json_payload(
            overlay_projection_status_summary.render(snapshot_id, conn, repo_root)
        )
    finally:
        conn.close()
    assert payload["payload_kind"] == "summary"
    assert payload["overlay_advisory"] is True
    assert payload["worktree_dirty"] is False
    assert payload["overlay_available"] is False
    assert payload["overlay_reason"] == "clean_worktree"
    projections = {row["projection"]: row for row in payload["projections"]}
    assert projections["structural_index"]["mode"] == "patchable"
    assert projections["structural_index"]["current_state"] == "committed_only"
    assert projections["snapshot_provenance"]["mode"] == "metadata_only"
    assert projections["snapshot_provenance"]["current_state"] == "committed_only"


def test_overlay_projection_status_summary_reports_dirty_overlay_modes(
    repo_with_snapshot,
):
    repo_root, snapshot_id = repo_with_snapshot
    service_path = repo_root / "pkg/alpha/service.py"
    service_path.write_text(
        "def helper():\n    return 1\n\n\ndef helper2():\n    return 2\n",
        encoding="utf-8",
    )
    text, _, _ = emit(
        "overlay_projection_status_summary",
        repo_root=repo_root,
    )
    payload = parse_json_payload(text)
    assert payload["worktree_dirty"] is True
    assert payload["overlay_available"] is True
    assert payload["overlay_reason"] == "available"
    assert payload["worktree_hash"]
    projections = {row["projection"]: row for row in payload["projections"]}
    assert projections["structural_index"]["current_state"] == "patchable"
    assert projections["snapshot_provenance"]["current_state"] == "metadata_only"


def test_overlay_projection_status_summary_reducer_rejects_stale_snapshot(
    repo_with_snapshot,
):
    repo_root, snapshot_id = repo_with_snapshot
    del snapshot_id
    conn = core_conn(repo_root)
    try:
        payload_text = overlay_projection_status_summary.render(
            "not-latest",
            conn,
            repo_root,
        )
    except ValueError as exc:
        assert "committed snapshot selected by build" in str(exc)
    else:
        raise AssertionError(payload_text)
    finally:
        conn.close()
