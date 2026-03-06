# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

from __future__ import annotations

import json

from sciona import api
from sciona.reducers import overlay_projection_status_summary
from sciona.pipelines.diff_overlay.patchers.core import patch_dependency_edges
from sciona.pipelines.diff_overlay.ops_get import _OVERLAY_PROFILE
from sciona.pipelines.diff_overlay.types import OverlayPayload
from tests.helpers import core_conn, parse_json_payload, qualify_repo_name


def test_dirty_overlay_adds_node(repo_with_snapshot):
    repo_root, _snapshot_id = repo_with_snapshot
    service_path = repo_root / "pkg/alpha/service.py"
    service_path.write_text(
        "def helper():\n    return 1\n\n\ndef helper2():\n    return 2\n",
        encoding="utf-8",
    )

    text, _, _ = api.addons.emit(
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

    text, _, _ = api.addons.emit(
        "fan_summary",
        repo_root=repo_root,
    )
    payload = parse_json_payload(text)
    diff = payload.get("_diff")
    assert diff, "Expected diff overlay in reducer payload"
    assert diff.get("affected") is True
    assert "calls" in diff.get("affected_by", [])


def test_dirty_overlay_summary_mode(repo_with_snapshot):
    repo_root, _snapshot_id = repo_with_snapshot
    service_path = repo_root / "pkg/alpha/service.py"
    service_path.write_text(
        "def helper():\n    return 1\n\n\ndef helper3():\n    return 3\n",
        encoding="utf-8",
    )

    text, _, _ = api.addons.emit(
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


def test_dirty_overlay_fan_summary_node_id_updates(repo_with_snapshot):
    repo_root, _snapshot_id = repo_with_snapshot
    service_path = repo_root / "pkg/alpha/service.py"
    service_path.write_text(
        "def helper():\n    return 1\n\n\ndef caller():\n    return helper()\n",
        encoding="utf-8",
    )

    text, _, _ = api.addons.emit(
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
    text, _, _ = api.addons.emit(
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

    text, _, _ = api.addons.emit(
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

    text, _, _ = api.addons.emit(
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

    text, _, _ = api.addons.emit(
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

    text, _, _ = api.addons.emit(
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
    text, _, _ = api.addons.emit(
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
